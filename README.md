# Employee Onboarding & HR Workflow Management System

A full-stack web application that helps HR teams manage employee records and track new-hire onboarding. HR admins create employees, assign onboarding tasks and monitor progress on a dashboard, while employees log in to see and update only their own tasks. Every change to an employee record is saved in an audit history.

**Tech stack:** React (Vite) · FastAPI · MongoDB Atlas · Pydantic · JWT

> **Live demo:** _add your deployed link here_
> **API docs:** _add your deployed backend URL_`/docs`

---

## Screenshots

| Dashboard | Tasks |
|---|---|
| ![Dashboard](screenshots/dashboard.png) | ![Tasks](screenshots/tasks.png) |

| Audit history | API docs |
|---|---|
| ![Audit history](screenshots/audit.png) | ![API docs](screenshots/api-docs.png) |

---

## Features

- **Authentication:** JWT login with bcrypt password hashing and token expiry
- **Role-based access control:** HR admins manage everything; employees can only view and update their own tasks
- **Employee and department records:** create, list, filter and update profiles
- **Onboarding workflow:** assign tasks with due dates and move them through `pending`, `in_progress` and `done`
- **Dashboard:** totals, completed, in-progress and overdue counts, plus per-employee completion percentage, all computed with MongoDB aggregation pipelines
- **Audit history:** every create, update, task assignment and status change is logged with who did it, what changed (old and new values) and when
- **Validated REST API:** Pydantic models validate all input, and interactive documentation is generated automatically at `/docs`

---

## Architecture

```
React (Vite)  ──HTTP/JSON──▶  FastAPI REST API  ──PyMongo──▶  MongoDB Atlas
   │                              │
   └── stores JWT in memory       ├── JWT verification + role checks
                                  ├── Pydantic validation
                                  └── Audit logging
```

### Project structure

```
onboarding-hr/
├── backend/
│   ├── main.py              # API routes, models, auth, aggregation
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Login, dashboard, employees, tasks
│   │   └── main.jsx
│   ├── index.html
│   └── package.json
└── README.md
```

---

## Database design

MongoDB database `onboarding` with these collections:

| Collection | Purpose | Key fields | Indexes |
|---|---|---|---|
| `users` | Login accounts | `email`, `password` (hashed), `role` | unique `email` |
| `employees` | Employee profiles | `name`, `email`, `department`, `title`, `start_date` | unique `email` |
| `departments` | Department records | `name` | unique `name` |
| `tasks` | Onboarding tasks | `title`, `assignee`, `due`, `status` | compound `assignee + status` |
| `audit` | Change history | `employee_id`, `actor`, `action`, `changes`, `at` | compound `employee_id + at` |

### Example aggregation (dashboard progress)

```python
db.tasks.aggregate([
    {"$group": {"_id": "$assignee",
                "total": {"$sum": 1},
                "done": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}}}},
    {"$project": {"assignee": "$_id", "total": 1, "done": 1,
                  "pct": {"$round": [{"$multiply": [{"$divide": ["$done", "$total"]}, 100]}, 0]}}},
    {"$sort": {"pct": 1}}
])
```

---

## API reference

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Create an account (first user becomes admin) |
| POST | `/auth/login` | Public | Returns a JWT access token |
| GET | `/departments` | Any user | List departments |
| POST | `/departments` | Admin | Create a department |
| GET | `/employees` | Admin | List employees (optional `?department=`) |
| POST | `/employees` | Admin | Create an employee (audit logged) |
| PUT | `/employees/{id}` | Admin | Update an employee (changes diffed and logged) |
| GET | `/employees/{id}/audit` | Admin | View an employee's audit history |
| GET | `/tasks` | Any user | Admins see all tasks; employees see only their own |
| POST | `/tasks` | Admin | Assign an onboarding task |
| PATCH | `/tasks/{id}/status` | Admin or assignee | Update task status |
| GET | `/dashboard` | Admin | Aggregated onboarding statistics |

Full interactive documentation is available at `http://localhost:8000/docs`.

---

## Getting started

### Prerequisites
- Python 3.10+
- Node.js 18+
- A free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster (or a local MongoDB)

### 1. Clone the repository
```bash
git clone https://github.com/YOUR-USERNAME/onboarding-hr-system.git
cd onboarding-hr-system
```

### 2. Run the backend
```bash
cd backend
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill it in:

```
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net
DB_NAME=onboarding
JWT_SECRET=use-a-long-random-string
```

Start the server:
```bash
python -m uvicorn main:app --reload
```
The API runs at `http://localhost:8000`.

### 3. Run the frontend
```bash
cd frontend
npm install
npm run dev
```
The app runs at `http://localhost:5173`. To point it at a different API, set `VITE_API` in `frontend/.env`.

### 4. Try it out
1. Register an account. **The first account becomes the HR admin.**
2. Open the **employees** tab and add an employee.
3. Open the **tasks** tab and assign onboarding tasks to that employee's email.
4. Register a second account using the employee's email to see the employee view.
5. Return to the admin account to see the dashboard and audit history update.

---

## Security notes

- Passwords are hashed with bcrypt and never stored in plain text
- JWTs expire after 8 hours and are verified on every protected route
- Role checks happen on the server, so hiding buttons in the UI is never the only protection
- Secrets live in `.env`, which is excluded from Git
- Before deploying, restrict CORS (`allow_origins`) to your frontend URL and use a strong `JWT_SECRET`

---

## Roadmap

- [ ] Automated tests with pytest
- [ ] Docker setup and deployment (Render + Vercel)
- [ ] Task templates and bulk assignment
- [ ] Pagination and search on employee lists
- [ ] Email notifications for overdue tasks
- [ ] Rate limiting on login

---

## What I learned

- Designing MongoDB collections and indexes around real query patterns
- Building MongoDB aggregation pipelines for reporting
- Implementing JWT authentication and server-side role-based authorization
- Validating API input with Pydantic and structuring a REST API in FastAPI
- Recording audit trails by diffing old and new document values

---

## Author

**Your Name** · [GitHub](https://github.com/YOUR-USERNAME) · [LinkedIn](https://linkedin.com/in/YOUR-PROFILE)