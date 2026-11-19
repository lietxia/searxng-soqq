
import asyncio, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(
        command="uvx",
        args=["--from","git+https://github.com/27Aaron/yuanban_so_mcp.git","yuanban_so_mcp"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as sess:
            await sess.initialize()
            tools = await sess.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])
            # call web_search
            try:
                res = await sess.call_tool("web_search", {"query":"惠州市天气"})
                txt = res.content[0].text if res.content else ""
                print("CALL web_search OK, result preview:")
                print(txt[:800])
            except Exception as e:
                print("CALL ERR:", repr(e))

asyncio.run(main())
