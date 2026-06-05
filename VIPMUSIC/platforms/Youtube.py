import asyncio
import re
from typing import Union

import aiohttp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from VIPMUSIC.utils.database import is_on_off

# ─── Invidious public instances — fallback order mein ────────────────────────
# Agar pehla kaam na kare toh agla try hoga automatically
INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://invidious.privacyredirect.com",
    "https://iv.datura.network",
    "https://invidious.einfachzocken.eu",
    "https://invidious.fdn.fr",
]
# ─────────────────────────────────────────────────────────────────────────────

_SESSION: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    global _SESSION
    if _SESSION is None or _SESSION.closed:
        _SESSION = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": "Mozilla/5.0"},
        )
    return _SESSION


async def _api_get(path: str, params: dict = None) -> dict | list | None:
    """
    Saare instances try karo — jo pehla kaam kare uska result return karo.
    Sab fail ho jaaye toh None return karo.
    """
    session = await _get_session()
    for base in INVIDIOUS_INSTANCES:
        url = f"{base}/api/v1/{path}"
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    # Empty response check
                    if data:
                        return data
        except Exception:
            continue
    return None


def _seconds_to_mmss(seconds: int) -> str:
    """Seconds ko H:MM:SS ya M:SS format mein convert karo."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02}:{s:02}"
    return f"{m}:{s:02}"


def _best_thumbnail(thumbnails: list) -> str:
    """videoThumbnails list se best quality URL lo."""
    if not thumbnails:
        return ""
    for q in ("maxresdefault", "sddefault", "high", "medium", "default"):
        for t in thumbnails:
            if t.get("quality") == q:
                return t.get("url", "")
    return thumbnails[0].get("url", "")


def _best_stream_url(data: dict, prefer_video: bool = False) -> str | None:
    """
    Invidious /videos/:id response se best stream URL nikalo.
      prefer_video=False  -> best audio-only stream
      prefer_video=True   -> best progressive video+audio stream (max 720p)
    """
    if prefer_video:
        streams = data.get("formatStreams", [])
        for res in ("720p", "480p", "360p", "240p"):
            for s in streams:
                if s.get("resolution") == res:
                    return s.get("url")
        if streams:
            return streams[0].get("url")
    else:
        adaptive = data.get("adaptiveFormats", [])
        audio_streams = [
            s for s in adaptive
            if s.get("audioQuality") and not s.get("resolution")
        ]
        if audio_streams:
            best = max(audio_streams, key=lambda s: int(s.get("bitrate", 0)))
            return best.get("url")
    return None


def _empty_track() -> dict:
    """Guaranteed safe empty track dict — KeyError kabhi nahi aayega."""
    return {
        "title": "",
        "link": "",
        "vidid": "",
        "duration_min": None,
        "duration_sec": 0,
        "thumb": "",
    }


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _extract_videoid(self, link: str) -> str | None:
        """
        YouTube URL se 11-char video ID nikalo.
        Plain text query pe None return karo — caller search karega.
        """
        match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", link)
        return match.group(1) if match else None

    def _clean_link(self, link: str) -> str:
        if "&" in link:
            link = link.split("&")[0]
        return link.strip()

    async def _search_first(self, query: str) -> dict | None:
        """Invidious search se pehla video result lo."""
        results = await _api_get("search", {"q": query, "type": "video", "page": 1})
        if isinstance(results, list):
            for item in results:
                if item.get("type") == "video":
                    return item
        return None

    async def _get_video_data(self, link: str) -> tuple[dict | None, str]:
        """
        Link ya query se video data aur video ID return karo.
        Pehle ID extract karo, nahi toh search karo.
        Returns: (data_dict, video_id_str)
        """
        link = self._clean_link(link)
        vid = self._extract_videoid(link)

        data = None
        if vid:
            data = await _api_get(f"videos/{vid}")

        if not data:
            # Plain text search ya fallback
            search_result = await self._search_first(link)
            if not search_result:
                return None, ""
            vid = search_result.get("videoId", "")
            # Full video info lo — search result mein sab fields nahi hoti
            full = await _api_get(f"videos/{vid}")
            data = full if full else search_result

        vid = vid or data.get("videoId", "")
        return data, vid

    # ─── Public API methods ──────────────────────────────────────────────────

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        offset = None
        length = None
        text = ""
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

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        data, vid = await self._get_video_data(link)
        if not data:
            return None, None, None, None, None
        title        = data.get("title", "")
        length_sec   = int(data.get("lengthSeconds", 0))
        duration_min = _seconds_to_mmss(length_sec)
        thumbnail    = _best_thumbnail(data.get("videoThumbnails", []))
        return title, duration_min, length_sec, thumbnail, vid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        data, _ = await self._get_video_data(link)
        return data.get("title", "") if data else ""

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        data, _ = await self._get_video_data(link)
        if not data:
            return "0:00"
        return _seconds_to_mmss(int(data.get("lengthSeconds", 0)))

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        data, _ = await self._get_video_data(link)
        if not data:
            return ""
        return _best_thumbnail(data.get("videoThumbnails", []))

    async def video(self, link: str, videoid: Union[bool, str] = None):
        """
        Direct stream URL return karo (video mode).
        Returns: (1, url) on success | (0, error_str) on failure
        """
        if videoid:
            link = self.base + link
        data, _ = await self._get_video_data(link)
        if not data:
            return 0, "Invidious se video info nahi mili"
        url = _best_stream_url(data, prefer_video=True)
        if url:
            return 1, url
        if data.get("hlsUrl"):
            return 1, data["hlsUrl"]
        return 0, "Stream URL nahi mili"

    async def playlist(self, link: str, limit: int, user_id, videoid: Union[bool, str] = None):
        """Playlist ke video IDs ki list return karo."""
        if videoid:
            link = self.listbase + link
        link = self._clean_link(link)

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
            if len(data["videos"]) < 100:
                break
            page += 1

        return video_ids

    async def track(self, link: str, videoid: Union[bool, str] = None):
        """
        Video ki track details dict return karo.
        Returns: (track_details_dict, video_id)
        Failure pe guaranteed safe dict return hoti hai — KeyError nahi aayega.
        """
        if videoid:
            link = self.base + link

        data, vid = await self._get_video_data(link)

        if not data or not vid:
            return _empty_track(), None

        title        = data.get("title", "")
        length_sec   = int(data.get("lengthSeconds", 0))
        # duration_min = None means livestream (play.py ka `if details["duration_min"]:` check)
        duration_min = _seconds_to_mmss(length_sec) if length_sec else None
        thumbnail    = _best_thumbnail(data.get("videoThumbnails", []))
        yturl        = f"https://www.youtube.com/watch?v={vid}"

        track_details = {
            "title":        title,
            "link":         yturl,
            "vidid":        vid,
            "duration_min": duration_min,
            "duration_sec": length_sec,
            "thumb":        thumbnail,
        }
        return track_details, vid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        """Available stream formats return karo."""
        if videoid:
            link = self.base + link
        data, vid = await self._get_video_data(link)
        if not data:
            return [], link

        formats_available = []

        # Progressive streams (video + audio)
        for fmt in data.get("formatStreams", []):
            formats_available.append({
                "format":      f"{fmt.get('qualityLabel', '')} ({fmt.get('container', '')})",
                "filesize":    None,
                "format_id":  fmt.get("itag", ""),
                "ext":         fmt.get("container", ""),
                "format_note": fmt.get("qualityLabel", ""),
                "yturl":       fmt.get("url", ""),
            })

        # Adaptive streams (separate audio / video)
        for fmt in data.get("adaptiveFormats", []):
            label = fmt.get("qualityLabel") or fmt.get("audioQuality") or ""
            if not label:
                continue
            formats_available.append({
                "format":      f"{label} ({fmt.get('container', '')})",
                "filesize":    fmt.get("clen"),
                "format_id":  fmt.get("itag", ""),
                "ext":         fmt.get("container", ""),
                "format_note": label,
                "yturl":       fmt.get("url", ""),
            })

        return formats_available, f"https://www.youtube.com/watch?v={vid}"

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        """Search results mein se query_type index wala result return karo."""
        if videoid:
            link = self.base + link
        link = self._clean_link(link)

        results = await _api_get("search", {"q": link, "type": "video", "page": 1})
        videos  = [r for r in (results or []) if r.get("type") == "video"]

        if not videos or query_type >= len(videos):
            return None, None, None, None

        item         = videos[query_type]
        title        = item.get("title", "")
        vid          = item.get("videoId", "")
        length_sec   = int(item.get("lengthSeconds", 0))
        duration_min = _seconds_to_mmss(length_sec)
        thumbnail    = _best_thumbnail(item.get("videoThumbnails", []))
        return title, duration_min, thumbnail, vid

    async def download(
        self,
        link: str,
        mystic,
        video:      Union[bool, str] = None,
        videoid:    Union[bool, str] = None,
        songaudio:  Union[bool, str] = None,
        songvideo:  Union[bool, str] = None,
        format_id:  Union[bool, str] = None,
        title:      Union[bool, str] = None,
    ):
        """
        Invidious se direct stream URL return karo.
        Physically download nahi karta — URL directly player ko deta hai.
        Returns: (url_str, direct_bool) | (None, None) on failure
        """
        if videoid:
            link = self.base + link

        data, vid = await self._get_video_data(link)
        if not data:
            return None, None

        all_formats = data.get("adaptiveFormats", []) + data.get("formatStreams", [])

        if songvideo or (video and await is_on_off(1)):
            if format_id:
                for fmt in all_formats:
                    if str(fmt.get("itag")) == str(format_id):
                        return fmt["url"], True
            url = _best_stream_url(data, prefer_video=True)
            if not url:
                url = data.get("hlsUrl")
            return url, True

        elif songaudio:
            if format_id:
                for fmt in data.get("adaptiveFormats", []):
                    if str(fmt.get("itag")) == str(format_id):
                        return fmt["url"], True
            return _best_stream_url(data, prefer_video=False), True

        elif video:
            url = _best_stream_url(data, prefer_video=True)
            if not url:
                url = data.get("hlsUrl")
            return url, None

        else:
            # Default: audio only
            return _best_stream_url(data, prefer_video=False), True
