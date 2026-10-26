# Employee Onboarding & HR Workflow Management System
**Stack:** React (Vite), FastAPI, MongoDB Atlas, Pydantic, JWT

## Features
- Employee profiles and departments
- Onboarding task assignment and workflow status (pending / in_progress / done)
- Role-based access (HR admin vs employee)
- REST APIs with Pydantic validation, interactive docs at `/docs`
- Dashboard built on MongoDB aggregation pipelines (completion %, overdue tasks)
- Audit history of every change to employee records

## Run
Backend:
    cd backend && python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # add your Atlas URI + JWT secret
    uvicorn main:app --reload

Frontend:
    cd frontend && npm install && npm run dev

The first registered account becomes the HR admin; later ones are employees.
To see an employee's tasks, create an employee record with the same email they registered with.
