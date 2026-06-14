import requests
import asyncio
from VIPMUSIC.utils.formatters import time_to_sec

class YoutubeAPI:
    def __init__(self):
        self.base_url = "https://youtube-mp3-audio-video-downloader.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": "996842dcfbmsh540dd8f0931b4abp1fd139jsn1f4362a63cd",
            "X-RapidAPI-Host": "youtube-mp3-audio-video-downloader.p.rapidapi.com"
        }

    async def search(self, query, limit=1):
        # सर्च करने के लिए RapidAPI का एंडपॉइंट
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
        # वीडियो आईडी निकालना
        video_id = url_or_id.split("v=")[-1] if "v=" in url_or_id else url_or_id
        
        # डायरेक्ट ऑडियो डाउनलोड लिंक निकालने का एंडपॉइंट
        url = f"{self.base_url}/v1/youtube/download"
        querystring = {"url": f"https://www.youtube.com/watch?v={video_id}"}
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.get(url, headers=self.headers, params=querystring, timeout=10)
            )
            if response.status_code == 200:
                data = response.json()
                # RapidAPI से मिलने वाला डायरेक्ट MP3/M4A ऑडियो लिंक
                stream_url = data.get("downloadUrl") or data.get("audioUrl")
                title = data.get("title", "Track")
                duration_str = data.get("duration", "03:00")
                duration_sec = time_to_sec(duration_str)
                
                return stream_url, title, duration_sec
        except Exception as e:
            print(f"Fetch Stream Error: {e}")
        return None, None, None

# बॉट के बाकी कोड के लिए क्लास को इनिशियलाइज करना
Youtube = YoutubeAPI()
