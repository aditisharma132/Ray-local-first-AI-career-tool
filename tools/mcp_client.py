import asyncio
import re
from typing import Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPWebScraper:
    def __init__(self):
        # We use npx to run the official Puppeteer MCP server.
        # This will spin up a headless browser automatically.
        self.server_params = StdioServerParameters(
            command="npx.cmd",
            args=["-y", "@modelcontextprotocol/server-puppeteer"],
            env=None
        )
    
    async def _raw_fetch(self, url: str) -> str:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.call_tool("puppeteer_navigate", arguments={"url": url})
                js_script = "document.body.innerText"
                result = await session.call_tool(
                    "puppeteer_evaluate", 
                    arguments={"script": js_script}
                )
                if result.isError:
                    raise Exception(f"MCP Tool Error: Failed to extract text from {url}")
                output = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                text = re.sub(r'\s+', ' ', output).strip()
                return text[:4000]

    async def fetch_url(self, url: str) -> str:
        """
        Connects to the Puppeteer MCP server with a hard timeout to prevent deadlocks.
        """
        try:
            return await asyncio.wait_for(self._raw_fetch(url), timeout=25.0)
        except asyncio.TimeoutError:
            print(f"MCP Fetch timed out for {url}, returning empty.")
            return ""
        except Exception as e:
            print(f"MCP Client Error fetching {url}: {str(e)}")
            return ""

# Global singleton for efficiency if reused
_scraper = MCPWebScraper()

async def mcp_fetch_url(url: str) -> str:
    """Wrapper to fetch a URL using the async MCP client."""
    return await _scraper.fetch_url(url)

