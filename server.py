from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import time
import uvicorn
from typing import Optional
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
_tasks: dict[str, dict] = {}

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

if __name__ == "__main__":
    print(f"Server starting on http://localhost:18000")
    print(f"Default save directory: {DEFAULT_SAVE_DIR}")
    uvicorn.run(app, host="127.0.0.1", port=18000)
