import os, requests, json, uuid
from fastapi import FastAPI, Request, File, UploadFile, Form, Cookie, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.cloud import firestore
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from collections import defaultdict
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import jwt

app = FastAPI()
APP_DIR = Path(__file__).resolve().parent

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for d in disconnected:
            self.disconnect(d)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    device_key = websocket.query_params.get("device_key", "anonymous")
    await manager.connect(websocket)
    print(f"WS Client connected: {device_key}")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "device_status":
                    # Zapisujemy status urządzenia w Firestore
                    db.collection("devices").document(device_key).set({
                        "status": "online",
                        "ip": msg.get("ip", "unknown"),
                        "last_seen": datetime.now(timezone.utc).isoformat()
                    }, merge=True)
                    # Rozgłaszamy do paneli admina/wydawki że status się zmienił
                    await manager.broadcast(json.dumps({"type": "update"}))
            except: pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        db.collection("devices").document(device_key).set({"status": "offline"}, merge=True)
        await manager.broadcast(json.dumps({"type": "update"}))
        print(f"WS Client disconnected: {device_key}")

@app.get("/api/device_status/{device_key}")
async def get_device_status(device_key: str):
    doc = db.collection("devices").document(device_key).get()
    return doc.to_dict() if doc.exists else {"status": "offline"}
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

db = firestore.Client()

API_KEY = ""
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
STATUS_MAP = {
    "nowe": "W kolejce", 
    "preparing": "W kuchni", 
    "ready": "Gotowe!", 
    "closed": "Wydane"
}

# --- API ENDPOINTS (JOKES & STORY) ---

@app.get("/api/get_joke")
async def get_joke(item: str = "jedzenie"):
    prompt = f"Jesteś Duchem Burgera. Klient wybrał: {item}. Rzuć 1 krótkim żartem. Max 60 znaków."
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 50, "temperature": 0.7}}
        res = requests.post(GEMINI_URL, json=payload, timeout=5).json()
        return {"joke": res['candidates'][0]['content']['parts'][0]['text'].strip()}
    except: 
        return {"joke": "Smacznego! Ten burger to legenda."}

@app.get("/api/get_story")
async def get_story(item: str = "burger"):
    prompt = f"Jesteś historykiem kulinarnym. Napisz jedną, fascynującą anegdotę o: {item}. Max 300 znaków. Zakończ kropką."
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 400, "temperature": 0.8}}
        res = requests.post(GEMINI_URL, json=payload, timeout=5).json()
        story = res['candidates'][0]['content']['parts'][0]['text'].strip()
        return {"story": story}
    except:
        return {"story": "Czy wiesz, że pierwszy burger powstał z potrzeby zjedzenia posiłku w biegu?"}

@app.get("/api/get_burger_story")
async def get_burger_story():
    prompt = "Napisz krótką, pozytywną i ciekawą historię o jedzeniu burgerów. Maksymalnie 3 zdania, które wywołają uśmiech."
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 150, "temperature": 0.8}}
        res = requests.post(GEMINI_URL, json=payload, timeout=5).json()
        story = res['candidates'][0]['content']['parts'][0]['text'].strip()
        return {"story": story}
    except:
        return {"story": "Jeden kęs dobrego burgera potrafi przenieść w wymiar prawdziwej rozkoszy gastronomicznej. Chrupiąca bułka i soczyste mięso tworzą kompozycję idealną. Pamiętaj, że zawsze warto znaleźć chwilę na taką drobną przyjemność!"}

# --- STAFF MANAGEMENT & PIN AUTH ---

@app.post("/api/admin/save_staff")
async def save_staff(request: Request):
    data = await request.json()
    name = data.get("name")
    pin = data.get("pin")
    role = data.get("role")
    if not pin or len(pin) < 6: return {"ok": False, "error": "Hasło musi mieć min 6 znaków."}
    print(f"DEBUG: Saving staff: {name}, PIN: {pin}, Role: {role}")
    db.collection("staff").document(str(pin)).set({"name": name, "role": role})
    return {"ok": True}

@app.get("/api/admin/get_staff")
async def get_staff():
    return [{"pin": d.id, **d.to_dict()} for d in db.collection("staff").stream()]

@app.post("/api/auth/staff_login")
async def staff_login(request: Request):
    data = await request.json()
    pin = str(data.get("pin"))
    # MASTER PIN (Dla szefa - Hajdukiewicz)
    if pin == "789643":
        return {"ok": True, "name": "MASTER", "role": "admin"}
    # Domyślny admin
    if pin == "102938":
        return {"ok": True, "name": "ADMIN", "role": "admin"}

    doc = db.collection("staff").document(pin).get()
    if doc.exists:
        u = doc.to_dict()
        return {"ok": True, "name": u.get("name"), "role": u.get("role")}
    return {"ok": False}

# --- MENU & LAYOUT ---

@app.get("/api/get_menu")
async def get_menu(): 
    menu_dict = {d.id: d.to_dict() for d in db.collection("menu").stream()}
    return dict(sorted(menu_dict.items(), key=lambda x: int(x[1].get('sort_order', 99))))

@app.get("/api/get_layout")
async def get_layout():
    doc = db.collection("config").document("floor_plan").get()
    if doc.exists:
        return doc.to_dict()
    # Zwraca domyślną mapę 10x10, jeśli jeszcze nic nie zapisano
    return {"width": 10, "height": 10, "tables": []}

@app.post("/api/admin/save_layout")
async def save_layout(request: Request):
    try:
        payload = await request.json()
        print(f"DEBUG: Saving layout: {len(payload.get('tables', []))} tables")
        db.collection("config").document("floor_plan").set(payload)
        await manager.broadcast(json.dumps({"type": "update"}))
        return {"ok": True}
    except Exception as e:
        print(f"ERROR: Save layout failed: {str(e)}")
        return {"ok": False, "error": str(e)}

# --- AUTHENTICATION & ROLES ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID_HERE")
MASTER_EMAIL = "hajdukiewicz@gmail.com"

@app.post("/api/auth/login")
async def auth_login(request: Request, response: Response):
    data = await request.json()
    token = data.get("credential")
    email = None
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo['email']
    except Exception as e:
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            email = decoded.get('email')
        except:
            return {"ok": False, "error": str(e)}

    if not email:
        return {"ok": False, "error": "Brak email w tokenie"}

    role = "user"
    if email == MASTER_EMAIL:
        role = "master"
    else:
        doc = db.collection("users").document(email).get()
        if doc.exists:
            role = doc.to_dict().get("role", "user")

    return {"ok": True, "email": email, "role": role}

@app.post("/api/admin/set_role")
async def set_role(request: Request):
    data = await request.json()
    auth_role = data.get("auth_role")
    if auth_role not in ["master", "admin"]: return {"error": "Brak uprawnień"}
    
    target_email = data.get("email")
    new_role = data.get("role")
    if target_email == MASTER_EMAIL: return {"error": "Nie można zmienić Mastera"}
    if auth_role == "admin" and new_role == "admin": return {"error": "Admin nie może nadać roli Admina"}
    
    db.collection("users").document(target_email).set({"role": new_role})
    await manager.broadcast(json.dumps({"type": "update"}))
    return {"ok": True}

@app.get("/api/admin/get_users")
async def get_users():
    return [{"email": d.id, **d.to_dict()} for d in db.collection("users").stream()]

@app.post("/api/admin/set_password")
async def set_password(request: Request):
    data = await request.json()
    auth_role = data.get("auth_role")
    if auth_role not in ["master", "admin"]: return {"error": "Brak uprawnień"}
    
    view = data.get("view")
    pwd = data.get("password")
    db.collection("config").document("passwords").set({f"{view}_pwd": pwd}, merge=True)
    return {"ok": True}

@app.post("/api/auth/verify_password")
async def verify_pwd(request: Request):
    data = await request.json()
    view = data.get("view")
    pwd = data.get("password")
    doc = db.collection("config").document("passwords").get()
    correct = doc.to_dict().get(f"{view}_pwd") if doc.exists else None
    if not correct: return {"ok": True}
    return {"ok": pwd == correct}

@app.post("/api/admin/save_product")
async def save_product(
    key: str=Form(...), name: str=Form(...), price: float=Form(...), description: str=Form(""),
    allergens: str=Form(""), kcal: str=Form(""), weight: str=Form(""),
    sort_order: int=Form(10), to_kitchen: str=Form("true"),
    file: Optional[UploadFile]=File(None)
):
    print(f"DEBUG: Saving product {key}, Name: {name}, Price: {price}")
    # Handle boolean conversion manually to be robust
    is_kitchen = str(to_kitchen).lower() == "true"
    
    update_data = {
        "name": name, "price": price, "description": description, "allergens": allergens,
        "kcal": kcal, "weight": weight, "sort_order": sort_order, "to_kitchen": is_kitchen
    }
    if file and file.filename:
        img_dir = APP_DIR / "static" / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        with open(img_dir / file.filename, "wb+") as f: f.write(content)
        update_data["image"] = file.filename
        
    db.collection("menu").document(str(key)).set(update_data, merge=True)
    await manager.broadcast(json.dumps({"type": "update"}))
    print(f"DEBUG: Product {key} saved successfully.")
    return {"ok": True}

# --- TABLES & CALLS ---

@app.get("/api/active_tables")
async def active_tables(): 
    return {"tables": [d.to_dict() for d in db.collection("active_tables").stream()]}

@app.post("/api/call_waiter/{table_num}")
async def call_waiter(table_num: int):
    db.collection("active_tables").document(str(table_num)).set({"call_waiter": True}, merge=True)
    await manager.broadcast(json.dumps({"type": "update"}))
    return {"ok": True}

@app.post("/api/pay_request/{table_num}")
async def pay_request(table_num: int):
    db.collection("active_tables").document(str(table_num)).set({"pay_request": True}, merge=True)
    await manager.broadcast(json.dumps({"type": "update"}))
    return {"ok": True}

@app.post("/api/reset_call/{table_num}")
async def reset_call(table_num: int):
    db.collection("active_tables").document(str(table_num)).set({"call_waiter": False, "pay_request": False}, merge=True)
    await manager.broadcast(json.dumps({"type": "update"}))
    return {"ok": True}

# --- ORDERS ---

@app.post("/api/update_status/{id}")
async def update_status(id: str, request: Request):
    try:
        payload = await request.json()
        db.collection("orders").document(id).update({"status": payload.get("status")})
        await manager.broadcast(json.dumps({"type": "update"}))
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/orders")
async def add_order(order: dict):
    try:
        table_num = str(order.get("table_number"))
        current_session = order.get("session_id")
        
        if not current_session:
            table_ref = db.collection("active_tables").document(table_num).get()
            current_session = table_ref.to_dict().get("session_id") if table_ref.exists else "unknown"

        # Bezpieczniejsza konwersja ceny
        price_val = order.get("price", 0.0)
        try:
            price_val = float(price_val)
        except ValueError:
            price_val = 0.0

        order_data = {
            "table_number": table_num,
            "burger_name": order.get("burger_name"),
            "price": price_val,
            "status": "nowe",
            "paid": False,
            "session_id": current_session,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "note": order.get("note", ""),
            "to_kitchen": order.get("to_kitchen", True)
        }
        db.collection("orders").add(order_data)
        await manager.broadcast(json.dumps({"type": "update"}))
        return {"ok": True}
    except Exception as e:
        print("Błąd dodawania zamówienia:", e)
        return {"error": str(e)}

# BARDZO WAŻNE: Poniższej funkcji brakowało w przesłanym kodzie!
@app.get("/api/all_orders")
async def all_orders():
    try:
        docs = db.collection("orders").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100).stream()
        orders = []
        for d in docs:
            data = d.to_dict()
            data["id"] = d.id
            if "to_kitchen" not in data:
                menu_ref = db.collection("menu").document(data.get("burger_name", "")).get()
                data["to_kitchen"] = menu_ref.to_dict().get("to_kitchen", True) if menu_ref.exists else True
            
            data["status_pl"] = STATUS_MAP.get(data.get("status"), "Oczekujące")
            orders.append(data)
        return {"orders": orders}
    except Exception as e:
        print("Błąd pobierania zamówień:", e)
        return {"error": str(e), "orders": []}

@app.post("/api/mark_paid/{table_num}")
async def mark_paid(table_num: int):
    table_str = str(table_num)
    table_ref = db.collection("active_tables").document(table_str).get()
    if not table_ref.exists:
        return {"error": "Brak aktywnej sesji"}
    
    current_session = table_ref.to_dict().get("session_id")
    docs = db.collection("orders").where("table_number", "==", table_str).where("session_id", "==", current_session).where("paid", "==", False).stream()
    
    batch = db.batch()
    found = False
    orders_to_print = []
    for d in docs:
        batch.update(db.collection("orders").document(d.id), {"paid": True})
        orders_to_print.append(d.to_dict())
        found = True
    if found: batch.commit()
    db.collection("active_tables").document(table_str).update({"pay_request": False})
    await manager.broadcast(json.dumps({"type": "update"}))
    if orders_to_print:
        await manager.broadcast(json.dumps({
            "type": "receipt",
            "table_number": table_str,
            "items": orders_to_print
        }))
    return {"ok": True}

# --- WYDAWKA API ---

@app.get("/api/wydawka/bony")
async def get_wydawka_bony():
    docs = db.collection("orders").where("status", "in", ["nowe", "preparing", "ready"]).stream()
    grouped_orders = defaultdict(list)
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        key = f"{data.get('table_number')}_{data.get('session_id')}"
        grouped_orders[key].append(data)

    do_oplacenia = []
    gotowe_do_wydania = []
    for key, items in grouped_orders.items():
        total_price = sum(float(item.get("price", 0)) for item in items)
        is_unpaid = any(item.get("paid") == False for item in items)
        is_ready = all(item.get("status") == "ready" for item in items)
        bon_id = str(abs(hash(items[0].get("session_id", "brak"))))[:3]
        
        ticket = {
            "bon_id": f"#{bon_id}",
            "table_number": items[0].get("table_number"),
            "session_id": items[0].get("session_id"),
            "items": items,
            "total_price": total_price,
            "is_unpaid": is_unpaid
        }
        if is_ready: gotowe_do_wydania.append(ticket)
        else: do_oplacenia.append(ticket)

    return {"do_oplacenia": do_oplacenia, "gotowe_do_wydania": gotowe_do_wydania}

@app.post("/api/wydawka/wydaj_bon")
async def wydaj_bon(payload: dict):
    session_id = payload.get("session_id")
    table_number = str(payload.get("table_number"))
    docs = db.collection("orders").where("table_number", "==", table_number).where("session_id", "==", session_id).where("status", "==", "ready").stream()
    batch = db.batch()
    for d in docs:
        batch.update(db.collection("orders").document(d.id), {"status": "closed"})
    batch.commit()
    await manager.broadcast(json.dumps({"type": "update"}))
    return {"ok": True}

@app.get("/api/admin/stats")
async def admin_stats(start_date: str, end_date: str):
    try:
        docs = db.collection("orders").stream()
        revenue = 0.0
        products = defaultdict(int)
        for d in docs:
            data = d.to_dict()
            ts = data.get("timestamp")
            if ts:
                ts_str = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
                date_str = ts_str[:10]
                if start_date <= date_str <= end_date:
                    revenue += float(data.get("price", 0))
                    name = data.get("burger_name", "Nieznany")
                    if name:
                        products[name] += 1
        return {"revenue": revenue, "products": dict(sorted(products.items(), key=lambda x: x[1], reverse=True)[:10])}
    except Exception as e:
        return {"revenue": 0.0, "products": {}, "error": str(e)}

# --- HTML PAGES ---
# --- HTML PAGES ---
@app.post("/api/clear_table/{table_id}")
async def clear_table(table_id: str):
    # Całkowite usunięcie dokumentu = stolik w 100% ZIELONY/WOLNY
    db.collection("active_tables").document(table_id).delete()
    await manager.broadcast(json.dumps({"type": "update"}))
    return {"ok": True}
# --- HTML PAGES ---

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request, table: Optional[str] = None, burger_session: Optional[str] = Cookie(None)):
    if not burger_session: 
        burger_session = str(uuid.uuid4())
    
    menu_dict = {d.id: d.to_dict() for d in db.collection("menu").stream()}
    menu = dict(sorted(menu_dict.items(), key=lambda x: int(x[1].get('sort_order', 99))))

    # JAWNY SŁOWNIK CONTEXT
    ctx = {
        "request": request, 
        "menu": menu, 
        "session_table": table, 
        "table_locked": False, 
        "locked_num": None, 
        "my_session_id": burger_session
    }

    if table:
        table_ref = db.collection("active_tables").document(str(table))
        table_doc = table_ref.get()
        if table_doc.exists:
            existing_session = table_doc.to_dict().get("session_id")
            if existing_session and existing_session != burger_session:
                ctx["table_locked"] = True
                ctx["locked_num"] = table
                ctx["session_table"] = None
        
        if not ctx["table_locked"]:
            table_ref.set({"table_number": int(table), "session_id": burger_session}, merge=True)

    # UŻYCIE ARGUMENTU NAZWANEGO context=
    resp = templates.TemplateResponse(request=request, name="index.html", context=ctx)
    resp.set_cookie(key="burger_session", value=burger_session, max_age=86400)
    return resp

@app.get("/wydawka", response_class=HTMLResponse)
async def wydawka_page(request: Request):
    return templates.TemplateResponse(request=request, name="wydawka.html", context={"request": request})

@app.get("/kds", response_class=HTMLResponse)
async def kds(request: Request):
    return templates.TemplateResponse(request=request, name="kds.html", context={"request": request})

@app.get("/waiter", response_class=HTMLResponse)
async def waiter(request: Request):
    return templates.TemplateResponse(request=request, name="waiter.html", context={"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html", context={"request": request})

@app.get("/master", response_class=HTMLResponse)
async def master_page(request: Request):
    return templates.TemplateResponse(request=request, name="master.html", context={"request": request, "client_id": GOOGLE_CLIENT_ID})