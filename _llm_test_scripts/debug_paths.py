import os
from pathlib import Path


def check_path(name, path_str):
    p = Path(path_str)
    exists = p.exists()
    print(f"{name}: '{path_str}' -> Exists: {exists}")
    if exists:
        print(f"  Resolved: {p.resolve()}")


print(f"LOCALAPPDATA: {os.environ.get('LOCALAPPDATA')}")
print(f"APPDATA: {os.environ.get('APPDATA')}")
print(f"USERPROFILE: {os.environ.get('USERPROFILE')}")
print(f"ProgramFiles: {os.environ.get('ProgramFiles')}")

# Replicate logic from client_integration.py
local_app_data = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\%USERNAME%\AppData\Local"))
program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
user_profile = Path(os.environ.get("USERPROFILE", Path.home()))

print("\n--- Testing Constructed Paths ---")

# Claude
claude_path = local_app_data / "AnthropicClaude" / "claude.exe"
check_path("Claude Exe", str(claude_path))

claude_config = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
check_path("Claude Config", str(claude_config))

# Cursor
cursor_path = local_app_data / "Programs" / "cursor" / "Cursor.exe"
check_path("Cursor Exe", str(cursor_path))

cursor_config = (
    Path.home() / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage" / "cursor-storage" / "mcp_config.json"
)
check_path("Cursor Config", str(cursor_config))

# Antigravity
antigravity_path = user_profile / ".gemini" / "antigravity" / "antigravity.exe"
check_path("Antigravity Exe", str(antigravity_path))
