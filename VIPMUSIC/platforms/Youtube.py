import asyncio
import logging
import os
import random
import re
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from VIPMUSIC.utils.formatters import time_to_seconds

log = logging.getLogger(__name__)

# ── Optional auth paths ───────────────────────────────────────────────────────
OAUTH2_TOKEN  = os.path.expanduser("~/.cache/yt-dlp/youtube-oauth2.token")
COOKIES_FILE  = os.path.expanduser("~/.config/yt-dlp/cookies.txt")

# ── Android YouTube app User-Agent (realistic, rotated periodically) ──────────
ANDROID_UA = (
    "com.google.android.youtube/19.09.37 (Linux; U; Android 13; Pixel 7) gzip"
)

# ── Player clients tried in order (most reliable first) ──────────────────────
PLAYER_CLIENTS = ["android", "ios", "web", "mweb"]

# ── GeoNode Proxy Manager ─────────────────────────────────────────────────────
import aiohttp
import time

GEONODE_API = (
    "https://proxylist.geonode.com/api/proxy-list"
    "?limit=500&page=1&sort_by=lastChecked&sort_type=desc"
)
PROXY_REFRESH_INTERVAL = 600   # Seconds between auto-refresh (10 min)
PROXY_TEST_TIMEOUT     = 6     # Seconds before marking a proxy dead
PROXY_TEST_URL         = "https://www.youtube.com/robots.txt"


class _ProxyManager:
    """
    Fetches fresh proxies from GeoNode API and rotates them per request.

    Features:
      - Auto-fetches on first use (lazy init)
      - Background refresh every PROXY_REFRESH_INTERVAL seconds
      - Dead proxy auto-removal on failure reports
      - Falls back to direct connection if list is empty
    """

    def __init__(self):
        self._proxies:      list[str] = []
        self._lock:         asyncio.Lock | None = None   # created lazily
        self._last_fetch:   float = 0.0
        self._refresh_task: asyncio.Task | None = None

    def _ensure_lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()

    # ── Fetch ─────────────────────────────────────────────────────────────────

    async def _fetch(self) -> list[str]:
        """Pull proxies from GeoNode and return as protocol://host:port strings."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            ) as session:
                async with session.get(GEONODE_API) as resp:
                    if resp.status != 200:
                        log.warning("GeoNode API returned HTTP %s", resp.status)
                        return []
                    data = await resp.json()

            out = []
            for item in data.get("data", []):
                host = item.get("ip")
                port = item.get("port")
                # GeoNode returns a list of supported protocols
                protocols: list = item.get("protocols", [])
                if not (host and port and protocols):
                    continue
                # Prefer socks5 > socks4 > https > http
                proto = next(
                    (p for p in ("socks5", "socks4", "https", "http") if p in protocols),
                    protocols[0],
                )
                out.append(f"{proto}://{host}:{port}")

            log.info("GeoNode: loaded %d proxies", len(out))
            return out

        except Exception as exc:
            log.warning("GeoNode fetch failed: %s", exc)
            return []

    # ── Refresh logic ─────────────────────────────────────────────────────────

    async def _maybe_refresh(self):
        """Refresh proxy list if stale or empty."""
        now = time.monotonic()
        if self._proxies and (now - self._last_fetch) < PROXY_REFRESH_INTERVAL:
            return
        self._ensure_lock()
        async with self._lock:
            # Double-check after acquiring lock
            now = time.monotonic()
            if self._proxies and (now - self._last_fetch) < PROXY_REFRESH_INTERVAL:
                return
            fresh = await self._fetch()
            if fresh:
                self._proxies  = fresh
                self._last_fetch = time.monotonic()

    def _start_background_refresh(self):
        """Launch a background task that refreshes the list periodically."""
        if self._refresh_task and not self._refresh_task.done():
            return
        async def _loop():
            while True:
                await asyncio.sleep(PROXY_REFRESH_INTERVAL)
                fresh = await self._fetch()
                if fresh:
                    self._ensure_lock()
                    async with self._lock:
                        self._proxies    = fresh
                        self._last_fetch = time.monotonic()
        try:
            self._refresh_task = asyncio.get_event_loop().create_task(_loop())
        except RuntimeError:
            pass   # No running loop yet — task will be created on first use

    # ── Public interface ──────────────────────────────────────────────────────

    async def get(self) -> str | None:
        """Return a random proxy URL, or None if unavailable."""
        await self._maybe_refresh()
        self._start_background_refresh()
        if not self._proxies:
            return None
        return random.choice(self._proxies)

    def mark_dead(self, proxy: str):
        """Remove a proxy that has been confirmed dead."""
        try:
            self._proxies.remove(proxy)
            log.debug("Proxy removed (dead): %s — %d left", proxy, len(self._proxies))
        except ValueError:
            pass


# Singleton — shared across all YouTubeAPI instances
proxy_manager = _ProxyManager()


async def _get_proxy() -> str | None:
    """Convenience wrapper — returns a proxy or None."""
    return await proxy_manager.get()


def _report_dead_proxy(proxy: str | None):
    """Call this when a proxy causes a failure."""
    if proxy:
        proxy_manager.mark_dead(proxy)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def shell_cmd(cmd: str) -> str:
    """Run a shell command asynchronously and return stdout (or stderr on error)."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if err:
        decoded_err = err.decode("utf-8", errors="replace")
        if "unavailable videos are hidden" in decoded_err.lower():
            return out.decode("utf-8", errors="replace")
        return decoded_err
    return out.decode("utf-8", errors="replace")


def _ydl_opts(extra: dict = None, proxy: str | None = None) -> dict:
    """
    Return a hardened yt-dlp options dict.

    Pass `proxy` explicitly (fetched via await _get_proxy() before calling).
    """
    opts: dict = {
        "extractor_args": {
            "youtube": {
                "player_client": PLAYER_CLIENTS,
                # Skip age-gate check — reduces unnecessary requests
                "skip": ["dash", "hls"],
            }
        },
        "http_headers": {
            "User-Agent": ANDROID_UA,
            "Accept-Language": "en-US,en;q=0.9",
        },
        # Sleep between requests (seconds) — avoids bot detection
        "sleep_interval":          2,
        "max_sleep_interval":      6,
        "sleep_interval_requests": 1,
        # Retry config
        "retries":          8,
        "fragment_retries": 8,
        "retry_sleep_functions": {
            "http":     lambda n: min(2 ** n, 30),
            "fragment": lambda n: min(2 ** n, 30),
        },
        # Geo / network
        "geo_bypass":          True,
        "nocheckcertificate":  True,
        # Output suppression
        "quiet":       True,
        "no_warnings": True,
    }

    # OAuth2 token (strongest protection — preferred when available)
    if os.path.exists(OAUTH2_TOKEN):
        opts["username"] = "oauth2"
        opts["password"] = ""

    # Browser cookies (second-best protection)
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE

    # Proxy (from GeoNode rotating pool)
    if proxy:
        opts["proxy"] = proxy
        log.debug("Using proxy: %s", proxy)

    if extra:
        opts.update(extra)
    return opts


def _clean_url(link: str, videoid=None, base: str = "") -> str:
    """Normalize a YouTube URL — strip tracking params, prepend base if needed."""
    if videoid and base:
        link = base + link
    return link.split("&")[0] if "&" in link else link


# ─────────────────────────────────────────────────────────────────────────────
#  Main class
# ─────────────────────────────────────────────────────────────────────────────

class YouTubeAPI:
    def __init__(self):
        self.base     = "https://www.youtube.com/watch?v="
        self.regex    = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self._ansi    = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_url(self, link: str, videoid=None) -> str:
        return _clean_url(link, videoid, self.base)

    async def _search_one(self, query: str) -> dict:
        """Return first VideosSearch result dict for a query."""
        result = await (VideosSearch(query, limit=1)).next()
        items = result.get("result", [])
        if not items:
            raise ValueError(f"No YouTube result found for: '{query}'")
        return items[0]

    async def _resolve_link(self, link: str) -> str:
        """
        If `link` is already a YouTube URL, clean and return it.
        Otherwise treat it as a search query and return the top result URL.
        """
        if re.search(self.regex, link):
            return link.split("&")[0] if "&" in link else link
        item = await self._search_one(link)
        return self.base + item["id"]

    def _extract_stream_url(self, link: str, fmt_selector: str, proxy: str | None = None) -> str:
        """
        Blocking call (run via executor) — fetches a direct stream URL from
        yt-dlp without writing anything to disk (simulate=True).
        """
        with yt_dlp.YoutubeDL(_ydl_opts({
            "format":      fmt_selector,
            "simulate":    True,
            "forceurl":    True,
            "quiet":       True,
            "no_warnings": True,
        }, proxy=proxy)) as ydl:
            info = ydl.extract_info(link, download=False)
            # Merged (video+audio) streams expose requested_formats
            if "requested_formats" in info:
                return info["requested_formats"][0]["url"]
            return info["url"]

    # ── Public API ────────────────────────────────────────────────────────────

    async def exists(self, link: str, videoid: Union[bool, str] = None) -> bool:
        """Check whether `link` looks like a YouTube URL."""
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message: Message) -> Union[str, None]:
        """Extract the first YouTube URL from a Pyrogram message (or its reply)."""
        candidates = [message]
        if message.reply_to_message:
            candidates.append(message.reply_to_message)

        for msg in candidates:
            # Inline URLs via entity offset
            for entity_list, text_src in [
                (msg.entities,         msg.text or msg.caption),
                (msg.caption_entities, msg.caption),
            ]:
                if not entity_list:
                    continue
                for ent in entity_list:
                    if ent.type == MessageEntityType.URL and text_src:
                        return text_src[ent.offset: ent.offset + ent.length]
                    if ent.type == MessageEntityType.TEXT_LINK:
                        return ent.url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        """Return (title, duration_str, duration_sec, thumbnail_url, video_id)."""
        link = self._build_url(link, videoid)
        r = await self._search_one(link)
        dur_min = r["duration"]
        dur_sec = 0 if not dur_min else int(time_to_seconds(dur_min))
        return (
            r["title"],
            dur_min,
            dur_sec,
            r["thumbnails"][0]["url"].split("?")[0],
            r["id"],
        )

    async def title(self, link: str, videoid: Union[bool, str] = None) -> str:
        link = self._build_url(link, videoid)
        return (await self._search_one(link))["title"]

    async def duration(self, link: str, videoid: Union[bool, str] = None) -> str:
        link = self._build_url(link, videoid)
        return (await self._search_one(link))["duration"]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None) -> str:
        link = self._build_url(link, videoid)
        r = await self._search_one(link)
        return r["thumbnails"][0]["url"].split("?")[0]

    async def track(self, link: str, videoid: Union[bool, str] = None):
        """Return a track info dict and the video ID."""
        link = self._build_url(link, videoid)
        r = await self._search_one(link)
        return {
            "title":        r["title"],
            "link":         r["link"],
            "vidid":        r["id"],
            "duration_min": r["duration"],
            "thumb":        r["thumbnails"][0]["url"].split("?")[0],
        }, r["id"]

    async def video(self, link: str, videoid: Union[bool, str] = None):
        """
        Get a direct video stream URL (≤720p) via yt-dlp subprocess.
        Returns (1, url) on success, (0, error_msg) on failure.
        """
        link = self._build_url(link, videoid)
        proxy = await _get_proxy()
        cmd = [
            "yt-dlp", "-g",
            "-f", "best[height<=?720][width<=?1280]",
            "--extractor-args", f"youtube:player_client={','.join(PLAYER_CLIENTS)}",
            "--no-warnings",
        ]
        if proxy:
            cmd += ["--proxy", proxy]
        cmd.append(link)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode(errors="replace").split("\n")[0]
        _report_dead_proxy(proxy)
        return 0, stderr.decode(errors="replace")

    async def playlist(
        self,
        link: str,
        limit: int,
        user_id,
        videoid: Union[bool, str] = None,
    ) -> list[str]:
        """Fetch up to `limit` video IDs from a YouTube playlist."""
        if videoid:
            link = self.listbase + link
        link = link.split("&")[0] if "&" in link else link

        proxy = await _get_proxy()
        proxy_flag = f'--proxy "{proxy}" ' if proxy else ""
        raw = await shell_cmd(
            f'yt-dlp -i --get-id --flat-playlist --playlist-end {limit} '
            f'--extractor-args "youtube:player_client={",".join(PLAYER_CLIENTS)}" '
            + proxy_flag
            + f'--skip-download "{link}"'
        )
        return [v for v in raw.split("\n") if v.strip()]

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        """
        Return available non-DASH formats with filesize info.
        Runs yt-dlp in an executor to avoid blocking the event loop.
        """
        link = self._build_url(link, videoid)
        proxy = await _get_proxy()

        def _extract_formats():
            out = []
            with yt_dlp.YoutubeDL(_ydl_opts(proxy=proxy)) as ydl:
                info = ydl.extract_info(link, download=False)
                for fmt in info.get("formats", []):
                    fmt_str = str(fmt.get("format", ""))
                    if not fmt_str or "dash" in fmt_str.lower():
                        continue
                    required = ("filesize", "format_id", "ext", "format_note")
                    if not all(k in fmt and fmt[k] for k in required):
                        continue
                    out.append({
                        "format":      fmt_str,
                        "filesize":    fmt["filesize"],
                        "format_id":  fmt["format_id"],
                        "ext":         fmt["ext"],
                        "format_note": fmt["format_note"],
                        "yturl":       link,
                    })
            return out

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _extract_formats)
        return result, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        """Return (title, duration, thumbnail, video_id) for the Nth search result."""
        link = self._build_url(link, videoid)
        results = (await (VideosSearch(link, limit=10)).next()).get("result", [])
        if query_type >= len(results):
            raise IndexError(
                f"slider: query_type={query_type} out of range ({len(results)} results)"
            )
        r = results[query_type]
        return r["title"], r["duration"], r["thumbnails"][0]["url"].split("?")[0], r["id"]

    async def download(
        self,
        link:       str,
        mystic,
        video:      Union[bool, str] = None,
        videoid:    Union[bool, str] = None,
        songaudio:  Union[bool, str] = None,
        songvideo:  Union[bool, str] = None,
        format_id:  Union[bool, str] = None,
        title:      Union[bool, str] = None,
    ):
        """
        Resolve and return a direct stream URL — nothing is written to disk.

        Priority order:
          1. Song video  (specific format_id + audio)
          2. Song audio  (specific format_id)
          3. Video stream (≤720p via subprocess for speed)
          4. Audio stream (best available — default)

        Returns: (stream_url, None)
          The `None` second value signals to callers that this is a stream,
          not a local file path.
        """
        # Resolve link to a proper YouTube URL
        if videoid:
            link = self.base + link
        else:
            link = await self._resolve_link(link)

        loop = asyncio.get_running_loop()

        # ── 1. Song Video ─────────────────────────────────────────────────────
        if songvideo:
            fmt = f"{format_id}+140" if format_id else "bestvideo[height<=?720]+bestaudio/best"
            proxy = await _get_proxy()
            try:
                url = await loop.run_in_executor(
                    None, self._extract_stream_url, link, fmt, proxy
                )
                return url, None
            except Exception as e:
                _report_dead_proxy(proxy)
                log.warning("songvideo stream fetch failed (%s), retrying with fallback", e)
                proxy = await _get_proxy()
                url = await loop.run_in_executor(
                    None, self._extract_stream_url, link, "best[height<=?720]/best", proxy
                )
                return url, None

        # ── 2. Song Audio ───
