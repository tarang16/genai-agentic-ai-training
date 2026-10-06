"""Talk to the TriageDesk MCP server from plain Python, the same way a desktop MCP client does.

    python mcp_client_demo.py

Launches mcp_server.py as a subprocess over stdio, lists its tools, and runs a search.
No LLM and no API key involved: MCP is just a protocol for tools.
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

SERVER = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("mcp_server.py"))])


async def main() -> None:
    async with Client(SERVER) as client:
        tools = await client.list_tools()
        print("Tools offered by the server:")
        for t in tools.tools:
            print(f"  - {t.name}: {(t.description or '').splitlines()[0]}")

        result = await client.call_tool("search_past_tickets", {"query": "monitor switches off after 10 minutes", "product": "VX2780"})
        print("\nsearch_past_tickets -> top hits:")
        for block in result.content:
            for hit in json.loads(block.text) if block.text.lstrip().startswith("[") else [json.loads(block.text)]:
                print(f"  {hit['id']:10} score={hit['score']:<6} links={hit['links']}  {hit['title']}")


if __name__ == "__main__":
    asyncio.run(main())
