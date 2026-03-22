# 🍔 Elvis Burger POS - System Gastronomiczny v1.0

Kompletny, nowoczesny system zarządzania restauracją oparty na chmurze Google Cloud Platform, zintegrowany z AI Gemini oraz systemem KDS.

## 🚀 Główne Funkcje (v1.0)
* **Interaktywne Menu Klienta**: Zamawianie przez kody QR z funkcją "Ducha Burgera" (AI Gemini), który bawi gości ciekawostkami i żartami.
* **Kitchen Display System (KDS)**: Cyfrowe zarządzanie bonami w kuchni z timerem i blokadą procesów.
* **Panel Kelnera (SALA)**: Dynamiczna mapa stolików, wezwania kelnera i obsługa płatności w czasie rzeczywistym.
* **Master Admin Dashboard**: 
    * Przesuwanie stolików metodą Drag & Drop.
    * Zaawansowane statystyki sprzedaży z filtrowaniem dat.
    * Symulacja połączenia POS/Fiskalizacja (E-paragony).
* **Bezpieczeństwo**: Pełna izolacja sesji klientów i obsługa przez Firebase Firestore.

## 🛠️ Technologia  
* **Backend**: Python (FastAPI)
* **Frontend**: JS (ES6), HTML5, CSS3 (Modern UI)
* **Baza Danych**: Google Firestore (NoSQL)
* **Hosting**: Google Cloud Run (Serverless)
* **AI**: Google Gemini Pro (Generative AI)

## 📦 Instalacja i Deploy
1. Skonfiguruj projekt w Google Cloud Console.
2. Włącz Firestore API i Cloud Run API.
3. Deploy aplikacji:
   ```bash
   gcloud run deploy elvis-app --source . --region europe-west1


---

### 2. Komendy "Zgitowania" projektu (Wersja 1.0)

W terminalu Cloud Shell, będąc w folderze `~/elvis-app`, wpisz po kolei te komendy:

```bash
# 1. Zainicjuj gita (jeśli jeszcze tego nie zrobiłeś)
git init

# 2. Dodaj swój adres e-mail i imię (żeby GitHub wiedział kto wysyła)
git config --global user.email "Hajdukiewicz@gmail.com"
git config --global user.name "hajdukiewicz"

# 3. Podepnij swoje repozytorium
git remote add origin https://github.com/sensorwifi1/elvis-app.git

# 4. Dodaj wszystkie pliki
git add .

# 5. Zrób pierwszy oficjalny commit wersji 1.0
git commit -m "🚀 Ostateczna wersja 1.0 - Full POS System (AI, KDS, Stats)"

# 6. Ustaw nazwę głównej gałęzi na main
git branch -M main

# 7. Wyślij kod na GitHub (poprosi o login i Token/Hasło)
git push -u origin main