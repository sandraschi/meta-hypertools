import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.abspath("src"))

import asyncio

from meta_mcp.tools.emojibuster import EmojiBuster


async def debug():
    eb = EmojiBuster()
    test_file = Path("debug_emoji.py")
    # Rocket emoji literal
    rocket = "Process"
    content = f"logger.info('Hello {rocket}')"
    test_file.write_text(content, encoding="utf-8")

    print(f"Original content: {test_file.read_text(encoding='utf-8')}")
    print(f"Rocket char codes: {[hex(ord(c)) for c in rocket]}")

    result = await eb.fix_unicode_logging(str(test_file.parent))
    print(f"Fix result: {result}")

    new_content = test_file.read_text(encoding="utf-8")
    print(f"New content: {new_content}")

    if "Process" in new_content:
        print("SUCCESS: 'Process' found!")
    else:
        print("FAILURE: 'Process' not found!")

    # Cleanup
    if test_file.exists():
        test_file.unlink()


if __name__ == "__main__":
    asyncio.run(debug())
