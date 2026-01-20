import os
import re
import json
import datetime
from openai import OpenAI
from typing import Optional

class ContentRefinery:
    def __init__(self):
        # Default environment key as fallback
        self.default_api_key = os.getenv("OPENAI_API_KEY")
        self.default_base_url = os.getenv("OPENAI_BASE_URL")
        self.allowed_categories = [
            "AI科技",
            "体育",
            "影视",
            "财经",
            "政治",
            "编程",
            "其他"
        ]
        self.category_aliases = {
            "ai_tech": "AI科技",
            "ai-tech": "AI科技",
            "aitech": "AI科技",
            "ai": "AI科技",
            "tech": "AI科技",
            "人工智能": "AI科技",
            "大模型": "AI科技",
            "sports": "体育",
            "sport": "体育",
            "体育": "体育",
            "movies": "影视",
            "movie": "影视",
            "film": "影视",
            "tv": "影视",
            "影视": "影视",
            "finance": "财经",
            "fin": "财经",
            "财经": "财经",
            "politics": "政治",
            "political": "政治",
            "政治": "政治",
            "coding": "编程",
            "code": "编程",
            "programming": "编程",
            "编程": "编程",
            "others": "其他",
            "other": "其他",
            "misc": "其他",
            "其他": "其他"
        }

    def refine_content(self, 
                       data: dict, 
                       mode: str = "raw", 
                       model: str = "gpt-3.5-turbo", 
                       api_key: Optional[str] = None,
                       base_url: Optional[str] = None) -> str:
        """
        Refine content based on mode.
        data: dict from ContentExtractor (title, content, source_type, etc.)
        """
        print(f"[Refinery] Processing mode: {mode}, Model: {model}")

        # 1. RAW MODE: Just format as Markdown
        if mode == "raw":
            return self._format_raw_markdown(data)

        # 2. AI REWRITE MODE
        if mode == "ai_rewrite":
            return self._ai_rewrite(data, model, api_key, base_url)
        
        return self._format_raw_markdown(data)

    def generate_metadata(self,
                         data: dict,
                         model: str = "gpt-3.5-turbo",
                         api_key: Optional[str] = None,
                         base_url: Optional[str] = None,
                         use_ai: bool = False) -> dict:
        """
        Generate smart metadata (filename, category) using AI.
        Returns a dict with 'filename' and 'category'.
        """
        if not use_ai:
            return self._rule_based_metadata(data)

        # Resolve Key/URL
        client_api_key = api_key or self.default_api_key
        client_base_url = base_url or self.default_base_url
        
        if model.startswith("deepseek"):
            client_base_url = client_base_url or "https://api.deepseek.com/v1"
        elif model == "ollama":
             client_base_url = client_base_url or "http://localhost:11434/v1"
             client_api_key = "ollama" # Dummy key
        
        if not client_api_key and model != "ollama":
            return self._rule_based_metadata(data)

        try:
            client = OpenAI(api_key=client_api_key, base_url=client_base_url)
            
            # Prepare prompt for JSON output
            today_str = datetime.datetime.now().strftime("%Y%m%d")
            content_snippet = data.get('content', '')[:2000]
            
            prompt = f"""
Analyze the following content and generate metadata in JSON format.

Input Content:
- Title: {data.get('title')}
- URL: {data.get('url')}
- Content Snippet: {content_snippet}

Output Requirements:
1. category: 必须严格从以下列表中选择一个（用于创建同名文件夹）：[AI科技, 体育, 影视, 财经, 政治, 编程, 其他]。
   - AI科技：AI、LLM、大模型、科技趋势与行业动态
   - 体育：比赛、球员、训练、赛事分析
   - 影视：电影/剧集评论、娱乐行业动态
   - 财经：宏观经济、投资、股票、企业与商业
   - 政治：政策、选举、政经热点与分析
   - 编程：开发教程、工程实践、代码相关
   - 其他：无法归入以上类别
2. filename: 文件名必须是中文，格式为 "{today_str}_主题.md"。
   - 忽略标题党/夸张表述，必须根据内容片段提炼核心主题重命名。
   - 不要包含任何非法文件名字符（如 \\ / : * ? \" < > |）。
   - 尽量简短（建议 8-24 个汉字），不超过 60 字符（不含扩展名）。
   - 示例："{today_str}_DeepSeek架构解析.md" 或 "{today_str}_宏观经济走势解读.md"

Response Format:
Return ONLY a valid JSON object, no markdown, no extra text:
{{"category":"...","filename":"..."}}
""".strip()
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个精明的内容管理员：必须严格按内容分类，并用中文生成文件名与分类。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            result_text = (response.choices[0].message.content or "").strip()
            metadata = self._extract_json_object(result_text)
            
            # Validate output
            if not metadata.get('filename') or not metadata.get('category'):
                raise ValueError("Incomplete JSON from AI")
                
            # Sanitize filename just in case
            metadata['filename'] = self._sanitize_filename(metadata['filename'])
            normalized_category = self._normalize_category(metadata.get("category"))
            if normalized_category not in self.allowed_categories:
                raise ValueError("Invalid category from AI")
            metadata['category'] = normalized_category
            if not metadata['filename'].lower().endswith(".md"):
                metadata['filename'] = f"{metadata['filename']}.md"
            today_str = datetime.datetime.now().strftime("%Y%m%d")
            if not metadata['filename'].startswith(today_str):
                metadata['filename'] = f"{today_str}_{metadata['filename']}"
            
            return metadata
            
        except Exception as e:
            print(f"[Refinery] Metadata Gen Error: {e}")
            return self._rule_based_metadata(data)

    def _normalize_category(self, category: Optional[str]) -> str:
        raw = (category or "").strip()
        if not raw:
            return "其他"
        key = raw.lower()
        key = re.sub(r"\s+", "", key)
        mapped = self.category_aliases.get(key)
        if mapped:
            return mapped
        raw_clean = self._sanitize_path_segment(raw)
        if raw_clean in self.allowed_categories:
            return raw_clean
        return raw_clean

    def _rule_based_metadata(self, data: dict) -> dict:
        """Fallback when AI fails or is not configured"""
        url = (data.get('url') or '').lower()
        title = data.get('title') or 'Untitled'
        content = data.get('content') or ''
        blob = f"{title}\n{content}".lower()
        today_str = datetime.datetime.now().strftime("%Y%m%d")
        
        # Simple Rule Engine
        category = "其他"
        if re.search(r"\bai\b", blob) or any(k in blob for k in ["llm", "chatgpt", "deepseek", "transformer", "machine learning", "大模型", "人工智能", "科技"]):
            category = "AI科技"
        elif any(k in blob for k in ["sports", "football", "soccer", "nba", "fifa", "olympic", "体育", "足球", "篮球", "赛事", "奥运"]):
            category = "体育"
        elif any(k in blob for k in ["movie", "film", "tv", "series", "box office", "trailer", "电影", "影视", "剧集", "票房", "导演", "演员"]):
            category = "影视"
        elif any(k in blob for k in ["finance", "stock", "market", "investment", "economy", "crypto", "interest rate", "inflation", "财经", "股票", "基金", "投资", "经济", "美联储", "通胀", "利率"]):
            category = "财经"
        elif any(k in blob for k in ["politics", "election", "policy", "government", "congress", "parliament", "政治", "政策", "选举", "政府", "国会", "议会"]):
            category = "政治"
        elif any(k in blob for k in ["python", "javascript", "typescript", "java", "golang", "rust", "api", "bug", "debug", "编程", "代码", "教程", "开发", "算法", "git"]):
            category = "编程"
        elif any(x in url for x in ['github.com', 'stackoverflow.com', 'pypi.org']):
            category = "编程"
            
        # Safe Filename
        topic = self._guess_topic(title, content)
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", topic or "")
        if len(chinese_chars) < 4:
            topic = f"{category}素材" if category != "其他" else "通用素材"
        safe_title = self._sanitize_filename(topic)[:50]
        filename = f"{today_str}_{safe_title}.md"
        
        return {
            "category": category,
            "filename": filename
        }

    def _sanitize_path_segment(self, name: str) -> str:
        s = (name or "").strip()
        s = re.sub(r"[<>:\"/\\\\|?*\\x00-\\x1F]", "", s)
        s = re.sub(r"\\s+", "_", s).strip(" .")
        s = re.sub(r"_+", "_", s)
        return s

    def _sanitize_filename(self, name: str) -> str:
        s = self._sanitize_path_segment(name)
        s = "".join([c for c in s if c.isalnum() or c in ('-', '_', '.')]).strip(" .")
        s = re.sub(r"_+", "_", s).strip("_")
        if not s:
            s = "未命名"
        upper = s.upper()
        if upper in {"CON", "PRN", "AUX", "NUL"} or re.match(r"^COM\\d+$", upper) or re.match(r"^LPT\\d+$", upper):
            s = f"文件_{s}"
        return s[:80]

    def _guess_topic(self, title: str, content: str) -> str:
        title = (title or "").strip()
        content = (content or "").strip()
        
        # Priority 1: Use title if it's substantial and not generic
        if title and len(title) > 4 and not any(x in title for x in ["抖音", "Bilibili", "YouTube", "Untitled"]):
            return title
            
        # Priority 2: Try to find a good Chinese sequence in content or title
        text = content or title
        text = re.sub(r"\s+", "", text)
        text = re.sub(r"[#*_`\[\]()>\-—–~|]", "", text)
        
        # Look for a meaningful Chinese phrase (at least 4 chars)
        m = re.search(r"[\u4e00-\u9fff]{4,30}", text)
        if m:
            return m.group(0)
            
        return title[:30] or text[:30] or "未命名内容"

    def _extract_json_object(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            pass

        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError("No JSON object found in AI response")
        return json.loads(m.group(0))

    def _format_raw_markdown(self, data: dict) -> str:
        return f"""# {data.get('title', 'Untitled')}

**来源**：{data.get('url', 'N/A')}
**日期**：{data.get('publish_date', 'N/A')}
**作者**：{data.get('author', 'N/A')}

---

{data.get('content', '')}
"""

    def _ai_rewrite(self, data: dict, model: str, api_key: str, base_url: str) -> str:
        # Resolve Key/URL
        client_api_key = api_key or self.default_api_key
        client_base_url = base_url or self.default_base_url
        
        if model.startswith("deepseek"):
            client_base_url = client_base_url or "https://api.deepseek.com/v1"
        elif model == "ollama":
             client_base_url = client_base_url or "http://localhost:11434/v1"
             client_api_key = "ollama" # Dummy key
        
        if not client_api_key and model != "ollama":
             return f"# AI 改写失败\n\n缺少 API Key，无法进行 AI 改写。请在插件设置中填写 Key（或切换到 Raw 模式）。\n\n---\n\n{self._format_raw_markdown(data)}"

        try:
            client = OpenAI(api_key=client_api_key, base_url=client_base_url)
            
            prompt = self._build_blog_prompt(data)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是资深中文专栏作家与编辑，擅长把零散素材写成可直接发布的精明博客文章。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"[Refinery] AI Error: {e}")
            safe_error = self._sanitize_error(str(e), client_api_key)
            return f"# AI 处理异常\n\n{safe_error}\n\n---\n\n{self._format_raw_markdown(data)}"

    def _sanitize_error(self, message: str, api_key: Optional[str]) -> str:
        msg = message or "Unknown error"
        msg = re.sub(r"sk-[A-Za-z0-9]{12,}", "sk-***", msg)
        if api_key:
            msg = msg.replace(api_key, "***")
        msg = re.sub(r"(api key:)\s*[^\\s]+", r"\1 ***", msg, flags=re.IGNORECASE)
        return msg

    def _build_blog_prompt(self, data: dict) -> str:
        source_type = data.get('source_type', 'article')
        content = data.get('content', '')[:15000] # Truncate to avoid context limit if too huge
        
        base_prompt = f"""
请将以下原始内容改写成一篇“可直接发布的中文精明博客文章”。

**元信息**：
- 原标题：{data.get('title')}
- 内容类型：{source_type}

**硬性要求**：
1. **语言**：无论原文是什么语言，最终输出必须为中文。
2. **定位**：资深专栏作家/行业分析师视角，强调洞察与判断，而不是流水账摘要。
3. **结构**：必须包含清晰的二级标题（H2），建议包含“背景/核心观点/影响与启示/结论”。
4. **少代码**：不要输出大量代码。除非是明确的“编程教程”，否则最多给 1 个短小代码块作为示例，且必须解释其用途。
5. **可用性**：输出应像一份可直接复用的素材：观点明确、要点可复制、段落短、可读性强。
6. **事实与边界**：如果原文信息不足，明确用“可能/推测/不确定”表达，不要编造具体数据或结论。
7. **篇幅**：建议 800-1600 字，重点突出。

**原始内容**：
{content}
"""
        return base_prompt
