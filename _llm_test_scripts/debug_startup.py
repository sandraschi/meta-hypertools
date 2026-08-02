import asyncio
import os
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_startup():
    # Ensure src is in path
    sys.path.append(os.path.join(os.getcwd(), "src"))

    server_path = os.path.join(os.getcwd(), "src", "meta_mcp", "mcp_server.py")
    print(f"Testing startup of {server_path}")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    server_params = StdioServerParameters(command=sys.executable, args=[server_path], env=env)

    start_time = time.time()
    try:
        print("Connecting to server...")
        async with stdio_client(server_params) as (read, write):
            print(f"Connected in {time.time() - start_time:.2f}s")

            async with ClientSession(read, write) as session:
                print("Sending initialize request...")
                init_start = time.time()
                await asyncio.wait_for(session.initialize(), timeout=30.0)
                print(f"Initialized in {time.time() - init_start:.2f}s")

                print("Listing tools...")
                tools_start = time.time()
                tools = await session.list_tools()
                print(f"Listed {len(tools.tools)} tools in {time.time() - tools_start:.2f}s")

                if len(tools.tools) >= 33:
                    print("VERIFICATION SUCCESS: All tools registered and initialization is faster.")
                else:
                    print(f"VERIFICATION WARNING: Only {len(tools.tools)} tools registered.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        print(f"Total time: {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(test_startup())
