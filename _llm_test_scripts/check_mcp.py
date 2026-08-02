try:
    import mcp.client.stdio

    print("mcp.client.stdio available")
except ImportError as e:
    print(f"mcp.client.stdio NOT available: {e}")

try:
    from mcp import ClientSession, StdioServerParameters

    print("ClientSession available")
except ImportError as e:
    print(f"ClientSession NOT available: {e}")
