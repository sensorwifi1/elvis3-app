# Elvis POS — Mapa Drogowa (Roadmap)

## Faza 1: Fundamenty (Zakończone ✅)
- Architektura Serverless (Google Cloud Run + Firestore).
- Podstawowe moduły: Klient (QR Order), Kelner (POS), KDS, Wydawka.
- System WebSocket dla powiadomień w czasie rzeczywistym.
- Brama RPi (Gateway) dla wydruków.
- Ujednolicony Portal Pracownika (PIN Login).

## Faza 2: Stabilizacja i Bezpieczeństwo (W trakcie 🔄)
- [x] Unikalne role dla pracowników (obsługa wielu uprawnień).
- [x] Bezpieczeństwo bramy RPi (blokada dostępu zewnętrznego).
- [x] Panel Boss (zarządzanie menedżerskie).
- [x] Panel Master (zarządzanie systemowe).
- [ ] Stabilne ACK (potwierdzenie odbioru) dla wszystkich typów wydruków.
- [ ] Logowanie zdarzeń błędów do chmury (Cloud Logging).

## Faza 3: Inteligencja i Sprzedaż (Planowane 🚀)
- [ ] **AI Menu Architect**: System sam sugeruje ceny na podstawie popytu (dynamic pricing).
- [ ] **Customer Memory**: AI rozpoznaje powracającego klienta (po session_id/phone) i wita go "Cześć! Znowu Twój ulubiony Elvis Special?".
- [ ] **Social Integration**: Automatyczne generowanie postów na FB/IG z dzisiejszymi promocjami w oparciu o stany magazynowe.

## Faza 4: Ekosystem i Mobilność
- [ ] **Mobile Wallet Integration**: Jabłko/Google Pay bezpośrednio w menu QR (eliminacja terminala płatniczego).
- [ ] **Multi-Location Hub**: Panel dla właściciela sieci 5-10 food trucków (centralne sterowanie menu jednym przyciskiem).
- [ ] **Offline-First Excellence**: Pełna baza SQLite na RPi jako mirror Firestore dla 100% niezawodności w lesie/na festiwalu.
