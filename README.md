# 🩸 FreeStyle Libre 3 • Live Taskbar Blood Sugar Monitor & Desktop Analytics

[![Windows 10 / 11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078d7.svg?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Release](https://img.shields.io/badge/Release-v1.2.0%20Setup.exe-emerald.svg)](https://github.com/konradschrein-star/freestyle-libre-live-bloodshugar-connector/releases)
[![Sensor Support](https://img.shields.io/badge/Sensors-FreeStyle%20Libre%203%20%7C%20Libre%202-10b981.svg)](https://freestylelibre.de)
[![Privacy First](https://img.shields.io/badge/GDPR%20%2F%20DSGVO-100%25%20Lokal-brightgreen.svg)](#-100-datenschutz--gdpr-compliance)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Echtzeit-Blutzucker direkt in der Windows-Taskleiste (neben der Uhr) mit großen, gut lesbaren Ziffern, Trendpfeil und Farbcodes — 100% lokal, datenschutzkonform und ohne externe Server.**
> 
> *Real-time continuous glucose monitor (CGM) in your Windows taskbar system tray next to the clock with ultra-readable typography, live trend arrows, color badges, local SQLite persistence, and a standalone desktop analytics window.*

---

## 🌟 Highlights & Funktionen

- 🎯 **Kristallklares Taskleisten-Icon**:
  - Extra große, fette Ziffern (optimiert für `mmol/L` wie z. B. `5.4` und `mg/dL` wie `98`), die selbst aus der Distanz sofort lesbar sind.
  - Separater Richtungspfeil in der Ecke (`↑`, `↗`, `→`, `↘`, `↓`, `⇈`, `⇊`).
  - Farbcodierte Ampel-Badges: 🟢 Im Zielbereich, 🟡 Erhöht / Leicht niedrig, 🔴 Kritisch.
- 💻 **Standalone Desktop App Window (App-Mode)**:
  - Öffnet sich als sauberes, randloses Windows-Desktop-Fenster ohne Browser-Adressleiste oder störende Tabs.
  - Läuft lautlos im Hintergrund in der Taskleiste weiter, wenn das Fenster geschlossen wird.
- ⚡ **60 FPS Performance & LTTB Downsampling**:
  - Serverseitiges Time-Bucketing verhindert jedes Ruckeln, selbst bei tausenden gespeicherten Messwerten über Wochen hinweg.
- 📈 **Glukose-Geschwindigkeit & 30-Minuten-Prognose**:
  - Berechnet die exakte Veränderungsrate in `mmol/L/min` (z. B. `+0.05 mmol/L/min`) und prognostiziert den Wert in 30 Minuten.
- 🍽️ **Ereignis- & Mahlzeiten-Tracking**:
  - Protokollierung von Mahlzeiten (Kohlenhydrate in g), Insulin-Dosen (Einheiten), Sport und Notizen direkt im Diagramm.
- 📊 **Klinische Auswertungen (TIR & GMI)**:
  - **Time in Range (TIR)** Donut-Diagramm mit Standard-Zielbereich (3.9 – 10.0 mmol/L).
  - Geschätzter HbA1c (GMI), Standardabweichung (SD) und Variationskoeffizient (CV%).
  - 1-Klick CSV-Export für Arztbesuche.
- 🛡️ **100% DSGVO & Privatsphäre**:
  - Null externe Server von Drittanbietern. Alle Daten und Tokens liegen ausschließlich in einer lokalen SQLite-Datenbank (`%APPDATA%\FreeStyleLibreTaskbar\blood_sugar.db`).
- 📦 **Nativer Windows Setup-Installer (`Setup.exe`)**:
  - Einfacher Windows-Installationsassistent mit Startmenü, Desktop-Icon und automatischem Windows-Autostart bei Computer-Neustart.

---

## 🚀 Installation & Schnellstart (Für Freunde & Anwender)

### Schritt 1: Einladung in der Libre 3 Smartphone App erstellen
1. Öffnen Sie die offizielle **FreeStyle Libre 3 App** auf Ihrem Smartphone.
2. Gehen Sie auf **Menü ☰ ➔ Verbundene Apps ➔ LibreLinkUp**.
3. Tippen Sie auf **Verbindung hinzufügen** und laden Sie Ihre eigene (oder eine beliebige) E-Mail-Adresse als Follower ein.
4. Öffnen Sie die Einladungs-E-Mail, erstellen Sie das kostenlose LibreLinkUp-Konto und akzeptieren Sie die Nutzungsbedingungen.

### Schritt 2: Setup.exe herunterladen & installieren
1. Laden Sie die **[`FreeStyleLibre_Setup.exe`](https://github.com/konradschrein-star/freestyle-libre-live-bloodshugar-connector/releases)** herunter.
2. Führen Sie die Installation aus (Weiter ➔ Weiter ➔ Fertigstellen).
3. Das Programm startet sofort im Hintergrund und richtet den Autostart bei jedem PC-Start ein.

### Schritt 3: Anmelden & Loslegen
1. Tragen Sie Ihre LibreLinkUp E-Mail und Ihr Passwort im Einstellungsfenster ein.
2. Klicken Sie auf **"Verbindung jetzt live testen"** ➔ Ihr Sensor wird sofort erkannt.
3. Klicken Sie auf **"Speichern"** ➔ Ihr aktueller Blutzucker erscheint direkt in der Windows-Taskleiste!

> 💡 **Taskleisten-Tipp**: Falls Windows das Symbol zuerst in das kleine Pfeil-Menü (**`^`**) neben der Uhr legt, klicken Sie auf **`^`** und **ziehen Sie das grüne Blutzucker-Icon mit der Maus direkt auf Ihre Taskleiste**.

---

## 🛠️ Entwicklung & Aus Quellcode ausführen (Python)

```bash
# 1. Repository klonen
git clone https://github.com/konradschrein-star/freestyle-libre-live-bloodshugar-connector.git
cd freestyle-libre-live-bloodshugar-connector

# 2. Abhängigkeiten installieren
pip install -r requirements.txt

# 3. Starten
python main.py
```

### Eigenen Installer kompilieren:
```bash
# Erstellt dist\FreeStyleLibreTaskbar.exe
build_exe.bat

# Erstellt den Windows Setup Wizard (dist\FreeStyleLibre_Setup.exe via Inno Setup)
iscc installer.iss
```

---

## 🇬🇧 Quickstart Guide (English)

1. **Invite Follower**: In your official **FreeStyle Libre 3 App**, go to **Menu ☰ ➔ Connected Apps ➔ LibreLinkUp ➔ Add Connection** and invite your email. Accept the invite email.
2. **Download Installer**: Download and run **[`FreeStyleLibre_Setup.exe`](https://github.com/konradschrein-star/freestyle-libre-live-bloodshugar-connector/releases)**.
3. **Login**: Enter your LibreLinkUp credentials in the settings dialog and click **Save**.
4. **Enjoy**: Your real-time blood sugar is now live next to your Windows clock in `mmol/L` or `mg/dL`!

---

## 🔒 100% Datenschutz & GDPR / DSGVO Compliance

- **Zero Third-Party Cloud**: Keine Zwischenserver, kein Tracking, keine Werbung.
- **Lokale Verschlüsselung**: Die Verbindung erfolgt per SSL direkt zwischen Ihrem PC und den offiziellen Abbott-Servern (`api-de.libreview.io` / `api-eu.libreview.io`).
- **Lokale Speicherung**: Sämtliche Verlaufsdaten verbleiben auf Ihrer Festplatte in einer SQLite-Datenbank (`%APPDATA%\FreeStyleLibreTaskbar\blood_sugar.db`).

---

## 📄 Lizenz
Dieses Projekt ist unter der **MIT-Lizenz** lizenziert — frei zur privaten und nicht-kommerziellen Nutzung.

*Haftungsausschluss: Dieses Open-Source-Projekt steht in keiner offiziellen Verbindung zu Abbott Diabetes Care. Die angezeigten Werte dienen ausschließlich informativen Zwecken und ersetzen keine ärztliche Beratung oder medizinische Notfalldiagnostik.*
