import os
import sys
import logging
from urllib.parse import urlparse

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
    test_links()
