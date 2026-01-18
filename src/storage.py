import os
import time

class StorageManager:
    def __init__(self, base_dir="materials"):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def save_markdown(self, content: str, title_hint: str = "untitled") -> str:
        """
        Saves the markdown content to a file. Returns the absolute path.
        """
        # Sanitize filename
        safe_title = "".join([c for c in title_hint if c.isalnum() or c in (' ', '-', '_')]).strip()
        safe_title = safe_title.replace(" ", "_")
        timestamp = int(time.time())
        filename = f"{safe_title}_{timestamp}.md"
        
        filepath = os.path.join(self.base_dir, filename)
        absolute_path = os.path.abspath(filepath)
        
        with open(absolute_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"[Storage] Saved file to: {absolute_path}")
        return absolute_path
