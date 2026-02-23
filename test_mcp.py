import asyncio
import time
from tools.mcp_client import mcp_fetch_url

async def test():
    urls = [
        "https://elizabethnorman.com/about",
        "https://elizabethnorman.com/jobs/data-strategy-manager-in-london-jid-72a3"
    ]
    for url in urls:
        print(f"Testing MCP connection for {url}...")
        t0 = time.time()
        try:
            text = await mcp_fetch_url(url)
            print(f"Success! Fetched {len(text)} chars.")
            print(f"First 100 chars: {text[:100]}")
        except Exception as e:
            print(f"Error: {e}")
        print(f"Time taken: {time.time() - t0:.2f} seconds\n")

if __name__ == "__main__":
    asyncio.run(test())
