import json
import os
import threading
import asyncio
import logging
import socket
from pathlib import Path
from datetime import datetime

import requests
import websockets
from flask import Flask, jsonify, request, render_template_string, redirect, session, url_for

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "elvis-rpi-secret-key-2026")

# Ścieżki danych
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
DATA_DIR.mkdir(exist_ok=True)
KEY_FILE = DATA_DIR / "device_key.txt"
CONFIG_PATH = DATA_DIR / "device_config.json"

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

def get_config():
    if CONFIG_PATH.exists():
        try: return json.loads(CONFIG_PATH.read_text())
        except: pass
    return {"cloud_url": os.environ.get("CLOUD_BASE_URL", "http://127.0.0.1:8000")}

def save_config(conf):
    CONFIG_PATH.write_text(json.dumps(conf))

# Konfiguracja Cloud
CONFIG = get_config()
CLOUD_BASE_URL = CONFIG.get("cloud_url", "http://127.0.0.1:8000")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "292715946390-kb36g21aoeithmpanfd82jcmjfs7b5v9.apps.googleusercontent.com")
MASTER_EMAIL = "hajdukiewicz@gmail.com"

# Globalny bufor zdarzeń i paragonów
event_log = []

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    event_log.append(f"[{ts}] {msg}")
    if len(event_log) > 20: event_log.pop(0)

def get_device_key():
    return KEY_FILE.read_text().strip() if KEY_FILE.exists() else ""

# --- PREMIUM UI TEMPLATE ---
INDEX_HTML = """
<!doctype html>
<html lang="pl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Elvis RPi zjedz | Gateway</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root { --gold: #d4af37; --bg: #0a0a0a; --card: #161616; --green: #388e3c; --red: #d32f2f; }
        * { box-sizing: border-box; }
        body { 
            font-family: 'Outfit', sans-serif; background: var(--bg); color: #e0e0e0; 
            margin: 0; display: flex; flex-direction: column; align-items: center; min-height: 100vh;
        }
        .container { max-width: 900px; width: 100%; padding: 40px 20px; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; border-bottom: 1px solid #222; padding-bottom: 20px; }
        h1 { color: var(--gold); margin: 0; font-weight: 800; font-size: 1.8em; letter-spacing: -1px; }
        
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        
        .card { 
            background: var(--card); border: 1px solid #222; padding: 25px; border-radius: 20px; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .card:hover { border-color: var(--gold); transform: translateY(-5px); }
        .card h3 { margin-top: 0; font-weight: 600; color: #fff; display: flex; align-items: center; gap: 10px; font-size: 1.1em; }
        
        .status-pill { padding: 4px 12px; border-radius: 20px; font-size: 0.75em; font-weight: 800; text-transform: uppercase; }
        .online { background: rgba(56, 142, 60, 0.2); color: #81c784; border: 1px solid #388e3c; }
        .offline { background: rgba(211, 47, 47, 0.2); color: #ef5350; border: 1px solid #d32f2f; }
        
        input { 
            width: 100%; background: #000; border: 1px solid #333; color: #fff; padding: 14px; 
            border-radius: 12px; font-size: 1em; margin-bottom: 15px; outline: none; transition: 0.2s;
        }
        input:focus { border-color: var(--gold); }
        
        .btn { 
            background: var(--gold); color: #000; padding: 14px 24px; border: none; border-radius: 12px; 
            font-weight: 800; cursor: pointer; transition: 0.2s; text-decoration: none; display: inline-block; text-align: center;
        }
        .btn:hover { background: #fff; transform: scale(1.02); }
        .btn-outline { background: transparent; color: #888; border: 1px solid #333; }
        .btn-outline:hover { color: #fff; border-color: #fff; }

        .log-box { background: #000; font-family: monospace; padding: 15px; border-radius: 12px; height: 180px; overflow-y: auto; font-size: 0.85em; color: #777; border: 1px solid #111; }
        .log-box div { border-bottom: 1px solid #0a0a0a; padding: 4px 0; }
        
        .iframe-link { color: var(--gold); font-weight: 600; text-decoration: none; border: 1px solid var(--gold); padding: 5px 15px; border-radius: 8px; transition: 0.2s; font-size: 0.9em; }
        .iframe-link:hover { background: var(--gold); color: #000; }
    </style>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>ELVIS RPI <span>GATEWAY</span></h1>
            <div style="display:flex; gap:10px;">
                <a href="/pos" class="iframe-link" style="background:var(--gold); color:#000;">STACJA POS</a>
                <a href="/kds" class="iframe-link" target="_blank">KDS</a>
                <a href="/wydawka" class="iframe-link" target="_blank">Wydawka</a>
            </div>
        </header>

        {% if not session.get('email') %}
        <div class="card" style="text-align: center; max-width: 500px; margin: 0 auto;">
            <h3>🔐 Autoryzacja Administratora</h3>
            <p style="color:#888; margin-bottom:30px;">Zaloguj się kontem Master, aby zarządzać ustawieniami.</p>
            <div id="g_id_onload" data-client_id="{{ client_id }}" data-callback="handleCredentialResponse" data-auto_prompt="false"></div>
            <div class="g_id_signin" data-type="standard" data-shape="rectangular" data-theme="filled_black" data-text="signin_with" data-size="large" data-logo_alignment="left"></div>
            <script>
                function handleCredentialResponse(response) {
                    fetch('/login', { 
                        method: 'POST', 
                        headers: {'Content-Type': 'application/json'}, 
                        body: JSON.stringify({credential: response.credential}) 
                    })
                    .then(r => r.json()).then(data => { 
                        if(data.ok) location.reload(); 
                        else alert("Błąd autoryzacji: " + data.error); 
                    });
                }
            </script>
        </div>
        {% else %}
        <div class="grid">
            <!-- KONFIGURACJA CHMURY -->
            <div class="card" style="grid-column: 1 / -1;">
                <h3>☁️ Konfiguracja Chmury</h3>
                <form method="POST" action="/set_config" style="display:flex; gap:10px; align-items:center;">
                    <input type="text" name="cloud_url" value="{{ cloud_url }}" placeholder="https://elvis3-app.a.run.app" style="margin-bottom:0;">
                    <button class="btn" style="white-space:nowrap;">ZAPISZ URL</button>
                </form>
                <p style="color:#555; font-size:0.75em; margin-top:8px;">Malinka szuka teraz chmury pod: <b style="color:var(--gold)">{{ cloud_url }}</b></p>
            </div>

            <!-- KONFIGURACJA URZĄDZENIA -->
            <div class="card">
                <h3>🆔 Tożsamość (Device Key)</h3>
                <form method="POST" action="/set_device_key">
                    <input type="text" name="device_key" value="{{ device_key }}" placeholder="Elvis_KWI_0326">
                    <button class="btn" style="width:100%">💾 AKTUALIZUJ KLUCZ</button>
                </form>
                <div style="margin-top:20px; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:0.9em;">Status Parowania:</span>
                    {% if device_key %}
                    <span class="status-pill online">SPAROWANO</span>
                    {% else %}
                    <span class="status-pill offline">BRAK</span>
                    {% endif %}
                </div>
            </div>

            <div class="card">
                <h3>👤 Administrator</h3>
                <p style="margin:5px 0 20px; color:#aaa;">Zalogowany jako:<br><b style="color:#fff;">{{ session['email'] }}</b></p>
                <form method="POST" action="/logout"><button class="btn btn-outline" style="width:100%">WYLOGUJ SIĘ</button></form>
            </div>

            <!-- LOGI SYSTEMOWE -->
            <div class="card" style="grid-column: 1 / -1;">
                <h3>📜 Live Activity Stream</h3>
                <div class="log-box">
                    {% for log in event_log %}
                        <div>{{ log }}</div>
                    {% else %}
                        <div style="color:#333;">Oczekiwanie na zdarzenia...</div>
                    {% endfor %}
                </div>
                <div style="margin-top:15px; display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#555; font-size:0.8em;">Lokalne IP: <b>{{ local_ip }}</b></span>
                    <button class="btn btn-outline" style="padding:5px 12px; font-size:0.8em;" onclick="location.reload()">ODŚWIEŻ</button>
                </div>
            </div>
        </div>
        {% endif %}

        <footer style="margin-top:40px; text-align:center; color:#333; font-size:0.8em;">
            Elvis POS RPi Gateway v2.5 | Powering NextGen Gastronomy
        </footer>
    </div>
</body>
</html>
"""

IFRAME_HTML = """
<!doctype html>
<html>
<head>
    <title>Elvis {{ name }}</title>
    <style>body,html{margin:0;padding:0;height:100%;overflow:hidden;background:#000;}</style>
</head>
<body><iframe src="{{ url }}" style="width:100%; height:100%; border:none;"></iframe></body>
</html>
"""

# --- ROUTES ---

@app.route("/")
def index():
    return render_template_string(
        INDEX_HTML, 
        session=session, 
        client_id=GOOGLE_CLIENT_ID, 
        event_log=reversed(event_log), 
        device_key=get_device_key(),
        cloud_url=CLOUD_BASE_URL,
        local_ip=get_local_ip()
    )

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    token = data.get("credential")
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo['email']
        if email == MASTER_EMAIL:
            session['email'] = email
            add_log(f"Zalogowano Mastera: {email}")
            return jsonify({"ok": True})
        return jsonify({"error": "Brak uprawnień Mastera"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/set_config", methods=["POST"])
def set_config():
    if session.get('email') != MASTER_EMAIL: return "Unauthorized", 401
    url = request.form.get("cloud_url", "").strip()
    conf = get_config()
    conf["cloud_url"] = url
    save_config(conf)
    add_log(f"Zmieniono URL chmury na: {url}. Restart...")
    threading.Timer(1, lambda: os._exit(1)).start()
    return redirect(url_for("index"))

@app.route("/set_device_key", methods=["POST"])
def set_device_key():
    if session.get('email') != MASTER_EMAIL: return "Unauthorized", 401
    dk = request.form.get("device_key", "").strip()
    KEY_FILE.write_text(dk)
    add_log(f"Zmieniono klucz urządzenia. Restart...")
    threading.Timer(1, lambda: os._exit(1)).start()
    return redirect(url_for("index"))

@app.route("/pos")
def pos():
    # User-requested POS stacja on RPi
    return render_template_string(IFRAME_HTML, name="POS", url=f"{CLOUD_BASE_URL}/waiter")

@app.route("/kds")
def kds():
    return render_template_string(IFRAME_HTML, name="KDS", url=f"{CLOUD_BASE_URL}/kds")

@app.route("/wydawka")
def wydawka():
    return render_template_string(IFRAME_HTML, name="Wydawka", url=f"{CLOUD_BASE_URL}/wydawka")

# --- BACKGROUND WEBSOCKET CLIENT ---
async def ws_client_loop():
    while True:
        dk = get_device_key()
        conf = get_config()
        base_url = conf.get("cloud_url", "http://127.0.0.1:8000")
        
        if not dk or not base_url or "127.0.0.1" in base_url:
            add_log(f"⚠️ Skonfiguruj Cloud URL i Klucz ({dk or 'Brak klucza'})")
            await asyncio.sleep(10)
            continue
            
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://") + f"/ws?device_key={dk}"
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                add_log(f"Połączono z Chmurą ({dk})")
                await ws.send(json.dumps({"type": "device_status", "status": "online", "ip": get_local_ip()}))
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("type") == "receipt":
                        add_log(f"🧾 Odebrano paragon (Stolik {data.get('table')})")
        except Exception as e:
            add_log(f"Błąd WS ({base_url}): {e}. Ponawiam za 5s...")
            await asyncio.sleep(5)

def run_ws_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_client_loop())

if __name__ == "__main__":
    threading.Thread(target=run_ws_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
