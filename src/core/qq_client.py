# qqbot/qq_client.py — QQ Bot API client (token, send, upload)
import json, time
from urllib.request import Request, urlopen
from .config import APP_ID, APP_SECRET, ACCESS_TOKEN_URL, SEND_MSG_URL, UPLOAD_URL, _log

_token = {"v": None, "exp": 0}

def get_token():
    now = time.time()
    if _token["v"] and now < _token["exp"]:
        return _token["v"]
    body = json.dumps({"appId": APP_ID, "clientSecret": APP_SECRET}).encode()
    req = Request(ACCESS_TOKEN_URL, data=body, headers={"Content-Type": "application/json"})
    resp = json.loads(urlopen(req, timeout=10).read())
    _token["v"] = resp["access_token"]
    _token["exp"] = now + int(resp.get("expires_in", 7200)) - 60
    return _token["v"]

def send_qq(openid, content, msg_id=None):
    body = {"content": content, "msg_type": 0}
    if msg_id:
        body["msg_id"] = msg_id
    req = Request(SEND_MSG_URL.format(openid=openid),
                  data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json", "Authorization": f"QQBot {get_token()}"})
    try:
        urlopen(req, timeout=10)
    except Exception as e:
        _log("ERROR", f"send_qq fail: {e}")

def send_markdown(openid, content, msg_id=None, keyboard=None):
    body = {"markdown": {"content": content}, "msg_type": 2}
    if msg_id:
        body["msg_id"] = msg_id
    if keyboard:
        body["keyboard"] = keyboard
    req = Request(SEND_MSG_URL.format(openid=openid),
                  data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json", "Authorization": f"QQBot {get_token()}"})
    try:
        urlopen(req, timeout=10)
    except Exception as e:
        _log("ERROR", f"send_md fail: {e}")

def upload_and_send_voice(openid, audio_url, msg_id=None):
    """Upload remote audio URL to QQ as voice, then send."""
    token = get_token()
    body = {"file_type": 3, "url": audio_url}
    req = Request(UPLOAD_URL.format(openid=openid),
                  data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json", "Authorization": f"QQBot {token}"})
    try:
        resp = json.loads(urlopen(req, timeout=30).read())
        file_info = resp.get("file_info", "")
    except Exception as e:
        _log("ERROR", f"upload fail: {e}")
        return False

    if not file_info:
        _log("WARN", "upload no file_info")
        return False

    body2 = {"media": {"file_info": file_info}, "msg_type": 7}
    req2 = Request(SEND_MSG_URL.format(openid=openid),
                   data=json.dumps(body2).encode(),
                   headers={"Content-Type": "application/json", "Authorization": f"QQBot {token}"})
    try:
        urlopen(req2, timeout=10)
        return True
    except Exception as e:
        _log("ERROR", f"send_media fail: {e}")
        return False
