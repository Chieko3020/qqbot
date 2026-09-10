#!/usr/bin/env python3
# qqbot/main.py — entry point: HTTP handler + alert monitor
import json, os, re, sys, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from cryptography.hazmat.primitives.asymmetric import ed25519

from .core.config import (
    APP_ID, APP_SECRET, LISTEN_HOST, LISTEN_PORT, _log, _check_rate_limit,
    _seen_msg_ids, _user_msg_times, _alert_openid, _alert_active,
    ALERT_CHECK_SEC, MSG_RATE_LIMIT, MSG_RATE_WINDOW, REJECT_MSG, load_config,
)
from .core.qq_client import get_token, send_qq, send_markdown
from .mc.server import fmt_status, run
from .core.handlers import HANDLERS, PREFIX_HANDLERS

# ── ed25519 ──────────────────────────────────────────────────
def _ed25519_sign(secret, event_ts, plain_token):
    seed = secret
    while len(seed) < 32:
        seed = seed * 2
    seed = seed[:32].encode()
    pk = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
    return pk.sign(f"{event_ts}{plain_token}".encode()).hex()

# ── Keyboard ────────────────────────────────────────────────
HELP_BUTTONS = [
    [{"id": "btn_status", "label": "🟢 状态", "data": "状态"},
     {"id": "btn_tps", "label": "🟡 性能", "data": "性能"},
     {"id": "btn_players", "label": "🔵 在线人数", "data": "在线人数"}],
    [{"id": "btn_memory", "label": "🟣 内存", "data": "内存"},
     {"id": "btn_logs", "label": "📋 日志", "data": "日志"},
     {"id": "btn_backup", "label": "💾 备份", "data": "备份"}],
    [{"id": "btn_luna", "label": "🌸 luna (聊天)", "data": "luna"},
     {"id": "btn_help", "label": "❓ 帮助", "data": "帮助"}],
]

def _build_keyboard(buttons_data: list) -> dict:
    rows = []
    for row_btns in buttons_data:
        buttons = []
        for b in row_btns:
            buttons.append({
                "id": b["id"],
                "render_data": {"label": b["label"], "visited_label": b["label"], "style": 0},
                "action": {"type": 2, "data": b["data"], "reply": True, "enter": True},
            })
        rows.append({"buttons": buttons})
    return {"content": {"rows": rows}}


# ── HTTP Handler ────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        op = body.get("op", 0)
        d = body.get("d", {})

        if op == 13:
            sig = _ed25519_sign(APP_SECRET, d.get("event_ts", ""), d.get("plain_token", ""))
            self._json(200, {"plain_token": d["plain_token"], "signature": sig})
            return

        event_type = body.get("t", "")
        if event_type in ("C2C_MESSAGE_CREATE", "GROUP_AT_MESSAGE_CREATE"):
            pass
        elif event_type == "INTERACTION_CREATE":
            self._handle_interaction(body)
            return
        else:
            self._json(200, {}); return

        msg = d.get("content", "").strip()
        msg = re.sub(r'<@!\d+>\s*', '', msg).strip()
        msg_id = d.get("id", "")
        openid = d.get("author", {}).get("user_openid", "")

        if not openid or not msg:
            self._json(200, {}); return

        global _alert_openid
        if openid:
            _alert_openid = openid

        if msg_id in _seen_msg_ids:
            _log("DEBUG", f"dedup skip msg_id={msg_id[:20]}...")
            self._json(200, {}); return
        _seen_msg_ids.add(msg_id)
        if len(_seen_msg_ids) > 1000:
            _seen_msg_ids.clear()

        blocked, _ = _check_rate_limit(_user_msg_times, openid, MSG_RATE_LIMIT, MSG_RATE_WINDOW)
        if blocked:
            _log("WARN", f"rate-limit openid={openid[:10]}...")
            send_qq(openid, "⚠ 发送太频繁了，请稍后再试")
            self._json(200, {}); return

        _log("INFO", f"msg openid={openid[:10]}... cmd={msg[:30]!r}")
        cfg = load_config()

        handler = HANDLERS.get(msg)
        if handler:
            reply = handler() if cfg.get(msg, True) else "⚠ 该指令已关闭"
        else:
            matched = False
            for prefix, fn in PREFIX_HANDLERS.items():
                if msg == prefix:
                    reply = fn("", openid, msg_id) if cfg.get(prefix, True) else "⚠ 该指令已关闭"
                    matched = True; break
                elif msg.startswith(prefix + " "):
                    arg = msg[len(prefix) + 1:].strip()
                    reply = fn(arg, openid, msg_id) if cfg.get(prefix, True) else "⚠ 该指令已关闭"
                    matched = True; break
            if not matched:
                reply = REJECT_MSG

        if reply is not None:
            if msg in ("帮助", "/help"):
                send_markdown(openid, reply, msg_id, keyboard=_build_keyboard(HELP_BUTTONS))
            else:
                send_qq(openid, reply, msg_id)
        self._json(200, {})

    def _handle_interaction(self, body):
        try:
            d = body.get("d", {})
            interaction_id = d.get("id", "")
            btn_data = d.get("data", {}).get("resolved", {}).get("button_data", "")
            openid = d.get("user_openid", d.get("group_openid", ""))
            if not interaction_id or not btn_data:
                self._json(200, {}); return
            _log("INFO", f"interaction btn={btn_data} openid={openid[:10]}...")
            handler = HANDLERS.get(btn_data)
            if handler:
                reply = handler()
            else:
                for prefix, fn in PREFIX_HANDLERS.items():
                    if btn_data == prefix:
                        reply = fn("", openid, ""); break
                else:
                    reply = REJECT_MSG
            token = get_token()
            ack_url = f"https://api.sgroup.qq.com/interactions/{interaction_id}"
            ack_body = json.dumps({"code": 0, "content": reply}).encode()
            req = Request(ack_url, data=ack_body,
                          headers={"Content-Type": "application/json", "Authorization": f"QQBot {token}"})
            urlopen(req, timeout=5)
            _log("INFO", f"interaction ack: {btn_data}")
        except Exception as e:
            _log("ERROR", f"interaction error: {e}")
            self._json(200, {})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, *a): pass


# ── Alert monitor ────────────────────────────────────────────
def _alert_monitor():
    _log("INFO", "Alert monitor started")
    while True:
        time.sleep(ALERT_CHECK_SEC)
        if not _alert_openid:
            continue
        try:
            st = run(["sudo", "systemctl", "status", "mcserver", "--no-pager"])
            # 仅当服务 active 时才检查内存（避免 cgroup 残留导致幽灵告警）
            is_active = "Active: active" in st
            mc_mem_val = 0
            if is_active:
                mc_mem_m = re.search(r"Memory:\s*(\d+\.?\d*)([KMG])", st)
                if mc_mem_m:
                    val = float(mc_mem_m.group(1))
                    unit = mc_mem_m.group(2)
                    if unit == "G": mc_mem_val = val * 1024
                    elif unit == "M": mc_mem_val = val
                    elif unit == "K": mc_mem_val = val / 1024
            mem_out = run(["bash", "-c", "LC_ALL=C free -m | grep Mem:"])
            sys_avail = 0
            mem_m = re.search(r"Mem:\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)", mem_out)
            if mem_m: sys_avail = float(mem_m.group(1))
            if mc_mem_val > 600 and not _alert_active.get("mc_mem"):
                send_qq(_alert_openid, f"⚠ MC 内存告警: {mc_mem_val:.0f}M / 900M")
                _alert_active["mc_mem"] = True
            elif mc_mem_val <= 600:
                _alert_active["mc_mem"] = False
            if sys_avail < 200 and sys_avail > 0 and not _alert_active.get("sys_mem"):
                send_qq(_alert_openid, f"🔴 系统内存不足: 可用 {sys_avail:.0f}M / 总计 1.9G")
                _alert_active["sys_mem"] = True
            elif sys_avail >= 200:
                _alert_active["sys_mem"] = False
        except Exception as e:
            _log("ERROR", f"Alert check error: {e}")


# ── Entry point ──────────────────────────────────────────────
def main():
    if not APP_ID or not APP_SECRET:
        _log("ERROR", "缺少环境变量 QQ_APP_ID / QQ_APP_SECRET，拒绝启动（凭据只通过环境变量注入，禁止硬编码）")
        sys.exit(1)
    port = int(os.environ.get("PORT", LISTEN_PORT))
    _log("INFO", f"Starting filter-proxy on {LISTEN_HOST}:{port}")
    threading.Thread(target=_alert_monitor, daemon=True).start()
    HTTPServer((LISTEN_HOST, port), Handler).serve_forever()

if __name__ == "__main__":
    main()
