
import requests
import asyncio

class YoutubeAPI:
    def __init__(self):
        self.base_url = "https://youtube-mp3-audio-video-downloader.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": "996842dcfbmsh540dd8f0931b4abp1fd139jsn1f4362a63cd",
            "X-RapidAPI-Host": "youtube-mp3-audio-video-downloader.p.rapidapi.com"
        }

    def _str_to_sec(self, time_str):
        """समय को सेकंड में बदलने का खुद का तरीका"""
        try:
            parts = list(map(int, time_str.split(':')))
            if len(parts) == 2:  # MM:SS
                return parts[0] * 60 + parts[1]
            elif len(parts) == 3:  # HH:MM:SS
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
        except:
            pass
        return 180  # डिफ़ॉल्ट 3 मिनट

    async def search(self, query, limit=1):
        url = f"{self.base_url}/v1/youtube/search"
        querystring = {"query": query}
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.get(url, headers=self.headers, params=querystring, timeout=10)
            )
            if response.status_code == 200:
                data = response.json()
                results = []
                for video in data.get("videos", [])[:limit]:
                    results.append({
                        "title": video.get("title"),
                        "link": f"https://www.youtube.com/watch?v={video.get('videoId')}",
                        "id": video.get("videoId"),
                        "duration": video.get("duration"),
                    })
                return results
        except Exception as e:
            print(f"Search Error: {e}")
        return []

    async def force_fetch(self, url_or_id):
        video_id = url_or_id.split("v=")[-1] if "v=" in url_or_id else url_or_id
        url = f"{self.base_url}/v1/youtube/download"
        querystring = {"url": f"https://www.youtube.com/watch?v={video_id}"}
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.get(url, headers=self.headers, params=querystring, timeout=10)
            )
            if response.status_code == 200:
                data = response.json()
                stream_url = data.get("downloadUrl") or data.get("audioUrl")
                title = data.get("title", "Track")
                duration_str = data.get("duration", "03:00")
                duration_sec = self._str_to_sec(duration_str)
                
                return stream_url, title, duration_sec
        except Exception as e:
            print(f"Fetch Stream Error: {e}")
        return None, None, None

# बॉट के कोड के नाम से मैच करने के लिए क्लास को इनिशियलाइज करना
YouTubeAPI = YoutubeAPI()
