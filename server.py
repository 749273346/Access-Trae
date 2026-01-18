from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import time
import uvicorn
from typing import Optional

app = FastAPI(title="Trae-Doubao Bridge Server")

# Enable CORS to allow requests from Tampermonkey script (running on any domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Configuration
MATERIALS_DIR = os.path.abspath("materials")
if not os.path.exists(MATERIALS_DIR):
    os.makedirs(MATERIALS_DIR)

class ClipRequest(BaseModel):
    content: str
    url: Optional[str] = None
    title: Optional[str] = "Doubao_Clip"

@app.post("/api/clip")
async def save_clip(clip: ClipRequest):
    try:
        timestamp = int(time.time())
        # Sanitize title
        safe_title = "".join([c for c in clip.title if c.isalnum() or c in (' ', '-', '_')]).strip()
        safe_title = safe_title.replace(" ", "_") or "Doubao_Clip"
        
        filename = f"{safe_title}_{timestamp}.md"
        filepath = os.path.join(MATERIALS_DIR, filename)
        
        # Format content
        markdown_content = f"""# {clip.title}

**Source URL**: {clip.url or 'N/A'}
**Date**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}

---

{clip.content}
"""
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        print(f"[Server] Saved clip to: {filepath}")
        return {"status": "success", "filepath": filepath, "filename": filename}
        
    except Exception as e:
        print(f"[Server] Error saving clip: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok", "materials_dir": MATERIALS_DIR}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
