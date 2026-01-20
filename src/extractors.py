import json
import re
import time
from dataclasses import dataclass
from newspaper import Article, Config
from youtube_transcript_api import YouTubeTranscriptApi
import requests
from urllib.parse import urlparse, parse_qs
from urllib.parse import unquote

class ContentExtractor:
    def __init__(self, request_timeout_s: int = 20):
        self.request_timeout_s = request_timeout_s

    def _newspaper_config(self) -> Config:
        cfg = Config()
        cfg.request_timeout = self.request_timeout_s
        cfg.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        return cfg

    def extract(self, url: str) -> dict:
        """
        Main entry point. Detects URL type and dispatches to specific extractor.
        """
        domain = urlparse(url).netloc.lower()
        
        if "youtube.com" in domain or "youtu.be" in domain:
            return self._extract_youtube(url)
        if "bilibili.com" in domain:
            return self._extract_bilibili(url)
        if "douyin.com" in domain or "iesdouyin.com" in domain:
            return self._extract_douyin(url)
        else:
            return self._extract_web(url)

    def _extract_youtube(self, url: str) -> dict:
        try:
            video_id = self._get_youtube_id(url)
            if not video_id:
                raise ValueError("Could not extract YouTube Video ID")
            
            # 1. Get Transcript
            try:
                api = YouTubeTranscriptApi()
                fetched = api.fetch(video_id, languages=['zh-Hans', 'zh-Hant', 'en'])
                transcript_list = fetched.to_raw_data()
                # Formatter
                text_content = ""
                for item in transcript_list:
                    text_content += f"{item['text']} "
                
                has_transcript = True
            except Exception as e:
                print(f"[Extractor] YouTube transcript failed: {e}")
                text_content = self._extract_youtube_captions_from_page(url)
                has_transcript = bool(text_content and not text_content.startswith("(No transcript"))

            # 2. Get Metadata (oEmbed; no API key required)
            title, author = self._extract_youtube_oembed(url)
            if not title:
                article = Article(url, config=self._newspaper_config())
                article.download()
                article.parse()
                title = article.title or f"YouTube Video ({video_id})"
                author = author or "YouTube Creator"
            
            return {
                "title": title,
                "content": text_content,
                "author": author or "YouTube Creator",
                "publish_date": None,
                "source_type": "video",
                "has_transcript": has_transcript,
                "url": url
            }
            
        except Exception as e:
            return {
                "title": "Error Extracting YouTube",
                "content": f"Failed to process YouTube video: {str(e)}",
                "source_type": "error",
                "url": url
            }

    def _extract_bilibili(self, url: str) -> dict:
        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://www.bilibili.com/"
            })
            bvid = self._get_bilibili_bvid(url)
            if not bvid:
                return {
                    "title": "Bilibili Video",
                    "content": "Could not extract Bilibili BV id from URL. Metadata only.",
                    "source_type": "video",
                    "has_transcript": False,
                    "url": url
                }

            view_api = "https://api.bilibili.com/x/web-interface/view"
            view_resp = session.get(view_api, params={"bvid": bvid}, timeout=20)
            view_resp.raise_for_status()
            view_json = view_resp.json()
            if view_json.get("code") != 0:
                raise ValueError(f"Bilibili view API error: {view_json.get('message')}")

            data = view_json.get("data") or {}
            title = data.get("title") or f"Bilibili Video ({bvid})"
            desc = data.get("desc") or ""
            owner = (data.get("owner") or {}).get("name") or None
            pubdate = data.get("pubdate")
            publish_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(pubdate)) if pubdate else None

            cid = None
            pages = data.get("pages") or []
            if pages and isinstance(pages, list):
                cid = pages[0].get("cid")

            transcript_text = ""
            has_transcript = False
            if cid:
                player_api = "https://api.bilibili.com/x/player/v2"
                player_resp = session.get(player_api, params={"bvid": bvid, "cid": cid}, timeout=20)
                player_resp.raise_for_status()
                player_json = player_resp.json()
                if player_json.get("code") == 0:
                    sub = ((player_json.get("data") or {}).get("subtitle") or {}).get("subtitles") or []
                    if sub:
                        sub_url = sub[0].get("subtitle_url") or ""
                        if sub_url.startswith("//"):
                            sub_url = "https:" + sub_url
                        if sub_url:
                            sub_resp = session.get(sub_url, timeout=20)
                            sub_resp.raise_for_status()
                            sub_json = sub_resp.json()
                            body = sub_json.get("body") or []
                            lines = []
                            for item in body:
                                txt = (item or {}).get("content")
                                if txt:
                                    lines.append(txt.strip())
                            transcript_text = "\n".join(lines).strip()
                            has_transcript = bool(transcript_text)

            if not has_transcript:
                try:
                    page_resp = session.get(url, timeout=20)
                    if page_resp.ok:
                        html = page_resp.text or ""
                        m = re.search(r"\"subtitle_url\":\"(.*?)\"", html)
                        if m:
                            raw = m.group(1)
                            sub_url = json.loads(f"\"{raw}\"")
                            if sub_url.startswith("//"):
                                sub_url = "https:" + sub_url
                            if sub_url:
                                sub_resp = session.get(sub_url, timeout=20)
                                sub_resp.raise_for_status()
                                sub_json = sub_resp.json()
                                body = sub_json.get("body") or []
                                lines = []
                                for item in body:
                                    txt = (item or {}).get("content")
                                    if txt:
                                        lines.append(txt.strip())
                                transcript_text = "\n".join(lines).strip()
                                has_transcript = bool(transcript_text)
                except Exception:
                    pass

            content = transcript_text or desc or "(No subtitle found; metadata only.)"

            return {
                "title": title,
                "content": content,
                "author": owner,
                "publish_date": publish_date,
                "source_type": "video",
                "has_transcript": has_transcript,
                "url": url
            }
        except Exception as e:
            return {
                "title": "Error Extracting Bilibili",
                "content": f"Failed to process Bilibili video: {str(e)}",
                "source_type": "error",
                "url": url
            }

    def _extract_douyin(self, url: str) -> dict:
        """
        Best-effort metadata extraction for Douyin. Subtitle extraction is not guaranteed.
        """
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query or "")
            modal_id = (qs.get("modal_id") or [None])[0]
            if modal_id and re.match(r"^\d+$", str(modal_id)) and not re.search(r"/video/\d+", parsed.path or ""):
                url = f"https://www.douyin.com/video/{modal_id}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
            resp = requests.get(url, headers=headers, timeout=25, allow_redirects=True)
            resp.raise_for_status()
            html = resp.text or ""

            title = self._extract_html_title(html) or "Douyin Video"
            desc = self._extract_meta_content(html, "description") or ""

            render_data = self._extract_render_data(html)
            if render_data:
                extracted = self._extract_douyin_from_render_data(render_data)
                title = extracted.title or title
                desc = extracted.desc or desc

            if not desc and not render_data:
                vid = self._get_douyin_video_id(resp.url) or self._get_douyin_video_id(url)
                if vid:
                    share_url = f"https://www.iesdouyin.com/share/video/{vid}"
                    mobile_headers = dict(headers)
                    mobile_headers["User-Agent"] = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                    share_resp = requests.get(share_url, headers=mobile_headers, timeout=25, allow_redirects=True)
                    if share_resp.ok:
                        share_html = share_resp.text or ""
                        title = self._extract_html_title(share_html) or title
                        desc = self._extract_meta_content(share_html, "description") or desc

            content = desc.strip() or "(Metadata only; transcript not available.)"

            return {
                "title": title,
                "content": content,
                "author": None,
                "publish_date": None,
                "source_type": "video",
                "has_transcript": False,
                "url": resp.url
            }
        except Exception as e:
            return {
                "title": "Error Extracting Douyin",
                "content": f"Failed to process Douyin link: {str(e)}",
                "source_type": "error",
                "url": url
            }

    def _extract_web(self, url: str) -> dict:
        try:
            article = Article(url, config=self._newspaper_config())
            article.download()
            article.parse()
            
            # Newspaper3k is great for text
            return {
                "title": article.title,
                "content": article.text,
                "author": ", ".join(article.authors) if article.authors else None,
                "publish_date": str(article.publish_date) if article.publish_date else None,
                "source_type": "article",
                "url": url
            }
        except Exception as e:
             return {
                "title": "Error Extracting Webpage",
                "content": f"Failed to process webpage: {str(e)}",
                "source_type": "error",
                "url": url
            }

    def _get_youtube_id(self, url: str):
        """
        Examples:
        - http://youtu.be/SA2iWivDJiE
        - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
        - http://www.youtube.com/embed/SA2iWivDJiE
        - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
        """
        query = urlparse(url)
        if query.hostname == 'youtu.be':
            return query.path[1:]
        if query.hostname in ('www.youtube.com', 'youtube.com'):
            if query.path == '/watch':
                p = parse_qs(query.query)
                return p['v'][0]
            if query.path[:7] == '/embed/':
                return query.path.split('/')[2]
            if query.path[:3] == '/v/':
                return query.path.split('/')[2]
        return None

    def _get_bilibili_bvid(self, url: str) -> str | None:
        m = re.search(r"/video/(BV[0-9A-Za-z]+)", url)
        if m:
            return m.group(1)
        return None

    def _get_douyin_video_id(self, url: str) -> str | None:
        m = re.search(r"/video/(\d+)", url)
        if m:
            return m.group(1)
        return None

    def _extract_youtube_oembed(self, url: str) -> tuple[str | None, str | None]:
        try:
            oembed = "https://www.youtube.com/oembed"
            r = requests.get(oembed, params={"url": url, "format": "json"}, timeout=15)
            if not r.ok:
                return (None, None)
            j = r.json()
            return (j.get("title"), j.get("author_name"))
        except Exception:
            return (None, None)

    def _extract_youtube_captions_from_page(self, url: str) -> str:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8"
            }
            r = requests.get(url, headers=headers, timeout=25)
            r.raise_for_status()
            html = r.text or ""

            m = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.*?\}?);", html, flags=re.DOTALL)
            if not m:
                # Try without trailing semicolon or different spacing
                m = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.*?\})", html, flags=re.DOTALL)
            if not m:
                return "(No transcript available for this video. Metadata only.)"
            player_text = m.group(1)
            # Handle potential escaping in some versions of the page
            if '\\"' in player_text:
                player_text = player_text.replace('\\"', '"').replace('\\\\', '\\')
            
            try:
                player = json.loads(player_text)
            except json.JSONDecodeError:
                # Last resort attempt to fix common JSON issues from regex
                try:
                    # If it has trailing garbage or incomplete
                    player = json.loads(player_text + "}")
                except:
                    return "(No transcript available for this video. Metadata only.)"
            tracks = (((player.get("captions") or {}).get("playerCaptionsTracklistRenderer") or {}).get("captionTracks") or [])
            if not tracks:
                return "(No transcript available for this video. Metadata only.)"

            preferred = None
            for lang in ("zh-Hans", "zh-CN", "zh", "en"):
                for t in tracks:
                    lc = (t.get("languageCode") or "").lower()
                    if lc.startswith(lang.lower()):
                        preferred = t
                        break
                if preferred:
                    break
            if not preferred:
                preferred = tracks[0]

            base_url = preferred.get("baseUrl")
            if not base_url:
                return "(No transcript available for this video. Metadata only.)"

            sep = "&" if "?" in base_url else "?"
            vtt_url = base_url + f"{sep}fmt=vtt"
            vtt = requests.get(vtt_url, headers=headers, timeout=25)
            vtt.raise_for_status()

            lines = []
            for line in (vtt.text or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("WEBVTT"):
                    continue
                if "-->" in line:
                    continue
                if re.match(r"^\d+$", line):
                    continue
                lines.append(line)

            out = "\n".join(lines).strip()
            return out or "(No transcript available for this video. Metadata only.)"
        except Exception as e:
            print(f"[Extractor] YouTube captionTracks fallback failed: {e}")
            return "(No transcript available for this video. Metadata only.)"

    def _extract_html_title(self, html: str) -> str | None:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        return title or None

    def _extract_meta_content(self, html: str, name: str) -> str | None:
        # e.g. <meta name="description" content="...">
        pattern = rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']'
        m = re.search(pattern, html, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip() or None
        return None

    @dataclass
    class _DouyinData:
        title: str | None = None
        desc: str | None = None

    def _extract_render_data(self, html: str) -> str | None:
        m = re.search(r'RENDER_DATA["\']?\s*:\s*["\']([^"\']+)["\']', html)
        if not m:
            return None
        return unquote(m.group(1))

    def _extract_douyin_from_render_data(self, decoded: str) -> "_DouyinData":
        try:
            data = json.loads(decoded)
        except Exception:
            return self._DouyinData()
        if not isinstance(data, dict):
            return self._DouyinData()

        for _, v in data.items():
            if not isinstance(v, dict):
                continue
            aweme = v.get("aweme") or v.get("awemeInfo") or v.get("aweme_detail") or v.get("awemeDetail")
            if isinstance(aweme, dict):
                title = aweme.get("desc") or None
                return self._DouyinData(title=title, desc=title)
        return self._DouyinData()
