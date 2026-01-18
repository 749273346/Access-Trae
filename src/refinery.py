import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ContentRefinery:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.use_mock = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
        
        if not self.use_mock and self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def refine_content(self, transcript: str, type: str = "tutorial") -> str:
        """
        Process the transcript using LLM to generate structured markdown.
        """
        print(f"[Refinery] Refining content as type: {type}")

        if self.use_mock:
            print("[Refinery] Using MOCK LLM response.")
            return self._get_mock_response(type)

        if not self.client:
             raise ValueError("OPENAI_API_KEY is not set and mock mode is disabled.")

        prompt = self._build_prompt(transcript, type)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo", # Or gpt-4
                messages=[
                    {"role": "system", "content": "You are an expert technical writer and developer."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[Refinery] Error calling LLM: {e}")
            raise e

    def _build_prompt(self, transcript: str, type: str) -> str:
        base_prompt = f"""
        Analyze the following video transcript and convert it into a structured Markdown document.
        
        Transcript:
        {transcript[:4000]}... (truncated if too long)
        
        """
        
        if type == "tutorial":
            base_prompt += """
            Focus on extracting code snippets and step-by-step instructions.
            Format Requirements:
            - Title: Derive a suitable title.
            - Summary: Brief overview (TL;DR).
            - Code: Use correct language blocks (e.g., ```python).
            - Steps: Numbered list of actions.
            """
        else:
            base_prompt += """
            Focus on key concepts and takeaways.
            Format Requirements:
            - Title: Derive a suitable title.
            - Summary: Brief overview.
            - Key Points: Bullet points of main ideas.
            """
            
        return base_prompt

    def _get_mock_response(self, type: str) -> str:
        if type == "tutorial":
            return """
# Automate Excel with Python

## Summary
This tutorial explains how to use the `pandas` library to read, filter, and save Excel files programmatically.

## Prerequisites
- Python installed
- `pandas` library (`pip install pandas`)

## Code Implementation

```python
import pandas as pd

# 1. Read the Excel file
data = pd.read_excel('data.xlsx')
print("Initial Data:")
print(data.head())

# 2. Filter data where 'Sales' > 100
filtered_data = data[data['Sales'] > 100]

# 3. Save to a new Excel file
filtered_data.to_excel('output.xlsx', index=False)
```

## Steps
1.  Install pandas.
2.  Load your excel file.
3.  Apply filtering logic.
4.  Export the results.
"""
        else:
            return """
# Productivity Tips

## Summary
Key strategies to improve focus and productivity.

## Key Points
- **Pomodoro Technique**: Work 25m, Rest 5m.
- **Time Blocking**: Schedule specific blocks for specific tasks.
"""
