import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from .mock_data import MOCK_TRANSCRIPT_PYTHON, MOCK_TRANSCRIPT_GENERIC

load_dotenv()

class VideoClipper:
    def __init__(self):
        self.api_key = os.getenv("SUPADATA_API_KEY")
        self.use_mock = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
        self.base_url = "https://api.supadata.ai/v1/youtube/transcript" # Example endpoint

    def normalize_url(self, url: str) -> tuple[str, str | None]:
        parsed = urlparse(url.strip())
        host = (parsed.netloc or "").lower()
        path = parsed.path or ""
        qs = parse_qs(parsed.query or "")

        if "douyin.com" in host:
            modal_id = (qs.get("modal_id") or [None])[0]
            if modal_id and (path.startswith("/user/") or path == "/user/self"):
                return f"https://www.douyin.com/video/{modal_id}", "检测到抖音个人页链接，已根据 modal_id 转换为视频链接。"
            if path.startswith("/video/"):
                return url, None
            raise ValueError("抖音链接请使用具体视频链接（形如 https://www.douyin.com/video/<id>），或包含 modal_id 的链接。")

        return url, None

    def detect_platform(self, url: str) -> str:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if "douyin.com" in host:
            return "douyin"
        if "youtube.com" in host or "youtu.be" in host:
            return "youtube"
        if "bilibili.com" in host:
            return "bilibili"
        return "generic_web"

    def get_webpage_content(self, url: str) -> str:
        """
        Scrapes text content from a generic webpage.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
                
            # Get text
            text = soup.get_text(separator="\n")
            
            # Clean up empty lines
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines[:5000]) # Limit content size
            
        except Exception as e:
            print(f"[Clipper] Web scraping error: {e}")
            return f"Error scraping webpage: {str(e)}"

    def get_transcript(self, url: str) -> str:
        """
        Retrieves the transcript for a given video URL or scrapes webpage content.
        """
        normalized_url, note = self.normalize_url(url)
        if note:
            print(f"[Clipper] {note}")
        print(f"[Clipper] Processing URL: {normalized_url}")
        
        if self.use_mock:
            print("[Clipper] Using MOCK data mode.")
            if "python" in normalized_url.lower() or "excel" in normalized_url.lower():
                return MOCK_TRANSCRIPT_PYTHON
            return MOCK_TRANSCRIPT_GENERIC

        platform = self.detect_platform(normalized_url)
        
        if platform == "generic_web":
            print("[Clipper] Detected generic webpage, scraping content...")
            return self.get_webpage_content(normalized_url)

        if platform == "douyin":
            raise NotImplementedError("当前版本尚未接入抖音转写接口。请先使用 Mock 模式或提供 YouTube 链接。")

        if not self.api_key:
            raise ValueError("SUPADATA_API_KEY is not set in .env file.")

        # Real API call implementation (Example)
        try:
            params = {"url": normalized_url, "text": True}
            headers = {"x-api-key": self.api_key}
            response = requests.get(self.base_url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get("content", "")
        except Exception as e:
            print(f"[Clipper] Error fetching transcript: {e}")
            raise e