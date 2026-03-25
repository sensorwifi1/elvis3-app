import os, requests, json, uuid
from fastapi import FastAPI, Request, File, UploadFile, Form, Cookie, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.cloud import firestore
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from collections import defaultdict

app = FastAPI()
APP_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

db = firestore.Client(database="elvis3-db")

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

# --- MENU & LAYOUT ---

@app.get("/api/get_menu")
async def get_menu(): 
    menu_dict = {d.id: d.to_dict() for d in db.collection("menu").stream()}
    return dict(sorted(menu_dict.items(), key=lambda x: int(x[1].get('sort_order', 99))))
# Podmień ten fragment w Twoim pliku Python (main.py):

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
        # Zmuszamy serwer do odebrania JSONa z frontendu
        payload = await request.json()
        db.collection("config").document("floor_plan").set(payload)
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}
@app.post("/api/admin/save_product")
async def save_product(
    key: str=Form(...), name: str=Form(...), price: float=Form(...), description: str=Form(""),
    allergens: str=Form(""), kcal: str=Form(""), weight: str=Form(""),
    sort_order: int=Form(10), to_kitchen: bool=Form(True),
    image_name: Optional[str]=Form(None), file: Optional[UploadFile]=File(None)
):
    final_image = image_name
    if file and file.filename:
        img_dir = APP_DIR / "static" / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        with open(img_dir / file.filename, "wb+") as f: f.write(file.file.read())
        final_image = file.filename
    db.collection("menu").document(key).set({
        "name": name, "price": price, "description": description, "allergens": allergens,
        "kcal": kcal, "weight": weight, "image": final_image, "sort_order": sort_order, "to_kitchen": to_kitchen
    }, merge=True)
    return {"ok": True}

# --- TABLES & CALLS ---

@app.get("/api/active_tables")
async def active_tables(): 
    return {"tables": [d.to_dict() for d in db.collection("active_tables").stream()]}

@app.post("/api/call_waiter/{table_num}")
async def call_waiter(table_num: int):
    db.collection("active_tables").document(str(table_num)).set({"call_waiter": True}, merge=True)
    return {"ok": True}

@app.post("/api/pay_request/{table_num}")
async def pay_request(table_num: int):
    db.collection("active_tables").document(str(table_num)).set({"pay_request": True}, merge=True)
    return {"ok": True}

@app.post("/api/reset_call/{table_num}")
async def reset_call(table_num: int):
    db.collection("active_tables").document(str(table_num)).set({"call_waiter": False, "pay_request": False}, merge=True)
    return {"ok": True}

# --- ORDERS ---

@app.post("/api/update_status/{id}")
async def update_status(id: str, request: Request):
    try:
        payload = await request.json()
        db.collection("orders").document(id).update({"status": payload.get("status")})
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
    for d in docs:
        batch.update(db.collection("orders").document(d.id), {"paid": True})
        found = True
    if found: batch.commit()
    db.collection("active_tables").document(table_str).update({"pay_request": False})
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
    return {"ok": True}

# --- HTML PAGES ---
# --- HTML PAGES ---
@app.post("/api/clear_table/{table_id}")
async def clear_table(table_id: str):
    # Całkowite usunięcie dokumentu = stolik w 100% ZIELONY/WOLNY
    db.collection("active_tables").document(table_id).delete()
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