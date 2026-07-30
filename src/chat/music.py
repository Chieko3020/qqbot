# qqbot/music.py — Music search and playback via Enhanced API
import json, os, re, random as _random
from urllib.request import Request, urlopen
from urllib.parse import quote as url_quote
from ..core.config import _log
from ..core.qq_client import send_qq, send_markdown, upload_and_send_voice

MUSIC_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".music_cache.json")
MUSIC_BACKUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_cache_backup.json")
MUSIC_COOKIE_FILE = "/home/ubuntu/music-api/.cookie"

def _load_cookie() -> str:
    try:
        with open(MUSIC_COOKIE_FILE) as f:
            return f.read().strip()
    except:
        return ""

def _load_music():
    for path in [MUSIC_CACHE_FILE, MUSIC_BACKUP_FILE]:
        try:
            with open(path) as f:
                songs = json.load(f)
                if isinstance(songs, list) and len(songs) > 0:
                    return songs
        except:
            pass
    return []

def _resolve_music_url(song_id) -> str:
    try:
        url = f"http://127.0.0.1:3000/song/url/v1?id={song_id}&level=exhigh&cookie=MUSIC_U={_load_cookie()}"
        resp = json.loads(urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=8).read())
        data = resp.get("data", [])
        if data and data[0].get("url"):
            return data[0]["url"]
    except:
        pass
    return ""

def _fetch_lyrics(lrc_url: str) -> str:
    try:
        raw = urlopen(Request(lrc_url), timeout=5).read().decode("utf-8", errors="replace")
    except:
        return ""
    lines = []
    for line in raw.splitlines():
        text = re.sub(r"\[\d{1,2}:\d{1,2}[\.:]\d{1,3}\]", "", line).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)

def _search_music(keyword: str) -> list:
    try:
        q = url_quote(keyword, safe="")
        url = f"http://127.0.0.1:3000/search?keywords={q}&limit=5"
        resp = json.loads(urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=10).read())
        songs = []
        result = resp.get("result", resp)
        for item in result.get("songs", [])[:5]:
            sid = item.get("id")
            if not sid:
                continue
            artist_list = item.get("ar", item.get("artists", []))
            if isinstance(artist_list, list) and artist_list and isinstance(artist_list[0], dict):
                artist = ", ".join(a.get("name", "") for a in artist_list if a.get("name"))
            else:
                artist = str(artist_list[0]) if artist_list else ""
            songs.append({
                "name": item.get("name", "未知"),
                "artist": artist,
                "id": sid,
                "url": f"https://music.chieko3020.xyz/?type=url&id={sid}",
                "lrc": f"https://music.chieko3020.xyz/?type=lrc&id={sid}",
                "cover": f"https://music.chieko3020.xyz/?type=pic&id={sid}",
            })
        return songs
    except:
        pass
    return []

def _song_display(song: dict) -> str:
    name = song.get("name", "未知歌曲")
    artist = song.get("artist", "")
    if artist and artist != "Chieko3020":
        return f"{name} — {artist}"
    return name

def fmt_music(user_msg: str = "", openid: str = "", msg_id: str = "") -> str | None:
    if user_msg.strip():
        query = user_msg.strip()
        results = _search_music(query)
        if not results:
            return f"🎵 未找到「{query}」的相关歌曲"
        preview = "\n".join(
            f"{i+1}. **{s['name']}** — *{s['artist']}*" if s.get('artist') else f"{i+1}. **{s['name']}**"
            for i, s in enumerate(results[:3])
        )
        send_markdown(openid, f"🔍 **搜索「{query}」**\n{preview}")
        song = results[0]
        audio_url = song.get("url", "")
        if audio_url and openid:
            if upload_and_send_voice(openid, audio_url, msg_id):
                _log("INFO", f"music search ok: {_song_display(song)}")
                send_qq(openid, f"🎵 {_song_display(song)}")
                lrc_text = _fetch_lyrics(song.get("lrc", ""))
                if lrc_text:
                    send_qq(openid, lrc_text)
                cached = _load_music()
                if song.get("url") not in {s.get("url") for s in cached}:
                    cached.append(song)
                    with open(MUSIC_CACHE_FILE, "w") as f:
                        json.dump(cached, f, ensure_ascii=False)
                return None
        _log("WARN", f"music search fail: {_song_display(song)}")
        return f"🎵 抱歉，「{query}」暂时无法播放，请稍后再试"

    songs = _load_music()
    if not songs:
        return "🎵 音乐列表暂时无法加载，请稍后再试"
    song = _random.choice(songs)
    audio_url = song.get("url", "")
    if "type=url" in audio_url:
        m_id = re.search(r"id=(\d+)", audio_url)
        if m_id:
            resolved = _resolve_music_url(m_id.group(1)).replace("http://", "https://", 1)
            if resolved:
                audio_url = resolved
    if audio_url:
        if openid and upload_and_send_voice(openid, audio_url, msg_id):
            _log("INFO", f"music ok: {_song_display(song)}")
            send_qq(openid, f"🎵 {_song_display(song)}")
            lrc_text = _fetch_lyrics(song.get("lrc", ""))
            if lrc_text:
                send_qq(openid, lrc_text)
            return None
    _log("WARN", f"music fail: {_song_display(song)}")
    return "🎵 抱歉，暂时无法播放，请稍后再试"
