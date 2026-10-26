import os, datetime as dt
from typing import Optional, Literal
import bcrypt, jwt
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient, ASCENDING

load_dotenv()
db = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))[os.getenv("DB_NAME", "onboarding")]
SECRET = os.getenv("JWT_SECRET", "change-me")

# Indexes: uniqueness + common query paths
db.users.create_index("email", unique=True)
db.employees.create_index("email", unique=True)
db.departments.create_index("name", unique=True)
db.tasks.create_index([("assignee", ASCENDING), ("status", ASCENDING)])
db.audit.create_index([("employee_id", ASCENDING), ("at", -1)])

app = FastAPI(title="Employee Onboarding & HR Workflow API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")

# ---------- Pydantic schemas ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    role: Literal["admin", "employee"] = "employee"

class DepartmentIn(BaseModel):
    name: str

class EmployeeIn(BaseModel):
    name: str
    email: EmailStr
    department: str
    title: str
    start_date: Optional[str] = None

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None

class TaskIn(BaseModel):
    title: str
    assignee: EmailStr
    due: str  # ISO date, e.g. 2026-11-15

class StatusIn(BaseModel):
    status: Literal["pending", "in_progress", "done"]

# ---------- helpers ----------
def ser(d):
    d["id"] = str(d.pop("_id"))
    return d

def oid(s):
    try: return ObjectId(s)
    except Exception: raise HTTPException(400, "Invalid id")

def now(): return dt.datetime.utcnow().isoformat()

def audit(employee_id, actor, action, changes=None):
    db.audit.insert_one({"employee_id": employee_id, "actor": actor, "action": action,
                         "changes": changes or {}, "at": now()})

def current_user(token: str = Depends(oauth2)):
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")

def admin_only(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "HR admin access required")
    return user

# ---------- auth ----------
@app.post("/auth/register")
def register(body: RegisterIn):
    # First account becomes admin so the app can be bootstrapped
    role = "admin" if db.users.count_documents({}) == 0 else "employee"
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt())
    try:
        db.users.insert_one({"email": body.email, "password": hashed, "role": role})
    except Exception:
        raise HTTPException(409, "Email already registered")
    return {"email": body.email, "role": role}

@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    u = db.users.find_one({"email": form.username})
    if not u or not bcrypt.checkpw(form.password.encode(), u["password"]):
        raise HTTPException(401, "Incorrect email or password")
    exp = dt.datetime.utcnow() + dt.timedelta(hours=8)
    token = jwt.encode({"sub": u["email"], "role": u["role"], "exp": exp}, SECRET, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "role": u["role"], "email": u["email"]}

# ---------- departments ----------
@app.post("/departments", status_code=201)
def add_department(body: DepartmentIn, user=Depends(admin_only)):
    try: r = db.departments.insert_one({"name": body.name})
    except Exception: raise HTTPException(409, "Department exists")
    return {"id": str(r.inserted_id), "name": body.name}

@app.get("/departments")
def list_departments(user=Depends(current_user)):
    return [ser(d) for d in db.departments.find()]

# ---------- employees (+ audit history) ----------
@app.post("/employees", status_code=201)
def create_employee(body: EmployeeIn, user=Depends(admin_only)):
    doc = body.model_dump() | {"created_at": now()}
    try: r = db.employees.insert_one(doc)
    except Exception: raise HTTPException(409, "Employee email exists")
    audit(str(r.inserted_id), user["sub"], "created", body.model_dump())
    return {"id": str(r.inserted_id)}

@app.get("/employees")
def list_employees(department: Optional[str] = None, user=Depends(admin_only)):
    q = {"department": department} if department else {}
    return [ser(e) for e in db.employees.find(q)]

@app.put("/employees/{emp_id}")
def update_employee(emp_id: str, body: EmployeeUpdate, user=Depends(admin_only)):
    old = db.employees.find_one({"_id": oid(emp_id)})
    if not old: raise HTTPException(404, "Employee not found")
    new = body.model_dump(exclude_none=True)
    changes = {k: {"from": old.get(k), "to": v} for k, v in new.items() if old.get(k) != v}
    if changes:
        db.employees.update_one({"_id": old["_id"]}, {"$set": new})
        audit(emp_id, user["sub"], "updated", changes)
    return {"changed": list(changes)}

@app.get("/employees/{emp_id}/audit")
def employee_audit(emp_id: str, user=Depends(admin_only)):
    return [ser(a) for a in db.audit.find({"employee_id": emp_id}).sort("at", -1)]

# ---------- onboarding tasks / workflow ----------
@app.post("/tasks", status_code=201)
def assign_task(body: TaskIn, user=Depends(admin_only)):
    emp = db.employees.find_one({"email": body.assignee})
    if not emp: raise HTTPException(404, "Assignee is not an employee")
    r = db.tasks.insert_one(body.model_dump() | {"status": "pending", "created_at": now()})
    audit(str(emp["_id"]), user["sub"], "task_assigned", {"title": body.title})
    return {"id": str(r.inserted_id)}

@app.get("/tasks")
def list_tasks(user=Depends(current_user)):
    q = {} if user["role"] == "admin" else {"assignee": user["sub"]}  # role-based scoping
    return [ser(t) for t in db.tasks.find(q).sort("due", 1)]

@app.patch("/tasks/{task_id}/status")
def set_status(task_id: str, body: StatusIn, user=Depends(current_user)):
    t = db.tasks.find_one({"_id": oid(task_id)})
    if not t: raise HTTPException(404, "Task not found")
    if user["role"] != "admin" and t["assignee"] != user["sub"]:
        raise HTTPException(403, "Not your task")
    db.tasks.update_one({"_id": t["_id"]}, {"$set": {"status": body.status}})
    emp = db.employees.find_one({"email": t["assignee"]})
    if emp: audit(str(emp["_id"]), user["sub"], "task_status", {"task": t["title"], "status": body.status})
    return {"status": body.status}

# ---------- dashboard (aggregation) ----------
@app.get("/dashboard")
def dashboard(user=Depends(admin_only)):
    today = dt.date.today().isoformat()
    by_status = {r["_id"]: r["n"] for r in db.tasks.aggregate(
        [{"$group": {"_id": "$status", "n": {"$sum": 1}}}])}
    overdue = db.tasks.count_documents({"status": {"$ne": "done"}, "due": {"$lt": today}})
    per_emp = list(db.tasks.aggregate([
        {"$group": {"_id": "$assignee", "total": {"$sum": 1},
                    "done": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}}}},
        {"$project": {"_id": 0, "assignee": "$_id", "total": 1, "done": 1,
                      "pct": {"$round": [{"$multiply": [{"$divide": ["$done", "$total"]}, 100]}, 0]}}},
        {"$sort": {"pct": 1}}]))
    return {"total_employees": db.employees.count_documents({}),
            "tasks": {"pending": by_status.get("pending", 0),
                      "in_progress": by_status.get("in_progress", 0),
                      "done": by_status.get("done", 0)},
            "overdue": overdue, "progress": per_emp}
