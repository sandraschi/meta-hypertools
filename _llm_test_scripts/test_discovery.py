import asyncio
import json
import os
import sys

# Ensure we can import meta_mcp
sys.path.append(os.path.join(os.getcwd(), "src"))

from meta_mcp.tools.client_integration import discover_clients


async def main():
    print("Running discover_clients()...")
    try:
        clients = await discover_clients()
        print(json.dumps(clients, indent=2, default=str))

        # Verify specific client configs manually to debug
        from meta_mcp.tools.client_integration import (
            CLIENT_CONFIGS,
            load_json_with_comments,
        )

        print("\n--- Manual Config Check ---")
        for client_id in ["claude", "cursor"]:
            path = CLIENT_CONFIGS[client_id]["config_path"]
            print(f"Checking {client_id} at {path}")
            if path.exists():
                try:
                    data = load_json_with_comments(path)
                    print(f"  Parsed keys: {list(data.keys()) if data else 'None'}")
                    if "mcpServers" in data:
                        print(f"  mcpServers count: {len(data['mcpServers'])}")
                    else:
                        print("  mcpServers NOT FOUND")
                except Exception as e:
                    print(f"  Error loading: {e}")
            else:
                print("  Path does not exist")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
