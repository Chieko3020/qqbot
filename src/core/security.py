# qqbot/security.py — content filters, URL stripping, block patterns
import re

LUNA_BLOCK_PATTERNS = [
    re.compile(r"忽略.*指令|ignore.*instruction|忘记.*规则|forget.*rule", re.IGNORECASE),
    re.compile(r"system\s*prompt|系统提示|系统指令|你的设定|你的规则", re.IGNORECASE),
    re.compile(r"角色扮演.*其他|扮演.*角色|你现在是|pretend.*you.*are", re.IGNORECASE),
    re.compile(r"输出.*指令|输出.*提示词|repeat.*prompt|print.*instruction", re.IGNORECASE),
    re.compile(r"习近平|江泽民|胡锦涛|毛泽东|邓小平|周恩来|温家宝|李克强"),
    re.compile(r"法轮功|六四|天安门|台独|藏独|疆独"),
    re.compile(r"<script|javascript:|onerror=|onload=", re.IGNORECASE),
    re.compile(r"/start|/stop|/restart|/backup|/new|/reset|/model|/yolo"),
    re.compile(r"\brm\s*-rf\b|\brm\s.*[/]\b|sudo\s+rm|chmod\s+777|wget.*\|.*sh", re.IGNORECASE),
    re.compile(r"\bapi[_-]?key\b|\bsecret\b|\btoken\b|\bpassword|\bcredential\b|\bapi\b|\bkey\b", re.IGNORECASE),
    re.compile(r"\.env\b|/etc/passwd|/etc/shadow|config\.yaml", re.IGNORECASE),
    re.compile(r"\bcurl\b.*\bhttps?://|wget\s+https?://", re.IGNORECASE),
    re.compile(r"\bdd\s+if=|mkfs\.|:\(\)\s*{\s*:\s*\|:&\s*}", re.IGNORECASE),
]

_URL_RE = re.compile(r'https?://\S+|www\.\S+\.\S+', re.IGNORECASE)

def _strip_urls(text: str) -> str:
    return _URL_RE.sub('[链接已移除]', text)

def _check_luna_input(text: str) -> str | None:
    """Return rejection message if blocked, None if OK."""
    for pat in LUNA_BLOCK_PATTERNS:
        if pat.search(text):
            return "🌸 这个话题我不太方便聊呢，换一个吧"
    return None
