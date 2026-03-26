import json
import os
import threading
import asyncio
import logging
import socket
import subprocess
from pathlib import Path
from datetime import datetime

import requests
import websockets
from flask import Flask, jsonify, request, render_template_string, redirect, session, url_for

# ─── INIT ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "elvis-rpi-2026")

BRAND      = os.environ.get("BRAND", "ELVIS")
MASTER_PIN = os.environ.get("MASTER_PIN", "019283")

DATA_DIR    = Path(os.environ.get("DATA_DIR", "./data"))
DATA_DIR.mkdir(exist_ok=True)
CONFIG_PATH = DATA_DIR / "config.json"

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError: return False

def get_config():
    if CONFIG_PATH.exists():
        try: return json.loads(CONFIG_PATH.read_text())
        except: pass
    return {"cloud_url": os.environ.get("CLOUD_URL", ""), "device_key": ""}

def save_config(c):
    CONFIG_PATH.write_text(json.dumps(c, indent=2))

event_log = []
def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    event_log.insert(0, f"[{ts}] {msg}")
    if len(event_log) > 80: event_log.pop()

# ─── CSS ─────────────────────────────────────────────────────────────────────
_CSS = """
<style>
:root{--gold:#d4af37;--bg:#0a0a0a;--card:#161616;--border:#252525;--green:#4caf50;--red:#f44336;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:var(--bg);color:#e0e0e0;min-height:100vh;display:flex;flex-direction:column;align-items:center;}
.wrap{width:100%;max-width:860px;padding:30px 20px;}
header{display:flex;justify-content:space-between;align-items:center;padding-bottom:20px;border-bottom:1px solid var(--border);margin-bottom:30px;}
h1{color:var(--gold);font-size:1.6em;font-weight:800;letter-spacing:-1px;}
.pill{padding:4px 12px;border-radius:20px;font-size:.72em;font-weight:700;text-transform:uppercase;}
.pill.ok{background:rgba(76,175,80,.15);color:#81c784;border:1px solid var(--green);}
.pill.err{background:rgba(244,67,54,.15);color:#ef9a9a;border:1px solid var(--red);}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;margin-bottom:20px;}
.card h2{font-size:1em;color:#fff;margin-bottom:16px;font-weight:600;}
input,select{width:100%;background:#000;border:1px solid #333;color:#fff;padding:12px 14px;border-radius:10px;font-size:.95em;margin-bottom:12px;outline:none;transition:.2s;}
input:focus{border-color:var(--gold);}
.btn{background:var(--gold);color:#000;padding:13px 22px;border:none;border-radius:10px;font-weight:700;cursor:pointer;transition:.2s;text-decoration:none;display:inline-block;text-align:center;font-size:.95em;}
.btn:hover{background:#fff;}
.btn.full{width:100%;}
.btn.outline{background:transparent;color:#777;border:1px solid #333;}
.btn.outline:hover{color:#fff;border-color:#fff;}
.btn.blue{background:#1976d2;color:#fff;}
.btn.purple{background:#7b1fa2;color:#fff;}
.btn.green{background:#388e3c;color:#fff;}
.btn.red-btn{background:#c62828;color:#fff;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
@media(max-width:600px){.grid2{grid-template-columns:1fr;}}
.logbox{background:#000;font-family:monospace;padding:14px;border-radius:10px;height:200px;overflow-y:auto;font-size:.82em;color:#666;border:1px solid #111;}
.logbox div{padding:3px 0;border-bottom:1px solid #0d0d0d;}
.sep{height:1px;background:var(--border);margin:16px 0;}
#msg{margin-top:10px;font-weight:600;font-size:.9em;min-height:1.2em;}
</style>
"""

# ─── PAGE: WIFI SETUP ────────────────────────────────────────────────────────
HTML_WIFI = _CSS + """
<div class="wrap">
  <header>
    <h1>{{ brand }} <span style="color:#fff;font-weight:300">RPi</span></h1>
    <span class="pill err">BRAK INTERNETU</span>
  </header>
  <div class="card" style="max-width:520px;margin:0 auto;text-align:center;">
    <h2 style="font-size:1.2em;color:var(--gold);margin-bottom:8px;">📡 Konfiguracja Wi-Fi</h2>
    <p style="color:#666;margin-bottom:20px;font-size:.9em;">Urządzenie nie ma dostępu do internetu.</p>
    <button onclick="scan()" id="btn-scan" class="btn full" style="margin-bottom:16px;">SKANUJ SIECI</button>
    <div id="nets" style="text-align:left;margin-bottom:12px;display:none;"></div>
    <div id="form-wifi" style="display:none;text-align:left;">
      <label style="font-size:.8em;color:#888;">Sieć (SSID)</label>
      <input id="ssid" readonly style="color:var(--gold);">
      <label style="font-size:.8em;color:#888;">Hasło</label>
      <input type="password" id="pwd" placeholder="Hasło Wi-Fi">
      <button onclick="connect()" class="btn full">POŁĄCZ</button>
    </div>
    <div id="msg"></div>
  </div>
</div>
<script>
async function scan(){
  document.getElementById('btn-scan').innerText='Skanowanie...';
  const r=await fetch('/api/wifi/scan');
  const d=await r.json();
  const el=document.getElementById('nets');
  el.style.display='block';
  el.innerHTML=(d.networks||[]).map(n=>`<div onclick="pick('${n}')" style="padding:10px;border-bottom:1px solid #1a1a1a;cursor:pointer;">📶 <b>${n}</b></div>`).join('')||'<div style="color:#555">Brak sieci</div>';
  document.getElementById('btn-scan').innerText='SKANUJ PONOWNIE';
}
function pick(n){
  document.getElementById('form-wifi').style.display='block';
  document.getElementById('ssid').value=n;
  document.getElementById('pwd').focus();
}
async function connect(){
  const msg=document.getElementById('msg');
  msg.innerHTML="<span style='color:var(--gold)'>Łączenie...</span>";
  const r=await fetch('/api/wifi/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ssid:document.getElementById('ssid').value,password:document.getElementById('pwd').value})});
  const d=await r.json();
  if(d.ok){msg.innerHTML="<span style='color:var(--green)'>Połączono! Odświeżam...</span>";setTimeout(()=>location.reload(),3000);}
  else msg.innerHTML=`<span style='color:var(--red)'>Błąd: ${d.error}</span>`;
}
</script>
"""

# ─── PAGE: LOGIN ─────────────────────────────────────────────────────────────
HTML_LOGIN = _CSS + """
<div class="wrap">
  <header>
    <h1>{{ brand }} <span style="color:#fff;font-weight:300">RPi</span></h1>
    <span class="pill ok">INTERNET OK</span>
  </header>
  <div class="card" style="max-width:400px;margin:0 auto;text-align:center;">
    <h2 style="font-size:1.3em;color:var(--gold);margin-bottom:6px;">🔐 Logowanie</h2>
    <p style="color:#555;margin-bottom:22px;font-size:.85em;">Wprowadź PIN lub hasło master</p>
    <input type="password" id="pin" placeholder="PIN / Hasło" style="text-align:center;font-size:1.8em;letter-spacing:8px;" maxlength="12"
      onkeydown="if(event.key==='Enter')auth()">
    <button onclick="auth()" class="btn full" style="padding:16px;font-size:1.1em;margin-top:4px;">ZALOGUJ</button>
    <div id="msg" style="color:var(--red);margin-top:14px;"></div>
  </div>
</div>
<script>
async function auth(){
  const pin=document.getElementById('pin').value;
  const msg=document.getElementById('msg');
  msg.innerHTML='';
  // 1. Sprawdź lokalne hasło master
  const lr=await fetch('/login_local',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin})});
  const ld=await lr.json();
  if(ld.ok){location.reload();return;}
  // 2. Próba przez chmurę
  const cfg=await (await fetch('/api/config')).json();
  if(!cfg.cloud_url){msg.innerText='Nie ustawiono adresu serwera. Zaloguj się jako master (019283).';return;}
  try{
    const r=await fetch(cfg.cloud_url+'/api/auth/staff_login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin})});
    const d=await r.json();
    if(d.ok){
      await fetch('/login_cloud',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin,role:d.role,name:d.name})});
      location.reload();
    }else{msg.innerText='Błędny PIN!';}
  }catch(e){msg.innerText='Brak połączenia z serwerem.';}
}
</script>
"""

# ─── PAGE: MASTER DASHBOARD ──────────────────────────────────────────────────
HTML_MASTER = _CSS + """
<div class="wrap">
  <header>
    <h1>{{ brand }} <span style="color:#fff;font-weight:300">MASTER</span></h1>
    <div style="display:flex;gap:8px;align-items:center;">
      <span style="font-size:.8em;color:#555;">IP: <b style="color:#888">{{ local_ip }}</b></span>
      <form action="/logout" method="POST" style="margin:0">
        <button class="btn outline" style="padding:6px 14px;font-size:.8em;">WYLOGUJ</button>
      </form>
    </div>
  </header>

  <!-- KONFIGURACJA SERWERA -->
  <div class="card">
    <h2>⚙️ Konfiguracja Serwera</h2>
    <label style="font-size:.8em;color:#888;">Adres serwera (https://...)</label>
    <input type="text" id="cloud-url" value="{{ config.cloud_url }}" placeholder="https://twoj-serwer.run.app">
    <label style="font-size:.8em;color:#888;">Klucz urządzenia / ID POS</label>
    <input type="text" id="device-key" value="{{ config.device_key }}" placeholder="Elvis_KWI_0326">
    <div style="display:flex;gap:10px;margin-top:4px;">
      <button onclick="saveConfig()" class="btn" style="flex:1;">ZAPISZ</button>
      <button onclick="testConn()" id="btn-test" class="btn outline" style="flex:1;">TEST POŁĄCZENIA</button>
    </div>
    <div id="test-result" style="margin-top:12px;font-size:.88em;"></div>
  </div>

  <!-- STATUS POŁĄCZENIA WS -->
  <div class="card">
    <h2>🔗 Status Połączenia z Serwerem</h2>
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="font-size:.85em;color:#888;">Serwer: <b style="color:var(--gold)">{{ config.cloud_url or 'Nie ustawiono' }}</b></div>
        <div style="font-size:.85em;color:#888;margin-top:4px;">Klucz: <b style="color:var(--gold)">{{ config.device_key or 'Nie ustawiono' }}</b></div>
      </div>
      {% if ws_connected %}
      <span class="pill ok">WS ONLINE</span>
      {% else %}
      <span class="pill err">WS OFFLINE</span>
      {% endif %}
    </div>
  </div>

  <!-- PRZYCISKI APLIKACJI -->
  <div class="card">
    <h2>🖥️ Aplikacje</h2>
    <div class="grid2">
      <a href="/kds" class="btn blue" style="padding:22px;font-size:1.1em;text-align:center;">👨‍🍳 KDS</a>
      <a href="/wydawka" class="btn purple" style="padding:22px;font-size:1.1em;text-align:center;">📦 Wydawka</a>
    </div>
  </div>

  <!-- LOGI -->
  <div class="card">
    <h2>📜 Log Zdarzeń</h2>
    <div class="logbox">
      {% for l in event_log %}<div>{{ l }}</div>{% else %}<div style="color:#333">Brak zdarzeń...</div>{% endfor %}
    </div>
    <div style="margin-top:12px;text-align:right;">
      <button onclick="location.reload()" class="btn outline" style="padding:6px 14px;font-size:.8em;">ODŚWIEŻ</button>
    </div>
  </div>
</div>

<script>
async function saveConfig(){
  const url=document.getElementById('cloud-url').value.trim();
  const key=document.getElementById('device-key').value.trim();
  const r=await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cloud_url:url,device_key:key})});
  const d=await r.json();
  if(d.ok){document.getElementById('test-result').innerHTML="<span style='color:var(--green)'>✅ Zapisano. Restartowanie połączenia...</span>";setTimeout(()=>location.reload(),2000);}
}

async function testConn(){
  const btn=document.getElementById('btn-test');
  const res=document.getElementById('test-result');
  const url=document.getElementById('cloud-url').value.trim();
  if(!url){res.innerHTML="<span style='color:var(--red)'>Najpierw wpisz adres serwera</span>";return;}
  btn.innerText='Testuję...';btn.disabled=true;
  res.innerHTML="<span style='color:var(--gold)'>⏳ Sprawdzam połączenie...</span>";
  try{
    const r=await fetch('/api/test_connection?url='+encodeURIComponent(url));
    const d=await r.json();
    if(d.ok){
      res.innerHTML=`<span style='color:var(--green)'>✅ Serwer odpowiada | HTTP ${d.status} | ${d.ms} ms</span>`;
    }else{
      res.innerHTML=`<span style='color:var(--red)'>❌ Błąd: ${d.error}</span>`;
    }
  }catch(e){
    res.innerHTML=`<span style='color:var(--red)'>❌ Błąd połączenia</span>`;
  }
  btn.innerText='TEST POŁĄCZENIA';btn.disabled=false;
}
</script>
"""

# ─── PAGE: STAFF DASHBOARD ───────────────────────────────────────────────────
HTML_STAFF = _CSS + """
<div class="wrap">
  <header>
    <h1>{{ brand }} <span style="color:#fff;font-weight:300">RPi</span></h1>
    <form action="/logout" method="POST" style="margin:0">
      <button class="btn outline" style="padding:6px 14px;font-size:.8em;">WYLOGUJ</button>
    </form>
  </header>
  <div class="card" style="text-align:center;max-width:520px;margin:0 auto;">
    <p style="color:#555;font-size:.85em;margin-bottom:6px;">Zalogowano jako</p>
    <h2 style="font-size:1.4em;color:var(--gold);margin-bottom:20px;">{{ name }} <span style="color:#555;font-size:.7em">({{ role }})</span></h2>
    <div class="grid2" style="gap:16px;">
      {% if role in ['kds','admin','master'] %}
      <a href="/kds" class="btn blue" style="padding:30px 10px;font-size:1.3em;">👨‍🍳<br>KDS</a>
      {% endif %}
      {% if role in ['wydawka','admin','master'] %}
      <a href="/wydawka" class="btn purple" style="padding:30px 10px;font-size:1.3em;">📦<br>Wydawka</a>
      {% endif %}
      {% if role in ['waiter','admin','master'] %}
      <a href="/waiter" class="btn green" style="padding:30px 10px;font-size:1.3em;">🍽️<br>Kelner</a>
      {% endif %}
    </div>
  </div>
</div>
"""

# ─── PAGE: IFRAME ─────────────────────────────────────────────────────────────
HTML_IFRAME = """<!doctype html><html><head><meta charset="utf-8">
<style>*{margin:0;padding:0;}body,html{height:100%;background:#000;}
.back{position:fixed;top:14px;left:14px;z-index:9999;background:#000;border:2px solid #d4af37;color:#d4af37;padding:8px 18px;border-radius:8px;font-family:sans-serif;text-decoration:none;font-weight:700;}
iframe{width:100%;height:100%;border:none;position:absolute;top:0;left:0;}
</style></head><body>
<a href="/" class="back">⬅ POWRÓT</a>
<iframe src="{{ url }}"></iframe>
</body></html>"""

# ─── WS STATUS ───────────────────────────────────────────────────────────────
_ws_connected = False

# ─── ROUTES ──────────────────────────────────────────────────────────────────
@app.before_request
def _watchdog():
    global _ws_thread
    if _ws_thread is None or not _ws_thread.is_alive():
        _ws_thread = _start_ws_thread()

@app.route("/")
def index():
    if not check_internet():
        return render_template_string(HTML_WIFI, brand=BRAND)

    role = session.get("role")
    if not role:
        return render_template_string(HTML_LOGIN, brand=BRAND)

    cfg = get_config()
    cloud = cfg.get("cloud_url", "")

    if role == "master":
        return render_template_string(
            HTML_MASTER,
            brand=BRAND,
            config=cfg,
            local_ip=get_local_ip(),
            event_log=event_log,
            ws_connected=_ws_connected,
        )
    else:
        return render_template_string(
            HTML_STAFF,
            brand=BRAND,
            name=session.get("name", "Pracownik"),
            role=role,
        )

# ─── AUTH ─────────────────────────────────────────────────────────────────────
@app.route("/login_local", methods=["POST"])
def login_local():
    pin = (request.json or {}).get("pin", "")
    if pin == MASTER_PIN:
        session.update({"pin": pin, "role": "master", "name": "Master"})
        add_log("Zalogowano Master (lokalnie)")
        return jsonify({"ok": True})
    return jsonify({"ok": False})

@app.route("/login_cloud", methods=["POST"])
def login_cloud():
    d = request.json or {}
    session.update({"pin": d.get("pin"), "role": d.get("role"), "name": d.get("name")})
    add_log(f"Zalogowano {d.get('name')} jako {d.get('role')}")
    return jsonify({"ok": True})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))

# ─── CONFIG ───────────────────────────────────────────────────────────────────
@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        return jsonify(get_config())
    if session.get("role") != "master":
        return jsonify({"ok": False}), 403
    d = request.json or {}
    cfg = get_config()
    cfg["cloud_url"]  = d.get("cloud_url", cfg.get("cloud_url", "")).strip()
    cfg["device_key"] = d.get("device_key", cfg.get("device_key", "")).strip()
    save_config(cfg)
    add_log(f"Zapisano konfigurację: {cfg['cloud_url']} | {cfg['device_key']}")
    return jsonify({"ok": True})

# ─── CONNECTION TEST ──────────────────────────────────────────────────────────
@app.route("/api/test_connection")
def test_connection():
    if session.get("role") != "master":
        return jsonify({"ok": False, "error": "Unauthorized"}), 403
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"ok": False, "error": "Brak URL"})
    try:
        t0 = datetime.now()
        r = requests.get(url, timeout=6)
        ms = int((datetime.now() - t0).total_seconds() * 1000)
        add_log(f"Test połączenia OK: {url} → HTTP {r.status_code} ({ms} ms)")
        return jsonify({"ok": True, "status": r.status_code, "ms": ms})
    except Exception as e:
        add_log(f"Test połączenia BŁĄD: {e}")
        return jsonify({"ok": False, "error": str(e)})

# ─── WIFI ─────────────────────────────────────────────────────────────────────
@app.route("/api/wifi/scan")
def wifi_scan():
    try:
        os.system("nmcli dev wifi rescan 2>/dev/null")
        out = subprocess.check_output("nmcli -t -f SSID dev wifi 2>/dev/null", shell=True).decode()
        nets = sorted(set(n for n in out.split("\n") if n.strip()))
        return jsonify({"networks": nets})
    except Exception as e:
        return jsonify({"networks": [], "error": str(e)})

@app.route("/api/wifi/connect", methods=["POST"])
def wifi_connect():
    d = request.json or {}
    ssid = d.get("ssid", "")
    pwd  = d.get("password", "")
    try:
        r = subprocess.run(
            f"nmcli dev wifi connect '{ssid}' password '{pwd}'",
            shell=True, capture_output=True, text=True
        )
        if r.returncode == 0:
            add_log(f"Wi-Fi połączono: {ssid}")
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": r.stderr or r.stdout})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

# ─── IFRAME VIEWS ─────────────────────────────────────────────────────────────
def _iframe(path):
    cfg = get_config()
    return render_template_string(HTML_IFRAME, url=cfg.get("cloud_url", "") + path)

@app.route("/kds")
def kds(): return _iframe("/kds")

@app.route("/wydawka")
def wydawka(): return _iframe("/wydawka")

@app.route("/waiter")
def waiter(): return _iframe("/waiter")

# ─── WEBSOCKET CLIENT ─────────────────────────────────────────────────────────
async def _ws_loop():
    global _ws_connected
    while True:
        try:
            cfg = get_config()
            url = cfg.get("cloud_url", "")
            key = cfg.get("device_key", "")

            if not url or not key:
                _ws_connected = False
                await asyncio.sleep(10)
                continue

            if not check_internet():
                _ws_connected = False
                await asyncio.sleep(5)
                continue

            ws_url = url.replace("https://", "wss://").replace("http://", "ws://") + f"/ws?device_key={key}"
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                _ws_connected = True
                add_log(f"✅ Połączono z serwerem ({key})")
                await ws.send(json.dumps({"type": "device_status", "status": "online", "ip": get_local_ip()}))
                async for raw in ws:
                    data = json.loads(raw)
                    if data.get("type") == "receipt":
                        items = data.get("items", [])
                        total = sum(float(i.get("price", 0)) for i in items)
                        add_log(f"🧾 Paragon Stolik {data.get('table_number')} | {len(items)} poz. | {total:.2f} zł")

        except Exception as e:
            _ws_connected = False
            add_log(f"WS rozłączono: {e} — ponawianie za 5s")
            await asyncio.sleep(5)

def _run_ws():
    asyncio.run(_ws_loop())

def _start_ws_thread():
    t = threading.Thread(target=_run_ws, daemon=True)
    t.start()
    return t

_ws_thread = _start_ws_thread()

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
