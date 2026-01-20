import os
import sys
import logging
from urllib.parse import urlparse
import time
import json

import requests

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
try:
    from extractors import ContentExtractor
except ImportError:
    print("Error: Could not import src.extractors. Make sure you are running this script from the 'Access Trae' directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_links():
    print("=========================================")
    print("   Trae Collector - Network Diagnosis    ")
    print("=========================================")
    print("This script checks if the collector can access key websites.")
    print("Please ensure your VPN is ON if you are testing foreign sites.\n")

    extractor = ContentExtractor()
    
    test_urls = [
        ("Web Article (Example.com)", "https://www.example.com"),
        ("YouTube (Google Service)", "https://www.youtube.com/watch?v=jNQXAC9IVRw"), 
        ("Bilibili (Domestic)", "https://www.bilibili.com/video/BV1GJ411x7h7"), 
    ]
    
    results = []

    for name, url in test_urls:
        print(f"Testing: {name}...")
        try:
            result = extractor.extract(url)
            title = result.get('title', 'No Title')
            content_len = len(result.get('content', ''))
            
            if content_len > 0:
                print(f"  [OK] Success! Title: {title} ({content_len} chars)")
                results.append((name, "PASS"))
            else:
                print(f"  [WARN] Extracted but content is empty.")
                results.append((name, "WARN (Empty)"))
                
        except Exception as e:
            print(f"  [FAIL] Error: {str(e)[:100]}...")
            results.append((name, "FAIL"))
            
    print("\n=========================================")
    print("             Diagnosis Summary           ")
    print("=========================================")
    for name, status in results:
        print(f"{name}: {status}")
    
    print("\nIf YouTube fails but Bilibili passes, check your VPN/Proxy settings.")

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "stress":
        server_url = os.getenv("TRAE_SERVER_URL", "http://127.0.0.1:18000").rstrip("/")
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 15
        urls = [
            "https://www.douyin.com/video/7597313245792686922",
            "https://www.douyin.com/video/7592899939764653348",
            "https://www.example.com"
        ]

        print("=========================================")
        print("   Trae Collector - Stress Test (HTTP)   ")
        print("=========================================")
        print(f"Server: {server_url}")
        try:
            r = requests.get(f"{server_url}/health", timeout=5)
            r.raise_for_status()
            print("Health:", r.json())
        except Exception as e:
            print("Error: server is not reachable:", str(e))
            sys.exit(2)

        ok = 0
        warn = 0
        fail = 0

        for i in range(n):
            url = urls[i % len(urls)]
            mode = "ai_rewrite" if (i % 2 == 0) else "raw"
            payload = {
                "url": url,
                "mode": mode,
                "model": "gpt-3.5-turbo",
                "api_key": "invalid_key_for_stress_test",
                "base_url": ""
            }

            try:
                resp = requests.post(f"{server_url}/api/clip", json=payload, timeout=10)
                resp.raise_for_status()
                task_id = (resp.json() or {}).get("task_id")
                if not task_id:
                    raise RuntimeError("No task_id returned")

                deadline = time.time() + 60
                last = None
                while time.time() < deadline:
                    st = requests.get(f"{server_url}/api/task/{task_id}", timeout=10)
                    st.raise_for_status()
                    last = st.json()
                    if last.get("status") in ("saved", "error"):
                        break
                    time.sleep(0.8)

                if not last or last.get("status") not in ("saved", "error"):
                    raise RuntimeError("Timeout waiting for task result")

                if last.get("status") == "saved":
                    if last.get("warning"):
                        warn += 1
                        print(f"[WARN] {i+1}/{n} saved with warning: {last.get('warning')}")
                    else:
                        ok += 1
                        print(f"[OK] {i+1}/{n} saved")
                else:
                    fail += 1
                    print(f"[FAIL] {i+1}/{n} error: {last.get('error')}")

            except Exception as e:
                fail += 1
                print(f"[FAIL] {i+1}/{n} request failed: {str(e)[:160]}")

        print("\n=========================================")
        print("                Stress Summary           ")
        print("=========================================")
        print("Saved:", ok)
        print("Saved with warning:", warn)
        print("Failed:", fail)
    else:
        test_links()
