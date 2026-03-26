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

def check_internet():
    try:
        # Sprawdzamy dostępność DNS Google by potwierdzić internet
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        pass
    return False

def get_config():
    if CONFIG_PATH.exists():
        try: return json.loads(CONFIG_PATH.read_text())
        except: pass
    return {"cloud_url": os.environ.get("CLOUD_BASE_URL", "https://elvis-burger-v1-292715946390.europe-west1.run.app")}

def save_config(conf):
    CONFIG_PATH.write_text(json.dumps(conf))

# Konfiguracja Cloud
CONFIG = get_config()
CLOUD_BASE_URL = CONFIG.get("cloud_url", "https://elvis-burger-v1-292715946390.europe-west1.run.app")

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
            font-weight: 800; cursor: pointer; transition: 0.2s; text-decoration: none; display: inline-block; text-align: center; width: 100%;
        }
        .btn:hover { background: #fff; transform: scale(1.02); }
        .btn-outline { background: transparent; color: #888; border: 1px solid #333; }
        .btn-outline:hover { color: #fff; border-color: #fff; }

        .log-box { background: #000; font-family: monospace; padding: 15px; border-radius: 12px; height: 180px; overflow-y: auto; font-size: 0.85em; color: #777; border: 1px solid #111; }
        .log-box div { border-bottom: 1px solid #0a0a0a; padding: 4px 0; }
        
        .iframe-link { color: var(--gold); font-weight: 600; text-decoration: none; border: 1px solid var(--gold); padding: 5px 15px; border-radius: 8px; transition: 0.2s; font-size: 0.9em; }
        .iframe-link:hover { background: var(--gold); color: #000; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ELVIS RPI <span>GATEWAY</span></h1>
            {% if has_internet %}
            <div style="display:flex; gap:10px;">
                <span style="color:var(--green); font-weight:bold; font-size:0.8em; border:1px solid var(--green); padding:5px 10px; border-radius:5px;">INTERNET OK</span>
            </div>
            {% else %}
            <div style="display:flex; gap:10px;">
                <span class="status-pill offline">BRAK INTERNETU</span>
            </div>
            {% endif %}
        </header>

        {% if not has_internet %}
        <div class="card" style="text-align: center; max-width: 600px; margin: 0 auto;">
            <h3 style="color:var(--red); justify-content:center;">📡 Brak Połączenia z Internetem</h3>
            <p style="color:#888; margin-bottom:20px;">Urządzenie Raspberry Pi nie ma dostępu do sieci. Wybierz sieć Wi-Fi, aby się podłączyć.</p>
            
            <button onclick="scanWifi()" id="btn-scan" class="btn btn-outline" style="margin-bottom:20px;">SKANUJ SIECI WI-FI</button>
            <div id="wifi-list" style="margin-bottom:20px; text-align:left; background:#000; padding:15px; border-radius:10px; display:none;"></div>
            
            <div id="wifi-form" style="display:none; text-align:left;">
                <label style="color:#aaa; font-size:0.8em;">Wybrana sieć (SSID):</label>
                <input type="text" id="wifi-ssid" readonly style="color:var(--gold);">
                <label style="color:#aaa; font-size:0.8em;">Hasło do Wi-Fi:</label>
                <input type="password" id="wifi-pwd" placeholder="Wprowadź hasło">
                <button onclick="connectWifi()" id="btn-connect" class="btn">POŁĄCZ</button>
                <div id="wifi-msg" style="margin-top:10px; font-weight:bold; text-align:center;"></div>
            </div>

            <script>
                async function scanWifi() {
                    const btn = document.getElementById('btn-scan');
                    btn.innerText = "Skanowanie...";
                    const res = await fetch('/api/wifi/scan');
                    const data = await res.json();
                    
                    const list = document.getElementById('wifi-list');
                    list.style.display = 'block';
                    if (data.networks && data.networks.length > 0) {
                        list.innerHTML = data.networks.map(n => 
                            `<div style="padding:10px; border-bottom:1px solid #222; cursor:pointer;" onclick="selectWifi('${n}')">
                                📶 <b>${n}</b>
                            </div>`
                        ).join('');
                    } else {
                        list.innerHTML = "<div style='color:#888;'>Nie znaleziono żadnych sieci.</div>";
                    }
                    btn.innerText = "SKANUJ SIECI WI-FI ZAMIAST";
                }
                function selectWifi(ssid) {
                    document.getElementById('wifi-form').style.display = 'block';
                    document.getElementById('wifi-ssid').value = ssid;
                    document.getElementById('wifi-pwd').focus();
                }
                async function connectWifi() {
                    const ssid = document.getElementById('wifi-ssid').value;
                    const pwd = document.getElementById('wifi-pwd').value;
                    const msg = document.getElementById('wifi-msg');
                    
                    document.getElementById('btn-connect').innerText = "Łączenie...";
                    msg.innerHTML = "<span style='color:var(--gold)'>Próba połączenia...</span>";
                    
                    try {
                        const res = await fetch('/api/wifi/connect', {
                            method: 'POST', headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ssid: ssid, password: pwd})
                        });
                        const data = await res.json();
                        if(data.ok) {
                            msg.innerHTML = "<span style='color:var(--green)'>Połączono! Odświeżam...</span>";
                            setTimeout(() => location.reload(), 3000);
                        } else {
                            msg.innerHTML = `<span style='color:var(--red)'>Błąd: ${data.error}</span>`;
                            document.getElementById('btn-connect').innerText = "POŁĄCZ PONOWNIE";
                        }
                    } catch(e) {
                         msg.innerHTML = `<span style='color:var(--red)'>Błąd: utracono łączność, odśwież formatkę.</span>`;
                         setTimeout(() => location.reload(), 3000);
                    }
                }
            </script>
        </div>

        {% elif not session.get('staff_pin') %}
        <div class="card" style="text-align: center; max-width: 500px; margin: 0 auto;">
            <h3 style="color:var(--gold); justify-content:center; font-size:1.5em; margin-bottom:20px;">🔐 Autoryzacja POS</h3>
            <p style="color:#888; margin-bottom:30px;">Wprowadź PIN Pracownika</p>
            
            <input type="password" id="auth-pin" style="text-align:center; font-size:2em; letter-spacing:10px;" placeholder="PIN" maxlength="8">
            <button onclick="authPin()" class="btn" style="padding:18px; font-size:1.2em;">ZALOGUJ SIĘ</button>
            <div id="auth-msg" style="color:var(--red); margin-top:15px; display:none; font-weight:bold;">Błędny PIN!</div>

            <script>
                async function authPin() {
                    const pin = document.getElementById('auth-pin').value;
                    // Uderzamy w chmurę
                    try {
                        const res = await fetch('{{ cloud_url }}/api/auth/staff_login', {
                            method: 'POST', headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({pin: pin})
                        });
                        const data = await res.json();
                        if (data.ok) {
                            // Localne przekazanie faktu bycia zalogowanym, aby backend flask mógł zapamiętać PIN w sesji
                            await fetch('/login_pin', {
                                method: 'POST', headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({pin: pin, role: data.role, name: data.name})
                            });
                            location.reload();
                        } else {
                            document.getElementById('auth-msg').innerText = "Błędny PIN!";
                            document.getElementById('auth-msg').style.display = 'block';
                        }
                    } catch(e) {
                        document.getElementById('auth-msg').innerText = "Brak dostępu do serwera cloud. Sprawdź adres konfiguracji.";
                        document.getElementById('auth-msg').style.display = 'block';
                    }
                }
            </script>
        </div>
        
        {% else %}
        <!-- EKRAN GŁÓWNY PO ZALOGOWANIU NA RPI -->
        <div class="card" style="text-align:center; max-width: 600px; margin: 0 auto 30px;">
            <h2 style="color:var(--gold); margin-top:0;">Witaj, {{ session.get('staff_name', 'Pracownik') }}</h2>
            <p style="margin-bottom:20px; color:#888;">Twoja rola: <b style="color:#fff; text-transform:uppercase;">{{ session.get('staff_role', '') }}</b></p>
            
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px;">
                {% if session.get('staff_role') in ['kds', 'admin', 'master'] %}
                <a href="/kds" class="btn" style="padding:30px 10px; font-size:1.5em; background:#1976d2; color:#fff;">👨‍🍳 KUCHNIA (KDS)</a>
                {% endif %}
                
                {% if session.get('staff_role') in ['wydawka', 'admin', 'master'] %}
                <a href="/wydawka" class="btn" style="padding:30px 10px; font-size:1.5em; background:#8e24aa; color:#fff;">📦 WYDAWKA</a>
                {% endif %}
            </div>
            
            <form action="/logout" method="POST" style="margin-top:20px;">
                <button type="submit" class="btn btn-outline">WYLOGUJ</button>
            </form>
        </div>

        <div class="grid">
            <!-- KONFIGURACJA CHMURY (TYLKO DLA SZEFA NA RPI) -->
            {% if session.get('staff_role') in ['admin', 'master'] %}
            <div class="card">
                <h2>Konfiguracja Urządzenia</h2>
                <form action="/set_config" method="POST" style="display:flex; flex-direction:column; gap:15px;">
                    <div>
                        <label style="font-size:0.8em; color:#888;">URL CHMURY (z https://):</label>
                        <input type="text" name="cloud_url" value="{{ config.get('cloud_url','') }}" placeholder="https://elvis...run.app" style="width:100%; padding:12px; background:#000; border:1px solid #333; color:var(--gold); border-radius:8px;">
                    </div>
                    <div>
                        <label style="font-size:0.8em; color:#888;">ID URZĄDZENIA (Klucz POS):</label>
                        <input type="text" name="device_key" value="{{ device_key }}" placeholder="Elvis_KWI_0326" style="width:100%; padding:12px; background:#000; border:1px solid #333; color:var(--gold); border-radius:8px;">
                    </div>
                    <button type="submit" class="btn btn-gold" style="background:var(--gold); color:#000;">Zapisz i Połącz</button>
                </form>
            </div>
            {% endif %}

            <!-- STATUS URZĄDZENIA -->
            <div class="card">
                <h3>🆔 Status Urządzenia</h3>
                <div style="margin-top:20px; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:0.9em;">ID: <b style="color:var(--gold)">{{ device_key or 'NIEUSTAWIONO' }}</b></span>
                    {% if device_key %}
                    <span class="status-pill online">SPAROWANO</span>
                    {% else %}
                    <span class="status-pill offline">BRAK</span>
                    {% endif %}
                </div>
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
            Elvis POS RPi Gateway v2.6 | Local First PIN Auth
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
<body>
    <div style="position:absolute; top:20px; left:20px; z-index:9999;">
        <a href="/" style="background:#000; border:2px solid #d4af37; color:#d4af37; padding:10px 20px; border-radius:10px; font-family:sans-serif; text-decoration:none; font-weight:bold;">⬅ POWRÓT</a>
    </div>
    <iframe src="{{ url }}" style="width:100%; height:100%; border:none;"></iframe>
</body>
</html>
"""

# --- ROUTES ---

@app.route("/")
def index():
    has_internet = check_internet()
    return render_template_string(
        INDEX_HTML, 
        session=session, 
        event_log=reversed(event_log), 
        device_key=get_device_key(),
        cloud_url=CLOUD_BASE_URL,
        local_ip=get_local_ip(),
        has_internet=has_internet,
        config=CONFIG
    )

@app.route("/api/wifi/scan")
def wifi_scan():
    try:
        # Próba skanowania przez nmcli
        os.system("nmcli dev wifi rescan")
        output = subprocess.check_output("nmcli -t -f SSID dev wifi", shell=True).decode('utf-8')
        networks = list(set([n for n in output.split('\n') if n.strip()]))
        return jsonify({"networks": networks})
    except Exception as e:
        return jsonify({"error": str(e), "networks": []})

@app.route("/api/wifi/connect", methods=["POST"])
def wifi_connect():
    data = request.json
    ssid = data.get("ssid")
    pwd = data.get("password")
    try:
        cmd = f"nmcli dev wifi connect '{ssid}' password '{pwd}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            add_log(f"Zestawiono połączenie Wi-Fi: {ssid}")
            return jsonify({"ok": True})
        else:
            return jsonify({"ok": False, "error": result.stderr or result.stdout})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/login_pin", methods=["POST"])
def login_pin():
    data = request.json
    session['staff_pin'] = data.get('pin')
    session['staff_role'] = data.get('role')
    session['staff_name'] = data.get('name')
    add_log(f"Zalogowano {data.get('name')} jako {data.get('role')}")
    return jsonify({"ok": True})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/set_config", methods=["POST"])
def set_config():
    if session.get('staff_role') not in ['admin', 'master']: return "Unauthorized", 401
    url = request.form.get("cloud_url", "").strip()
    dk = request.form.get("device_key", "").strip()
    
    conf = get_config()
    conf["cloud_url"] = url
    save_config(conf)
    
    if dk:
        KEY_FILE.write_text(dk)
        add_log(f"Zmieniono URL na {url} i klucz na {dk}. Restart...")
    else:
        add_log(f"Zmieniono URL na {url}. Restart...")
        
    threading.Timer(1, lambda: os._exit(1)).start()
    return redirect(url_for("index"))

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
        base_url = conf.get("cloud_url", "https://elvis-burger-v1-292715946390.europe-west1.run.app")
        
        if not dk or not base_url or "127.0.0.1" in base_url:
            add_log(f"⚠️ Skonfiguruj Cloud URL i Klucz ({dk or 'Brak klucza'})")
            await asyncio.sleep(10)
            continue
            
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://") + f"/ws?device_key={dk}"
        if not check_internet():
            await asyncio.sleep(5)
            continue
            
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                add_log(f"Połączono z Chmurą ({dk})")
                await ws.send(json.dumps({"type": "device_status", "status": "online", "ip": get_local_ip()}))
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("type") == "receipt":
                        items = data.get("items", [])
                        total = sum(float(i.get("price", 0)) for i in items)
                        add_log(f"🧾 Paragon Stolik {data.get('table_number')} | {len(items)} poz. | {total:.2f} zł")
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
