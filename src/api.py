"""UI + API: open http://localhost:8000/ in browser.
- Search form -> GET /search (lookup, no Telegram)
- Send to Telegram -> POST /notify (lookup + push)
- Auto-alerts -> saved to config.yaml, checked every POLL_SECONDS while server runs
"""
import asyncio
import os
import httpx
import yaml
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from .filtering import matches
from .models import Job
from .notifier import TelegramNotifier, format_job
from .sources.arbeitnow import ArbeitnowSource
from .sources.remotive import RemotiveSource
from .sources.remoteok import RemoteOKSource
from .sources.adzuna import AdzunaSource
from .sources.jsearch import JSearchSource
from .sources.serpapi import SerpAPIJobsSource
from .sources.company_boards import GreenhouseSource, LeverSource

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # auto-watch while UI server runs — same as `watch` mode
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from .watcher import check_once
    secs = int(os.getenv("POLL_SECONDS", "600"))
    sched = AsyncIOScheduler()
    sched.add_job(check_once, "interval", seconds=secs, kwargs={"config_path": "config.yaml", "db_path": "seen.db", "notify": True})
    sched.start()
    print(f"[auto] watching every {secs}s while UI runs")
    yield
    sched.shutdown()

app = FastAPI(title="job-alerts", lifespan=lifespan)

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job Alerts</title>
<style>
:root{--bg:#0f172a;--card:#ffffff;--muted:#64748b;--accent:#2563eb;--accent2:#7c3aed;--ok:#059669}
*{box-sizing:border-box}body{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f1f5f9;color:#0f172a}
.hero{background:linear-gradient(135deg,var(--bg),#1e3a8a 60%,var(--accent2));color:#fff;padding:28px 24px}
.hero h1{margin:0;font-size:26px}.hero p{margin:6px 0 0;opacity:.85}
.wrap{max-width:920px;margin:-18px auto 40px;padding:0 16px}
.panel{background:var(--card);border-radius:16px;box-shadow:0 8px 30px rgba(15,23,42,.12);padding:20px;margin-bottom:16px}
label{font-size:13px;color:var(--muted);font-weight:600}
input[type=text],input:not([type]),select{width:100%;padding:10px 12px;margin:6px 0 12px;border:1px solid #e2e8f0;border-radius:10px;font-size:15px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.btns{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:4px}
button{border:0;border-radius:10px;padding:10px 16px;font-size:15px;cursor:pointer;font-weight:600}
.btn-primary{background:var(--accent);color:#fff}.btn-primary:hover{filter:brightness(.95)}
.btn-telegram{background:#229ED9;color:#fff}.btn-ghost{background:#eef2ff;color:#1e293b}
#status{font-size:14px;color:var(--muted);margin-left:6px}
#out{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-top:12px}
.card{background:#fff;border:1px solid #e2e8f0;padding:14px;border-radius:14px;box-shadow:0 2px 10px rgba(15,23,42,.06)}
.card b{font-size:15px}.card small{color:var(--muted)}
.badge{display:inline-block;font-size:12px;background:#eef2ff;color:#3730a3;padding:2px 8px;border-radius:999px;margin-top:6px}
.apply{display:inline-block;margin-top:10px;background:var(--ok);color:#fff;padding:8px 12px;border-radius:9px;text-decoration:none;font-weight:700}
.switch{display:flex;align-items:center;gap:8px;font-size:14px;color:#0f172a}
@media(max-width:640px){.row{grid-template-columns:1fr}}</style></head><body>
<div class="hero"><h1>🔔 Job Alerts</h1><p>Search roles across free boards + Adzuna India, send hits to Telegram.</p></div>
<div class="wrap">
<div class="panel">
<h2 style="margin:0 0 8px">New search</h2>
<div class="row">
<div><label>Role / keywords (comma separated)</label><input id="role" value="" placeholder="e.g. technical support, SOC analyst"></div>
<div><label>Location (comma separated, empty = any)</label><input id="loc" value="" placeholder="e.g. Noida, Gurgaon, Delhi"></div>
</div>
<div class="row">
<div><label>Company (optional — e.g. Paytm, Deloitte)</label><input id="company" value="" placeholder="empty = all companies"></div>
<div class="row">
<div><label class="switch"><input type="checkbox" id="remote"> remote only</label></div>
<div><label>Limit</label><select id="limit"><option>5</option><option selected>10</option><option>20</option></select></div>
</div>
<div class="btns">
<button class="btn-primary" onclick="doSearch()">Lookup</button>
<button class="btn-telegram" onclick="doNotify()">Lookup + Send to Telegram</button>
<span id="status"></span>
</div>
<div id="out"></div>
</div>
<div class="panel">
<h3 style="margin:0 0 8px">Auto-alerts <small style="font-weight:400">— checked automatically while this server runs</small></h3>
<label>Alert name</label><input id="aname" value="" placeholder="e.g. my-ncr-jobs">
<div class="btns">
<button class="btn-ghost" onclick="saveAlert()">Save current as auto-alert</button>
<button class="btn-ghost" onclick="loadAlerts()">Refresh</button>
</div>
<div id="alerts" style="margin-top:12px;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px"></div>
<script>
async function doSearch(){
  const q=document.getElementById('role').value;
  if(!q.trim()){setStatus('type a role first');return;}
  const loc=document.getElementById('loc').value;
  const company=document.getElementById('company').value;
  const remote=document.getElementById('remote').checked;
  const limit=document.getElementById('limit').value;
  setStatus('searching...');
  const r=await fetch(`/search?q=${encodeURIComponent(q)}&location=${encodeURIComponent(loc)}&company=${encodeURIComponent(company)}&remote_only=${remote}&limit=${limit}`);
  const j=await r.json();
  setStatus(`found ${j.count}`);
  render(j.jobs);
}
async function doNotify(){
  const keywords=document.getElementById('role').value.split(',').map(s=>s.trim()).filter(Boolean);
  if(!keywords.length){setStatus('type a role first');return;}
  const company=document.getElementById('company').value.trim();
  const location=document.getElementById('loc').value.split(',').map(s=>s.trim()).filter(Boolean);
  const remote_only=document.getElementById('remote').checked;
  const limit=parseInt(document.getElementById('limit').value);
  setStatus('sending to Telegram...');
  const r=await fetch('/notify',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({keywords,location,remote_only,limit,company})});
  const j=await r.json();
  setStatus(`sent ${j.sent} to Telegram`);
  render(j.jobs||[]);
}
function setStatus(t){document.getElementById('status').textContent=t;}
function render(jobs){
  const out=document.getElementById('out'); out.innerHTML='';
  if(!jobs || !jobs.length){out.innerHTML='<small>No matches — try broader keywords or multi-location like Noida, Gurgaon, Delhi.</small>';return;}
  jobs.forEach(j=>{
    const d=document.createElement('div'); d.className='card';
    d.innerHTML=`<b>${esc(j.title)}</b><br><small>${esc(j.company||'')} | ${esc(j.location||'')}</small><br><span class="badge">${esc(j.source||'')}</span><br><a class="apply" href="${j.url}" target="_blank">Apply →</a>`;
    out.appendChild(d);
  });
}
function esc(s){return String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
async function saveAlert(){
  const name=document.getElementById('aname').value.trim()||'my-alert';
  const keywords=document.getElementById('role').value.split(',').map(s=>s.trim()).filter(Boolean);
  if(!keywords.length){setStatus('type a role first');return;}
  const company=document.getElementById('company').value.trim();
  const location=document.getElementById('loc').value.split(',').map(s=>s.trim()).filter(Boolean);
  const remote_only=document.getElementById('remote').checked;
  setStatus('saving auto-alert...');
  const r=await fetch('/alerts',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name,keywords,location,remote_only,company})});
  const j=await r.json();
  setStatus(`auto-alert saved (${j.queries.length} total)`);
  loadAlerts();
}
async function loadAlerts(){
  const r=await fetch('/config'); const j=await r.json();
  const box=document.getElementById('alerts'); box.innerHTML='';
  (j.queries||[]).forEach(q=>{
    const d=document.createElement('div'); d.className='card';
    d.innerHTML=`<b>${esc(q.name)}</b><br><small>${esc((q.keywords||[]).join(', '))} | ${esc([].concat(q.location||[]).join(', '))} | remote=${q.remote_only}</small><br><button class="btn-ghost" onclick="delAlert('${esc(q.name)}')">delete</button>`;
    box.appendChild(d);
  });
}
async function delAlert(name){
  await fetch('/alerts/'+encodeURIComponent(name),{method:'DELETE'});
  loadAlerts();
}
loadAlerts();
</script></div></body></html>"""

def _sources():
    # manual UI search includes SerpAPI (user-triggered, quota-safe)
    return [ArbeitnowSource(), RemotiveSource(), RemoteOKSource(), AdzunaSource(), JSearchSource(), SerpAPIJobsSource(), GreenhouseSource(), LeverSource()]

import time
_CACHE = {"ts": 0.0, "jobs": []}
CACHE_TTL = int(os.getenv("SEARCH_CACHE_SECONDS", "300"))

async def _fetch_one(client, src):
    try:
        return await src.fetch(client)
    except Exception as e:
        print(f"[warn] {src.name}: {e}")
        return []

async def _fetch_all(client, max_age: int = CACHE_TTL) -> list:
    global _CACHE
    now = time.time()
    if _CACHE["jobs"] and (now - _CACHE["ts"]) < max_age:
        return _CACHE["jobs"]
    parts = await asyncio.gather(*[_fetch_one(client, s) for s in _sources()])
    jobs = [j for sub in parts for j in sub]
    _CACHE = {"ts": now, "jobs": jobs}
    return jobs

def _split(v: str) -> list[str]:
    # "a, b" -> ["a","b"]; single value stays single
    return [x.strip() for x in (v or "").split(",") if x.strip()]

@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/config")
def get_config():
    import yaml
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

@app.get("/search")
async def search(
    q: str = Query(""),
    location: str = Query(""),
    company: str = Query(""),
    remote_only: bool = Query(False),
    limit: int = Query(10, le=50),
):
    keywords = _split(q)
    if not keywords:
        return {"count": 0, "jobs": []}
    locs = _split(location)
    loc_arg = locs if len(locs) > 1 else (locs[0] if locs else "")
    headers = {"User-Agent": "job-alerts-opensource/1.0"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        all_jobs = await _fetch_all(client)
    matched = [j for j in all_jobs if matches(j, keywords, loc_arg, remote_only, [], company.strip())][:limit]
    return {"count": len(matched), "jobs": [j.__dict__ for j in matched]}

class NotifyReq(BaseModel):
    keywords: list[str] = []
    location: list[str] | str = []
    company: str = ""
    remote_only: bool = False
    limit: int = 5

@app.post("/notify")
async def notify(req: NotifyReq):
    if not req.keywords:
        return {"sent": 0, "jobs": []}
    loc_arg = req.location if isinstance(req.location, list) else _split(req.location)
    if isinstance(loc_arg, list) and len(loc_arg) == 1:
        loc_arg = loc_arg[0]
    if isinstance(loc_arg, list) and not loc_arg:
        loc_arg = ""
    headers = {"User-Agent": "job-alerts-opensource/1.0"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        all_jobs = await _fetch_all(client)
        matched = [j for j in all_jobs if matches(j, req.keywords, loc_arg, req.remote_only, [], req.company.strip())][:req.limit]
        notifier = TelegramNotifier(client)
        sent = 0
        for job in matched:
            try:
                # ad-hoc sends use generic query label
                await notifier.send(format_job("manual", job))
                sent += 1
            except Exception as e:
                print(f"[warn] telegram send failed: {e}")
    return {"sent": sent, "jobs": [j.__dict__ for j in matched]}

class AlertReq(BaseModel):
    name: str
    keywords: list[str]
    location: list[str] | str = []
    company: str = ""
    remote_only: bool = False

def _read_cfg():
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _write_cfg(cfg):
    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)

@app.post("/alerts")
def save_alert(req: AlertReq):
    if not req.name.strip() or not req.keywords:
        from fastapi import HTTPException
        raise HTTPException(400, "name and keywords required")
    cfg = _read_cfg()
    queries = cfg.get("queries", []) or []
    queries = [q for q in queries if q.get("name") != req.name]
    loc = req.location if isinstance(req.location, list) else _split(req.location)
    queries.append({
        "name": req.name, "keywords": req.keywords,
        "location": loc if loc else "",
        "company": req.company.strip(),
        "remote_only": req.remote_only,
        "exclude_keywords": [],
    })
    cfg["queries"] = queries
    _write_cfg(cfg)
    return {"ok": True, "queries": queries}

@app.delete("/alerts/{name}")
def delete_alert(name: str):
    cfg = _read_cfg()
    cfg["queries"] = [q for q in (cfg.get("queries", []) or []) if q.get("name") != name]
    _write_cfg(cfg)
    return {"ok": True, "queries": cfg["queries"]}
