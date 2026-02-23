import requests
from bs4 import BeautifulSoup
import re
import asyncio

def fetch_and_clean_url(url: str) -> str:
    """
    Fetches text from a URL and cleans it, removing boilerplate.
    Returns limited character set to avoid context window explosion.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        for element in soup(["script", "style", "meta", "noscript"]):
            element.extract()

        text = soup.get_text(separator=" ")
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text[:4000]

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch {url}: {str(e)}")
        return ""

async def fetch_and_clean_url_async(url: str) -> str:
    """
    Async wrapper for FastAPI compatibility.
    """
    return await asyncio.to_thread(fetch_and_clean_url, url)
