import asyncio
import os
import re
import random
import logging
import aiohttp
import yt_dlp
from typing import Union, Optional, Tuple, List, Dict, Any
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from VIPMUSIC.utils.formatters import time_to_seconds
from VIPMUSIC import LOGGER

# ── CONFIG ────────────────────────────────────────────────────
from config import API_ID, BOT_TOKEN, MONGO_DB_URI, YOUTUBE_IMG_URL

# ── SECURITY FILTER ───────────────────────────────────────────
class SensitiveDataFilter(logging.Filter):
    _PATTERNS = [
        r"\d{8,10}:[a-zA-Z0-9_-]{35,}",
        r"mongodb\+srv://\S+",
        r"ya29\.[a-zA-Z0-9_-]+",
        r"AIza[a-zA-Z0-9_-]{35}",
    ]
    def filter(self, record):
        msg = str(record.msg)
        for pat in self._PATTERNS:
            msg = re.sub(pat, "[PROTECTED]", msg)
        record.msg = msg
        return True

logging.getLogger().addFilter(SensitiveDataFilter())

# ── CONSTANTS ─────────────────────────────────────────────────
API_URL      = "http://kiru-bot.up.railway.app"
COOKIES_PATH = os.path.join(os.path.dirname(__file__), "cookies.txt")

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

# ── UTILS ─────────────────────────────────────────────────────

def get_clean_id(link: str) -> Optional[str]:
    """
    YouTube video ID nikaalein.
    Support: watch?v=, youtu.be/, /shorts/, /live/, /embed/
    """
    m = re.search(
        r"(?:v=|youtu\.be/|/embed/|/shorts/|/live/)([a-zA-Z0-9_-]{11})",
        link,
    )
    if m:
        return m.group(1)
    clean = re.sub(r"[^a-zA-Z0-9_-]", "", link)
    return clean if len(clean) == 11 else None


def _random_ua() -> str:
    return random.choice(_USER_AGENTS)


def _yt_headers() -> Dict[str, str]:
    """Real browser jaisi headers — bot detection bypass."""
    return {
        "User-Agent"                : _random_ua(),
        "Accept"                    : "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language"           : "en-US,en;q=0.9",
        "Accept-Encoding"           : "gzip, deflate, br",
        "DNT"                       : "1",
        "Connection"                : "keep-alive",
        "Upgrade-Insecure-Requests" : "1",
        "Sec-Fetch-Dest"            : "document",
        "Sec-Fetch-Mode"            : "navigate",
        "Sec-Fetch-Site"            : "none",
        "Sec-Ch-Ua"                 : '"Chromium";v="124","Google Chrome";v="124","Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile"          : "?0",
        "Sec-Ch-Ua-Platform"        : '"Windows"',
        "Origin"                    : "https://www.youtube.com",
        "Referer"                   : "https://www.youtube.com/",
    }


def _cookies_opt() -> Dict[str, str]:
    """cookies.txt file mile toh use karo — logged-in session."""
    if os.path.isfile(COOKIES_PATH):
        LOGGER.info("[Cookies] cookies.txt mila — use ho raha hai.")
        return {"cookiefile": COOKIES_PATH}
    return {}


def extract_url_from_info(info: dict, prefer_video: bool = False) -> Optional[str]:
    """
    yt-dlp info dict se sabse best stream URL nikaalein.
    Audio: opus > m4a > best (bitrate descending)
    Video: mp4, height descending
    """
    if not info:
        return None
    try:
        if info.get("url"):
            return info["url"]

        for fmt in info.get("requested_formats", []):
            if prefer_video and fmt.get("vcodec") not in (None, "none") and fmt.get("url"):
                return fmt["url"]
            if not prefer_video and fmt.get("acodec") not in (None, "none") and fmt.get("url"):
                return fmt["url"]

        formats = info.get("formats", [])
        if not formats:
            return None

        if not prefer_video:
            audio = [
                f for f in formats
                if f.get("acodec") not in (None, "none")
                and f.get("vcodec") in (None, "none")
                and f.get("url")
            ]
            if audio:
                audio.sort(
                    key=lambda f: (
                        f.get("abr") or f.get("tbr") or 0,
                        1 if f.get("ext") in ("opus", "m4a") else 0,
                    ),
                    reverse=True,
                )
                return audio[0]["url"]
        else:
            video = [
                f for f in formats
                if f.get("vcodec") not in (None, "none") and f.get("url")
            ]
            if video:
                video.sort(
                    key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
                    reverse=True,
                )
                return video[0]["url"]

        return formats[-1].get("url")

    except Exception as e:
        LOGGER.error(f"[extract_url] Error: {e}")
    return None


# ── YT-DLP BASE ───────────────────────────────────────────────

def _base_opts(fmt: str, extractor_args: Optional[Dict] = None) -> Dict[str, Any]:
    """Sabhi strategies ka common yt-dlp config."""
    opts: Dict[str, Any] = {
        "format"             : fmt,
        "quiet"              : True,
        "no_warnings"        : True,
        "geo_bypass"         : True,
        "nocheckcertificate" : True,
        "noplaylist"         : True,
        "socket_timeout"     : 15,
        "retries"            : 3,
        "fragment_retries"   : 3,
        "skip_download"      : True,
        "headers"            : _yt_headers(),
        **_cookies_opt(),
    }
    if extractor_args:
        opts["extractor_args"] = extractor_args
    return opts


async def _ydl_extract(link: str, opts: Dict) -> Optional[Dict]:
    """Thread-safe yt-dlp extract — blocking call async mein."""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return await asyncio.to_thread(ydl.extract_info, link, download=False)
    except yt_dlp.utils.DownloadError as e:
        LOGGER.debug(f"[ydl] DownloadError: {e}")
    except Exception as e:
        LOGGER.debug(f"[ydl] {type(e).__name__}: {e}")
    return None


# ── 8 BYPASS STRATEGIES ───────────────────────────────────────

async def _s_web(link: str, fmt: str) -> Optional[str]:
    """1. Standard web client + cookies.txt"""
    info = await _ydl_extract(link, _base_opts(fmt))
    return extract_url_from_info(info, prefer_video="video" in fmt)


async def _s_android(link: str, fmt: str) -> Optional[str]:
    """2. Android YouTube app spoof — 2026 mein sabse reliable."""
    info = await _ydl_extract(link, _base_opts(fmt, {"youtube": {"player_client": ["android"]}}))
    return extract_url_from_info(info, prefer_video="video" in fmt)


async def _s_android_music(link: str, fmt: str) -> Optional[str]:
    """3. Android Music client — audio ke liye zyada permissive."""
    info = await _ydl_extract(link, _base_opts(fmt, {"youtube": {"player_client": ["android_music"]}}))
    return extract_url_from_info(info, prefer_video=False)


async def _s_ios(link: str, fmt: str) -> Optional[str]:
    """4. iOS YouTube app spoof."""
    info = await _ydl_extract(link, _base_opts(fmt, {"youtube": {"player_client": ["ios"]}}))
    return extract_url_from_info(info, prefer_video="video" in fmt)


async def _s_tv_embedded(link: str, fmt: str) -> Optional[str]:
    """5. TV Embedded — age-restricted videos bhi bypass hote hain."""
    info = await _ydl_extract(link, _base_opts(fmt, {"youtube": {"player_client": ["tv_embedded"]}}))
    return extract_url_from_info(info, prefer_video="video" in fmt)


async def _s_web_embedded(link: str, fmt: str) -> Optional[str]:
    """6. Web Embedded — iframe jaisi request."""
    info = await _ydl_extract(link, _base_opts(fmt, {"youtube": {"player_client": ["web_embedded"]}}))
    return extract_url_from_info(info, prefer_video="video" in fmt)


async def _s_mweb(link: str, fmt: str) -> Optional[str]:
    """7. Mobile Web — alag fingerprint, detection kam."""
    info = await _ydl_extract(link, _base_opts(fmt, {"youtube": {"player_client": ["mweb"]}}))
    return extract_url_from_info(info, prefer_video="video" in fmt)


async def _s_direct_api(link: str, m_type: str) -> Optional[str]:
    """8. kiru-bot API — last resort."""
    video_id = get_clean_id(link)
    if not video_id:
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(
            headers={"User-Agent": _random_ua()}, timeout=timeout
        ) as session:
            async with session.get(
                f"{API_URL}/download",
                params={"url": video_id, "type": m_type},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    token = data.get("download_token")
                    if token:
                        return f"{API_URL}/stream/{video_id}?type={m_type}&token={token}"
    except Exception:
        pass
    return None


# ── WATERFALL ORCHESTRATOR ────────────────────────────────────

async def _waterfall(link: str, prefer_video: bool) -> Tuple[Optional[str], bool]:
    """
    8 strategies ko order mein try karo.
    Pehli jo URL de — wahi return ho.
    """
    m_type = "video" if prefer_video else "audio"
    a_fmt  = "bestaudio[ext=m4a]/bestaudio[ext=opus]/bestaudio/best"
    v_fmt  = "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
    fmt    = v_fmt if prefer_video else a_fmt

    strategies = [
        ("Web + Cookies",  lambda: _s_web(link, fmt)),
        ("Android",        lambda: _s_android(link, fmt)),
        ("Android Music",  lambda: _s_android_music(link, a_fmt)),
        ("iOS",            lambda: _s_ios(link, fmt)),
        ("TV Embedded",    lambda: _s_tv_embedded(link, fmt)),
        ("Web Embedded",   lambda: _s_web_embedded(link, fmt)),
        ("Mobile Web",     lambda: _s_mweb(link, fmt)),
        ("Direct API",     lambda: _s_direct_api(link, m_type)),
    ]

    for name, fn in strategies:
        try:
            LOGGER.info(f"[Bypass] Trying → {name}")
            result = await fn()
            if result and len(result) > 15:
                LOGGER.info(f"[Bypass] ✅ Kaam aaya → {name}")
                return result, True
        except Exception as e:
            LOGGER.warning(f"[Bypass] ❌ {name} fail: {type(e).__name__}: {e}")

    LOGGER.error(f"[Bypass] 🚫 Sabhi 8 strategies fail: {link}")
    return None, False


# ── YouTubeAPI CLASS ──────────────────────────────────────────

class YouTubeAPI:
    def __init__(self):
        self.base   = "https://www.youtube.com/watch?v="
        self.regex  = r"(?:youtube\.com|youtu\.be)"
        self._cache: Dict[str, Any] = {}

    async def exists(self, link: str) -> bool:
        return bool(re.search(self.regex, link))

    async def url(self, message: Message) -> Optional[str]:
        """Message ya reply se YouTube URL nikaalein."""
        for msg in [message, message.reply_to_message]:
            if not msg:
                continue
            text = msg.text or msg.caption
            if not text:
                continue
            if msg.entities:
                for entity in msg.entities:
                    if entity.type == MessageEntityType.URL:
                        return text[entity.offset: entity.offset + entity.length]
            urls = re.findall(r"(https?://\S+)", text)
            if urls:
                return urls[0]
        return None

    async def search(self, query: str, limit: int = 1) -> List[Dict]:
        """YouTube search with in-memory cache."""
        key = f"{query}:{limit}"
        if key in self._cache:
            return self._cache[key]
        try:
            result  = await VideosSearch(query, limit=limit).next()
            results = result.get("result", [])
            self._cache[key] = results
            return results
        except Exception as e:
            LOGGER.error(f"[Search] Error: {e}")
            return []

    async def details(self, query: str, videoid: Union[bool, str] = None):
        """
        Video ka title, duration, thumbnail, ID nikaalein.
        YouTube link ya plain text — dono accept.
        """
        if videoid:
            link = self.base + query if not query.startswith("http") else query
        else:
            link = query

        try:
            if await self.exists(link):
                opts = _base_opts(
                    "bestaudio/best",
                    {"youtube": {"player_client": ["android"]}},
                )
                info = await _ydl_extract(link, opts)
                if info:
                    dur_sec = int(info.get("duration") or 0)
                    return (
                        info.get("title", "Unknown Title"),
                        f"{dur_sec // 60:02d}:{dur_sec % 60:02d}",
                        dur_sec,
                        info.get("thumbnail") or YOUTUBE_IMG_URL,
                        info.get("id"),
                    )

            res = await self.search(link, limit=1)
            if not res:
                return None
            v     = res[0]
            thumbs = v.get("thumbnails")
            thumb  = thumbs[0]["url"].split("?")[0] if thumbs else YOUTUBE_IMG_URL
            dur    = v.get("duration", "00:00")
            return (
                v.get("title", "Unknown Title"),
                dur,
                int(time_to_seconds(dur)),
                thumb,
                v.get("id"),
            )

        except Exception as e:
            LOGGER.error(f"[Details] Error: {e}")
            return None

    async def track(self, query: str, videoid: Union[bool, str] = None):
        """Track dict return karo — queue ke liye."""
        det = await self.details(query, videoid)
        if not det:
            return None, None
        return {
            "title"        : det[0],
            "link"         : self.base + det[4],
            "vidid"        : det[4],
            "duration_min" : det[1],
            "duration_sec" : det[2],
            "thumb"        : det[3],
        }, det[4]

    async def download(
        self,
        link: str,
        mystic=None,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        **kwargs,
    ) -> Tuple[Optional[str], bool]:
        """
        Main entry point.
        8-strategy waterfall — YouTube pareshan ho, hum nahi rukenge.
        """
        if videoid:
            link = self.base + link
        return await _waterfall(link, prefer_video=bool(video))


# ── GLOBAL INSTANCE ───────────────────────────────────────────
YouTube = YouTubeAPI()
