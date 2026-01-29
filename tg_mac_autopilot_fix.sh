#!/usr/bin/env bash
set -euo pipefail
set +H

TS="$(date +%Y%m%d_%H%M%S)"
LOG="/tmp/tg_mac_autopilot_fix_${TS}.log"
TMP="/tmp/tg_mac_autopilot_fix_${TS}"
mkdir -p "$TMP"
exec > >(tee -a "$LOG") 2>&1
trap 'rc=$?; rm -rf "$TMP" >/dev/null 2>&1 || true; echo DONE_RC=$rc; echo LOG=$LOG; tail -n 220 "$LOG" 2>/dev/null || true; exit $rc' EXIT

command -v python3 >/dev/null 2>&1 || { echo FATAL missing_python3; exit 1; }

HOME_DIR="$HOME"
ROOT="$HOME_DIR/codex_autopilot_workspace"
BIN="$HOME_DIR/bin"
VENV="$ROOT/venv"
LOGDIR="$ROOT/logs"
RUNDIR="$ROOT/run"
mkdir -p "$ROOT" "$BIN" "$LOGDIR" "$RUNDIR"

touch "$HOME_DIR/.zshrc" || true
grep -q 'export PATH="$HOME/bin:$PATH"' "$HOME_DIR/.zshrc" 2>/dev/null || echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME_DIR/.zshrc"

NEED_INSTALL="1"
if [ -x "$BIN/tg-autopilot" ]; then
  if "$BIN/tg-autopilot" --version 2>/dev/null | grep -q 'tg-autopilot-mac-v2'; then
    NEED_INSTALL="0"
  fi
fi

if [ "$NEED_INSTALL" = "1" ]; then
  [ -d "$VENV" ] || python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
  "$VENV/bin/python" -m pip install fastapi uvicorn psutil >/dev/null 2>&1

  cat > "$ROOT/panel_app.py" <<'PY'
import os, subprocess
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

HOME=os.path.expanduser("~")
ROOT=os.path.join(HOME,"codex_autopilot_workspace")

def sh(cmd):
  p=subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
  out=[]
  for line in p.stdout:
    out.append(line)
  rc=p.wait()
  return rc,"".join(out)

def exists(cmd):
  return subprocess.call(["/bin/bash","-lc",f"command -v {cmd} >/dev/null 2>&1"])==0

def doctor_text():
  lines=[]
  lines.append(f"OK_PYTHON3={1 if exists('python3') else 0}")
  lines.append(f"OK_NODE={1 if exists('node') else 0}")
  lines.append(f"OK_NPM={1 if exists('npm') else 0}")
  lines.append(f"OK_CODE={1 if exists('code') else 0}")
  lines.append(f"OK_CODEX={1 if exists('codex') else 0}")
  rc,out=sh(["/bin/bash","-lc","code --list-extensions 2>/dev/null | grep -i '^openai.chatgpt$' || true"])
  lines.append(f"OK_VSCODE_EXT_openai.chatgpt={1 if out.strip() else 0}")
  return "\n".join(lines)+"\n"

app=FastAPI()

@app.get("/health")
def health():
  return {"status":"OK"}

@app.get("/", response_class=HTMLResponse)
def index():
  return """<!doctype html><html><head><meta charset="utf-8"><title>TG Autopilot</title></head>
  <body style="font-family:-apple-system,system-ui,Segoe UI,Roboto,Arial;padding:16px;">
  <h2>TG Autopilot Panel (Mac)</h2>
  <div style="display:flex;gap:10px;flex-wrap:wrap;">
    <button onclick="run('doctor')">Doctor</button>
    <button onclick="run('open_workspace')">Open Workspace</button>
  </div>
  <pre id="out" style="margin-top:14px;padding:12px;background:#111;color:#0f0;border-radius:10px;white-space:pre-wrap;min-height:220px;"></pre>
  <script>
  async function run(cmd){
    document.getElementById('out').textContent='RUN '+cmd+'...';
    let r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cmd})});
    let t=await r.text();
    document.getElementById('out').textContent=t;
  }
  </script></body></html>"""

@app.post("/api/run")
async def api_run(req: Request):
  data=await req.json()
  cmd=data.get("cmd",")
  if cmd=="doctor":
    return PlainTextResponse(doctor_text())
  if cmd=="open_workspace":
    rc,out=sh(["/bin/bash","-lc",f"code '{ROOT}' >/dev/null 2>&1 || true; echo OK_OPENED={ROOT}"])
    return PlainTextResponse(out)
  return PlainTextResponse("ERR unknown_cmd\n", status_code=400)
PY

  cat > "$BIN/tg-autopilot" <<'PY'
#!/usr/bin/env python3
import os, sys, json, subprocess, socket, time, signal, urllib.request, argparse

VERSION="tg-autopilot-mac-v2"
HOME=os.path.expanduser("~")
ROOT=os.path.join(HOME,"codex_autopilot_workspace")
VENV=os.path.join(ROOT,"venv")
RUN=os.path.join(ROOT,"run")
LOG=os.path.join(ROOT,"logs")
os.makedirs(RUN, exist_ok=True)
os.makedirs(LOG, exist_ok=True)
STATE=os.path.join(RUN,"panel_state.json")

def sh(cmd):
  p=subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
  out=[]
  for line in p.stdout:
    out.append(line)
  rc=p.wait()
  return rc,"".join(out)

def exists(cmd):
  return subprocess.call(["/bin/bash","-lc",f"command -v {cmd} >/dev/null 2>&1"])==0

def free_port():
  for p in range(8890, 8910):
    s=socket.socket()
    try:
      s.bind(("127.0.0.1", p))
      s.close()
      return p
    except OSError:
      try: s.close()
      except: pass
  raise SystemExit("FATAL no_free_port_8890_8909")

def load_state():
  if not os.path.exists(STATE):
    return {}
  try:
    with open(STATE,"r") as f:
      return json.load(f)
  except Exception:
    return {}

def save_state(d):
  with open(STATE,"w") as f:
    json.dump(d,f)

def doctor():
  lines=[]
  lines.append(f"OK_PYTHON3={1 if exists('python3') else 0}")
  lines.append(f"OK_NODE={1 if exists('node') else 0}")
  lines.append(f"OK_NPM={1 if exists('npm') else 0}")
  lines.append(f"OK_CODE={1 if exists('code') else 0}")
  lines.append(f"OK_CODEX={1 if exists('codex') else 0}")
  rc,out=sh(["/bin/bash","-lc","code --list-extensions 2>/dev/null | grep -i '^openai.chatgpt$' || true"])
  lines.append(f"OK_VSCODE_EXT_openai.chatgpt={1 if out.strip() else 0}")
  print("\n".join(lines))

def panel_start():
  st=load_state()
  pid=st.get("pid")
  port=st.get("port")
  if pid and port:
    try:
      os.kill(pid, 0)
      print(f"OK_ALREADY_RUNNING url=http://127.0.0.1:{port} pid={pid}")
      return
    except Exception:
      pass
  port=free_port()
  app=os.path.join(ROOT,"panel_app.py")
  if not os.path.exists(app):
    raise SystemExit("FATAL missing_panel_app.py")
  log=os.path.join(LOG, f"panel_{time.strftime('%Y%m%d_%H%M%S')}.log")
  cmd=[os.path.join(VENV,"bin","python"),"-m","uvicorn","panel_app:app","--app-dir",ROOT,"--host","127.0.0.1","--port",str(port)]
  p=subprocess.Popen(cmd, stdout=open(log,"a"), stderr=subprocess.STDOUT)
  save_state({"pid":p.pid,"port":port,"log":log,"started_at":time.time()})
  time.sleep(0.9)
  print(f"OK_STARTED url=http://127.0.0.1:{port} pid={p.pid} log={log}")

def panel_stop():
  st=load_state()
  pid=st.get("pid")
  if not pid:
    print("OK_NOT_RUNNING")
    return
  try:
    os.kill(pid, signal.SIGTERM)
  except Exception:
    pass
  time.sleep(0.4)
  try:
    os.kill(pid, 0)
    try: os.kill(pid, signal.SIGKILL)
    except Exception: pass
  except Exception:
    pass
  print("OK_STOPPED")

def panel_status():
  st=load_state()
  pid=st.get("pid")
  port=st.get("port")
  if not pid or not port:
    print("STATUS=DOWN")
    return
  alive=0
  try:
    os.kill(pid, 0)
    alive=1
  except Exception:
    alive=0
  print(f"STATUS={'UP' if alive else 'DOWN'} pid={pid} port={port}")
  if st.get("log"):
    print(f"LOG={st['log']}")
  if alive:
    print(f"URL=http://127.0.0.1:{port}")

def panel_health():
  st=load_state()
  port=st.get("port")
  if not port:
    print("HEALTH=DOWN")
    return
  url=f"http://127.0.0.1:{port}/health"
  try:
    with urllib.request.urlopen(url, timeout=3) as r:
      code=r.getcode()
      print(f"HEALTH_HTTP={code} URL={url}")
  except Exception as e:
    print(f"HEALTH_HTTP=000 URL={url} ERR={type(e).__name__}")

def d_map(subcmd):
  if subcmd=="start":
    panel_start()
    return
  if subcmd=="stop":
    panel_stop()
    return
  if subcmd=="status":
    panel_status()
    return
  if subcmd=="health":
    panel_health()
    return
  if subcmd=="heal":
    panel_stop()
    time.sleep(0.4)
    panel_start()
    panel_health()
    return
  raise SystemExit("ERR unknown_D_subcmd")

def main():
  ap=argparse.ArgumentParser(add_help=True)
  ap.add_argument("--version", action="store_true")
  ap.add_argument("cmd", nargs="?")
  ap.add_argument("subcmd", nargs="?")
  args=ap.parse_args()
  if args.version:
    print(VERSION)
    return
  if not args.cmd:
    print("usage: tg-autopilot doctor|panel-start|panel-stop|panel-status|D <start|stop|status|health|heal>")
    sys.exit(2)
  if args.cmd=="doctor":
    doctor()
    return
  if args.cmd=="panel-start":
    panel_start()
    return
  if args.cmd=="panel-stop":
    panel_stop()
    return
  if args.cmd=="panel-status":
    panel_status()
    return
  if args.cmd=="D":
    if not args.subcmd:
      print("usage: tg-autopilot D <start|stop|status|health|heal>")
      sys.exit(2)
    d_map(args.subcmd)
    return
  raise SystemExit("ERR unknown_cmd")

if __name__=="__main__":
  main()
PY

  chmod +x "$BIN/tg-autopilot"
fi

WS="$(pwd)"
mkdir -p "$WS/.vscode"
python3 - <<PY
import json, os
ws=os.getcwd()
p=os.path.join(ws,".vscode","settings.json")
data={}
if os.path.exists(p):
  try:
    with open(p,"r",encoding="utf-8") as f:
      data=json.load(f)
  except Exception:
    data={}
data["python.defaultInterpreterPath"]=os.path.expanduser("~/codex_autopilot_workspace/venv/bin/python")
with open(p,"w",encoding="utf-8") as f:
  json.dump(data,f,indent=2,ensure_ascii=False)
print("OK_VSCODE_SETTINGS", p)
print("OK_PYTHON_DEFAULT", data["python.defaultInterpreterPath"])
PY

"$BIN/tg-autopilot" --version
"$BIN/tg-autopilot" doctor
"$BIN/tg-autopilot" D status
"$BIN/tg-autopilot" D start
"$BIN/tg-autopilot" D health
