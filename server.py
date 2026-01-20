from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import time
import uvicorn
from typing import Optional
import sys

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
DEFAULT_SAVE_DIR = os.path.join(os.getcwd(), "materials")
if not os.path.exists(DEFAULT_SAVE_DIR):
    os.makedirs(DEFAULT_SAVE_DIR)

class ClipRequest(BaseModel):
    url: str
    mode: str = "raw"  # "raw" or "ai_rewrite"
    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    save_path: Optional[str] = None

def process_and_save(request: ClipRequest):
    print(f"[Server] Processing URL: {request.url} | Mode: {request.mode}")
    
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

        metadata = refinery.generate_metadata(
            data=raw_data,
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url,
            use_ai=True
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
        
    except Exception as e:
        print(f"[Server] Error processing task: {e}")
        # Optionally write an error log file

@app.post("/api/clip")
async def handle_clip(request: ClipRequest, background_tasks: BackgroundTasks):
    """
    Receives clip request, starts background processing, returns immediate success.
    """
    # Validation
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Add to background task to avoid blocking the extension
    background_tasks.add_task(process_and_save, request)
    
    return {"status": "queued", "message": "Task started in background"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.1"}

if __name__ == "__main__":
    print(f"Server starting on http://localhost:18000")
    print(f"Default save directory: {DEFAULT_SAVE_DIR}")
    uvicorn.run(app, host="127.0.0.1", port=18000)
