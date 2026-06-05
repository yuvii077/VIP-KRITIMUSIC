import asyncio
import re
from typing import Union

import aiohttp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from kiru.utils.database import is_on_off
from kiru.utils.formatters import time_to_seconds

# ─── Invidious public instance (change if needed) ────────────────────────────
INVIDIOUS_BASE = "https://inv.nadeko.net"   # ya koi bhi public instance
# Public instances list: https://docs.invidious.io/instances/
# ─────────────────────────────────────────────────────────────────────────────


async def _api_get(path: str, params: dict = None) -> dict | list | None:
    """Invidious REST API ko async GET request karo."""
    url = f"{INVIDIOUS_BASE}/api/v1/{path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                return await resp.json()
            return None


def _seconds_to_mmss(seconds: int) -> str:
    """Seconds ko 'MM:SS' format mein convert karo."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02}:{s:02}"
    return f"{m}:{s:02}"


def _best_thumbnail(thumbnails: list) -> str:
    """videoThumbnails list se best quality URL lo."""
    if not thumbnails:
        return ""
    # 'maxresdefault' ya 'high' prefer karo
    for q in ("maxresdefault", "sddefault", "high", "medium", "default"):
        for t in thumbnails:
            if t.get("quality") == q:
                return t["url"]
    return thumbnails[0]["url"]


def _best_stream_url(data: dict, prefer_video: bool = False) -> str | None:
    """
    /api/v1/videos/:id response se direct stream URL nikalo.
    - prefer_video=False  → bestaudio (adaptiveFormats mein audioQuality wala)
    - prefer_video=True   → 720p tak ka progressive stream (formatStreams)
    """
    if prefer_video:
        # formatStreams mein progressive (video+audio) streams hote hain
        streams = data.get("formatStreams", [])
        # 720p ya usse kam prefer karo
        for res in ("720p", "480p", "360p", "240p"):
            for s in streams:
                if s.get("resolution") == res:
                    return s["url"]
        if streams:
            return streams[0]["url"]
    else:
        # adaptiveFormats mein audio-only streams
        adaptive = data.get("adaptiveFormats", [])
        audio_streams = [
            s for s in adaptive
            if s.get("audioQuality") and not s.get("resolution")
        ]
        # highest bitrate audio lo
        if audio_streams:
            best = max(audio_streams, key=lambda s: int(s.get("bitrate", 0)))
            return best["url"]
    return None


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    # ── helpers ────────────────────────────────────────────────────────────────

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset is None:
            return None
        return text[offset: offset + length]

    def _extract_videoid(self, link: str) -> str:
        """YouTube URL se video ID nikalo ya jo bhi diya ho woh return karo."""
        match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", link)
        return match.group(1) if match else link

    def _clean_link(self, link: str) -> str:
        if "&" in link:
            link = link.split("&")[0]
        return link

    # ── search helper ─────────────────────────────────────────────────────────

    async def _search_first(self, query: str) -> dict | None:
        """Invidious search se pehla video result lo."""
        results = await _api_get("search", {"q": query, "type": "video", "page": 1})
        if results:
            for item in results:
                if item.get("type") == "video":
                    return item
        return None

    # ── public methods ─────────────────────────────────────────────────────────

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        link = self._clean_link(link)

        # Agar URL hai to video ID se direct info lo, warna search karo
        vid = self._extract_videoid(link)
        data = await _api_get(f"videos/{vid}")
        if not data:
            # fallback: search
            data = await self._search_first(link)
            if not data:
                return None, None, None, None, None
            vid = data["videoId"]
            data = await _api_get(f"videos/{vid}") or data

        title = data.get("title", "")
        length_sec = int(data.get("lengthSeconds", 0))
        duration_min = _seconds_to_mmss(length_sec)
        thumbnail = _best_thumbnail(data.get("videoThumbnails", []))
        return title, duration_min, length_sec, thumbnail, vid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        link = self._clean_link(link)
        vid = self._extract_videoid(link)
        data = await _api_get(f"videos/{vid}")
        if data:
            return data.get("title", "")
        result = await self._search_first(link)
        return result["title"] if result else ""

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        link = self._clean_link(link)
        vid = self._extract_videoid(link)
        data = await _api_get(f"videos/{vid}")
        if data:
            return _seconds_to_mmss(int(data.get("lengthSeconds", 0)))
        result = await self._search_first(link)
        return _seconds_to_mmss(int(result.get("lengthSeconds", 0))) if result else "0:00"

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        link = self._clean_link(link)
        vid = self._extract_videoid(link)
        data = await _api_get(f"videos/{vid}")
        if data:
            return _best_thumbnail(data.get("videoThumbnails", []))
        result = await self._search_first(link)
        if result:
            return _best_thumbnail(result.get("videoThumbnails", []))
        return ""

    async def video(self, link: str, videoid: Union[bool, str] = None):
        """
        Direct stream URL return karta hai (video).
        Return: (1, url) on success, (0, error_msg) on failure
        """
        if videoid:
            link = self.base + link
        link = self._clean_link(link)
        vid = self._extract_videoid(link)
        data = await _api_get(f"videos/{vid}")
        if not data:
            return 0, "Invidious se video info nahi mili"
        url = _best_stream_url(data, prefer_video=True)
        if url:
            return 1, url
        # hlsUrl fallback
        if data.get("hlsUrl"):
            return 1, data["hlsUrl"]
        return 0, "Stream URL nahi mili"

    async def playlist(self, link: str, limit: int, user_id, videoid: Union[bool, str] = None):
        """Playlist ke video IDs return karta hai."""
        if videoid:
            link = self.listbase + link
        link = self._clean_link(link)

        # playlist ID nikalo
        match = re.search(r"list=([A-Za-z0-9_-]+)", link)
        plid = match.group(1) if match else link

        video_ids = []
        page = 1
        while len(video_ids) < limit:
            data = await _api_get(f"playlists/{plid}", {"page": page})
            if not data or not data.get("videos"):
                break
            for v in data["videos"]:
                if len(video_ids) >= limit:
                    break
                vid = v.get("videoId")
                if vid:
                    video_ids.append(vid)
            # Agar ek page pe sab aa gaye
            if len(data["videos"]) < 100:
                break
            page += 1

        return video_ids

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        link = self._clean_link(link)
        vid = self._extract_videoid(link)
        data = await _api_get(f"videos/{vid}")
        if not data:
            data = await self._search_first(link)
            if not data:
                return {}, None
            vid = data.get("videoId", "")
            data = await _api_get(f"videos/{vid}") or data

        title = data.get("title", "")
        length_sec = int(data.get("lengthSeconds", 0))
        duration_min = _seconds_to_mmss(length_sec)
        thumbnail = _best_thumbnail(data.get("videoThumbnails", []))
        yturl = f"https://www.youtube.com/watch?v={vid}"

        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vid,
            "duration_min": duration_min,
            "duration_sec": length_sec,   # kuch plugins yeh key use karte hain
            "thumb": thumbnail,
        }
        return track_details, vid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        """Available formats return karta hai."""
        if videoid:
            link = self.base + link
        link = self._clean_link(link)
        vid = self._extract_videoid(link)
        data = await _api_get(f"videos/{vid}")
        if not data:
            return [], link

        formats_available = []

        # formatStreams (progressive video+audio)
        for fmt in data.get("formatStreams", []):
            formats_available.append({
                "format": f"{fmt.get('qualityLabel', '')} ({fmt.get('container', '')})",
                "filesize": None,  # Invidious formatStreams mein filesize nahi hoti
                "format_id": fmt.get("itag", ""),
                "ext": fmt.get("container", ""),
                "format_note": fmt.get("qualityLabel", ""),
                "yturl": fmt.get("url", ""),
            })

        # adaptiveFormats (separate audio/video)
        for fmt in data.get("adaptiveFormats", []):
            label = fmt.get("qualityLabel") or fmt.get("audioQuality") or ""
            if not label:
                continue
            formats_available.append({
                "format": f"{label} ({fmt.get('container', '')})",
                "filesize": fmt.get("clen"),
                "format_id": fmt.get("itag", ""),
                "ext": fmt.get("container", ""),
                "format_note": label,
                "yturl": fmt.get("url", ""),
            })

        return formats_available, f"https://www.youtube.com/watch?v={vid}"

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        """Search results mein se query_type index ka result return karo."""
        if videoid:
            link = self.base + link
        link = self._clean_link(link)

        results = await _api_get("search", {"q": link, "type": "video", "page": 1})
        videos = [r for r in (results or []) if r.get("type") == "video"]

        if not videos or query_type >= len(videos):
            return None, None, None, None

        item = videos[query_type]
        title = item["title"]
        vid = item["videoId"]
        length_sec = int(item.get("lengthSeconds", 0))
        duration_min = _seconds_to_mmss(length_sec)
        thumbnail = _best_thumbnail(item.get("videoThumbnails", []))
        return title, duration_min, thumbnail, vid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        """
        Invidious se direct stream URL return karta hai.

        Note: Invidious direct URLs deta hai, isliye alag se download
        karne ki zaroorat nahi — URL ko directly player ko de sakte ho.
        Agar physically download karna ho to yt-dlp ko woh URL do.
        """
        if videoid:
            link = self.base + link
        link = self._clean_link(link)
        vid = self._extract_videoid(link)

        data = await _api_get(f"videos/{vid}")
        if not data:
            return None, None

        if songvideo or (video and await is_on_off(1)):
            # Specific format_id se stream URL lo
            if format_id:
                all_formats = data.get("adaptiveFormats", []) + data.get("formatStreams", [])
                for fmt in all_formats:
                    if str(fmt.get("itag")) == str(format_id):
                        return fmt["url"], True
            # Fallback: best video stream
            url = _best_stream_url(data, prefer_video=True)
            if not url and data.get("hlsUrl"):
                url = data["hlsUrl"]
            return url, True

        elif songaudio:
            if format_id:
                for fmt in data.get("adaptiveFormats", []):
                    if str(fmt.get("itag")) == str(format_id):
                        return fmt["url"], True
            url = _best_stream_url(data, prefer_video=False)
            return url, True

        elif video:
            # is_on_off(1) False hai to direct URL
            url = _best_stream_url(data, prefer_video=True)
            if not url and data.get("hlsUrl"):
                url = data["hlsUrl"]
            return url, None

        else:
            # Audio only (default)
            url = _best_stream_url(data, prefer_video=False)
            return url, True
