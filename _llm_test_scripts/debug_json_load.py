import json
import os
from pathlib import Path


def load_json_with_comments(file_path: Path):
    print(f"Loading: {file_path}")
    if not file_path.exists():
        print("  -> Does not exist")
        return {}

    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    clean_lines = []
    for line in lines:
        comment_index = line.find("//")
        if comment_index != -1:
            line = line[:comment_index]
        clean_lines.append(line)

    content = "".join(clean_lines).strip()
    if not content:
        return {}

    try:
        return json.loads(content)
    except Exception as e:
        print(f"  -> ERROR: {e}")
        return None


# Replicate paths
local_app_data = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\%USERNAME%\AppData\Local"))
user_profile = Path(os.environ.get("USERPROFILE", Path.home()))

paths_to_check = [
    Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
    Path.home() / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage" / "cursor-storage" / "mcp_config.json",
    user_profile / ".gemini" / "antigravity" / "mcp_config.json",
    Path.home() / "AppData" / "Roaming" / "Code" / "User" / "settings.json",
    Path.home() / "AppData" / "Roaming" / "Windsurf" / "mcp_config.json",
]

for p in paths_to_check:
    load_json_with_comments(p)
