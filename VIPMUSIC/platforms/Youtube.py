import asyncio
import hashlib
import logging
import os
import random
import re
import time
from functools import wraps
from typing import Dict, List, Optional, Tuple, Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from VIPMUSIC.utils.formatters import time_to_seconds

# ══════════════════════════════════════════════════════════════════
#  Logger
# ══════════════════════════════════════════════════════════════════
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ══════════════════════════════════════════════════════════════════
#  OAuth2 Token (ek baar login → hamesha ke liye)
#    pip install yt-dlp-youtube-oauth2
#    yt-dlp --username oauth2 --password "" <any-yt-url>
# ══════════════════════════════════════════════════════════════════
OAUTH2_TOKEN = os.path.expanduser("~/.cache/yt-dlp/youtube-oauth2.token")
COOKIES_FILE = os.path.expanduser("~/.cache/yt-dlp/cookies.txt")

# ══════════════════════════════════════════════════════════════════
#  Rotating User-Agents (Android + iOS + Desktop)
# ══════════════════════════════════════════════════════════════════
USER_AGENTS: List[str] = [
    # Android YouTube App
    "com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip",
    "com.google.android.youtube/18.11.34 (Linux; U; Android 13; SM-G991B) gzip",
    "com.google.android.youtube/17.31.35 (Linux; U; Android 11; Pixel 5) gzip",
    # iOS YouTube App
    "com.google.ios.youtube/17.33.2 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)",
    "com.google.ios.youtube/16.46.3 (iPhone13,2; U; CPU iOS 15_1 like Mac OS X)",
    # Desktop Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ══════════════════════════════════════════════════════════════════
#  In-Memory Cache  (TTL = 10 min default)
# ══════════════════════════════════════════════════════════════════
_CACHE: Dict[str, Tuple[float, object]] = {}
_CACHE_TTL = 600  # seconds


def _cache_key(*args) -> str:
    return hashlib.md5(str(args).encode()).hexdigest()


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    _CACHE.pop(key, None)
    return None


def _cache_set(key: str, value):
    _CACHE[key] = (time.time(), value)


def cached(func):
    """Async function ke results cache karo."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        key = _cache_key(func.__name__, args[1:], kwargs)
        hit = _cache_get(key)
        if hit is not None:
            logger.debug(f"[CACHE HIT] {func.__name__}")
            return hit
        result = await func(*args, **kwargs)
        _cache_set(key, result)
        return result
    return wrapper


# ══════════════════════════════════════════════════════════════════
#  Retry Decorator
# ══════════════════════════════════════════════════════════════════
def async_retry(max_attempts: int = 4, base_delay: float = 2.0, exceptions=(Exception,)):
    """Exponential backoff ke saath retry."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts:
                        break
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    logger.warning(
                        f"[RETRY {attempt}/{max_attempts}] {func.__name__} "
                        f"failed: {e}. Waiting {delay:.1f}s…"
                    )
                    await asyncio.sleep(delay)
            raise last_exc
        return wrapper
    return decorator


# ══════════════════════════════════════════════════════════════════
#  Shell Helper
# ══════════════════════════════════════════════════════════════════
async def shell_cmd(cmd: str) -> str:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if err:
        decoded = err.decode("utf-8", errors="replace")
        if "unavailable videos are hidden" in decoded.lower():
            return out.decode("utf-8", errors="replace")
        logger.debug(f"[shell_cmd stderr] {decoded}")
        return decoded
    return out.decode("utf-8", errors="replace")


# ══════════════════════════════════════════════════════════════════
#  yt-dlp Options Builder
# ══════════════════════════════════════════════════════════════════
def _ydl_opts(extra: Optional[dict] = None) -> dict:
    """
    Anti-ban optimized yt-dlp options.
    - Android/iOS/Web player clients rotate karte hain
    - Random User-Agent har baar
    - OAuth2 token agar available hai
    - Cookies agar available hain
    """
    ua = random.choice(USER_AGENTS)

    opts: dict = {
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
                "skip": ["hls", "dash"],          # cleaner streams
            }
        },
        "http_headers": {
            "User-Agent": ua,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        # Rate limiting (bot detection se bachne ke liye)
        "sleep_interval":           random.uniform(1, 3),
        "max_sleep_interval":       random.uniform(4, 8),
        "sleep_interval_requests":  1,
        # Retry config
        "retries":          8,
        "fragment_retries": 8,
        "retry_sleep_functions": {"http": lambda n: min(2 ** n, 60)},
        # Network
        "geo_bypass":           True,
        "nocheckcertificate":   True,
        # Output
        "quiet":        True,
        "no_warnings":  True,
        "ignoreerrors": False,
    }

    # OAuth2 token (strongest protection)
    if os.path.exists(OAUTH2_TOKEN):
        opts["username"] = "oauth2"
        opts["password"] = ""

    # Cookies fallback
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE

    if extra:
        opts.update(extra)
    return opts


# ══════════════════════════════════════════════════════════════════
#  URL Sanitizer
# ══════════════════════════════════════════════════════════════════
def _clean(link: str, videoid=None, base: str = "") -> str:
    if videoid and base:
        link = base + link
    return link.split("&")[0] if "&" in link else link


# ══════════════════════════════════════════════════════════════════
#  Main Class
# ══════════════════════════════════════════════════════════════════
class YouTubeAPI:
    def __init__(self):
        self.base     = "https://www.youtube.com/watch?v="
        self.regex    = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.reg      = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def _l(self, link: str, videoid=None) -> str:
        return _clean(link, videoid, self.base)

    # ── exists ────────────────────────────────────────────────────────────────

    async def exists(self, link: str, videoid: Union[bool, str] = None) -> bool:
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    # ── url ───────────────────────────────────────────────────────────────────

    async def url(self, message_1: Message) -> Optional[str]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for msg in messages:
            for entities, text_src in [
                (msg.entities,         msg.text or msg.caption),
                (msg.caption_entities, msg.caption),
            ]:
                if not entities:
                    continue
                for ent in entities:
                    if ent.type == MessageEntityType.URL and text_src:
                        return text_src[ent.offset: ent.offset + ent.length]
                    if ent.type == MessageEntityType.TEXT_LINK:
                        return ent.url
        return None

    # ── Search Helper ─────────────────────────────────────────────────────────

    @async_retry(max_attempts=3, base_delay=1.5)
    async def _search(self, query: str, limit: int = 10) -> List[dict]:
        results = await (VideosSearch(query, limit=limit)).next()
        return results.get("result", [])

    # ── details ───────────────────────────────────────────────────────────────

    @cached
    @async_retry(max_attempts=3, base_delay=1.5)
    async def details(self, link: str, videoid: Union[bool, str] = None):
        link = self._l(link, videoid)
        results = await self._search(link, limit=1)
        if not results:
            raise ValueError(f"No results found for: {link}")
        r = results[0]
        dur_min = r.get("duration") or "0:00"
        dur_sec = int(time_to_seconds(dur_min)) if dur_min else 0
        thumb   = (r.get("thumbnails") or [{}])[0].get("url", "").split("?")[0]
        return r["title"], dur_min, dur_sec, thumb, r["id"]

    @cached
    async def title(self, link: str, videoid: Union[bool, str] = None) -> str:
        t, *_ = await self.details(link, videoid)
        return t

    @cached
    async def duration(self, link: str, videoid: Union[bool, str] = None) -> str:
        _, d, *_ = await self.details(link, videoid)
        return d

    @cached
    async def thumbnail(self, link: str, videoid: Union[bool, str] = None) -> str:
        _, _, _, thumb, _ = await self.details(link, videoid)
        return thumb

    # ── video (streaming URL) ─────────────────────────────────────────────────

    @async_retry(max_attempts=4, base_delay=2.0)
    async def video(self, link: str, videoid: Union[bool, str] = None):
        link = self._l(link, videoid)
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "-g",
            "-f", "best[height<=?720][width<=?1280]",
            "--extractor-args", "youtube:player_client=android,ios,web",
            "--no-warnings",
            "--geo-bypass",
            link,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            url = stdout.decode(errors="replace").strip().split("\n")[0]
            if url:
                return 1, url
        err_msg = stderr.decode(errors="replace").strip()
        logger.error(f"[video] yt-dlp failed: {err_msg}")
        return 0, err_msg

    # ── playlist ──────────────────────────────────────────────────────────────

    @async_retry(max_attempts=3, base_delay=2.0)
    async def playlist(
        self,
        link: str,
        limit: int,
        user_id,
        videoid: Union[bool, str] = None,
    ) -> List[str]:
        if videoid:
            link = self.listbase + link
        link = link.split("&")[0] if "&" in link else link
        raw = await shell_cmd(
            f'yt-dlp -i --get-id --flat-playlist --playlist-end {limit} '
            f'--extractor-args "youtube:player_client=android,ios,web" '
            f'--geo-bypass --no-warnings '
            f'--skip-download "{link}"'
        )
        ids = [v.strip() for v in raw.split("\n") if v.strip() and not v.startswith("[")]
        if not ids:
            raise ValueError(f"Playlist empty or blocked: {link}")
        return ids

    # ── track ─────────────────────────────────────────────────────────────────

    @cached
    @async_retry(max_attempts=3, base_delay=1.5)
    async def track(self, link: str, videoid: Union[bool, str] = None):
        link = self._l(link, videoid)
        results = await self._search(link, limit=1)
        if not results:
            raise ValueError(f"No track found for: {link}")
        r = results[0]
        thumb = (r.get("thumbnails") or [{}])[0].get("url", "").split("?")[0]
        return {
            "title":        r["title"],
            "link":         r["link"],
            "vidid":        r["id"],
            "duration_min": r.get("duration", "0:00"),
            "thumb":        thumb,
        }, r["id"]

    # ── formats ───────────────────────────────────────────────────────────────

    @async_retry(max_attempts=3, base_delay=2.0)
    async def formats(self, link: str, videoid: Union[bool, str] = None):
        link = self._l(link, videoid)
        loop = asyncio.get_running_loop()

        def _fetch():
            out = []
            with yt_dlp.YoutubeDL(_ydl_opts()) as ydl:
                info = ydl.extract_info(link, download=False)
                for fmt in info.get("formats", []):
                    fmt_str = str(fmt.get("format", ""))
                    if not fmt_str or "dash" in fmt_str.lower():
                        continue
                    if not all(k in fmt for k in ("filesize", "format_id", "ext", "format_note")):
                        continue
                    out.append({
                        "format":      fmt_str,
                        "filesize":    fmt["filesize"],
                        "format_id":   fmt["format_id"],
                        "ext":         fmt["ext"],
                        "format_note": fmt["format_note"],
                        "yturl":       link,
                    })
            return out

        result = await loop.run_in_executor(None, _fetch)
        return result, link

    # ── slider ────────────────────────────────────────────────────────────────

    @async_retry(max_attempts=3, base_delay=1.5)
    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        link = self._l(link, videoid)
        results = await self._search(link, limit=max(10, query_type + 1))
        if query_type >= len(results):
            raise IndexError(f"Slider index {query_type} out of range (got {len(results)} results)")
        item  = results[query_type]
        thumb = (item.get("thumbnails") or [{}])[0].get("url", "").split("?")[0]
        return item["title"], item.get("duration", "0:00"), thumb, item["id"]

    # ── _resolve_link ─────────────────────────────────────────────────────────

    @async_retry(max_attempts=3, base_delay=1.5)
    async def _resolve_link(self, link: str) -> str:
        """
        Song/video naam → YouTube URL.
        Agar pehle se YouTube URL hai toh unchanged return karo.
        """
        if re.search(self.regex, link):
            return link.split("&")[0] if "&" in link else link

        results = await self._search(link, limit=1)
        if not results:
            raise ValueError(f"YouTube pe '{link}' ka koi result nahi mila.")
        return self.base + results[0]["id"]

    # ── _get_stream_url (blocking — executor mein chalao) ─────────────────────

    def _get_stream_url(self, link: str, fmt_selector: str) -> str:
        """
        yt-dlp se direct stream URL nikalo.
        Koi file disk pe save nahi hoti (simulate=True).
        """
        with yt_dlp.YoutubeDL(_ydl_opts({
            "format":       fmt_selector,
            "simulate":     True,
            "forceurl":     True,
            "quiet":        True,
            "no_warnings":  True,
        })) as ydl:
            info = ydl.extract_info(link, download=False)
            if "requested_formats" in info:
                return info["requested_formats"][0]["url"]
            url = info.get("url") or info.get("manifest_url")
            if not url:
                raise ValueError("yt-dlp returned no stream URL.")
            return url

    # ── download ──────────────────────────────────────────────────────────────

    @async_retry(max_attempts=4, base_delay=2.0, exceptions=(ValueError, Exception))
    async def download(
        self,
        link:      str,
        mystic,
        video:     Union[bool, str] = None,
        videoid:   Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title:     Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        else:
            link = await self._resolve_link(link)

        loop = asyncio.get_running_loop()

        # ── 1. Song Video (format_id se) ──────────────────────────────────────
        if songvideo:
            fmt = f"{format_id}+140" if format_id else "bestvideo[height<=?720]+bestaudio/best"
            url = await loop.run_in_executor(None, self._get_stream_url, link, fmt)
            return url, None

        # ── 2. Song Audio (format_id se) ──────────────────────────────────────
        if songaudio:
            fmt = format_id if format_id else "bestaudio[ext=m4a]/bestaudio/best"
            url = await loop.run_in_executor(None, self._get_stream_url, link, fmt)
            return url, None

        # ── 3. Video Stream ───────────────────────────────────────────────────
        if video:
            status, result = await self.video(link)
            if status == 1:
                return result, None
            raise ValueError(f"Video stream URL fetch failed: {result}")

        # ── 4. Audio Stream (default) ─────────────────────────────────────────
        fmt = "bestaudio[ext=m4a]/bestaudio/best"
        url = await loop.run_in_executor(None, self._get_stream_url, link, fmt)
        return url, None

    # ── Cache Management ──────────────────────────────────────────────────────

    def clear_cache(self):
        """Saara cache manually clear karo."""
        _CACHE.clear()
        logger.info("[CACHE] Cleared all entries.")

    def cache_stats(self) -> dict:
        """Cache ka stats dekho."""
        now = time.time()
        active = sum(1 for ts, _ in _CACHE.values() if (now - ts) < _CACHE_TTL)
        return {"total_entries": len(_CACHE), "active_entries": active, "ttl_seconds": _CACHE_TTL}
