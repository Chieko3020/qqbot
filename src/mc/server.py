# qqbot/mc_server.py — MC server monitoring, RCON, backup
import os, re, socket, struct, subprocess, time
from ..core.config import _mc_cfg, FREE_CMD, _log

def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=_mc_cfg()["server_dir"])
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return "(timeout)"
    except Exception as e:
        return f"(error: {e})"

def is_server_up():
    r = run(["sudo", "systemctl", "is-active", _mc_cfg()["service_name"]], timeout=5)
    return r == "active"

def fmt_server_down():
    return "🔴 服务器已关闭\n发送 /start 启动服务器"

def _rcon(cmd: str) -> str:
    """Send RCON command to MC server."""
    cfg = _mc_cfg()
    password = cfg["rcon_password"]
    if not password:
        props_file = os.path.join(cfg["server_dir"], "server", "server.properties")
        try:
            with open(props_file) as f:
                for line in f:
                    if line.startswith("rcon.password="):
                        password = line.split("=", 1)[1].strip()
                        break
        except:
            pass
    if not password:
        return "(RCON not configured)"
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((cfg["host"], cfg["rcon_port"]))
        data = password.encode() + b"\x00\x00"
        packet_len = 4 + 4 + len(data)
        sock.sendall(struct.pack("<iii", packet_len, 0, 3) + data)
        hdr = sock.recv(12)
        if len(hdr) < 12 or struct.unpack("<i", hdr[4:8])[0] == -1:
            sock.close()
            return "(RCON auth failed)"
        data = cmd.encode() + b"\x00\x00"
        packet_len = 4 + 4 + len(data)
        sock.sendall(struct.pack("<iii", packet_len, 1, 2) + data)
        hdr = sock.recv(12)
        if len(hdr) < 12:
            sock.close()
            return ""
        length = struct.unpack("<i", hdr[:4])[0]
        payload_len = length - 8
        resp = b""
        while len(resp) < payload_len:
            chunk = sock.recv(payload_len - len(resp))
            if not chunk: break
            resp += chunk
        sock.close()
        return resp.rstrip(b"\x00").decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"(RCON error: {e})"

def _backup_world() -> str:
    """Create world backup via RCON save-off → tar → save-on."""
    cfg = _mc_cfg()
    ts = time.strftime("%Y%m%d-%H%M")
    backup_dir = os.path.join(cfg["server_dir"], "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, f"backup-{ts}.tar.gz")
    _rcon("save-off")
    time.sleep(1)
    _rcon("save-all")
    time.sleep(2)
    try:
        subprocess.run(["tar", "-czf", backup_file, "-C",
                        os.path.join(cfg["server_dir"], "server"), "world"],
                       timeout=60, capture_output=True)
        size = os.path.getsize(backup_file)
        _rcon("save-on")
        _rcon(f"say Backup complete: backup-{ts}")
        return f"✅ 备份完成\n文件: backup-{ts}.tar.gz\n大小: {size//1024//1024}MB"
    except Exception as e:
        _rcon("save-on")
        return f"⚠ 备份失败: {e}"

# ── Output formatters ───────────────────────────────────────

def fmt_status():
    if not is_server_up():
        return fmt_server_down()
    st = run(["sudo", "systemctl", "status", _mc_cfg()["service_name"], "--no-pager"])
    mem = run(FREE_CMD)
    active, uptime, mc_mem = "未知", "", ""
    m = re.search(r'Active:\s*(\S+)\s*\((\S+)\)\s*since\s*(.+?);\s*(.+?)\n', st)
    if m:
        active = "运行中" if m.group(1) == "active" else m.group(1)
        uptime = re.sub(r'\s+ago$', '', m.group(4).strip())
    mm = re.search(r'Memory:\s*([\d.]+[KMGT]?)', st)
    if mm: mc_mem = mm.group(1)
    fm = re.search(r'Mem:\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)', mem)
    ft = re.search(r'Mem:\s+(\S+)', mem)
    lines = [f"🟢 服务器{active} | 已运行 {uptime}"]
    if mc_mem: lines.append(f"MC 内存: {mc_mem}")
    if fm and ft: lines.append(f"系统: 可用 {fm.group(1)} / 总计 {ft.group(1)}")
    return "\n".join(lines)

def fmt_tps():
    if not is_server_up():
        return fmt_server_down()
    out = _rcon("/tick query")
    parts = []
    for pat, label in [(r'tick rate:\s*([\d.]+)', 'TPS'), (r'Average time per tick:\s*([\d.]+)ms', 'MSPT'),
                       (r'P50:\s*([\d.]+)ms', 'P50'), (r'P95:\s*([\d.]+)ms', 'P95'),
                       (r'P99:\s*([\d.]+)ms', 'P99')]:
        m = re.search(pat, out)
        if m: parts.append(f"{label}: {m.group(1)}{'ms' if label!='TPS' else ''}")
    return " | ".join(parts) if parts else "(无数据)"

def fmt_players():
    if not is_server_up():
        return fmt_server_down()
    out = _rcon("/list")
    if not out: return "暂无在线玩家"
    m = re.search(r'(\d+)\s*of\s*a\s*max\s*of\s*(\d+)', out)
    if m:
        players = out.split(":")[-1].strip() if ":" in out else ""
        return f"在线玩家 ({m.group(1)}/{m.group(2)}): {players or '无'}"
    return out[:200]

def fmt_memory():
    if not is_server_up():
        return fmt_server_down()
    st = run(["sudo", "systemctl", "status", _mc_cfg()["service_name"], "--no-pager"])
    mem = run(FREE_CMD)
    mm = re.search(r'Memory:\s*([\d.]+[KMGT]?).*?max:\s*([\d.]+[KMGT]?)', st)
    fm = re.search(r'Mem:\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)', mem)
    ft = re.search(r'Mem:\s+(\S+)', mem)
    lines = []
    if mm: lines.append(f"MC 内存: {mm.group(1)}/{mm.group(2)}")
    if fm and ft: lines.append(f"系统内存: 可用 {fm.group(1)} / 总计 {ft.group(1)}")
    return "\n".join(lines) if lines else "(无数据)"

def fmt_logs():
    out = run(["sudo", "journalctl", "-u", _mc_cfg()["service_name"], "--no-pager", "-n", "50"])
    errors = re.findall(r'(?i)(.{0,120}(?:error|warn|can\'?t\s+keep\s+up).{0,120})', out)
    if not errors:
        return "✅ 最近无错误或警告"
    lines = []
    for e in errors[:5]:
        clean = re.sub(r'^\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\[.*?\]\s*', '', e.strip())
        lines.append(f"⚠ {clean[:150]}")
    return f"最近 {len(errors)} 条警告:\n" + "\n".join(lines)

def fmt_backups():
    out = run(["ls", "-lh", f"{_mc_cfg()['server_dir']}/backups/"])
    if not out or "总计" not in out:
        return "暂无备份"
    files = [l for l in out.split("\n") if l.strip() and not l.startswith("总")]
    if not files:
        return "暂无备份"
    lines = [f"共 {len(files)} 份备份:"]
    for f in files[-5:]:
        parts = f.split()
        if len(parts) >= 5:
            lines.append(f"  {parts[-1]} ({parts[4]})")
    return "\n".join(lines)

def fmt_help():
    return (
        "**📋 MC 服务器监控助手**\n\n"
        "mc.chieko3020.xyz 实时状态查询\n\n"
        "🟢 **状态** — 运行状态、内存占用\n"
        "🟡 **性能** — TPS 与 tick 耗时\n"
        "🔵 **在线人数** — 当前玩家\n"
        "🟣 **内存** — MC 与系统内存\n"
        "📋 **日志** — 最近错误与警告\n"
        "💾 **备份** — 已备份存档\n"
        "🌸 **luna** — 露娜 AI 聊天\n"
        "   用法: `luna 你好`、`luna 今天天气真好`\n"
        "❓ **帮助** — 显示本消息\n\n"
        "> 调试指令: /status /tps /player /memory /log /backups\n"
        "> 管理员: /start /stop /restart /backup"
    )

def fmt_raw(cmd_list):
    return run(cmd_list)[:3000] or "(无输出)"

def fmt_admin(action):
    svc = _mc_cfg()["service_name"]
    if action == "start":
        out = run(["sudo", "systemctl", "start", svc])
        return "✅ 服务器已启动" if not out else f"⚠ {out[:200]}"
    elif action == "stop":
        out = run(["sudo", "systemctl", "stop", svc])
        return "🛑 服务器已关闭" if not out else f"⚠ {out[:200]}"
    elif action == "restart":
        out = run(["sudo", "systemctl", "restart", svc])
        return "🔄 服务器已重启" if not out else f"⚠ {out[:200]}"
    elif action == "backup":
        return _backup_world()
