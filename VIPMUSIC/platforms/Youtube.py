import asyncio
import re
import logging
import aiohttp
from typing import Union, Optional, Tuple, List
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from VIPMUSIC import LOGGER

# --- CONFIGURATION ---
from config import YOUTUBE_IMG_URL

# --- SECURITY FILTER ---
class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        msg = str(record.msg)
        patterns = [r"\d{8,10}:[a-zA-Z0-9_-]{35,}", r"mongodb\+srv://\S+"]
        for pattern in patterns:
            msg = re.sub(pattern, "[PROTECTED]", msg)
        record.msg = msg
        return True

logging.getLogger().addFilter(SensitiveDataFilter())

# ─── VIP-MUSIC API ────────────────────────────────────────────────────────────
API_BASE = "https://youtube-mini.up.railway.app"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# ─── Duration Parser ──────────────────────────────────────────────────────────
def parse_duration(duration_str) -> Tuple[str, int]:
    if not duration_str:
        return "00:00", 0
    try:
        parts = [int(p) for p in str(duration_str).strip().split(":")]
        if len(parts) == 1:
            secs = parts[0]
        elif len(parts) == 2:
            secs = parts[0] * 60 + parts[1]
        else:
            secs = parts[0] * 3600 + parts[1] * 60 + parts[2]
        return f"{secs // 60:02d}:{secs % 60:02d}", secs
    except Exception:
        return "00:00", 0


# ─── UTILS ───────────────────────────────────────────────────────────────────
def get_clean_id(link: str) -> Optional[str]:
    if "v=" in link:
        video_id = link.split('v=')[-1].split('&')[0]
    elif "youtu.be/" in link:
        video_id = link.split('youtu.be/')[-1].split('?')[0]
    else:
        video_id = link
    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '', video_id)
    return clean_id if 5 <= len(clean_id) <= 15 else None


async def api_get(endpoint: str, params: dict = {}) -> Optional[dict]:
    url = f"{API_BASE}/{endpoint}"
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                text = await resp.text()
                LOGGER(__name__).debug(f"[API] {url} | status={resp.status} | response={text[:300]}")
                if resp.status == 200:
                    import json
                    return json.loads(text)
    except Exception as e:
        LOGGER(__name__).error(f"[API ERROR] {endpoint}: {e}")
    return None


async def get_stream_url(video_id: str) -> Optional[str]:
    data = await api_get("api/yt/stream", {"id": video_id})
    if data and data.get("stream"):
        return data["stream"]
    return None


async def search_api(query: str, limit: int = 1) -> List[dict]:
    data = await api_get("api/yt/search", {"q": query, "max": limit})
    if data and isinstance(data.get("results"), list):
        return data["results"]
    return []


# ─── YouTubeAPI Class ─────────────────────────────────────────────────────────
class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"

    async def exists(self, link: str) -> bool:
        return bool(re.search(self.regex, link))

    async def url(self, message: Message) -> Optional[str]:
        messages = [message, message.reply_to_message]
        for msg in messages:
            if not msg:
                continue
            text = msg.text or msg.caption
            if not text:
                continue
            if msg.entities:
                for entity in msg.entities:
                    if entity.type == MessageEntityType.URL:
                        return text[entity.offset: entity.offset + entity.length]
            urls = re.findall(r'(https?://\S+)', text)
            if urls:
                return urls[0]
        return None

    async def details(self, query: str, videoid: Union[bool, str] = None) -> Optional[Tuple]:
        LOGGER(__name__).debug(f"[DETAILS] query={query} videoid={videoid}")
        video_id = None

        if videoid:
            video_id = get_clean_id(query) or query
        elif await self.exists(query):
            video_id = get_clean_id(query)

        LOGGER(__name__).debug(f"[DETAILS] video_id={video_id}")

        # Direct video ID
        if video_id:
            stream_data = await api_get("api/yt/stream", {"id": video_id})
            LOGGER(__name__).debug(f"[DETAILS] stream_data={stream_data}")
            if stream_data and stream_data.get("stream"):
                title = stream_data.get("title") or "Unknown Title"
                thumb = stream_data.get("thumb") or YOUTUBE_IMG_URL
                search_res = await search_api(title, limit=1)
                duration_str, duration_sec = "00:00", 0
                if search_res:
                    duration_str, duration_sec = parse_duration(search_res[0].get("duration"))
                return title, duration_str, duration_sec, thumb, video_id

        # Text search
        LOGGER(__name__).debug(f"[DETAILS] Trying search for: {query}")
        results = await search_api(query, limit=1)
        LOGGER(__name__).debug(f"[DETAILS] search results={results}")

        if results:
            v = results[0]
            vid_id = v.get("id", "")
            title = v.get("title", "Unknown Title")
            thumb = v.get("thumb") or YOUTUBE_IMG_URL
            dur_str, dur_sec = parse_duration(v.get("duration", "0:00"))
            LOGGER(__name__).debug(f"[DETAILS] Found: {title} | {vid_id} | {dur_str}")
            return title, dur_str, dur_sec, thumb, vid_id

        # Last fallback
        LOGGER(__name__).debug(f"[DETAILS] Trying youtubesearchpython fallback")
        try:
            search = VideosSearch(query, limit=1)
            resp = await search.next()
            res = resp.get("result", [])
            if res:
                v = res[0]
                thumb = (v.get("thumbnails") or [{}])[0].get("url", YOUTUBE_IMG_URL).split("?")[0]
                dur_str, dur_sec = parse_duration(v.get("duration", "0:00"))
                LOGGER(__name__).debug(f"[DETAILS] Fallback found: {v.get('title')} | {v.get('id')}")
                return v.get("title", "Unknown"), dur_str, dur_sec, thumb, v.get("id", "")
        except Exception as e:
            LOGGER(__name__).error(f"[DETAILS] Fallback error: {e}")

        LOGGER(__name__).warning("[DETAILS] All methods failed!")
        return None

    async def track(self, query: str, videoid: Union[bool, str] = None):
        det = await self.details(query, videoid)
        if not det:
            return None, None
        track_details = {
            "title":        det[0],
            "link":         self.base + det[4],
            "vidid":        det[4],
            "duration_min": det[1],
            "duration_sec": det[2],
            "thumb":        det[3],
        }
        return track_details, det[4]

    async def download(
        self,
        link: str,
        mystic=None,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        **kwargs,
    ) -> Tuple[Optional[str], bool]:
        """
        Koi file download nahi hoti.
        Seedha stream URL return karta hai — direct play ke liye.
        Returns: (stream_url, True) on success, (None, False) on failure.
        """
        video_id = get_clean_id(link) if not videoid else (get_clean_id(link) or link)

        if not video_id:
            LOGGER(__name__).warning(f"[STREAM] Invalid video ID: {link}")
            return None, False

        LOGGER(__name__).info(f"[STREAM] Fetching direct stream URL: {video_id}")
        stream_url = await get_stream_url(video_id)

        if stream_url:
            LOGGER(__name__).info(f"[STREAM] Stream URL ready: {video_id}")
            return stream_url, True

        LOGGER(__name__).warning(f"[STREAM] Stream URL not found: {video_id}")
        return None, False


# Global Instance
YouTube = YouTubeAPI()
