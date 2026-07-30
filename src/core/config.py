# qqbot/config.py — shared configuration, logging, rate limiting
import json, os, sys, time

# ── QQ Bot credentials ──────────────────────────────────────
APP_ID = "1905273698"
APP_SECRET = "57yjMrJgw30oRq47"
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 3005

ACCESS_TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
SEND_MSG_URL = "https://api.sgroup.qq.com/v2/users/{openid}/messages"
UPLOAD_URL = "https://api.sgroup.qq.com/v2/users/{openid}/files"

DEEPSEEK_KEY = "YOUR_DEEPSEEK_KEY"
DEEPSEEK_URL = "http://127.0.0.1:3003/v1/chat/completions"

FREE_CMD = ["bash", "-c", "LC_ALL=C free -h"]

# ── Module-level state ──────────────────────────────────────
_seen_msg_ids: set = set()
_user_msg_times: dict[str, list[float]] = {}
_luna_ratelimit: dict[str, list[float]] = {}
_alert_openid: str = ""
_alert_active: dict[str, bool] = {}
_config_cache: dict | None = None
_config_mtime: float = 0.0

MSG_RATE_LIMIT = 20
MSG_RATE_WINDOW = 60
ALERT_CHECK_SEC = 30

REJECT_MSG = (
    "⚠ 无法识别该指令\n\n"
    "本 bot 用于查询 mc.chieko3020.xyz 的实时状态\n\n"
    "📋 可用指令：\n"
    "状态 / 性能 / 在线人数 / 内存 / 日志 / 备份\n"
    "luna — 露娜 AI 聊天（例: luna 你好）\n\n"
    "💡 发送「帮助」查看完整菜单"
)

# ── Logging ─────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_LEVELS = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log")

def _log(level: str, msg: str):
    if LOG_LEVELS.get(level, 1) >= LOG_LEVELS.get(LOG_LEVEL, 1):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        print(line, file=sys.stderr, flush=True)
        try:
            with open(LOG_FILE, "a") as f:
                f.write(line + "\n")
        except:
            pass

def _check_rate_limit(store: dict, key: str, limit: int, window: float) -> tuple[bool, list[float]]:
    """Sliding-window rate limit. Returns (blocked, timestamps)."""
    now = time.time()
    times = [t for t in store.get(key, []) if now - t < window]
    blocked = len(times) >= limit
    if not blocked:
        times.append(now)
        store[key] = times
    return blocked, times

# ── MC Server config ────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../config/bot_config.json")
DEFAULT_CONFIG = {
    "状态": True, "性能": True, "在线人数": True, "内存": True,
    "日志": True, "备份": True, "帮助": True, "音乐": False, "luna": True,
}

def load_config() -> dict:
    """Load bot_config.json with mtime-based caching."""
    global _config_cache, _config_mtime
    try:
        mtime = os.path.getmtime(CONFIG_FILE)
    except OSError:
        return dict(DEFAULT_CONFIG)
    if _config_cache is not None and mtime == _config_mtime:
        return _config_cache
    try:
        with open(CONFIG_FILE) as f:
            _config_cache = {**DEFAULT_CONFIG, **json.load(f)}
            _config_mtime = mtime
            return _config_cache
    except:
        return dict(DEFAULT_CONFIG)

def _mc_cfg():
    """Lazy load MC server config from bot_config.json."""
    cfg = load_config().get("mc_server", {})
    return {
        "name": cfg.get("name", "MC Server"),
        "host": cfg.get("host", "127.0.0.1"),
        "rcon_port": cfg.get("rcon_port", 25575),
        "rcon_password": cfg.get("rcon_password", ""),
        "service_name": cfg.get("service_name", "mcserver"),
        "server_dir": cfg.get("server_dir", "/home/ubuntu/minecraft"),
    }
