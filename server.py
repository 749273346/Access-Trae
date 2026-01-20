from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import time
import uvicorn
from typing import Optional, Dict, Any
import sys
import uuid
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extractors import ContentExtractor
from src.refinery import ContentRefinery

app = FastAPI(title="Trae Smart Collector Server")

# Enable CORS for Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Modules
extractor = ContentExtractor()
refinery = ContentRefinery()

# Default Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SAVE_DIR = os.path.join(BASE_DIR, "materials")
if not os.path.exists(DEFAULT_SAVE_DIR):
    os.makedirs(DEFAULT_SAVE_DIR)

_tasks_lock = threading.Lock()
_tasks: Dict[str, Dict[str, Any]] = {}

class ClipRequest(BaseModel):
    url: str
    mode: str = "raw"  # "raw" or "ai_rewrite"
    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    save_path: Optional[str] = None

def _set_task(task_id: str, patch: dict):
    with _tasks_lock:
        cur = _tasks.get(task_id) or {}
        cur.update(patch)
        _tasks[task_id] = cur

def _is_auth_error(text: str) -> bool:
    t = (text or "").lower()
    return ("error code: 401" in t) or ("authentication fails" in t) or ("authentication_error" in t)

def process_and_save(task_id: str, request: ClipRequest):
    _set_task(task_id, {"status": "processing", "started_at": time.time()})
    print(f"[Server] Processing URL: {request.url} | Mode: {request.mode} | Task: {task_id}")
    
    try:
        raw_data = extractor.extract(request.url)
        final_url = raw_data.get('url') or request.url
        print(f"[Server] Final Extracted URL: {final_url} | Title: {raw_data.get('title')}")
        
        # 2. Refine / Rewrite
        final_content = refinery.refine_content(
            data=raw_data,
            mode=request.mode,
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url
        )
        warning = None
        if request.mode == "ai_rewrite" and _is_auth_error(final_content):
            final_content = refinery.refine_content(
                data=raw_data,
                mode="raw",
                model=request.model,
                api_key=request.api_key,
                base_url=request.base_url
            )
            warning = "AI 处理失败（API Key 无效或无权限），已自动降级为 Raw 保存。"

        metadata = refinery.generate_metadata(
            data=raw_data,
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url,
            use_ai=bool(request.api_key or os.getenv("OPENAI_API_KEY"))
        )
        
        category = metadata.get('category') or "其他"
        filename = metadata.get('filename') or f"{time.strftime('%Y%m%d')}_未命名内容.md"
        
        # 3. Save
        # Determine base root directory
        root_dir = DEFAULT_SAVE_DIR
        if request.save_path:
            try:
                os.makedirs(request.save_path, exist_ok=True)
                if os.path.isdir(request.save_path):
                    root_dir = request.save_path
            except Exception as e:
                print(f"[Server] Invalid save_path, falling back to default: {e}")

        # Create category subdirectory
        target_dir = os.path.join(root_dir, category)
        os.makedirs(target_dir, exist_ok=True)
        
        filepath = os.path.join(target_dir, filename)
        if os.path.exists(filepath):
            base, ext = os.path.splitext(filename)
            filepath = os.path.join(target_dir, f"{base}_{int(time.time())}{ext or '.md'}")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        print(f"[Server] Saved to: {filepath}")
        _set_task(task_id, {"status": "saved", "filepath": filepath, "warning": warning, "finished_at": time.time()})
        
    except Exception as e:
        print(f"[Server] Error processing task: {e}")
        _set_task(task_id, {"status": "error", "error": str(e), "finished_at": time.time()})

@app.post("/api/clip")
async def handle_clip(request: ClipRequest, background_tasks: BackgroundTasks):
    """
    Receives clip request, starts background processing, returns immediate success.
    """
    # Validation
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Add to background task to avoid blocking the extension
    task_id = str(uuid.uuid4())
    _set_task(task_id, {"status": "queued", "created_at": time.time(), "url": request.url, "mode": request.mode})
    background_tasks.add_task(process_and_save, task_id, request)
    
    return {"status": "queued", "task_id": task_id}

@app.get("/api/task/{task_id}")
async def get_task(task_id: str):
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.2"}

@app.get("/debug/toast", response_class=HTMLResponse)
async def debug_toast():
    return """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Toast 模拟</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; padding: 20px; }
      button { margin-right: 8px; margin-bottom: 8px; }
      #log { white-space: pre-wrap; background: #111; color: #ddd; padding: 12px; border-radius: 8px; min-height: 120px; }
    </style>
  </head>
  <body>
    <h2>极简律动漏斗提示 - 预览模拟</h2>
    <div>
      <button id="btnStart">开始模拟轮询 setToast(900ms)</button>
      <button id="btnStop">停止轮询</button>
      <button id="btnWheel">模拟滚轮切换视频(抑制并移除)</button>
      <button id="btnNav">模拟 pushState 导航(抑制并移除)</button>
      <button id="btnClear">清除抑制(允许再次显示)</button>
    </div>
    <div style="margin: 12px 0;">
      当前抑制状态: <b id="suppressed">0</b> | animationDuration: <b id="dur">-</b>
    </div>
    <div id="log"></div>

    <script>
      const toastId = "trae-processing-toast";
      const styleId = "trae-toast-styles";
      const logEl = document.getElementById("log");
      const suppressedEl = document.getElementById("suppressed");
      const durEl = document.getElementById("dur");

      const log = (s) => {
        const t = new Date().toISOString().slice(11, 23);
        logEl.textContent = `[${t}] ${s}\\n` + logEl.textContent;
      };

      const setSuppressed = (v) => {
        document.documentElement.dataset.traeToastSuppressed = v ? "1" : "0";
        suppressedEl.textContent = document.documentElement.dataset.traeToastSuppressed || "0";
      };

      const removeToastNow = () => {
        const t = document.getElementById(toastId);
        if (t) t.remove();
      };

      const ensureStyle = () => {
        const styleText = `
          @keyframes traeSlideIn {
            from { transform: translateY(-20px) scale(0.8); opacity: 0; }
            to { transform: translateY(0) scale(1); opacity: 1; }
          }
          @keyframes traeFadeOut {
            from { opacity: 1; transform: scale(1); }
            to { opacity: 0; transform: scale(0.8); }
          }
          @keyframes traePulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.15); opacity: 0.8; }
            100% { transform: scale(1); opacity: 1; }
          }
          .trae-toast {
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 2147483647;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
          }
          .trae-toast-icon { width: 32px; height: 32px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2)); }
          .trae-toast-icon svg { width: 100%; height: 100%; }
          .trae-toast.show { animation: traeSlideIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
          .trae-toast.hiding { animation: traeFadeOut 0.3s ease forwards; }
          .trae-icon-loading { color: #3b82f6; }
          .trae-pulse { animation: traePulse 1.5s infinite ease-in-out; }
        `;
        let style = document.getElementById(styleId);
        if (!style) {
          style = document.createElement("style");
          style.id = styleId;
          document.head.appendChild(style);
        }
        if (style.textContent !== styleText) style.textContent = styleText;
      };

      const icons = {
        loading: `<svg class="trae-icon-loading trae-pulse" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
          <path d="M10 18H14V16H10V18ZM3 6V8H21V6H3ZM6 13H18V11H6V13Z" />
        </svg>`
      };

      function setToast({ type = "loading" } = {}) {
        const suppressed = document.documentElement?.dataset?.traeToastSuppressed === "1";
        if (suppressed) {
          removeToastNow();
          return;
        }

        ensureStyle();

        let toast = document.getElementById(toastId);
        if (!toast) {
          toast = document.createElement("div");
          toast.id = toastId;
          toast.className = "trae-toast";
          toast.innerHTML = `<div class="trae-toast-icon"></div>`;
          document.body.appendChild(toast);
        }

        const iconEl = toast.querySelector(".trae-toast-icon");
        const nextType = icons[type] ? type : "loading";
        if (toast.dataset.traeToastType !== nextType) {
          toast.dataset.traeToastType = nextType;
          iconEl.innerHTML = icons[nextType];

          const svg = iconEl.querySelector("svg");
          if (svg) {
            durEl.textContent = getComputedStyle(svg).animationDuration || "-";
            let last = null;
            svg.addEventListener("animationiteration", () => {
              const now = performance.now();
              if (last != null) log(`animationiteration Δ ${(now - last).toFixed(0)}ms`);
              last = now;
            });
          }
        }

        toast.classList.remove("hiding");
        toast.classList.add("show");
      }

      setSuppressed(0);
      setToast();

      let timer = null;
      document.getElementById("btnStart").onclick = () => {
        if (timer) return;
        log("开始 900ms 轮询调用 setToast()");
        timer = setInterval(() => setToast({ type: "loading" }), 900);
      };
      document.getElementById("btnStop").onclick = () => {
        if (!timer) return;
        clearInterval(timer);
        timer = null;
        log("停止轮询");
      };
      document.getElementById("btnWheel").onclick = () => {
        setSuppressed(1);
        removeToastNow();
        window.dispatchEvent(new WheelEvent("wheel", { deltaY: 120 }));
        log("模拟滚轮切换：已抑制并移除（后续轮询不应再出现）");
      };
      document.getElementById("btnNav").onclick = () => {
        setSuppressed(1);
        removeToastNow();
        history.pushState({}, "", "#video=" + Math.random().toString(16).slice(2));
        log("模拟 pushState：已抑制并移除（后续轮询不应再出现）");
      };
      document.getElementById("btnClear").onclick = () => {
        setSuppressed(0);
        setToast();
        log("清除抑制：允许再次显示");
      };
    </script>
  </body>
</html>"""

if __name__ == "__main__":
    host = os.getenv("TRAE_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("TRAE_SERVER_PORT", "18000"))
    reload_enabled = os.getenv("TRAE_RELOAD", "").lower() in ("1", "true", "yes", "y")
    print(f"Server starting on http://{host}:{port}")
    print(f"Default save directory: {DEFAULT_SAVE_DIR}")
    if reload_enabled:
        uvicorn.run("server:app", host=host, port=port, reload=True)
    else:
        uvicorn.run(app, host=host, port=port)
