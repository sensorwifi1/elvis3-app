---
description: all features based
---

🍔 Elvis RPi Wi-Fi Kiosk
System uruchamiany na Raspberry Pi, odpowiedzialny za:
konfigurację Wi-Fi przez przeglądarkę
identyfikację urządzenia (SN + device_key)
komunikację z backendem (elvis.zjedz.it)
przyszłą integrację z drukarką fiskalną

🔧 Funkcjonalności
📡 Konfiguracja Wi-Fi (portal lokalny)
dostęp przez przeglądarkę:

 http://elvis.local:8080

 lub:

 http://<IP_RPI>:8080


skanowanie dostępnych sieci Wi-Fi (nmcli)
wybór sieci z listy lub ręczne wpisanie SSID
zapis konfiguracji do pliku:

 /data/wifi_config.json


natychmiastowa próba połączenia

🆔 Identyfikacja urządzenia
Każde urządzenie posiada:
serial_number (z /proc/cpuinfo)
device_key (np. Elvis_KWI_0326)
pubsub_topic (np. devices/Elvis_KWI_0326)
Dostęp przez API:
GET /api/device_identity
Przykład:
{"device_k{"device_key":"Elvis_KWI_0326","ok":true,"pubsub_topic":"devices/Elvis_KWI_0326","serial_number":"10000000f143bf48"}
ey":"Elvis_KWI_0326","ok":true,"pubsub_topic":"devices/Elvis_KWI_0326","serial_number":"10000000f143bf48"}

{
 "ok": true,
 "serial_number": "f334439afadbb5ee",
 "device_key": "Elvis_KWI_0326",
 "pubsub_topic": "devices/Elvis_KWI_0326"
}

💾 Lokalna pamięć danych
Wszystkie dane trzymane są w katalogu:
/data
(pliki mapowane z hosta przez Docker volume)
Plik
Opis
wifi_config.json
zapisane dane Wi-Fi
status.json
status konfiguracji
device_sn.txt
numer seryjny
device_key.txt
unikalny identyfikator urządzenia


🔑 Device Key (identyfikator systemowy)
Używany jako:
identyfikator urządzenia
topic Pub/Sub / MQTT
powiązanie z backendem Elvis
Przykład:
Elvis_KWI_0326
Topic:
devices/Elvis_KWI_0326

🌐 Integracja z backendem
Urządzenie komunikuje się z:
http://elvis.zjedz.it/
Planowane funkcje:
pobieranie konfiguracji urządzenia
wysyłanie statusu (online/offline)
obsługa zamówień
komunikacja Pub/Sub (MQTT / HTTP)

🧾 Integracja z drukarką fiskalną (planowana)
RPi będzie działać jako pośrednik fiskalny:
odbiera zamówienia z backendu
formatuje dane fiskalne
wysyła do drukarki fiskalnej (USB / RS232 / Ethernet)
Możliwe tryby:
ESC/POS
dedykowany driver producenta
komunikacja TCP/IP

🔌 Docker
Uruchomienie:
sudo docker run -d \
 --name wifi-portal \
 --restart unless-stopped \
 --network host \
 --privileged \
 -e DATA_DIR=/data \
 -e WIFI_IFACE=wlan0 \
 -e TARGET_URL=http://elvis.zjedz.it/ \
 -v "$(pwd)/data:/data" \
 -v /run/dbus:/run/dbus \
 rpi4-wifi-kiosk-wifi-portal

🔒 Bezpieczeństwo
Możliwości:
ograniczenie dostępu do portalu tylko do LAN
firewall (iptables) na wlan0
brak publicznego dostępu do API

📡 API
🔍 Skan sieci
GET /api/scan
📶 Status Wi-Fi
GET /api/status
🆔 Tożsamość urządzenia
GET /api/device_identity
🔑 Device Key
GET /api/device_key
POST /api/device_key

🚀 Roadmap
Wi-Fi provisioning
Device identity
Docker deployment
MQTT / PubSub integration
Backend Elvis sync
Printer fiscal integration
Offline mode + queue
OTA update

🧠 Architektura
[ User / Browser ]
       ↓
[ Flask Wi-Fi Portal ]
       ↓
[ nmcli / NetworkManager ]
       ↓
[ Wi-Fi ]
       ↓
[ Backend: elvis.zjedz.it ]
       ↓
[ (future) Printer fiskalna ]

📌 Podsumowanie
Raspberry Pi pełni rolę:
🔌 gateway'a sieciowego (Wi-Fi provisioning)
🆔 identyfikatora urządzenia w systemie Elvis
🌐 klienta backendu (elvis.zjedz.it)
🧾 przyszłego sterownika drukarki fiskalnej

Jeśli chcesz, mogę dorzucić jeszcze:
schemat architektury (ładny diagram)
README pod produkcję (systemd + autostart)
albo wersję pod OTA update + provisioning QR code 👍 
🍔 Burger POS NextGen – Data-Driven Gastronomy & Smart HVAC
Rozproszony ekosystem All-in-One dla branży HoReCa. Architektura łączy aplikację chmurową typu Serverless (POS/KDS), analitykę biznesową w czasie rzeczywistym oraz warstwę Edge Computing (IoT, telemetria środowiskowa, automatyzacja fiskalna).

🚀 Architektura i Kluczowe Moduły
1. 👻 Duch Burgera (Conversational AI & Upselling)
Silnik: Google Gemini AI (Flash dla niskich opóźnień, Pro dla złożonej analityki). Rola: Kontekstowy silnik rekomendacyjny (Upselling) operujący na wektorach preferencji klienta. Generuje dynamiczny mikro-copywriting, maksymalizując średnią wartość koszyka (AOV - Average Order Value) przy zachowaniu niskiego progu tarcia (friction) w interfejsie.
2. 🧾 Fiskalizacja 2.0 (Edge Computing Node)
Delegacja sprzętowa realizowana przez mikrokomputer (Raspberry Pi) pełniący rolę bramy brzegowej (Edge Node) komunikującej się z systemem chmurowym. Integracja: Bezpośrednia kontrola protokołu drukarek Elzab Zeta. Obieg dokumentów: Pełna elastyczność prawna: E-paragon (paperless), wydruk fiskalny, bony niefiskalne (kuchnia/bar), tryb operacyjny (dark kitchen). Niezawodność: Asynchroniczne kolejkowanie zadań wydruku zapobiegające blokowaniu głównego wątku sprzedażowego.
3. 🌬️ Smart HVAC & Telemetry (IoT Data Pipeline)
System monitorowania jakości mikroklimatu, zintegrowany z modelem operacyjnym lokalu. Hardware: Moduły ESP32 z precyzyjnymi sensorami SCD40 (NDIR CO2) oraz SHT40 (Temp/Wilg). Data Ingestion: Szereg czasowy (Time-Series Data) próbkowany co 15 minut i wysyłany do Google Cloud Monitoring. AI Predictive Maintenance: Algorytmy Gemini pełniące rolę eksperta HVAC. Badanie korelacji między zagęszczeniem osób na metrze kwadratowym (wynikającym z Live-POS) a dynamiką stężenia CO2 (ppm), celem optymalizacji cykli rekuperacji i redukcji kosztów energii.
4. 👨‍🍳 KDS Line (Event-Driven Kitchen Display)
Zarządzanie cyklem życia zamówienia (State Machine) zoptymalizowane pod kątem wysokiej przepustowości (High Throughput). Traceability & Auditing: Zapisywanie precyzyjnych znaczników czasu (ISO Timestamp) przy każdej zmianie stanu: New -> Preparing -> Ready -> Closed. Concurrency Control: Niezależne modyfikatory stanu dla pojedynczych pozycji (biletów), pozwalające na asynchroniczne wydawanie dań z jednego zamówienia. Wizualizacja: Dynamiczny Grid z systemem wczesnego ostrzegania (Color-coded SLA Alerts) w przypadku przekroczenia zdefiniowanego czasu SLA (np. >120 sekund).
5. 📍 Smart Floor Plan (Synchronizacja Stanów)
Real-time State Sync: Interaktywna mapa lokalu dla obsługi, reagująca na zdarzenia asynchroniczne (WebSocket / Smart Polling).
Call-Waiter Priorities: Wielostopniowy system priorytetyzacji alertów (np. fioletowy puls dla płatności, niebieski dla obsługi), redukujący czas reakcji personelu (Response Time). Session Locking (Smart Lock): Zaawansowane blokowanie współbieżności (Mutex/Lock) na poziomie bazy danych – zapobiega kolizjom, gdy wielu klientów próbuje modyfikować ten sam koszyk przy jednym stoliku.
📊 Moduł: Business Intelligence & Admin Dashboard
Moduł analityczny przeznaczony dla kadry zarządzającej (C-Level / Store Manager), pozwalający na monitorowanie kluczowych wskaźników wydajności (KPI) lokalu w czasie rzeczywistym. Baza Firestore zasila ten wbudowany moduł analityczny.
🚀 Kluczowe Metryki (Dzienne)
Gross Revenue (Utarg): Suma wartości (price) wszystkich zamówień z dzisiejszego dnia roboczego. Podstawa do raportu kasowego.
Sales Volume (Ilość): Całkowita liczba sprzedanych pozycji z menu. Pokazuje natężenie ruchu (Traffic).
Average Ticket Time (Średni czas kuchni): Algorytm wylicza różnicę między znacznikiem time_ordered a time_ready (lub time_closed) dla każdego burgera, dając obiektywny obraz szybkości wydawania dań.
🛠️ Architektura Danych
Backend: Endpoint /api/admin/report agreguje dane ze strumienia bazy Firestore (Document DB).
Filtrowanie Czasowe: System automatycznie odrzuca stare zamówienia, analizując tylko te z dzisiejszą datą (Timezone UTC/Local sync).
Prezentacja: Asynchroniczny panel HTML5/CSS Grid w trybie Dark Mode, zbudowany z myślą o czytelności na tabletach kierowników zmiany.
Architektura zaprojektowana do podejmowania decyzji w oparciu o dane (Data-Driven Decisions).

🛠️ Stack Technologiczny & Infrastruktura
Backend: Python 3.12+ (FastAPI) – Wysokowydajny, asynchroniczny serwer API. Baza Danych: Google Firestore – Baza dokumentowa (NoSQL) zapewniająca synchronizację klientów w czasie rzeczywistym. Infrastruktura: Google Cloud Run (Serverless) – Automatyczne skalowanie do zera (Zero-Scale) redukujące koszty w godzinach nocnych oraz błyskawiczne skalowanie poziome (Horizontal Pod Autoscaling) w godzinach szczytu. Telemetria: Google Cloud Monitoring & Cloud Logging. Hardware: RPi 4 (Edge), ESP32 (Sensors). Frontend: Vanilla JS + CSS Grid – Lekki, bezramkowy interfejs (Zero-dependency UI) optymalizowany pod kątem urządzeń mobilnych klientów (PWA-ready).

🛠️ Wdrażanie i Rozbudowa: Przewodnik Programisty
Ten dokument opisuje aktualną architekturę systemu zjedz.it Burger POS oraz szczegółowy plan roadmapy technicznej dla programistów wdrażających zaawansowane funkcje skalowania i synchronizacji w czasie rzeczywistym.

🏗️ 1. Architektura Systemu (Stan Docelowy)
System przechodzi z architektury monolitycznej na rozproszoną, chmurową architekturę sterowaną zdarzeniami (Event-Driven Architecture).
Kluczowe Komponenty:
Backend (Cloud Run - Python/FastAPI): Bezstanowa logika aplikacji, obsługa API, zarządzanie tunelami WebSocket i publikacja zdarzeń do Pub/Sub.
Baza Danych (Firestore): Przechowywanie danych strukturalnych (menu, zamówienia, sesje stolików).
Storage Grafiki (Google Cloud Storage - GCS + CDN): Tani i szybki storage dla wszystkich zdjęć produktów i logotypów.
Komunikacja Real-time (WebSockets - Socket.io): Błyskawiczna synchronizacja interfejsów frontendowych (Tablety, KDS, Wydawka).
Komunikacja Cloud-to-Local (Google Cloud Pub/Sub): Niezawodny kanał przesyłania komend sterujących do lokalnego sprzętu (Drukarka Fiskalna na RPi).
Lokalny Kontroler (Raspberry Pi): Subskrybent Pub/Sub, sterownik drukarki fiskalnej USB.

🖼️ 2. Zmiany w Zarządzaniu Grafiką (Wdrożone)
Ze względu na koszty i wydajność (Cold Start), zakazuje się trzymania dużej ilości grafik w folderze static/images kontenera aplikacji.
Szczegóły Wdrożenia:
GCS Bucket: Utworzono globalny bucket zjedzit-burger-images w regionie europe-west1.
Struktura Folderów: bucket/restaurant_id/menu/nazwa_pliku.jpg.
Firestore: Pola image_url w dokumentach produktów muszą teraz zawierać pełny, publiczny adres URL z GCS/CDN (np. https://cdn.zjedz.it/...).
Optymalizacja plików: Przed uploadem należy skompresować pliki JPG/PNG (TinyPNG/Imagemagick) i upewnić się, że rozdzielzzość nie przekracza 800x600px dla zdjęć dań. Ikony i logotypy należy wgrywać jako SVG.
Deployment: Przy gcloud run deploy należy używać flagi --execution-environment=gen2 dla poprawnej obsługi bibliotek klienckich GCS w Pythonie.

🚀 3. Plan Rozbudowy: Synchronizacja Real-time (WebSockets)
Cel:
Wymiana mechanizmu Pollingu (setInterval co 4s) na stałe połączenie WebSocket, aby zapewnić zerowe opóźnienia w synchronizacji statusów między Tabletem Kelnera, KDS, Wydawką i Klientem, przy jednoczesnym obniżeniu kosztów odczytu z Firestore.
Kroki Implementacji:
A. Server-Side (Python FastAPI + python-socketio):
Integracja socketio.AsyncServer z FastAPI.
Konfiguracja AsyncRedisManager (lub MemoryManager dla małej skali) do zarządzania stanem połączeń.
Wyzwalanie zdarzeń emit w funkcjach zmieniających stan bazy, np.:
W save_order: await sio.emit('new_order', order_data)
W update_status: await sio.emit('status_update', {'id': order_id, 'status': 'ready'})
Ważne (Cloud Run): Wymagane włączenie flagi --session-affinity w Cloud Run, aby tunel WebSocket nie był zrywany przez load balancer chmury.
B. Client-Side (HTML/JS we wszystkich panelach):
Dodanie biblioteki socket.io-client.js.
Zamiana logiki fetchData na nasłuchiwanie zdarzeń:
JavaScript
socket.on('status_update', (data) => {
    // Manipulacja DOM bez przeładowania strony, zmiana koloru kafelka
    updateOrderCard(data.id, data.status); 
});


Zastosowanie tego mechanizmu we wszystkich plikach: index.html, waiter.html, kds.html oraz w nowym panelu Wydawka przy Barze.

🛡️ 4. Plan Rozbudowy: Komunikacja z Raspberry Pi (Pub/Sub)
Cel:
Zapewnienie bezpiecznego i niezawodnego mechanizmu sterowania lokalną drukarką fiskalną po USB z poziomu Panelu Admina w chmurze, bez otwierania portów na router
