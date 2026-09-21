import keyboard
import sounddevice as sd
import numpy as np
import wave
import tempfile
import os
import io
import json
import base64
import copy
import logging
import queue
import shutil
import subprocess
from collections import deque
from datetime import date, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import quote_plus
import pyperclip
import time
from groq import Groq
import threading
import pystray
from PIL import Image, ImageDraw
import sys
import winsound
import ctypes
from ctypes import wintypes
import win32gui # Lấy thông tin cửa sổ Windows
import win32crypt
import winreg
import re
import webbrowser
import pyttsx3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Optional, Dict, List, Any

# ================= CẤU HÌNH HỆ THỐNG =================
APP_NAME = "SmartVoiceAI"
SOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
EXECUTABLE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else SOURCE_DIR
APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME

API_KEY = ""
client: Optional[Groq] = None

SAMPLE_RATE = 16000
HOTKEY_F8 = 'f8'
HOTKEY_F9 = 'f9'
QUOTA_FILE = APP_DATA_DIR / "groq_quota_v3.json"
GLOSSARY_FILE = APP_DATA_DIR / "dictionary.json"

# --- HẠN MỨC (ASD, ASH, RPD, RPM) ---
LIMIT_ASD = 28800  # 8 tiếng/ngày
LIMIT_ASH = 7200   # 2 tiếng/giờ
LIMIT_RPD = 1000   # Mức bảo thủ cho model chat; quota thật phụ thuộc tài khoản/model
LIMIT_RPM = 20     # 20 lượt gọi/phút

SILENCE_THRESHOLD = 500  # Ngưỡng âm lượng
CONFIG_FILE = APP_DATA_DIR / "app_settings.json"
LOG_FILE = APP_DATA_DIR / "smart_voice_ai.log"

DEFAULT_CONFIG = {
    "config_version": 2,
    "api_key": "",
    "api_key_encrypted": "",
    "transcription_model": "whisper-large-v3",
    "fast_model": "qwen/qwen3.8-27b",
    "assistant_model": "qwen/qwen3.8-27b",
    "language": "vi",
    "hands_free": True,
    "silence_threshold": 500,
    "transcription_prompt": "Xin chào, tôi là trợ lý tiếng Việt. Đây là đoạn văn bản tiếng Việt có dấu, chính tả chuẩn xác, ngữ biểu tự nhiên, bao gồm cả các từ ngữ hiện đại và kỹ thuật như code, data, app, API, AI, python.",
    "ai_system_prompt": "Bạn là trợ lý AI thông minh có bộ nhớ ngữ cảnh. TRƯỜNG HỢP 1: Nếu người dùng có 'Văn bản gốc', hãy xử lý nó theo 'Lệnh/Yêu cầu'. TRƯỜNG HỢP 2: Nếu không có 'Văn bản gốc', hãy thực hiện yêu cầu trực tiếp hoặc dựa trên các câu trả lời trước đó trong lịch sử hội thoại. QUY TẮC: CHỈ TRẢ VỀ KẾT QUẢ CUỐI CÙNG ĐÃ ĐỊNH DẠNG (Text/Markdown), KHÔNG GIẢI THÍCH.",
    "hotkey_f8": "ctrl+alt+f8",
    "hotkey_f9": "ctrl+alt+f9",
    "vad_enabled": True,
    "vad_silence_limit": 2.0,
    "enable_tts": False,
    "smart_punctuation": False, # Mặc định tắt để đảm bảo tốc độ
    "translation_mode": "Tắt",
    "prompt_templates": [
        {"name": "Trợ lý Mặc định", "prompt": "Bạn là trợ lý AI thông minh có bộ nhớ ngữ cảnh. TRƯỜNG HỢP 1: Nếu người dùng có 'Văn bản gốc', hãy xử lý nó theo 'Lệnh/Yêu cầu'. TRƯỜNG HỢP 2: Nếu không có 'Văn bản gốc', hãy thực hiện yêu cầu trực tiếp hoặc dựa trên các câu trả lời trước đó trong lịch sử hội thoại. QUY TẮC: CHỈ TRẢ VỀ KẾT QUẢ CUỐI CÙNG ĐÃ ĐỊNH DẠNG (Text/Markdown), KHÔNG GIẢI THÍCH."},
        {"name": "Dịch thuật (Anh-Việt)", "prompt": "Bạn là một biên dịch viên cao cấp. Hãy dịch văn bản sang tiếng Anh hoặc tiếng Việt tùy theo ngôn ngữ đầu vào. Chỉ trả về kết quả dịch, không giải thích."},
        {"name": "Lập trình viên", "prompt": "Bạn là kỹ sư phần mềm cao cấp. Hãy giải thích, sửa lỗi hoặc viết code dựa trên yêu cầu. Trả về Markdown code block."},
        {"name": "Viết Mail chuyên nghiệp", "prompt": "Bạn là trợ lý soạn thảo văn bản. Hãy viết email chuyên nghiệp, lịch sự dựa trên ý chính được cung cấp."}
    ],
    "current_prompt_index": 0
}

# Trạng thái ứng dụng và dữ liệu lưu lượng
class AppState:
    def __init__(self):
        self.hands_free_mode: bool = True
        self.is_recording: bool = False
        self.is_processing: bool = False
        self.app_running: bool = True
        self.tray_icon: Any = None
        self.root: Optional[tk.Tk] = None
        self.status_window: Optional[Any] = None
        self.dashboard_window: Optional[Any] = None
        self.llm_history: List[Dict[str, Any]] = [] # Bộ nhớ ngữ cảnh AI
        self.used_seconds: float = 0.0
        self.used_requests: int = 0
        self.hourly_seconds: Dict[str, float] = {}
        self.minute_requests: List[float] = []
        self.glossary: Dict[str, str] = {}
        self.config: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self.tts_engine: Optional[Any] = None
        self.lock = threading.RLock()
        self.tts_lock = threading.Lock()
        self.ui_queue: queue.Queue = queue.Queue()
        self.hotkey_queue: queue.Queue = queue.Queue()
        self.last_hotkey_time: Dict[str, float] = {}
        self.hotkey_thread: Optional[threading.Thread] = None
        self.hotkey_thread_id: Optional[int] = None

state = AppState()


def setup_logging() -> None:
    """Ghi log quay vòng vì bản windowed .exe không có console để chẩn đoán."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    root_logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root_logger.addHandler(handler)


def log_message(message: str, level: int = logging.INFO) -> None:
    logging.log(level, message)
    try:
        if sys.stdout:
            print(message)
    except (OSError, UnicodeError):
        pass


def resource_path(name: str) -> Path:
    return SOURCE_DIR / name


def atomic_write_json(path: Path, data: Any) -> None:
    """Tránh làm hỏng JSON nếu Windows/app bị tắt giữa lúc đang ghi."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=4)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def protect_secret(secret: str) -> str:
    if not secret:
        return ""
    encrypted = win32crypt.CryptProtectData(secret.encode("utf-8"), APP_NAME, None, None, None, 0)
    return base64.b64encode(encrypted).decode("ascii")


def unprotect_secret(value: str) -> str:
    if not value:
        return ""
    _, decrypted = win32crypt.CryptUnprotectData(base64.b64decode(value), None, None, None, 0)
    return decrypted.decode("utf-8")


def migrate_legacy_files() -> None:
    """Chuyển dữ liệu cũ cạnh script/.exe sang LocalAppData một lần."""
    for filename, destination in (
        ("app_settings.json", CONFIG_FILE),
        ("dictionary.json", GLOSSARY_FILE),
        ("groq_quota_v3.json", QUOTA_FILE),
    ):
        if destination.exists():
            continue
        for folder in (EXECUTABLE_DIR, Path.cwd()):
            source = folder / filename
            if source.is_file() and source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
                break


def get_client() -> Groq:
    global client
    api_key = str(state.config.get("api_key", "")).strip()
    if not api_key:
        raise RuntimeError("Chưa cấu hình Groq API key. Mở Dashboard > Cài đặt để nhập key.")
    if client is None:
        client = Groq(api_key=api_key, timeout=45.0, max_retries=2)
    return client


def is_valid_hotkey(value: str) -> bool:
    try:
        parse_windows_hotkey(value)
        return True
    except ValueError:
        return False


def post_ui(callback, *args, **kwargs) -> None:
    """Đưa mọi thao tác Tkinter về main thread."""
    state.ui_queue.put((callback, args, kwargs))


def process_ui_queue() -> None:
    try:
        while True:
            callback, args, kwargs = state.ui_queue.get_nowait()
            try:
                callback(*args, **kwargs)
            except Exception:
                logging.exception("Lỗi cập nhật giao diện")
    except queue.Empty:
        pass
    if state.root and state.app_running:
        state.root.after(40, process_ui_queue)

# ================= HỖ TRỢ GIỌNG NÓI (TTS) =================
def init_tts():
    """Tạo engine trong đúng worker thread để COM/SAPI hoạt động ổn định."""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        if "vietnam" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    engine.setProperty('rate', 170)
    return engine

def speak_text(text: str):
    """Đọc văn bản nếu tính năng TTS được bật."""
    if state.config.get("enable_tts", False):
        def _speak():
            with state.tts_lock:
                engine = None
                try:
                    engine = init_tts()
                    engine.say(text)
                    engine.runAndWait()
                except Exception:
                    logging.exception("Lỗi TTS")
                finally:
                    if engine:
                        try:
                            engine.stop()
                        except Exception:
                            pass
        threading.Thread(target=_speak, daemon=True).start()

# ================= QUẢN LÝ CÀI ĐẶT (SETTINGS) =================
def load_settings():
    """Tải cài đặt từ file JSON."""
    state.config = copy.deepcopy(DEFAULT_CONFIG)
    needs_persist = False
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open('r', encoding='utf-8') as f:
                loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise ValueError("Cấu hình phải là một JSON object")
                if int(loaded.get("config_version", 1) or 1) < 2:
                    if loaded.get("hotkey_f8") in {"f8", "ctrl+f8"}:
                        loaded["hotkey_f8"] = "ctrl+alt+f8"
                    if loaded.get("hotkey_f9") in {"f9", "ctrl+f9"}:
                        loaded["hotkey_f9"] = "ctrl+alt+f9"
                    loaded["config_version"] = 2
                    needs_persist = True
                state.config.update(loaded)
            log_message("Đã tải cài đặt từ file.")
        except Exception as e:
            logging.exception("Lỗi tải cài đặt")
            log_message(f"Lỗi tải cài đặt: {e}", logging.ERROR)

    # Ưu tiên biến môi trường; nếu không có thì giải mã key bằng Windows DPAPI.
    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    encrypted_key = str(state.config.get("api_key_encrypted", "")).strip()
    legacy_key = str(state.config.get("api_key", "")).strip()
    api_key = env_key
    if not api_key and encrypted_key:
        try:
            api_key = unprotect_secret(encrypted_key)
        except Exception:
            logging.exception("Không giải mã được API key (có thể thuộc Windows user khác)")
    if not api_key:
        api_key = legacy_key
    state.config["api_key"] = api_key

    # Cập nhật client Groq và các biến toàn cục
    global client, API_KEY, SILENCE_THRESHOLD, HOTKEY_F8, HOTKEY_F9
    API_KEY = api_key
    client = None
    state.hands_free_mode = state.config.get("hands_free", True)
    SILENCE_THRESHOLD = max(0, int(state.config.get("silence_threshold", 500)))
    configured_f8 = str(state.config.get("hotkey_f8", "ctrl+alt+f8")).strip().lower()
    configured_f9 = str(state.config.get("hotkey_f9", "ctrl+alt+f9")).strip().lower()
    HOTKEY_F8 = configured_f8 if is_valid_hotkey(configured_f8) else "ctrl+alt+f8"
    HOTKEY_F9 = configured_f9 if is_valid_hotkey(configured_f9) else "ctrl+alt+f9"
    if HOTKEY_F8 == HOTKEY_F9:
        HOTKEY_F8, HOTKEY_F9 = "ctrl+alt+f8", "ctrl+alt+f9"

    # Tự động thay plaintext key cũ bằng bản mã hóa gắn với Windows user hiện tại.
    if legacy_key and not env_key:
        needs_persist = True
    if needs_persist:
        save_settings_to_file()

    if state.root:
        restart_hotkey_listener()
    
    log_message(f"Hệ thống: Khởi động với Groq Whisper (Phím: {HOTKEY_F8}/{HOTKEY_F9})")

def save_settings_to_file() -> None:
    """Lưu cài đặt hiện tại vào file JSON."""
    try:
        persisted = copy.deepcopy(state.config)
        secret = str(persisted.pop("api_key", "")).strip()
        persisted["api_key_encrypted"] = protect_secret(secret) if secret else ""
        atomic_write_json(CONFIG_FILE, persisted)
    except Exception as e:
        logging.exception("Lỗi lưu cài đặt")
        log_message(f"Lỗi lưu cài đặt: {e}", logging.ERROR)

# ================= QUẢN LÝ TỪ ĐIỂN (GLOSSARY) =================
def load_glossary():
    if GLOSSARY_FILE.exists():
        try:
            with GLOSSARY_FILE.open('r', encoding='utf-8') as f:
                loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise ValueError("Từ điển phải là một JSON object")
                state.glossary = {str(k): str(v) for k, v in loaded.items() if str(k)}
            log_message(f"Đã tải {len(state.glossary)} từ khóa từ điển.")
        except Exception as e:
            logging.exception("Lỗi tải từ điển")
            log_message(f"Lỗi tải từ điển: {e}", logging.ERROR)
    else:
        atomic_write_json(GLOSSARY_FILE, {})
        state.glossary = {}

def apply_glossary(text: str) -> str:
    """Tự động thay thế các cụm từ trong từ điển (không phân biệt hoa thường)."""
    if not state.glossary: return text
    
    # Sắp xếp từ khóa theo độ dài giảm dần để tránh thay thế từ ngắn nằm trong từ dài
    sorted_keywords = sorted(state.glossary.keys(), key=len, reverse=True)
    
    for key in sorted_keywords:
        # Sử dụng regex để thay thế case-insensitive
        pattern = re.compile(re.escape(key), re.IGNORECASE)
        replacement = state.glossary[key]
        text = pattern.sub(lambda _match, value=replacement: value, text)
    return text

# ================= QUẢN LÝ LƯU LƯỢNG (QUOTA) =================
def load_quota():
    today = date.today().isoformat()
    if QUOTA_FILE.exists():
        try:
            with QUOTA_FILE.open('r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("date") == today:
                    state.used_seconds = float(data.get("used_seconds", 0.0))
                    state.used_requests = int(data.get("used_requests", 0))
                    state.hourly_seconds = {str(k): float(v) for k, v in data.get("hourly_seconds", {}).items()}
                    state.minute_requests = [float(ts) for ts in data.get("minute_requests", [])]
                    update_tooltip()
                    return
        except Exception:
            logging.exception("Lỗi tải quota")
    
    state.used_seconds = 0.0
    state.used_requests = 0
    state.hourly_seconds = {}
    state.minute_requests = []
    update_tooltip()

def save_quota():
    with state.lock:
        data = {
            "date": date.today().isoformat(),
            "used_seconds": state.used_seconds,
            "used_requests": state.used_requests,
            "hourly_seconds": state.hourly_seconds,
            "minute_requests": state.minute_requests
        }
        atomic_write_json(QUOTA_FILE, data)
    update_tooltip()

def update_tooltip():
    if state.tray_icon:
        used_p = state.used_seconds / 60
        total_p = LIMIT_ASD / 60
        mode = "Rảnh tay" if state.hands_free_mode else "Nhấn giữ"
        try:
            state.tray_icon.title = f"Smart Voice AI ({HOTKEY_F8}/{HOTKEY_F9}) - {mode}\nĐã dùng: {used_p:.1f}/{total_p:.0f}p\nLượt gọi: {state.used_requests}/{LIMIT_RPD}"
        except Exception:
            pass

# ================= QUẢN LÝ CLIPBOARD AN TOÀN =================
class ClipboardQueue:
    def __init__(self):
        self.lock = threading.Lock()

    def paste_text(self, text: str):
        """Gõ văn bản mà không làm mất dữ liệu clipboard cũ của người dùng."""
        def _task():
            with self.lock:
                old_clip = None
                try:
                    old_clip = str(pyperclip.paste())
                    pyperclip.copy(text)
                    time.sleep(0.08) # Đợi clipboard hệ thống cập nhật
                    keyboard.send('ctrl+v')
                    time.sleep(0.4) # Đợi ứng dụng nhận lệnh dán
                except Exception:
                    logging.exception("Không thể dán hoặc khôi phục clipboard")
                finally:
                    if old_clip is not None:
                        try:
                            pyperclip.copy(old_clip)
                        except Exception:
                            logging.exception("Không thể khôi phục clipboard")
        threading.Thread(target=_task, daemon=True).start()

clipboard_manager = ClipboardQueue()

# ================= ÂM THANH PHẢN HỒI =================
def play_sound(event_type):
    def _beep():
        try:
            if event_type == "start":
                # Tiếng beep mặc định của hệ thống
                winsound.MessageBeep(-1)
            elif event_type == "end":
                # Tiếng thông báo nhẹ (MB_OK)
                winsound.MessageBeep(winsound.MB_OK)
            elif event_type == "error":
                # Tiếng báo lỗi (MB_ICONHAND)
                winsound.MessageBeep(winsound.MB_ICONHAND)
        except Exception:
            # Fallback nếu MessageBeep không hoạt động
            try:
                if event_type == "start": winsound.Beep(1000, 150)
                elif event_type == "end": winsound.Beep(800, 150)
            except Exception:
                logging.exception("Không thể phát âm báo")
    threading.Thread(target=_beep, daemon=True).start()

# ================= XỬ LÝ ÂM THANH (HELPER) =================
def normalize_audio(audio_data):
    """Cân bằng âm lượng đoạn ghi âm (Auto Gain)."""
    try:
        if len(audio_data) == 0: return audio_data
        # Chuyển sang float32 để tính toán độ chính xác cao và tránh tràn số
        audio_float = audio_data.astype(np.float32)
        max_vol = np.max(np.abs(audio_float))
        
        # Nếu âm thanh nhỏ hơn ~60% mức tối đa int16 (32768)
        if max_vol > 0 and max_vol < 20000:
            target_vol = 28000
            gain = target_vol / max_vol
            gain = min(gain, 5.0) # Không tăng quá 5 lần để tránh nhiễu nền
            
            normalized = audio_float * gain
            # Giới hạn giá trị trong khoảng hợp lệ của int16
            return np.clip(normalized, -32768, 32767).astype(np.int16)
    except Exception as e:
        log_message(f"Lỗi chuẩn hóa: {e}", logging.ERROR)
    return audio_data

def get_active_window_context():
    """Lấy tiêu đề cửa sổ đang active để làm ngữ cảnh cho AI."""
    try:
        window = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(window).lower()
        
        if any(x in title for x in ['visual studio', 'vsc', 'code', 'pycharm', 'sublime', 'terminal', 'cmd', 'powershell']):
            return "LẬP TRÌNH (Code/Tech)"
        elif any(x in title for x in ['word', 'outlook', 'email', 'soạn thảo', 'văn bản', 'pdf']):
            return "VĂN PHÒNG (Chuyên nghiệp)"
        elif any(x in title for x in ['facebook', 'zalo', 'messenger', 'chat', 'telegram', 'skype']):
            return "TRÒ CHUYỆN (Thân thiện/Chat)"
        return "CƠ BẢN"
    except:
        return "CƠ BẢN"

LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", ""))
PROGRAM_FILES = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
APP_ALIASES = {
    "edge": ["msedge"],
    "chrome": ["chrome"],
    "zalo": [str(LOCAL_APPDATA / "Programs" / "Zalo" / "Zalo.exe")],
    "da lô": [str(LOCAL_APPDATA / "Programs" / "Zalo" / "Zalo.exe")],
    "discord": [str(LOCAL_APPDATA / "Discord" / "Update.exe"), "--processStart", "Discord.exe"],
    "kmplayer": [str(PROGRAM_FILES / "KMPlayer 64X" / "KMPlayer64.exe")],
    "kmp": [str(PROGRAM_FILES / "KMPlayer 64X" / "KMPlayer64.exe")],
    "ca mờ pờ": [str(PROGRAM_FILES / "KMPlayer 64X" / "KMPlayer64.exe")],
    "ca mờ pê": [str(PROGRAM_FILES / "KMPlayer 64X" / "KMPlayer64.exe")],
    "word": ["winword"],
    "excel": ["excel"],
    "powerpoint": ["powerpnt"],
    "máy tính": ["calc"],
    "calculator": ["calc"],
    "trình duyệt": ["msedge"],
    "ét": ["msedge"],
    "note": ["notepad"],
    "notepad": ["notepad"],
    "youtube": ["https://www.youtube.com"],
    "facebook": ["https://www.facebook.com"],
    "gmail": ["https://mail.google.com"]
}


def resolve_windows_executable(command: str) -> Optional[str]:
    candidate = Path(command)
    if candidate.is_absolute():
        return str(candidate) if candidate.exists() else None
    resolved = shutil.which(command)
    if resolved:
        return resolved
    executable_name = command if command.lower().endswith(".exe") else f"{command}.exe"
    subkey = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{executable_name}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, subkey) as key:
                value, _ = winreg.QueryValueEx(key, None)
                if Path(value).is_file():
                    return value
        except OSError:
            continue
    return None

def execute_action(action_text: str):
    """Thực thi các hành động hệ thống dựa trên yêu cầu từ AI."""
    try:
        action_text = action_text.strip()
        open_match = re.fullmatch(r"ACTION:\s*OPEN\s+(.+?)\s*", action_text, re.IGNORECASE)
        if open_match:
            app_name_raw = open_match.group(1).strip().lower()
            app_cmd = APP_ALIASES.get(app_name_raw)
            if not app_cmd:
                return f"Ứng dụng chưa được cho phép: {app_name_raw}"
            if app_cmd[0].startswith("http"):
                webbrowser.open(app_cmd[0])
            else:
                executable = resolve_windows_executable(app_cmd[0])
                if not executable:
                    return f"Không tìm thấy ứng dụng: {app_name_raw}"
                subprocess.Popen([executable, *app_cmd[1:]], shell=False)
            return f"Đã nhận lệnh khởi chạy: {app_name_raw.title()}"

        search_match = re.fullmatch(r"ACTION:\s*SEARCH\s+(.+?)\s*", action_text, re.IGNORECASE)
        if search_match:
            query = search_match.group(1).strip()
            webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
            return f"Đã tiến hành tra cứu: {query}"
            
        return None
    except Exception as e:
        return f"Lỗi thực thi chỉ thị: {e}"

# ================= GIAO DIỆN NỔI (FLOATING UI) =================
class FloatingIndicator:
    def __init__(self, root):
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.92) # Tăng nhẹ độ đậm để rõ nét hơn
        self.window.configure(bg='#121212') # Nền xám đen sâu
        
        # Frame chính với viền mỏng tinh tế
        self.frame = tk.Frame(self.window, bg='#121212', highlightthickness=1, highlightbackground='#333333')
        self.frame.pack(fill='both', expand=True)
        
        # Thanh chỉ dẫn trạng thái trên cùng (màu dải mỏng)
        self.status_bar = tk.Frame(self.frame, height=2, bg='#00c8ff')
        self.status_bar.pack(fill='x', side='top')
        
        self.label = tk.Label(self.frame, text="Đang nghe...", font=('Segoe UI Variable Display', 10, 'bold'), 
                             bg='#121212', fg='#00c8ff', padx=15, pady=10) # Giảm bớt padding chút cho cân đối
        self.label.pack()
        
        # Audio Canvas (Waveform) - Thiết kế thanh mảnh hơn
        self.canvas = tk.Canvas(self.frame, height=30, width=160, bg='#121212', highlightthickness=0)
        self.canvas.pack(pady=(0, 10))
        self.bars = []
        for i in range(16):
            # Tạo các thanh bar với màu gradient giả lập
            b = self.canvas.create_rectangle(i*10 + 5, 15, i*10 + 9, 15, fill='#00c8ff', outline='')
            self.bars.append(b)
        # Vị trí: góc dưới bên phải, cách lề một chút
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        self.window.geometry(f"+{screen_w - 230}+{screen_h - 180}")

        # Nút Dừng thủ công (Manual Stop)
        self.btn_stop = tk.Button(self.frame, text="⏹ DỪNG (ESC)", font=('Segoe UI', 9, 'bold'),
                                 bg='#ff4b4b', fg='white', activebackground='#ff3333', 
                                 activeforeground='white', bd=0, padx=10, pady=5,
                                 command=self.manual_stop_trigger)
        self.btn_stop.pack(pady=(0, 10))

    def manual_stop_trigger(self):
        """Kích hoạt dừng ghi âm thủ công."""
        state.is_recording = False
        log_message("Hệ thống: Dừng thủ công bằng nút bấm.")

    def show(self, text, color='#00c8ff'):
        def _update():
            self.label.config(text=text, fg=color)
            self.status_bar.config(bg=color)
            self.window.deiconify()
            if "NGHE" not in text: # Nếu không phải trạng thái đang nghe thì ẩn waveform và nút dừng
                self.canvas.pack_forget()
                self.btn_stop.pack_forget()
            else:
                self.canvas.pack(pady=(0, 10))
                self.btn_stop.pack(pady=(0, 10))
        post_ui(_update)

    def update_meter(self, level):
        """ level từ 0 đến 1.0 """
        if not state.root: return
        def _anim():
            for i, bar in enumerate(self.bars):
                # Hiệu ứng sóng mượt hơn với random offset
                h = max(3, level * 25 * (0.4 + 0.6 * np.random.random())) 
                # Cập nhật vị trí thanh bar
                self.canvas.coords(bar, i*10 + 5, 15 - h/2, i*10 + 9, 15 + h/2)
                # Thay đổi độ sáng của màu dựa trên cao độ (hiệu ứng dải màu)
                if h > 15: self.canvas.itemconfig(bar, fill='#ffffff')
                else: self.canvas.itemconfig(bar, fill='#00c8ff')
        post_ui(_anim)

    def hide(self):
        post_ui(self.window.withdraw)

def update_status(mode: str, key_name: str = ""):
    """Cập nhật trạng thái hiển thị trên màn hình."""
    if state.status_window:
        prefix = f"[{key_name.upper()}] " if key_name else ""
        if mode == "recording":
            silence_seconds = state.config.get("vad_silence_limit", 2.0)
            state.status_window.show(
                f"{prefix}● ĐANG NGHE — HÃY NÓI\nIm lặng {silence_seconds:g}s hoặc ESC để hoàn tất",
                "#ff4b4b"
            )
        elif mode == "processing":
            color = "#a6e3a1" if key_name.lower() == "f8" else "#00c8ff"
            label = "ĐANG NHẬP LIỆU..." if key_name.lower() == "f8" else "AI ĐANG XỬ LÝ..."
            state.status_window.show(f"{prefix}{label}", color)
        else:
            state.status_window.hide()
            
    def _update_dashboard():
        if state.dashboard_window and state.dashboard_window.winfo_exists():
            state.dashboard_window.update_status(mode)
    post_ui(_update_dashboard)



# ================= DASHBOARD CÀI ĐẶT =================
class MainDashboard(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Smart Voice AI - Dashboard")
        self.geometry("750x650")
        self.configure(bg='#1e1e2e')
        self.attributes("-topmost", True)
        
        # Header - Trạng thái
        self.header_frame = tk.Frame(self, bg='#1e1e2e')
        self.header_frame.pack(fill='x', pady=10)
        tk.Label(self.header_frame, text="SMART VOICE AI", font=('Segoe UI Variable Display', 20, 'bold'), fg='white', bg='#1e1e2e').pack()
        self.lbl_status = tk.Label(self.header_frame, text="Trạng thái: Đang nghỉ", font=('Segoe UI', 10), fg='#a6adc8', bg='#1e1e2e')
        self.lbl_status.pack()
        tk.Label(
            self.header_frame,
            text=f"{HOTKEY_F8.upper()}: nói → văn bản   |   {HOTKEY_F9.upper()}: ra lệnh AI   |   ESC: dừng",
            font=('Segoe UI', 10, 'bold'), fg='#a6e3a1', bg='#1e1e2e'
        ).pack(pady=(6, 0))
        
        # Style
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#1e1e2e', borderwidth=0)
        style.configure('TNotebook.Tab', background='#313244', foreground='white', padding=[15, 8], font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', '#cba6f7')], foreground=[('selected', '#1e1e2e')])
        style.configure('Dark.TFrame', background='#1e1e2e')
        style.configure('Card.TFrame', background='#313244', borderwidth=0)
        
        # Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.tab_dash = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.tab_general = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.tab_prompts = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.tab_glossary = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.tab_about = ttk.Frame(self.notebook, style='Dark.TFrame')
        
        self.notebook.add(self.tab_dash, text=' DASHBOARD ')
        self.notebook.add(self.tab_general, text=' CÀI ĐẶT ')
        self.notebook.add(self.tab_prompts, text=' AI PROMPT ')
        self.notebook.add(self.tab_glossary, text=' TỪ ĐIỂN ')
        self.notebook.add(self.tab_about, text=' GIỚI THIỆU ')
        
        self.setup_dashboard_tab()
        self.setup_general_tab()
        self.setup_prompts_tab()
        self.setup_glossary_tab()
        self.setup_about_tab()
        
        btn_frame = tk.Frame(self, bg='#1e1e2e', pady=15)
        btn_frame.pack(side='bottom', fill='x')
        btn_save = tk.Button(btn_frame, text="LƯU TẤT CẢ THIẾT LẬP", font=('Segoe UI', 12, 'bold'), 
                             bg='#cba6f7', fg='#1e1e2e', borderwidth=0, cursor='hand2', padx=20, pady=8, command=self.save_all_settings)
        btn_save.pack()

    def update_status(self, mode):
        if not self.winfo_exists(): return
        if mode == "recording":
             self.lbl_status.config(text="Trạng thái: ● ĐANG NGHE...", fg="#f38ba8")
        elif mode == "processing":
             self.lbl_status.config(text="Trạng thái: ⟳ ĐANG XỬ LÝ...", fg="#89b4fa")
        else:
             self.lbl_status.config(text="Trạng thái: Đang nghỉ", fg="#a6adc8")
             
        # Update logs randomly by asking it to redraw
        self.update_log_list()

    def update_log_list(self):
        if hasattr(self, 'log_listbox') and self.log_listbox.winfo_exists():
            self.log_listbox.delete(0, 'end')
            for turn in state.llm_history[-15:]:
                prefix = "👤 User: " if turn["role"] == "user" else "🤖 AI: "
                text = turn["content"].replace("\\n", " ")
                self.log_listbox.insert('end', f"{prefix}{text}")
            self.log_listbox.yview('end')

    def setup_dashboard_tab(self):
        # Stats
        stat_frame = ttk.Frame(self.tab_dash, style='Dark.TFrame')
        stat_frame.pack(fill='x', pady=20)
        
        used_h = state.used_seconds / 3600
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d-%H")
        ash_m = state.hourly_seconds.get(hour_key, 0.0)/60
        
        lbl_style = {'font': ('Segoe UI', 11), 'fg': 'white', 'bg': '#313244', 'padx': 15, 'pady': 15}
        
        f1 = tk.Frame(stat_frame, bg='#313244')
        f1.pack(side='left', expand=True, fill='x', padx=5)
        tk.Label(f1, text=f"ASD Ngày\\n{used_h:.2f} / 8h", **lbl_style).pack()

        f2 = tk.Frame(stat_frame, bg='#313244')
        f2.pack(side='left', expand=True, fill='x', padx=5)
        tk.Label(f2, text=f"RPD Ngày\\n{state.used_requests} / {LIMIT_RPD}", **lbl_style).pack()

        f3 = tk.Frame(stat_frame, bg='#313244')
        f3.pack(side='left', expand=True, fill='x', padx=5)
        tk.Label(f3, text=f"ASH Trong giờ\\n{ash_m:.1f} / 120m", **lbl_style).pack()

        log_frame = tk.Frame(self.tab_dash, bg='#1e1e2e')
        log_frame.pack(fill='both', expand=True, pady=10)
        tk.Label(log_frame, text="Logs Hoạt động", font=('Segoe UI', 12, 'bold'), fg='white', bg='#1e1e2e').pack(anchor='w', pady=5)
        
        self.log_listbox = tk.Listbox(log_frame, font=('Segoe UI', 10), bg='#181825', fg='#cdd6f4', borderwidth=0, selectbackground='#cba6f7', selectforeground='#1e1e2e')
        self.log_listbox.pack(fill='both', expand=True)
        self.update_log_list()

    def setup_general_tab(self):
        def lbl(parent, txt):
            return tk.Label(parent, text=txt, fg='white', bg='#1e1e2e', font=('Segoe UI', 10))

        # API
        f_api = tk.LabelFrame(self.tab_general, text=" API Groq ", bg='#1e1e2e', fg='#a6adc8', font=('Segoe UI', 10, 'bold'))
        f_api.pack(fill='x', pady=10)
        self.api_entry = tk.Entry(f_api, width=60, bg='#313244', fg='white', borderwidth=1, show="*")
        self.api_entry.insert(0, state.config.get("api_key", ""))
        self.api_entry.pack(pady=10, padx=10, anchor='w')

        # Features
        f_feat = tk.LabelFrame(self.tab_general, text=" Tính năng ", bg='#1e1e2e', fg='#a6adc8', font=('Segoe UI', 10, 'bold'))
        f_feat.pack(fill='x', pady=10)
        
        self.vad_var = tk.BooleanVar(value=state.config.get("vad_enabled", True))
        tk.Checkbutton(f_feat, text="Tự động ngắt (VAD)", variable=self.vad_var, bg='#1e1e2e', fg='white', selectcolor='#313244').grid(row=0, column=0, sticky='w', pady=5, padx=10)
        
        lbl(f_feat, "Giây bỏ cuộc:").grid(row=0, column=1, sticky='w')
        self.vad_limit_entry = tk.Entry(f_feat, width=8, bg='#313244', fg='white', borderwidth=1)
        self.vad_limit_entry.insert(0, str(state.config.get("vad_silence_limit", 1.5)))
        self.vad_limit_entry.grid(row=0, column=2, padx=5, sticky='w')

        self.tts_var = tk.BooleanVar(value=state.config.get("enable_tts", False))
        tk.Checkbutton(f_feat, text="AI Đọc phản hồi (TTS)", variable=self.tts_var, bg='#1e1e2e', fg='white', selectcolor='#313244').grid(row=1, column=0, sticky='w', pady=5, padx=10)
        
        lbl(f_feat, "Ngôn ngữ (vi/en):").grid(row=1, column=1, sticky='w')
        self.lang_entry = tk.Entry(f_feat, width=8, bg='#313244', fg='white', borderwidth=1)
        self.lang_entry.insert(0, state.config.get("language", "vi"))
        self.lang_entry.grid(row=1, column=2, padx=5, sticky='w')

        self.smart_punc_var = tk.BooleanVar(value=state.config.get("smart_punctuation", False))
        tk.Checkbutton(f_feat, text="AI Tự sửa lỗi & Thêm dấu câu", variable=self.smart_punc_var, bg='#1e1e2e', fg='white', selectcolor='#313244').grid(row=2, column=0, columnspan=2, sticky='w', pady=5, padx=10)

        lbl(f_feat, "Chế độ Dịch:").grid(row=3, column=0, sticky='w', padx=10, pady=5)
        self.trans_mode_var = tk.StringVar(value=state.config.get("translation_mode", "Tắt"))
        self.trans_combo = ttk.Combobox(f_feat, textvariable=self.trans_mode_var, values=["Tắt", "Việt -> Anh", "Anh -> Việt"], width=15, state="readonly")
        self.trans_combo.grid(row=3, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        # Hotkeys
        f_keys = tk.LabelFrame(self.tab_general, text=" Phím tắt ", bg='#1e1e2e', fg='#a6adc8', font=('Segoe UI', 10, 'bold'))
        f_keys.pack(fill='x', pady=10)
        
        self.handsfree_var = tk.BooleanVar(value=state.config.get("hands_free", True))
        tk.Checkbutton(f_keys, text="Mặc định Rảnh tay", variable=self.handsfree_var, bg='#1e1e2e', fg='white', selectcolor='#313244').grid(row=0, column=0, columnspan=2, sticky='w', padx=10, pady=5)

        lbl(f_keys, "F8 (Gõ):").grid(row=1, column=0, sticky='w', padx=10)
        self.f8_key_entry = tk.Entry(f_keys, width=8, bg='#313244', fg='white', borderwidth=1)
        self.f8_key_entry.insert(0, state.config.get("hotkey_f8", "ctrl+alt+f8"))
        self.f8_key_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        lbl(f_keys, "F9 (AI):").grid(row=1, column=2, sticky='w', padx=10)
        self.f9_key_entry = tk.Entry(f_keys, width=8, bg='#313244', fg='white', borderwidth=1)
        self.f9_key_entry.insert(0, state.config.get("hotkey_f9", "ctrl+alt+f9"))
        self.f9_key_entry.grid(row=1, column=3, padx=5, pady=5, sticky='w')

    def setup_prompts_tab(self):
        f_tpl = tk.LabelFrame(self.tab_prompts, text=" Templates (Vai trò AI) ", bg='#1e1e2e', fg='#a6adc8', font=('Segoe UI', 10, 'bold'))
        f_tpl.pack(fill='both', expand=True, pady=10)

        self.tpl_listbox = tk.Listbox(f_tpl, height=5, bg='#313244', fg='white', borderwidth=0, selectbackground='#cba6f7', selectforeground='#1e1e2e')
        for t in state.config.get("prompt_templates", []):
            self.tpl_listbox.insert('end', t["name"])
        self.tpl_listbox.pack(fill='x', pady=10, padx=10)
        
        self.curr_idx = int(state.config.get("current_prompt_index", 0) or 0)
        if not 0 <= self.curr_idx < self.tpl_listbox.size():
            self.curr_idx = 0
        if 0 <= self.curr_idx < self.tpl_listbox.size():
            self.tpl_listbox.select_set(self.curr_idx)

        tk.Label(f_tpl, text="Prompt System hiện tại (F9):", fg='white', bg='#1e1e2e').pack(anchor='w', padx=10)
        self.f9_prompt_text = scrolledtext.ScrolledText(f_tpl, height=8, width=65, bg='#181825', fg='white', borderwidth=0, font=('Segoe UI', 9))
        
        def on_tpl_select(evt):
            w = evt.widget
            if not w.curselection(): return
            idx = w.curselection()[0]
            tpls = state.config.get("prompt_templates", [])
            self.f9_prompt_text.delete('1.0', 'end')
            self.f9_prompt_text.insert('1.0', tpls[idx]["prompt"])
        
        self.tpl_listbox.bind('<<ListboxSelect>>', on_tpl_select)
        if state.config.get("prompt_templates"):
            self.f9_prompt_text.insert('1.0', state.config["prompt_templates"][self.curr_idx]["prompt"])
        self.f9_prompt_text.pack(fill='both', expand=True, pady=10, padx=10)

    def setup_glossary_tab(self):
        f_glos = tk.LabelFrame(self.tab_glossary, text=" Từ Điển (Glossary) ", bg='#1e1e2e', fg='#a6adc8', font=('Segoe UI', 10, 'bold'))
        f_glos.pack(fill='both', expand=True, pady=10)

        self.glos_listbox = tk.Listbox(f_glos, height=8, bg='#313244', fg='white', borderwidth=0, selectbackground='#cba6f7', selectforeground='#1e1e2e')
        self.update_glos_list()
        self.glos_listbox.pack(fill='x', pady=10, padx=10)

        f_add = tk.Frame(f_glos, bg='#1e1e2e')
        f_add.pack(fill='x', pady=5, padx=10)
        tk.Label(f_add, text="Từ sai:", fg='white', bg='#1e1e2e').pack(side='left')
        self.wrong_entry = tk.Entry(f_add, width=15, bg='#313244', fg='white', borderwidth=1)
        self.wrong_entry.pack(side='left', padx=5)
        tk.Label(f_add, text="Sửa thành:", fg='white', bg='#1e1e2e').pack(side='left', padx=5)
        self.right_entry = tk.Entry(f_add, width=15, bg='#313244', fg='white', borderwidth=1)
        self.right_entry.pack(side='left')

        def add_term():
            w, r = self.wrong_entry.get().strip(), self.right_entry.get().strip()
            if w and r:
                state.glossary[w] = r
                save_glossary(); self.update_glos_list()
                self.wrong_entry.delete(0, 'end'); self.right_entry.delete(0, 'end')

        def del_term():
            sel = self.glos_listbox.curselection()
            if sel:
                key = self.glos_listbox.get(sel[0]).split(" -> ")[0]
                state.glossary.pop(key, None)
                save_glossary(); self.update_glos_list()

        tk.Button(f_add, text="THÊM", bg='#a6e3a1', fg='black', borderwidth=0, font=('Segoe UI', 8, 'bold'), command=add_term, cursor='hand2').pack(side='left', padx=10)
        tk.Button(f_glos, text="XÓA TỪ ĐANG CHỌN", bg='#f38ba8', fg='white', borderwidth=0, font=('Segoe UI', 8, 'bold'), command=del_term, cursor='hand2').pack(anchor='w', padx=10, pady=5)

    def setup_about_tab(self):
        f_about = tk.Frame(self.tab_about, bg='#1e1e2e')
        f_about.pack(fill='both', expand=True, pady=10)
        
        # App Info
        tk.Label(f_about, text="SMART VOICE AI ASSISTANT", font=('Segoe UI Variable Display', 18, 'bold'), fg='#89b4fa', bg='#1e1e2e').pack(pady=(10, 5))
        tk.Label(f_about, text="Phiên bản 3.0.0 | Powered by Whisper & Llama", font=('Segoe UI', 10), fg='#a6adc8', bg='#1e1e2e').pack(pady=(0, 20))
        
        # Guide
        f_guide = tk.LabelFrame(f_about, text=" Hướng Dẫn Sử Dụng Nhanh ", bg='#1e1e2e', fg='#a6adc8', font=('Segoe UI', 10, 'bold'), pady=10, padx=10)
        f_guide.pack(fill='x', padx=20, pady=10)
        
        guide_text = (
            f"• {HOTKEY_F8.upper()}: Nhấn một lần, nghe tiếng báo rồi bắt đầu nói. Dùng để chuyển giọng nói thành văn bản.\n"
            f"• App tự hoàn tất sau {state.config.get('vad_silence_limit', 2.0)} giây im lặng; cũng có thể nhấn ESC hoặc nhấn lại hotkey để dừng.\n"
            f"• {HOTKEY_F9.upper()}: Chế độ Trợ lý AI. Có thể:\n"
            "   - Hội thoại trực tiếp với LLM.\n"
            "   - Ra lệnh điều khiển máy tính (VD: 'Mở Discord', 'Mở Word').\n"
            "   - Tìm kiếm (VD: 'Tìm kiếm dự báo thời tiết mạng').\n"
            "• Khi thấy 'ĐANG XỬ LÝ', hãy chờ; kết quả sẽ được dán vào vị trí con trỏ."
        )
        tk.Label(f_guide, text=guide_text, font=('Segoe UI', 10), fg='#cdd6f4', bg='#1e1e2e', justify='left', anchor='w').pack(fill='x')
        
        # Copyright
        f_copy = tk.LabelFrame(f_about, text=" Bản Quyền & Liên Hệ ", bg='#1e1e2e', fg='#a6adc8', font=('Segoe UI', 10, 'bold'), pady=10, padx=10)
        f_copy.pack(fill='x', padx=20, pady=10)
        
        tk.Label(f_copy, text="Phát triển bởi: Phạm Đan Kha", font=('Segoe UI', 11, 'bold'), fg='#a6e3a1', bg='#1e1e2e').pack(anchor='w', pady=(0, 5))
        tk.Label(f_copy, text="Email hỗ trợ: khapham117@gmail.com", font=('Segoe UI', 10, 'italic'), fg='#f9e2af', bg='#1e1e2e').pack(anchor='w')

    def update_glos_list(self):
        self.glos_listbox.delete(0, 'end')
        for k, v in state.glossary.items(): self.glos_listbox.insert('end', f"{k} -> {v}")

    def save_all_settings(self):
        api_key = self.api_entry.get().strip()
        language = self.lang_entry.get().strip().lower()
        hotkey_f8 = self.f8_key_entry.get().strip().lower()
        hotkey_f9 = self.f9_key_entry.get().strip().lower()
        if language not in {"vi", "en"}:
            messagebox.showerror("Cấu hình không hợp lệ", "Ngôn ngữ chỉ nhận 'vi' hoặc 'en'.")
            return
        if not is_valid_hotkey(hotkey_f8) or not is_valid_hotkey(hotkey_f9) or hotkey_f8 == hotkey_f9:
            messagebox.showerror("Cấu hình không hợp lệ", "Hai phím tắt phải hợp lệ, khác nhau và không được để trống.")
            return
        try:
            vad_limit = float(self.vad_limit_entry.get().strip())
            if not 0.5 <= vad_limit <= 30:
                raise ValueError
        except ValueError:
            messagebox.showerror("Cấu hình không hợp lệ", "Thời gian VAD phải từ 0.5 đến 30 giây.")
            return

        state.config["api_key"] = api_key
        state.config["language"] = language
        state.config["hands_free"] = self.handsfree_var.get()
        state.config["hotkey_f8"] = hotkey_f8
        state.config["hotkey_f9"] = hotkey_f9
        state.config["vad_enabled"] = self.vad_var.get()
        state.config["enable_tts"] = self.tts_var.get()
        state.config["smart_punctuation"] = self.smart_punc_var.get()
        state.config["translation_mode"] = self.trans_mode_var.get()
        state.config["vad_silence_limit"] = vad_limit
        
        sel = self.tpl_listbox.curselection()
        if sel:
            state.config["current_prompt_index"] = sel[0]
            state.config["prompt_templates"][sel[0]]["prompt"] = self.f9_prompt_text.get('1.0', 'end').strip()
            state.config["ai_system_prompt"] = state.config["prompt_templates"][sel[0]]["prompt"]

        save_settings_to_file()
        load_settings()
        messagebox.showinfo("Thành công", "Đã lưu và áp dụng toàn bộ cấu hình mới!")
        self.destroy()

def show_dashboard():
    if not state.root: return
    if hasattr(state, 'dashboard_window') and state.dashboard_window and state.dashboard_window.winfo_exists():
        state.dashboard_window.deiconify()
        state.dashboard_window.lift()
        state.dashboard_window.focus_force()
    else:
        state.dashboard_window = MainDashboard(state.root)


def show_api_required() -> None:
    show_dashboard()
    messagebox.showwarning(
        "Cần Groq API key",
        "Ứng dụng đã nhận hotkey nhưng chưa có API key.\n\n"
        "Hãy nhập key ở tab CÀI ĐẶT → API Groq, rồi bấm LƯU TẤT CẢ THIẾT LẬP."
    )

def save_glossary():
    """Lưu từ điển hiện tại vào file JSON."""
    try:
        atomic_write_json(GLOSSARY_FILE, state.glossary)
        # Reload immediately in state
        load_glossary()
    except Exception as e:
        logging.exception("Lỗi lưu từ điển")
        log_message(f"Lỗi lưu từ điển: {e}", logging.ERROR)

# ================= KIỂM TRA GIỚI HẠN =================
def check_limits(duration: float, request_count: int = 1) -> tuple[bool, str]:
    now = datetime.now()
    hour_key = now.strftime("%Y-%m-%d-%H")
    with state.lock:
        if state.used_seconds + duration > LIMIT_ASD: return False, "Hết hạn mức ngày (8h)"
        if state.used_requests + request_count > LIMIT_RPD:
            return False, f"Hết lượt gọi ngày ({LIMIT_RPD} lượt)"
        current_hour_sec = state.hourly_seconds.get(hour_key, 0.0)
        if current_hour_sec + duration > LIMIT_ASH: return False, "Hết hạn mức giờ (2h/giờ)"
        now_ts = time.time()
        state.minute_requests = [ts for ts in state.minute_requests if now_ts - ts < 60]
        if len(state.minute_requests) + request_count > LIMIT_RPM:
            return False, "Quá nhanh! Giới hạn 20 lượt/phút"
    return True, ""


def record_usage(duration: float, request_count: int) -> None:
    now = datetime.now()
    hour_key = now.strftime("%Y-%m-%d-%H")
    request_time = time.time()
    with state.lock:
        state.used_seconds += duration
        state.used_requests += request_count
        state.hourly_seconds[hour_key] = state.hourly_seconds.get(hour_key, 0.0) + duration
        state.minute_requests.extend([request_time] * request_count)
    save_quota()

# ================= XỬ LÝ ÂM THANH & API =================
def process_audio(audio_data, is_raw=True):
    """Xử lý âm thanh voice-to-text thông thường. Nếu is_raw=True, bỏ qua context và LLM."""
    update_status("processing", "f8")
    audio_data = normalize_audio(audio_data)
    duration = float(len(audio_data) / SAMPLE_RATE)
    if duration < 0.4: return

    needs_second_request = not is_raw and (
        state.config.get("translation_mode", "Tắt") != "Tắt"
        or state.config.get("smart_punctuation", False)
    )
    can_proceed, msg = check_limits(duration, 2 if needs_second_request else 1)
    if not can_proceed:
        if state.status_window:
            state.status_window.show(f"⚠ {msg.upper()}", "#ff4b4b")
            threading.Timer(3.0, state.status_window.hide).start()
        play_sound("error")
        return

    # F8 tập trung vào độ chính xác thô (Raw Transcription)
    if is_raw:
        # Prompt cực kỳ đơn giản để tránh Whisper tự 'thông minh' hóa
        dynamic_prompt = "Hãy chép chính xác từng từ tiếng Việt, bao gồm cả các thuật ngữ: code, data, app, API, AI, python."
    else:
        # Nếu không phải raw (nhưng dùng function này) thì mới lấy context
        context = get_active_window_context()
        base_prompt = state.config.get("transcription_prompt", DEFAULT_CONFIG["transcription_prompt"])
        dynamic_prompt = f"{base_prompt} Ngữ cảnh hiện tại: {context}."

    # Sử dụng bộ nhớ đệm RAM thay vì ghi file xuống ổ cứng
    audio_buffer = io.BytesIO()
    with wave.open(audio_buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2) # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())
    
    audio_buffer.seek(0)

    try:
        api = get_client()
        raw_lang = state.config.get("language", DEFAULT_CONFIG["language"]).lower()
        iso_lang = "vi" if "vi" in raw_lang else "en"
        
        transcription = api.audio.transcriptions.create(
            file=("audio.wav", audio_buffer),
            model=state.config.get("transcription_model", "whisper-large-v3"),
            prompt=dynamic_prompt, 
            response_format="text",
            language=iso_lang
        )
        record_usage(duration, 1)
        user_input = str(transcription).strip()
        
        # Whisper Hallucination Filter
        hallucinations = ["hãy subscribe", "theo dõi kênh", "đăng ký kênh", "hẹn gặp lại", "la la school", "ghiền mì gõ"]
        if not user_input:
            return
        
        # Nếu chỉ có các từ rác này và độ dài ngắn, thì mới bỏ qua.
        # Không bỏ qua "cảm ơn" vì đây là câu nói bình thường của người dùng.
        if len(user_input) < 50 and any(h in user_input.lower() for h in hallucinations):
            log_message(f"Hallucination detected & filtered: {user_input}")
            return
            
        raw_text = user_input
        log_message(f"F8 (Gốc): '{raw_text}'")
        
        if raw_text:
            # 2. Xử lý Dịch thuật (chỉ thực hiện nếu KHÔNG đang ở chế độ Raw F8)
            trans_mode = "Tắt" if is_raw else state.config.get("translation_mode", "Tắt")
            if trans_mode != "Tắt":
                try:
                    target_lang = "English" if "Anh" in trans_mode else "Vietnamese"
                    src_lang = "Vietnamese" if "Việt" in trans_mode else "English"
                    
                    response = api.chat.completions.create(
                        model=state.config.get("fast_model", "qwen/qwen3.8-27b"),
                        messages=[
                            {"role": "system", "content": f"Bạn là biên dịch viên cao cấp. Hãy dịch văn bản sau từ {src_lang} sang {target_lang}. CHỈ TRẢ VỀ bản dịch, không giải thích."},
                            {"role": "user", "content": raw_text}
                        ],
                        temperature=0.1,
                        reasoning_effort="none"
                    )
                    raw_text = response.choices[0].message.content.strip()
                    record_usage(0.0, 1)
                except Exception as e:
                    logging.exception("Lỗi dịch")
                    log_message(f"Lỗi Dịch: {e}", logging.ERROR)
            
            # 3. Xử lý thông minh (chỉ thực hiện nếu bật & KHÔNG đang ở chế độ Raw F8)
            elif not is_raw and state.config.get("smart_punctuation", False):
                try:
                    context = get_active_window_context()
                    response = api.chat.completions.create(
                        model=state.config.get("fast_model", "qwen/qwen3.8-27b"),
                        messages=[
                            {"role": "system", "content": f"""Bạn là một biên tập viên. NGỮ CẢNH: {context}.
Chỉ làm 2 việc: 
1. Thêm dấu câu (phẩy, chấm, chấm hỏi) vào cho đúng ngữ pháp.
2. Viết hoa chữ cái đầu câu và tên riêng.
TUYỆT ĐỐI GIỮ NGUYÊN 100% TỪ VỰNG CỦA NGƯỜI DÙNG, không được tóm tắt, không thêm bớt chữ, không diễn giải lại. Chỉ trả về kết quả."""},
                            {"role": "user", "content": raw_text}
                        ],
                        temperature=0.1,
                        reasoning_effort="none"
                    )
                    raw_text = response.choices[0].message.content.strip()
                    record_usage(0.0, 1)
                except Exception as e:
                    logging.exception("Lỗi Smart Punctuation")
                    log_message(f"Lỗi Smart Punc: {e}", logging.ERROR)

            text = apply_glossary(raw_text)
            
            # Sử dụng Clipboard Manager mới
            clipboard_manager.paste_text(text)
            
    except Exception as e:
        logging.exception("Lỗi chuyển giọng nói thành văn bản")
        log_message(f"Lỗi Transcribe: {e}", logging.ERROR)
        if state.status_window:
            state.status_window.show("⚠ LỖI KẾT NỐI", "#ff4b4b")
            threading.Timer(3.0, state.status_window.hide).start()
        play_sound("error")
    finally:
        update_status("idle")
        audio_buffer.close()

def get_selected_text() -> str:
    """Sao chép văn bản đang chọn vào clipboard và trả về nội dung đó."""
    old_clip = None
    try:
        old_clip = pyperclip.paste()
        pyperclip.copy("")
        keyboard.send('ctrl+c')
        time.sleep(0.2)
        return str(pyperclip.paste() or "")
    except Exception:
        logging.exception("Không thể đọc văn bản đang chọn")
        return ""
    finally:
        if old_clip is not None:
            try:
                pyperclip.copy(old_clip)
            except Exception:
                logging.exception("Không thể khôi phục clipboard sau Ctrl+C")

def process_llm_task(audio_data, selected_text: str = ""):
    """Xử lý yêu cầu AI linh hoạt."""
    update_status("processing", "f9")
    audio_data = normalize_audio(audio_data)
    duration = float(len(audio_data) / SAMPLE_RATE)
    if duration < 0.4: return

    can_proceed, msg = check_limits(duration + 1.0, 2)
    if not can_proceed:
        if state.status_window:
            state.status_window.show(f"⚠ {msg.upper()}", "#ff4b4b")
            threading.Timer(3.0, state.status_window.hide).start()
        play_sound("error")
        return

    # Sử dụng bộ nhớ đệm RAM cho LLM task
    audio_buffer = io.BytesIO()
    with wave.open(audio_buffer, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())
    
    audio_buffer.seek(0)

    try:
        api = get_client()
        # 1. Chuyển giọng nói thành văn bản
        raw_lang = state.config.get("language", DEFAULT_CONFIG["language"]).lower()
        iso_lang = "vi" if "vi" in raw_lang else "en"
        
        transcription = api.audio.transcriptions.create(
            file=("audio_ai.wav", audio_buffer),
            model=state.config.get("transcription_model", "whisper-large-v3"),
            prompt="Chào bạn, tôi có thể giúp gì cho bạn? Đây là tiếng Việt.", # Prompt mồi để Whisper nhận dạng tốt tiếng Việt
            response_format="text", 
            language=iso_lang
        )
        record_usage(duration, 1)
        user_input = str(transcription).strip()
        
        # Whisper Hallucination Filter
        hallucinations = ["hãy subscribe", "theo dõi kênh", "đăng ký kênh", "hẹn gặp lại", "subcribe", "la la school", "ghiền mì gõ"]
        if not user_input:
            return
            
        if len(user_input) < 50 and any(h in user_input.lower() for h in hallucinations):
            return

        # Kiểm tra lệnh xóa bộ nhớ
        if any(cmd in user_input.lower() for cmd in ["xóa bộ nhớ", "xóa lịch sử", "bắt đầu mới"]):
            state.llm_history = []
            log_message("AI: Đã xóa bộ nhớ ngữ cảnh.")
            play_sound("end")
            return

        # 2. Chuẩn bị Messages cho LLM (có bao gồm lịch sử và ngữ cảnh)
        log_message(f"AI đang xử lý: '{user_input}'" + (f" trên đoạn văn bản chọn sẵn" if selected_text else ""))
        
        context = get_active_window_context()
        base_system_prompt = state.config.get("ai_system_prompt", DEFAULT_CONFIG["ai_system_prompt"])
        
        # Bổ sung hướng dẫn về Action cho AI
        action_instructions = """
Nếu người dùng yêu cầu MỞ một chương trình, ứng dụng hoặc Tìm kiếm Web, hãy trả về kết quả theo cấu trúc:
- 'ACTION: OPEN [tên ứng dụng]' (Ví dụ: ACTION: OPEN chrome, ACTION: OPEN notepad)
- 'ACTION: SEARCH [nội dung tìm kiếm]' (Ví dụ: ACTION: SEARCH thời tiết hôm nay)
Nếu không, chỉ trả về văn bản hồi đáp thông thường."""
        
        system_prompt = f"{base_system_prompt}\nNGỮ CẢNH HIỆN TẠI: Người dùng đang sử dụng ứng dụng {context}.\n{action_instructions}"
        
        # Xây dựng danh sách messages từ lịch sử
        messages = [{"role": "system", "content": system_prompt}]
        for turn in state.llm_history[-6:]: # Chỉ lấy 6 tương tác gần nhất (3 cặp) để tiết kiệm token
            messages.append(turn)
            
        current_content = f"Lệnh/Yêu cầu: \"{user_input}\""
        if selected_text:
            current_content = f"Văn bản gốc: \"{selected_text}\"\n\nLệnh/Yêu cầu: \"{user_input}\""
            
        messages.append({"role": "user", "content": current_content})

        response = api.chat.completions.create(
            model=state.config.get("assistant_model", "qwen/qwen3.8-27b"),
            messages=messages,
            temperature=0.3,
            reasoning_effort="none"
        )
        record_usage(0.0, 1)
        result_text = response.choices[0].message.content.strip()
        
        if result_text:
            # 3. Kiểm tra xem có phải là một hành động (Action) không
            action_result = execute_action(result_text)
            if action_result:
                speak_text(action_result)
                if state.status_window:
                    state.status_window.show(f"✔ {action_result.upper()}", "#4bb5ff")
                    threading.Timer(2.5, state.status_window.hide).start()
            else:
                state.llm_history.append({"role": "user", "content": f"Yêu cầu trước: {user_input}"})
                state.llm_history.append({"role": "assistant", "content": result_text})
                if len(state.llm_history) > 20:
                    state.llm_history = state.llm_history[-20:]
                clipboard_manager.paste_text(result_text)
                speak_text(result_text)
            
    except Exception as e:
        logging.exception("Lỗi tác vụ AI")
        log_message(f"Lỗi LLM: {e}", logging.ERROR)
        if state.status_window:
            state.status_window.show("⚠ LỖI AI", "#ff4b4b")
            threading.Timer(3.0, state.status_window.hide).start()
        play_sound("error")
    finally:
        update_status("idle")
        audio_buffer.close()

def _on_global_hotkey(is_ai: bool) -> None:
    key = HOTKEY_F9 if is_ai else HOTKEY_F8
    now = time.monotonic()
    if now - state.last_hotkey_time.get(key, 0.0) < 0.35:
        return
    state.last_hotkey_time[key] = now
    if state.is_recording:
        state.is_recording = False
        return
    if not state.is_processing:
        state.hotkey_queue.put(is_ai)


def parse_windows_hotkey(value: str) -> tuple[int, int]:
    parts = [part.strip().lower() for part in value.split("+") if part.strip()]
    if not parts:
        raise ValueError("Hotkey trống")
    modifiers = 0x4000  # MOD_NOREPEAT
    modifier_map = {"alt": 0x0001, "ctrl": 0x0002, "control": 0x0002, "shift": 0x0004, "win": 0x0008}
    key_name = parts[-1]
    for part in parts[:-1]:
        if part not in modifier_map:
            raise ValueError(f"Modifier không hỗ trợ: {part}")
        modifiers |= modifier_map[part]
    if re.fullmatch(r"f(?:[1-9]|1[0-9]|2[0-4])", key_name):
        virtual_key = 0x70 + int(key_name[1:]) - 1
    elif len(key_name) == 1 and key_name.isalnum():
        virtual_key = ord(key_name.upper())
    elif key_name == "space":
        virtual_key = 0x20
    else:
        raise ValueError(f"Phím không hỗ trợ: {key_name}")
    return modifiers, virtual_key


def native_hotkey_listener() -> None:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    state.hotkey_thread_id = kernel32.GetCurrentThreadId()
    f8_modifiers, f8_key = parse_windows_hotkey(HOTKEY_F8)
    f9_modifiers, f9_key = parse_windows_hotkey(HOTKEY_F9)
    registered_f8 = bool(user32.RegisterHotKey(None, 1, f8_modifiers, f8_key))
    registered_f9 = bool(user32.RegisterHotKey(None, 2, f9_modifiers, f9_key))
    if not registered_f8 or not registered_f9:
        message = f"Không thể đăng ký hotkey {HOTKEY_F8}/{HOTKEY_F9}. Có thể ứng dụng khác đang sử dụng."
        log_message(message, logging.ERROR)
        post_ui(messagebox.showerror, "Lỗi phím tắt", message)
    else:
        log_message(f"Đã đăng ký Windows hotkey: {HOTKEY_F8}, {HOTKEY_F9}")
    message = wintypes.MSG()
    try:
        while state.app_running:
            result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result <= 0:
                break
            if message.message == 0x0312:  # WM_HOTKEY
                if message.wParam == 1:
                    _on_global_hotkey(False)
                elif message.wParam == 2:
                    _on_global_hotkey(True)
    finally:
        if registered_f8:
            user32.UnregisterHotKey(None, 1)
        if registered_f9:
            user32.UnregisterHotKey(None, 2)
        state.hotkey_thread_id = None


def restart_hotkey_listener() -> None:
    if state.hotkey_thread_id:
        ctypes.windll.user32.PostThreadMessageW(state.hotkey_thread_id, 0x0012, 0, 0)  # WM_QUIT
    if state.hotkey_thread and state.hotkey_thread.is_alive():
        state.hotkey_thread.join(timeout=1.0)
    state.hotkey_thread = threading.Thread(target=native_hotkey_listener, daemon=True)
    state.hotkey_thread.start()


def voice_listener():
    log_message(f"Hệ thống sẵn sàng: {HOTKEY_F8} (Gõ phím), {HOTKEY_F9} (AI thông minh).")
    while state.app_running:
        try:
            is_ai = state.hotkey_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        key = HOTKEY_F9 if is_ai else HOTKEY_F8

        if not str(state.config.get("api_key", "")).strip():
            play_sound("error")
            post_ui(show_api_required)
            while keyboard.is_pressed(key):
                time.sleep(0.02)
            time.sleep(0.25)
            continue
        
        if state.is_recording or state.is_processing:
            continue

        selected_text = str(get_selected_text()).strip() if is_ai else ""
        state.is_recording = True
        update_status("recording", key)
        play_sound("start")
        
        active_chunks = []
        last_voice_time = time.time()
        vad_limit = state.config.get("vad_silence_limit", 1.5) if state.config.get("vad_enabled", True) else 9999
        
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16') as stream:
                thresh = state.config.get("silence_threshold", 500)
                
                # Hàm check âm lượng & cập nhật UI
                noise_floor = thresh
                def _process_frame(data):
                    nonlocal last_voice_time, noise_floor
                    vol = int(np.max(np.abs(data.astype(np.int32))))
                    
                    # Cập nhật mức ồn nền tĩnh (Noise Floor)
                    noise_floor = noise_floor * 0.98 + vol * 0.02
                    # Ngưỡng động: Cần lớn hơn mức ồn nền 20% hoặc ngưỡng tối thiểu
                    dynamic_thresh = max(thresh, noise_floor * 1.2)
                    
                    if state.status_window:
                        state.status_window.update_meter(min(1.0, vol / 5000))
                    
                    if vol > dynamic_thresh:
                        last_voice_time = time.time()
                        return True
                    return False

                if state.hands_free_mode:
                    # Nhả lần nhấn khởi động; lần nhấn kế tiếp mới là lệnh dừng.
                    release_deadline = time.time() + 2.0
                    while keyboard.is_pressed(key) and time.time() < release_deadline:
                        time.sleep(0.02)
                    pre_roll = deque(maxlen=13)  # Khoảng 0.4 giây để không mất âm đầu.
                    heard_speech = False
                    while state.is_recording:
                        data, _ = stream.read(512)
                        is_voice = _process_frame(data)
                        if not heard_speech:
                            pre_roll.append(data.copy())
                            if is_voice:
                                active_chunks.extend(pre_roll)
                                pre_roll.clear()
                                heard_speech = True
                        else:
                            # Giữ cả khoảng ngắt ngắn và âm cuối, thay vì ghép riêng frame lớn tiếng.
                            active_chunks.append(data.copy())
                        
                        # VAD: Tự động ngừng nếu im lặng quá lâu
                        if time.time() - last_voice_time > vad_limit:
                            log_message("VAD: Tự động ngắt do im lặng.")
                            state.is_recording = False
                        
                        # Dừng bằng phím Esc hoặc phím tắt
                        if keyboard.is_pressed('esc') or keyboard.is_pressed(key): 
                            state.is_recording = False
                else:
                    while keyboard.is_pressed(key):
                        data, _ = stream.read(512)
                        _process_frame(data)
                        active_chunks.append(data.copy())
                        if keyboard.is_pressed('esc'): break
                    state.is_recording = False
        except Exception as e:
            logging.exception("Lỗi âm thanh")
            log_message(f"Lỗi âm thanh: {e}", logging.ERROR)
            state.is_recording = False
            
        play_sound("end")
        
        if active_chunks:
            audio_data = np.concatenate(active_chunks, axis=0)
            worker = process_llm_task if is_ai else process_audio
            args = (audio_data, selected_text) if is_ai else (audio_data,)
            state.is_processing = True
            threading.Thread(target=run_processing_task, args=(worker, *args), daemon=True).start()
        
        time.sleep(0.3)

# ================= GIAO DIỆN TRAY =================
def toggle_mode(icon, item):
    state.hands_free_mode = not state.hands_free_mode
    state.config["hands_free"] = state.hands_free_mode
    save_settings_to_file()
    update_tooltip()

def reload_glossary_tray(icon, item):
    load_glossary()
    if hasattr(winsound, "Beep"):
        getattr(winsound, "Beep")(800, 150)

def show_info(icon):
    used_h = state.used_seconds / 3600
    now = datetime.now()
    hour_key = now.strftime("%Y-%m-%d-%H")
    msg = (f"ASD (Hạn mức Ngày): {used_h:.2f}/8.00 giờ\n"
           f"RPD (Lượt Ngày): {state.used_requests}/{LIMIT_RPD} lượt\n"
           f"ASH (Trong giờ này): {state.hourly_seconds.get(hour_key, 0.0)/60:.1f}/120 phút\n"
           f"RPM (Trong phút này): {len(state.minute_requests)}/{LIMIT_RPM} lượt\n\n"
           f"Từ điển: {len(state.glossary)} từ khóa đang nạp\n"
           f"F8: Voice-to-Text (Gõ phím) | F9: AI xử lý trực tiếp\n"
           f"Chế độ hiện tại: {'Rảnh tay (Nhấn F8/F9 để Bật/Tắt)' if state.hands_free_mode else 'Nhấn giữ F8/F9'}")
    
    if hasattr(ctypes, "windll"):
        getattr(ctypes, "windll").user32.MessageBoxW(0, msg, "Chi tiết Lưu lượng Groq", 64)
    else:
        log_message(msg)

def setup_tray():
    icon_path = resource_path("app_icon.png")
    try: icon_img = Image.open(icon_path)
    except Exception:
        icon_img = Image.new('RGB', (64, 64), color=(30, 30, 30))
        d = ImageDraw.Draw(icon_img); d.ellipse([16, 16, 48, 48], fill=(0, 200, 255))

    menu = (
        pystray.MenuItem(lambda item: "✓ Chế độ Rảnh tay" if state.hands_free_mode else "Chế độ Rảnh tay", toggle_mode),
        pystray.MenuItem(lambda item: f"{HOTKEY_F8.upper()}: Ghi âm → văn bản", lambda icon, item: None, enabled=False),
        pystray.MenuItem(lambda item: f"{HOTKEY_F9.upper()}: Trợ lý AI", lambda icon, item: None, enabled=False),
        pystray.MenuItem("Bảng điều khiển (Dashboard)", lambda icon, item: state.root.after(0, show_dashboard) if state.root else None, default=True),
        pystray.MenuItem("Tải lại từ điển", reload_glossary_tray),
        pystray.MenuItem("Thoát", shutdown_app)
    )
    state.tray_icon = pystray.Icon("GroqVoice", icon_img, "Smart Voice Typing (F8/F9)", menu)
    update_tooltip()
    # Chạy tray trong thread riêng để không block Tkinter
    threading.Thread(target=state.tray_icon.run, daemon=True).start()


def show_startup_state() -> None:
    if not str(state.config.get("api_key", "")).strip():
        show_api_required()
        return
    if state.status_window:
        state.status_window.show(
            f"✓ SẴN SÀNG\n{HOTKEY_F8.upper()}: nói → văn bản | {HOTKEY_F9.upper()}: AI",
            "#a6e3a1"
        )
        threading.Timer(5.0, state.status_window.hide).start()


def run_processing_task(worker, *args) -> None:
    try:
        worker(*args)
    except Exception:
        logging.exception("Worker xử lý bị lỗi ngoài dự kiến")
    finally:
        state.is_processing = False
        update_status("idle")


def shutdown_app(icon=None, item=None) -> None:
    state.app_running = False
    state.is_recording = False
    if state.hotkey_thread_id:
        ctypes.windll.user32.PostThreadMessageW(state.hotkey_thread_id, 0x0012, 0, 0)
    try:
        save_quota()
    except Exception:
        logging.exception("Không thể lưu quota khi thoát")
    if icon:
        icon.stop()
    if state.root:
        post_ui(state.root.quit)


_single_instance_handle = None


def ensure_single_instance() -> bool:
    global _single_instance_handle
    kernel32 = ctypes.windll.kernel32
    _single_instance_handle = kernel32.CreateMutexW(None, False, "Local\\SmartVoiceAI.Singleton")
    if kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(0, "Smart Voice AI đang chạy trong khay hệ thống.", APP_NAME, 48)
        return False
    return True

if __name__ == "__main__":
    if sys.platform != "win32": sys.exit()
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging()
    if not ensure_single_instance():
        sys.exit(0)
    migrate_legacy_files()
    load_settings() # Nạp cấu hình từ file
    load_quota()
    load_glossary()
    
    # Khởi tạo Tkinter
    state.root = tk.Tk()
    state.root.withdraw()
    state.root.protocol("WM_DELETE_WINDOW", shutdown_app)
    state.status_window = FloatingIndicator(state.root)
    state.root.after(40, process_ui_queue)
    
    restart_hotkey_listener()
    threading.Thread(target=voice_listener, daemon=True).start()
    setup_tray()
    state.root.after(300, show_startup_state)
    
    state.root.mainloop()
