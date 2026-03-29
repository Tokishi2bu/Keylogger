# KeyWatch 🔐

> A controlled keystroke monitoring and remote dashboard tool built for **ethical hacking labs and cybersecurity education**.

---

## ⚠️ Disclaimer

**This tool is strictly for educational and ethical hacking lab use only.**

- Only run this on machines you **own** or have **explicit written permission** to monitor
- Never deploy outside of an isolated lab or virtual machine environment
- Unauthorized use of this tool on systems you do not own is **illegal** in most countries
- The authors take no responsibility for misuse of this software

---

## 📖 What is KeyWatch?

KeyWatch is an educational keystroke monitoring system built as part of a **red team / blue team cybersecurity lab**. It demonstrates how keyloggers work under the hood — how they capture input, transmit data to a remote server, and how defenders can detect such activity.

The project consists of two components:

| Component | Description |
|-----------|-------------|
| `keylogger.py` | Windows agent that captures keystrokes and screenshots |
| Flask Server | Web application hosted on Render.com that receives and displays the captured data |

The goal is to understand attacker techniques so defenders can build better detection and response systems.

---

## ✨ Features

- ⌨️ **Real-time keystroke capture** — every keypress is sent to the server instantly via a non-blocking queue
- 📸 **Periodic screenshots** — captures the screen every 30 seconds and sends as base64 JPEG
- 🌐 **Live web dashboard** — view all keystrokes and screenshots in real time from any browser
- 🛑 **Remote stop/start control** — pause and resume the agent directly from the dashboard
- 🔐 **Password-protected dashboard** — login required to view any data
- 🪟 **Active window tracking** — every keystroke is tagged with the window title it was typed in
- 📊 **Activity stats** — top active windows, total keystrokes, screenshot count
- 🔍 **Window filter** — search and filter keystrokes by window name
- 📜 **Chronological feed** — oldest entries at top, newest at bottom, auto-scrolls to latest
- 🗑️ **Remote log purge** — clear all data from the dashboard with one click
- 👻 **Silent operation** — console window hidden on launch (for stealth simulation research)
- 💾 **In-memory storage** — all data is wiped on server restart, nothing persisted to disk on server

---

## 🏗️ Project Structure

```
keywatch/
├── app.py                  ← Flask web server (deploy to Render.com)
├── keylogger.py            ← Windows monitoring agent
├── requirements.txt        ← Python dependencies for server
├── render.yaml             ← Render.com deployment config
├── build_exe.md            ← Guide to compile agent as .exe
└── templates/
    ├── login.html          ← Dashboard login page
    └── dashboard.html      ← Live monitoring dashboard
```

---

## 🚀 Setup Guide

### Prerequisites

- Python 3.8+ on both machines
- A [Render.com](https://render.com) account (free tier works)
- A GitHub account
- Windows VM for running the agent (VirtualBox / VMware)

---

### Part 1 — Deploy the Flask Server to Render.com

**Step 1 — Push to GitHub**

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/keywatch.git
git push -u origin main
```

**Step 2 — Create a Web Service on Render**

1. Go to [render.com](https://render.com) → **New → Web Service**
2. Connect your GitHub repository
3. Configure the service:

| Setting | Value |
|---------|-------|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |

4. Add Environment Variables:

| Key | Value |
|-----|-------|
| `DASHBOARD_PASSWORD` | Your chosen password |
| `SECRET_KEY` | Any long random string |

5. Click **Deploy** and wait ~2 minutes

**Step 3 — Note your URL**

After deploy, your URL will look like:
```
https://keywatch-server.onrender.com
```

---

### Part 2 — Configure the Agent

**Step 1 — Update the server URL**

Open `keylogger.py` and set your Render URL:

```python
BASE_URL = "https://your-app.onrender.com"  # ← Your actual URL here
```

**Step 2 — Install dependencies on your Windows VM**

```bash
pip install pynput pywin32 Pillow requests
```

**Step 3 — Run the agent**

```bash
python keylogger.py
```

Or build as an `.exe` (see [Building the EXE](#building-the-exe) below).

---

### Part 3 — View the Dashboard

1. Visit your Render URL in any browser
2. Enter your `DASHBOARD_PASSWORD`
3. The dashboard will show live keystrokes and screenshots

---

## 🔨 Building the EXE

To compile the agent into a standalone Windows executable:

**Install PyInstaller:**
```bash
pip install pyinstaller
```

**Build:**
```bash
pyinstaller --onefile --noconsole --name KeyWatch keylogger.py
```

**Output:** `dist/KeyWatch.exe`

> Every time you update `keylogger.py`, delete the `build/`, `dist/` folders and `KeyWatch.spec` file, then rebuild.

---

## 📡 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/log` | None | Receive a keystroke from agent |
| `POST` | `/screenshot` | None | Receive a screenshot from agent |
| `GET` | `/command` | None | Agent polls for stop/start command |
| `POST` | `/command` | Login | Dashboard sends stop/start command |
| `GET` | `/api/events` | Login | Paginated keystroke log |
| `GET` | `/api/screenshots` | Login | All screenshots (oldest first) |
| `GET` | `/api/stats` | Login | Summary statistics |
| `POST` | `/api/clear` | Login | Clear all logs and screenshots |

### POST /log — Keystroke payload

```json
{
  "timestamp": "2026-03-27 00:25:19",
  "window": "Google Chrome",
  "key": "a"
}
```

### POST /screenshot — Screenshot payload

```json
{
  "timestamp": "2026-03-27 00:25:19",
  "window": "Google Chrome",
  "image": "<base64 encoded JPEG string>"
}
```

### POST /command — Command payload

```json
{ "command": "stop" }
{ "command": "run"  }
```

---

## 🖥️ Dashboard Features

| Feature | Description |
|---------|-------------|
| Live keystroke feed | Oldest at top, newest at bottom, auto-scrolls |
| Window filter | Type to filter keystrokes by active window name |
| Screenshot gallery | All screenshots in chronological order |
| Screenshot lightbox | Click any screenshot to view fullscreen |
| Stop / Start agent | Remotely pause or resume the agent within 5 seconds |
| Clear logs | Wipe all data from server memory |
| Auto-refresh | Dashboard polls every 2 seconds automatically |
| Session uptime | Shows how long the dashboard session has been active |

---

## ⚙️ Configuration

All settings are at the top of `keylogger.py`:

```python
BASE_URL             = "https://your-app.onrender.com"  # Render server URL
SCREENSHOT_INTERVAL  = 30   # Seconds between screenshots (0 = disabled)
POLL_INTERVAL        = 5    # Seconds between command polls
```

---

## 🧱 Tech Stack

**Agent (Windows)**
- `pynput` — keyboard listener
- `pywin32` — active window detection
- `Pillow` — screenshot capture
- `requests` — HTTP transmission
- `PyInstaller` — exe compilation

**Server**
- `Flask` — web framework
- `Gunicorn` — WSGI server for Render
- In-memory `deque` — lightweight data storage

**Frontend**
- Vanilla HTML / CSS / JavaScript
- DM Sans + DM Mono (Google Fonts)
- No frameworks or external JS dependencies

---

## 🛡️ Ethical Use & Legal Notes

This project was built to study:
- How attackers capture and exfiltrate keystrokes
- How remote C2 (Command & Control) communication works
- How to detect these patterns using network monitoring (Wireshark, Zeek)
- How to build SIEM detection rules for keystroke exfiltration

**Recommended lab setup:**
- Run the agent inside a **VirtualBox or VMware VM**
- Use a **host-only network** — no real internet access for the VM
- Always **snapshot your VM** before running the agent
- Use **Wireshark** alongside this to study the traffic patterns

**Resources to learn detection:**
- [MITRE ATT&CK — Input Capture (T1056)](https://attack.mitre.org/techniques/T1056/)
- [Wireshark](https://www.wireshark.org/)
- [Elastic SIEM](https://www.elastic.co/siem)


## 📄 License

For **educational and research purposes only**.
Do not use on systems you do not own or have explicit permission to test.