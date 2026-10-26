import { useState, useEffect } from "react";
const API = import.meta.env.VITE_API || "http://localhost:8000";

async function api(path, { method = "GET", body, form, token } = {}) {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(API + path, {
    method, headers, body: form ? new URLSearchParams(form) : body && JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail?.[0]?.msg || data.detail || "Request failed");
  return data;
}

const card = { background: "#fff", borderRadius: 12, padding: 16, boxShadow: "0 1px 4px #0002", flex: 1 };
const btn = { padding: "6px 12px", borderRadius: 6, border: 0, background: "#4f46e5", color: "#fff", cursor: "pointer" };
const inp = { padding: 6, margin: 4, borderRadius: 6, border: "1px solid #ccc" };

function Login({ onLogin }) {
  const [f, setF] = useState({ email: "", password: "" });
  const [err, setErr] = useState("");
  const go = async (reg) => {
    try {
      if (reg) await api("/auth/register", { method: "POST", body: f });
      onLogin(await api("/auth/login", { method: "POST", form: { username: f.email, password: f.password } }));
    } catch (e) { setErr(e.message); }
  };
  return (
    <div style={{ ...card, maxWidth: 320, margin: "80px auto" }}>
      <h2 style={{ color: "#4338ca" }}>Onboarding Management</h2>
      <input style={inp} placeholder="Email" onChange={(e) => setF({ ...f, email: e.target.value })} />
      <input style={inp} type="password" placeholder="Password" onChange={(e) => setF({ ...f, password: e.target.value })} />
      <div><button style={btn} onClick={() => go(false)}>Login</button>{" "}
        <button style={{ ...btn, background: "#64748b" }} onClick={() => go(true)}>Register</button></div>
      <p style={{ color: "crimson" }}>{err}</p>
    </div>
  );
}

function Dashboard({ token }) {
  const [d, setD] = useState(null);
  useEffect(() => { api("/dashboard", { token }).then(setD); }, []);
  if (!d) return <p>Loading…</p>;
  const stat = (label, v, c) => <div style={card}><small>{label}</small><h1 style={{ color: c }}>{v}</h1></div>;
  return (<>
    <div style={{ display: "flex", gap: 12 }}>
      {stat("Total Employees", d.total_employees, "#4f46e5")}
      {stat("Completed Tasks", d.tasks.done, "#16a34a")}
      {stat("In Progress", d.tasks.in_progress, "#2563eb")}
      {stat("Overdue", d.overdue, "#dc2626")}
    </div>
    <h3>Onboarding progress</h3>
    {d.progress.map((p) => (
      <div key={p.assignee} style={{ margin: "6px 0" }}>
        {p.assignee} — {p.done}/{p.total}
        <div style={{ background: "#e5e7eb", borderRadius: 6 }}>
          <div style={{ width: `${p.pct}%`, background: p.pct < 50 ? "#f59e0b" : "#16a34a", height: 8, borderRadius: 6 }} />
        </div>
      </div>))}
  </>);
}

function Employees({ token }) {
  const [list, setList] = useState([]);
  const [f, setF] = useState({ name: "", email: "", department: "", title: "" });
  const [hist, setHist] = useState(null);
  const load = () => api("/employees", { token }).then(setList);
  useEffect(() => { load(); }, []);
  const add = async () => { await api("/employees", { method: "POST", body: f, token }); load(); };
  const audit = async (id) => setHist(await api(`/employees/${id}/audit`, { token }));
  return (<>
    {Object.keys(f).map((k) => <input key={k} style={inp} placeholder={k} onChange={(e) => setF({ ...f, [k]: e.target.value })} />)}
    <button style={btn} onClick={add}>Add employee</button>
    <table width="100%" style={{ marginTop: 12 }}><tbody>
      {list.map((e) => (<tr key={e.id}><td>{e.name}</td><td>{e.email}</td><td>{e.department}</td><td>{e.title}</td>
        <td><button style={btn} onClick={() => audit(e.id)}>History</button></td></tr>))}
    </tbody></table>
    {hist && <div style={card}><h4>Audit history</h4>
      {hist.map((h) => <div key={h.id}><small>{h.at.slice(0, 16)}</small> {h.actor} — <b>{h.action}</b> {JSON.stringify(h.changes)}</div>)}</div>}
  </>);
}

function Tasks({ token, role }) {
  const [list, setList] = useState([]);
  const [f, setF] = useState({ title: "", assignee: "", due: "" });
  const load = () => api("/tasks", { token }).then(setList);
  useEffect(() => { load(); }, []);
  const add = async () => { await api("/tasks", { method: "POST", body: f, token }); load(); };
  const set = async (id, status) => { await api(`/tasks/${id}/status`, { method: "PATCH", body: { status }, token }); load(); };
  return (<>
    {role === "admin" && <div>
      <input style={inp} placeholder="title" onChange={(e) => setF({ ...f, title: e.target.value })} />
      <input style={inp} placeholder="assignee email" onChange={(e) => setF({ ...f, assignee: e.target.value })} />
      <input style={inp} type="date" onChange={(e) => setF({ ...f, due: e.target.value })} />
      <button style={btn} onClick={add}>Assign task</button></div>}
    {list.map((t) => (<div key={t.id} style={{ ...card, margin: "8px 0" }}>
      <b>{t.title}</b> · {t.assignee} · due {t.due} · <i>{t.status}</i>{" "}
      {["pending", "in_progress", "done"].map((s) => <button key={s} style={{ ...btn, margin: 2, background: t.status === s ? "#16a34a" : "#94a3b8" }} onClick={() => set(t.id, s)}>{s}</button>)}
    </div>))}
  </>);
}

export default function App() {
  const [auth, setAuth] = useState(null);
  const [tab, setTab] = useState("tasks");
  if (!auth) return <Login onLogin={(a) => { setAuth(a); setTab(a.role === "admin" ? "dashboard" : "tasks"); }} />;
  const tabs = auth.role === "admin" ? ["dashboard", "employees", "tasks"] : ["tasks"];
  return (
    <div style={{ fontFamily: "system-ui", background: "#f1f5f9", minHeight: "100vh", padding: 24 }}>
      <h2 style={{ color: "#4338ca" }}>Onboarding Management <small style={{ color: "#64748b" }}>({auth.email} · {auth.role})</small>
        <button style={{ ...btn, float: "right" }} onClick={() => setAuth(null)}>Logout</button></h2>
      {tabs.map((t) => <button key={t} style={{ ...btn, margin: 4, background: tab === t ? "#4f46e5" : "#94a3b8" }} onClick={() => setTab(t)}>{t}</button>)}
      <div style={{ marginTop: 16 }}>
        {tab === "dashboard" && <Dashboard token={auth.access_token} />}
        {tab === "employees" && <Employees token={auth.access_token} />}
        {tab === "tasks" && <Tasks token={auth.access_token} role={auth.role} />}
      </div>
    </div>);
}
