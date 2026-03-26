# Elvis Burger POS — System Gastronomiczny v3.0

Kompletny system zarządzania restauracją oparty na chmurze Google Cloud Platform.
Architektura: **chmura (FastAPI) + terminal RPi (Flask) + Firestore + WebSocket**.

---

## Architektura systemu

```
┌─────────────────────────────────────────────────────────┐
│                   CHMURA (Google Cloud Run)              │
│                                                         │
│   main.py  (FastAPI + Uvicorn)                          │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│   │ /admin   │  │ /waiter  │  │ /kds     │             │
│   │ /master  │  │ /wydawka │  │ /        │             │
│   └──────────┘  └──────────┘  └──────────┘             │
│                   WebSocket Hub (/ws)                   │
│                   Firestore Client                      │
└─────────────────────────┬───────────────────────────────┘
                          │ WebSocket (wss://)
                          │ Firestore SDK
                          │
┌─────────────────────────▼───────────────────────────────┐
│               RPi (lokal w restauracji)                  │
│                                                         │
│   rpi_app.py  (Flask + asyncio)                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│   │ /        │  │ /pos     │  │ /kds     │             │
│   │ gateway  │  │ (iframe) │  │ (iframe) │             │
│   └──────────┘  └──────────┘  └──────────┘             │
│   WS Client → odbiera receipt → loguje do event_log     │
│   Drukarka fiskalna / Ekran POS                         │
└─────────────────────────────────────────────────────────┘
```

---

## Panele i ich funkcje

### `/` — Menu Klienta
- Zamawianie przez QR kod przy stoliku
- Sesja przypisana do stolika (izolacja między gośćmi)
- Integracja z Gemini AI: żarty i ciekawostki o daniach
- Wezwanie kelnera / prośba o rachunek

### `/waiter` — Stacja Kelnera (POS)
- Logowanie PIN-em pracownika
- Dynamiczna mapa stolików (wolne / zajęte)
- Podgląd zamówień na stoliku w czasie rzeczywistym
- Obsługa wezwań i płatności
- Wystawianie rachunku → broadcast `receipt` do RPi

### `/kds` — Kitchen Display System (Kuchnia)
- Logowanie hasłem
- Lista bonów w kolejności: nowe → w przygotowaniu → gotowe
- Timer na każdym bonie
- Zmiany statusu broadcastowane do wszystkich paneli

### `/wydawka` — Wydawka (Expo)
- Logowanie hasłem
- Bony gotowe do wydania (wszystkie pozycje = ready)
- Wydanie bonu → zamknięcie zamówienia

### `/admin` — Panel Admina
- Logowanie PIN-em (domyślny: `102938`)
- **Dashboard**: utarg dzienny, statystyki, mapa sali
- **POS RPi**: status połączenia RPi + live kolejka druku (paragonów)
- **Statystyki**: filtrowanie dat, wykres bestselerów
- **Mapa Sali**: edytor Drag & Drop stolików
- **Produkty**: edytor menu z uploadem zdjęć
- **Pracownicy**: zarządzanie PIN-ami i rolami
- **Uprawnienia**: nadawanie dostępu Google (email → rola)

### `/master` — Panel Mastera
- Logowanie Google Auth (tylko `hajdukiewicz@gmail.com`)
- Nadawanie ról Google (admin, kuchnia, wydawka)
- Ustawianie haseł do paneli KDS / Wydawka

---

## Poziomy dostępu

| Poziom   | Metoda logowania        | Dostęp                                  |
|----------|-------------------------|-----------------------------------------|
| Klient   | Brak (sesja cookie)     | Menu, zamówienia, wezwanie kelnera      |
| Kelner   | PIN (6+ znaków)         | `/waiter` — POS                         |
| KDS      | Hasło lub PIN           | `/kds` — kuchnia                        |
| Wydawka  | Hasło lub PIN           | `/wydawka` — expo                       |
| Admin    | PIN `102938` lub własny | `/admin` — zarządzanie + uprawnienia    |
| Master   | Google Auth             | `/master` + pełny admin                 |

---

## Synchronizacja WebSocket

Każda zmiana w systemie broadcastuje `{"type": "update"}` do wszystkich podłączonych klientów.
Paragon po zamknięciu rachunku broadcastuje `{"type": "receipt", ...}` → RPi + zakładka POS RPi w adminie.

Typy wiadomości:
- `update` — ogólne odświeżenie danych
- `receipt` — paragon z pozycjami, numerem stolika, sumą
- `device_status` — RPi rejestruje się jako online/offline

---

## API — kluczowe endpointy

| Metoda | Endpoint                        | Opis                              |
|--------|---------------------------------|-----------------------------------|
| GET    | `/api/get_menu`                 | Pobierz menu                      |
| GET    | `/api/all_orders`               | Wszystkie zamówienia (100 last)   |
| POST   | `/api/orders`                   | Dodaj zamówienie                  |
| POST   | `/api/update_status/{id}`       | Zmień status zamówienia           |
| POST   | `/api/mark_paid/{table}`        | Zamknij rachunek + wyślij paragon |
| POST   | `/api/admin/save_product`       | Zapisz produkt (multipart)        |
| POST   | `/api/admin/save_layout`        | Zapisz mapę sali                  |
| POST   | `/api/admin/save_staff`         | Dodaj/edytuj pracownika           |
| GET    | `/api/admin/get_staff`          | Lista pracowników                 |
| POST   | `/api/admin/set_role`           | Nadaj rolę Google                 |
| GET    | `/api/admin/get_users`          | Lista dostępów Google             |
| GET    | `/api/admin/stats`              | Statystyki sprzedaży              |
| GET    | `/api/admin/last_receipt`       | Ostatni paragon (Firestore)       |
| POST   | `/api/admin/resend_receipt`     | Wyślij paragon ponownie           |
| POST   | `/api/auth/staff_login`         | Logowanie PIN-em                  |
| POST   | `/api/auth/login`               | Logowanie Google                  |
| POST   | `/api/auth/verify_password`     | Weryfikacja hasła panelu          |
| GET    | `/api/device_status/{key}`      | Status urządzenia RPi             |
| WS     | `/ws?device_key=...`            | WebSocket hub                     |

---

## Baza danych — Firestore

| Kolekcja        | Dokument / klucz     | Zawartość                          |
|-----------------|----------------------|------------------------------------|
| `menu`          | `{klucz}`            | name, price, image, to_kitchen...  |
| `orders`        | auto-ID              | burger_name, table, status, paid.. |
| `active_tables` | `{numer_stolika}`    | session_id, call_waiter, pay_req.. |
| `staff`         | `{pin}`              | name, role                         |
| `users`         | `{email}`            | role                               |
| `devices`       | `{device_key}`       | status, ip, last_seen              |
| `config`        | `floor_plan`         | width, height, tables[]            |
| `config`        | `passwords`          | kds_pwd, wydawka_pwd               |
| `config`        | `last_receipt`       | ostatni paragon                    |

---

## Deploy — Google Cloud Run

```bash
# Jednorazowo: buduj i deploy
gcloud run deploy elvis-app \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLIENT_ID=YOUR_ID

# Lub przez Docker
docker build -t elvis-app .
docker run -p 8080:8080 elvis-app
```

Wymagane zmienne środowiskowe:
- `GOOGLE_CLIENT_ID` — ID aplikacji OAuth 2.0 z Google Console
- `GOOGLE_APPLICATION_CREDENTIALS` — ścieżka do klucza serwisowego Firestore (lub ADC)

---

## Instalacja lokalna (dev)

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## Pliki projektu

```
elvis3-app/
├── main.py               # Serwer chmury (FastAPI)
├── rpi_app.py            # Aplikacja RPi (Flask)
├── requirements.txt      # Zależności chmury
├── requirements_rpi.txt  # Zależności RPi
├── Dockerfile            # Obraz Docker (Cloud Run)
├── wipe_db.py            # Skrypt czyszczenia Firestore
├── templates/
│   ├── index.html        # Menu klienta
│   ├── waiter.html       # Stacja kelnera
│   ├── kds.html          # Kuchnia
│   ├── wydawka.html      # Wydawka/Expo
│   ├── admin.html        # Panel admina
│   └── master.html       # Panel mastera
└── static/
    ├── style.css
    └── images/           # Zdjęcia produktów
```
