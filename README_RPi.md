# Elvis POS — Aplikacja RPi (Gateway)

Lokalna aplikacja działająca na Raspberry Pi w restauracji.
Łączy terminal drukarski / ekran POS z chmurą Elvis.

---

## Co robi rpi_app.py

1. **Serwer lokalny (Flask, port 8080)** — panel konfiguracyjny dostępny w sieci WiFi restauracji
2. **Klient WebSocket** — łączy się do chmury, odbiera zdarzenia w czasie rzeczywistym
3. **Paragon** — po zamknięciu rachunku w chmurze RPi odbiera `receipt` i loguje go (miejsce na integrację z drukarką)
4. **Rejestracja urządzenia** — wysyła swój klucz i IP do Firestore → widoczne w zakładce POS RPi panelu admina

---

## Instalacja

```bash
# Na Raspberry Pi OS (Debian)
pip install -r requirements_rpi.txt
python rpi_app.py
```

Aplikacja startuje na `http://0.0.0.0:8080` — otwórz w przeglądarce po adresie IP RPi.

### Automatyczny start przy uruchomieniu systemu

```bash
# Utwórz plik serwisu systemd
sudo nano /etc/systemd/system/elvis-rpi.service
```

Wklej:
```ini
[Unit]
Description=Elvis RPi Gateway
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/elvis3-app
ExecStart=/usr/bin/python3 /home/pi/elvis3-app/rpi_app.py
Restart=always
RestartSec=5
Environment=DATA_DIR=/home/pi/elvis3-app/data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable elvis-rpi
sudo systemctl start elvis-rpi
```

---

## Konfiguracja (pierwsze uruchomienie)

1. Otwórz przeglądarkę: `http://<IP-RPi>:8080`
2. Zaloguj się kontem **Master** (Google Auth)
3. Wpisz URL chmury: `https://elvis-app-xyz.a.run.app`
4. Wpisz ID urządzenia: np. `Elvis_KWI_0326`
5. Kliknij **Zapisz i Połącz** — RPi zrestartuje się i połączy z chmurą

Konfiguracja zapisuje się do `./data/device_config.json` i `./data/device_key.txt`.

---

## Zmienne środowiskowe

| Zmienna             | Domyślna           | Opis                              |
|---------------------|--------------------|-----------------------------------|
| `DATA_DIR`          | `./data`           | Folder na pliki konfiguracyjne    |
| `CLOUD_BASE_URL`    | `http://127.0.0.1:8000` | URL chmury (można nadpisać plikiem) |
| `GOOGLE_CLIENT_ID`  | (wbudowany)        | Client ID Google OAuth            |
| `SESSION_SECRET`    | `elvis-rpi-secret-key-2026` | Klucz sesji Flask        |

---

## Panele dostępne lokalnie z RPi

| Adres                   | Zawartość                              |
|-------------------------|----------------------------------------|
| `http://<IP>:8080/`     | Panel konfiguracyjny Gateway           |
| `http://<IP>:8080/pos`  | Stacja kelnera (iframe → chmura)       |
| `http://<IP>:8080/kds`  | Kuchnia KDS (iframe → chmura)          |
| `http://<IP>:8080/wydawka` | Wydawka/Expo (iframe → chmura)      |

---

## Flow paragonu

```
Kelner zamyka rachunek (/api/mark_paid)
         │
         ▼
Chmura zapisuje paragon do Firestore (config/last_receipt)
         │
         ▼
Chmura broadcastuje przez WebSocket:
  { type: "receipt", table_number, items[], total, timestamp }
         │
    ┌────┴────┐
    │         │
    ▼         ▼
admin.html   rpi_app.py
(zakładka    (event_log + obsługa drukarki)
 POS RPi)
```

Jeśli chcesz podłączyć fizyczną drukarkę, dodaj kod drukujący w `ws_client_loop()` po linii:
```python
if data.get("type") == "receipt":
    # tutaj: wywołanie drukarki ESC/POS przez python-escpos
```

---

## Zależności (requirements_rpi.txt)

```
flask
requests
websockets
google-auth
```

Znacznie lżejszy stack niż chmura — bez FastAPI, Firestore SDK, PyJWT.

---

## Logi

Live log zdarzeń widoczny w panelu gateway (`/`) w sekcji **Live Activity Stream**.
Ostatnie 20 wpisów trzymane w pamięci. Reset po restarcie procesu.
