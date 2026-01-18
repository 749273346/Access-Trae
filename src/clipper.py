import os
import requests
from dotenv import load_dotenv
from .mock_data import MOCK_TRANSCRIPT_PYTHON, MOCK_TRANSCRIPT_GENERIC

load_dotenv()

class VideoClipper:
    def __init__(self):
        self.api_key = os.getenv("SUPADATA_API_KEY")
        self.use_mock = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
        self.base_url = "https://api.supadata.ai/v1/youtube/transcript" # Example endpoint

    def get_transcript(self, url: str) -> str:
        """
        Retrieves the transcript for a given video URL.
        """
        print(f"[Clipper] Processing URL: {url}")
        
        if self.use_mock:
            print("[Clipper] Using MOCK data mode.")
            if "python" in url.lower() or "excel" in url.lower():
                return MOCK_TRANSCRIPT_PYTHON
            return MOCK_TRANSCRIPT_GENERIC

        if not self.api_key:
            raise ValueError("SUPADATA_API_KEY is not set in .env file.")

        # Real API call implementation (Example)
        try:
            params = {"url": url, "text": True}
            headers = {"x-api-key": self.api_key}
            response = requests.get(self.base_url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get("content", "")
        except Exception as e:
            print(f"[Clipper] Error fetching transcript: {e}")
            raise e
