"""python -m powerplan — run the powerplan MCP server on stdio."""

from powerplan.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
