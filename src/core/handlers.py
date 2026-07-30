# qqbot/handlers.py — command dispatch table
from ..mc.server import (
    fmt_status, fmt_tps, fmt_players, fmt_memory, fmt_logs, fmt_backups,
    fmt_help, fmt_raw, fmt_admin, run,
)
from ..chat.luna import fmt_luna
from ..chat.music import fmt_music
from .config import _mc_cfg, FREE_CMD

HANDLERS = {
    "状态": fmt_status, "性能": fmt_tps, "在线人数": fmt_players,
    "内存": fmt_memory, "日志": fmt_logs, "备份": fmt_backups, "帮助": fmt_help,
    "/status": lambda: fmt_raw(["sudo", "systemctl", "status", _mc_cfg()["service_name"], "--no-pager"]),
    "/tps": lambda: fmt_raw([f"{_mc_cfg()['server_dir']}/rcon-query.sh", "tps"]),
    "/player": lambda: fmt_raw([f"{_mc_cfg()['server_dir']}/rcon-query.sh", "list"]),
    "/memory": lambda: fmt_raw(FREE_CMD),
    "/log": lambda: fmt_raw(["sudo", "journalctl", "-u", _mc_cfg()["service_name"], "--no-pager", "-n", "30"]),
    "/backups": lambda: fmt_raw(["ls", "-lh", f"{_mc_cfg()['server_dir']}/backups/"]),
    "/help": fmt_help,
    "/start": lambda: fmt_admin("start"),
    "/stop": lambda: fmt_admin("stop"),
    "/restart": lambda: fmt_admin("restart"),
    "/backup": lambda: fmt_admin("backup"),
}

PREFIX_HANDLERS = {
    "luna": fmt_luna, "/luna": fmt_luna,
    "音乐": fmt_music, "/music": fmt_music,
}
