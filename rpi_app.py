import json
import os
import threading
import asyncio
from pathlib import Path

import requests
import websockets
from flask import Flask, jsonify, request, render_template_string, redirect, session, url_for

app = Flask(__name__)
app.secret_key = "super-secret-key-rpi"

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
DATA_DIR.mkdir(exist_ok=True)
CONFIG_PATH = DATA_DIR / "device_config.json"

CLOUD_BASE_URL = os.environ.get("CLOUD_BASE_URL", "http://127.0.0.1:8000")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
MASTER_EMAIL = "hajdukiewicz@gmail.com"

# Globalny log paragonów
receipts_log = []

INDEX_HTML = """
<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <title>RPi Ustawienia i Status</title>
  <style>
      body { font-family: sans-serif; background: #111; color: #fff; padding: 20px; }
      .box { border: 1px solid #333; padding: 20px; margin-bottom: 20px; border-radius: 8px; background: #222; }
      a { color: #d4af37; text-decoration: none; font-weight: bold; margin-right: 15px; }
      .btn { background: #d4af37; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; cursor: pointer; border: none; }
      input { padding: 10px; border-radius: 5px; border: 1px solid #333; background: #111; color: #fff; width: 60%; }
  </style>
  <script src="https://accounts.google.com/gsi/client" async defer></script>
</head>
<body>
  <div style="display:flex; justify-content:space-between; align-items:center;">
      <h1 style="color:#d4af37;">RPi Bramka Elvis</h1>
      <div>
          <a href="/kds" target="_blank">Kuchnia (KDS)</a>
          <a href="/wydawka" target="_blank">Wydawka</a>
      </div>
  </div>

  {% if not session.get('email') %}
      <div class="box">
          <h3>Zaloguj się jako Administrator (Google)</h3>
          <div id="g_id_onload" data-client_id="{{ client_id }}" data-callback="handleCredentialResponse"></div>
          <div class="g_id_signin" data-type="standard"></div>
          <script>
            function handleCredentialResponse(response) {
                fetch('/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({credential: response.credential}) })
                .then(r => r.json()).then(data => { if(data.ok) location.reload(); else alert("Błąd: " + data.error); });
            }
          </script>
      </div>
  {% else %}
      <div class="box" style="display:flex; justify-content:space-between; align-items:center;">
          <h3>Zalogowany: {{ session['email'] }}</h3>
          <form method="POST" action="/logout"><button class="btn">Wyloguj</button></form>
      </div>
      
      <div class="box">
          <h3>Parowanie Urządzenia (Device Key)</h3>
          <form method="POST" action="/set_device_key" style="display:flex; gap:10px; align-items:center;">
              <input type="text" name="device_key" value="{{ device_key }}" placeholder="np. Elvis_KWI_0326">
              <button class="btn" type="submit">Sparuj Urządzenie</button>
          </form>
          <p style="color:#aaa; font-size:0.9em; margin-top:10px;">
              Status połączenia z POS: 
              {% if device_key %}
                <span style="color:#4caf50; font-weight:bold;">SPAROWANO ({{ device_key }})</span>
              {% else %}
                <span style="color:#f44336; font-weight:bold;">BRAK PARY</span>
              {% endif %}
          </p>
      </div>

      <div class="box">
          <h3>Ostatnie paragony (z chmury)</h3>
          <ul style="color:#aaa;">
              {% for r in receipts %}
                  <li>{{ r }}</li>
              {% else %}
                  <li>Brak paragonów od uruchomienia.</li>
              {% endfor %}
          </ul>
          <button class="btn" onclick="location.reload()">Odśwież Listę</button>
      </div>
  {% endif %}
</body>
</html>
"""

IFRAME_HTML = """
<!doctype html>
<html>
<head><style>body,html{margin:0;padding:0;height:100%;overflow:hidden;}</style></head>
<body><iframe src="{{ url }}" style="width:100%; height:100%; border:none;"></iframe></body>
</html>
"""

def get_device_key():
    key_file = DATA_DIR / "device_key.txt"
    return key_file.read_text().strip() if key_file.exists() else ""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML, session=session, client_id=GOOGLE_CLIENT_ID, receipts=receipts_log[-10:], device_key=get_device_key())

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    token = data.get("credential")
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo['email']
    except Exception as e:
        import jwt
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            email = decoded.get('email')
        except:
            return jsonify({"error": str(e)})

    if email == MASTER_EMAIL:
        session['email'] = email
        return jsonify({"ok": True})
    return jsonify({"error": "Brak uprawnień Mastera dla tego RPi"})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/set_device_key", methods=["POST"])
def set_device_key():
    if session.get('email') != MASTER_EMAIL: return "Unauthorized", 401
    dk = request.form.get("device_key", "").strip()
    (DATA_DIR / "device_key.txt").write_text(dk)
    # Restart the background thread or simply exit so Docker/systemd restarts the process
    os._exit(1)
    return redirect(url_for("index"))

@app.route("/api/device_identity")
def device_identity():
    dk = get_device_key()
    return jsonify({
        "ok": True,
        "serial_number": os.environ.get("FALLBACK_SN", "RPI4-UNKNOWN"),
        "device_key": dk,
        "pubsub_topic": f"devices/{dk}" if dk else ""
    })

@app.route("/kds")
def kds():
    url = f"{CLOUD_BASE_URL}/kds"
    return render_template_string(IFRAME_HTML, url=url)

@app.route("/wydawka")
def wydawka():
    url = f"{CLOUD_BASE_URL}/wydawka"
    return render_template_string(IFRAME_HTML, url=url)

# --- BACKGROUND WEBSOCKET CLIENT ---
async def ws_client_task():
    dk = get_device_key()
    ws_url = CLOUD_BASE_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    if dk: ws_url += f"?device_key={dk}"
    
    while True:
        if not get_device_key():
            await asyncio.sleep(5)
            continue
            
        try:
            async with websockets.connect(ws_url) as ws:
                print(f"[RPi] Pomyślnie połączono z serwerem i sparowano bramkę z: {ws_url}")
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("type") == "receipt":
                        table = data.get("table")
                        orders = data.get("orders", [])
                        print(f"[RPi FISKALNE] Numer stolika: {table}, pozycje: {len(orders)}")
                        receipts_log.append(f"Stolik {table} - paragon odebrany ({len(orders)} pozycji)")
        except Exception as e:
            print(f"[RPi] Błąd WS: {e}. Ponawiam za 5s...")
            await asyncio.sleep(5)

def start_ws_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_client_task())

if __name__ == "__main__":
    t = threading.Thread(target=start_ws_thread, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=8080)
