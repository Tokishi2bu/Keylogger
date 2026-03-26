# KeyWatch — Ethical Keylogger Lab

A controlled, ethical keylogger system for educational purposes.
**Only use on machines you own or have explicit permission to monitor.**

---

## Project Structure

```
keylogger-server/
├── app.py              ← Flask server (deploy to Render)
├── keylogger.py        ← Windows keylogger agent
├── requirements.txt    ← Python dependencies for server
├── render.yaml         ← Render deployment config
└── templates/
    ├── login.html      ← Login page
    └── dashboard.html  ← Live keystroke dashboard
```

---

## Part 1 — Deploy Flask Server to Render.com

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
gh repo create keywatch-server --private --push
```

### Step 2: Deploy on Render
1. Go to https://render.com → **New → Web Service**
2. Connect your GitHub repo
3. Set these settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Add Environment Variables:
   - `DASHBOARD_PASSWORD` → your chosen password
   - `SECRET_KEY` → any random string
5. Click **Deploy**

### Step 3: Note your URL
After deploy, your URL will look like:
`https://keywatch-server.onrender.com`

---

## Part 2 — Configure & Run Keylogger

### Step 1: Install dependencies (Windows)
```bash
pip install pynput pywin32 Pillow requests
```

### Step 2: Set your server URL
Open `keylogger.py` and update:
```python
SERVER_URL = "https://your-app.onrender.com/log"
```

### Step 3: Run
```bash
python keylogger.py
```

---

## Dashboard

Visit `https://your-app.onrender.com` → enter your password.

| Feature | Detail |
|---------|--------|
| Live feed | Refreshes every 2 seconds |
| Window filter | Search by active window name |
| Stats | Total keystrokes + top windows |
| Clear | Wipe all in-memory logs |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/log` | Receive a keystroke (keylogger sends here) |
| GET | `/api/events?page=N` | Paginated keystroke log |
| GET | `/api/stats` | Summary stats |
| POST | `/api/clear` | Clear all logs |

### POST /log payload
```json
{
  "timestamp": "2024-01-01 12:00:00",
  "window": "Google Chrome",
  "key": "a"
}
```

---

## ⚠️ Ethics & Legal Notice

- Run **only in isolated VM environments** for research
- **Never deploy on systems you don't own**
- For educational purposes only