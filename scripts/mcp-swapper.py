#!/usr/bin/env python3
"""Swap MCP server tiers in Antigravity config.

Usage:
  mcp-swapper.py tier1 tier2          # Enable specific tiers
  mcp-swapper.py --list               # List available tiers
  mcp-swapper.py tier1 --dry-run      # Preview without writing
"""

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_CONFIG = Path(
    os.environ.get("ANTIGRAVITY_MCP_CONFIG", Path.home() / ".gemini" / "antigravity" / "mcp_config.json")
)

TIERS = {
    "tier1": {"advanced-memory-mcp", "speech-mcp", "clawops", "davinci", "beyondcompare", "brightdata", "context7"},
    "tier2": {"calibre-mcp", "plex-mcp", "yahboom-mcp", "dreame-mcp", "meta-mcp", "worldlabs-mcp"},
    "tier3": {"blender-mcp", "resonite-mcp"},
}

TOTAL_SERVERS = sum(len(s) for s in TIERS.values())


def load_config(path: Path) -> dict:
    if not path.exists():
        print(f"[ERR] Config not found: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_config(path: Path, config: dict, dry_run: bool = False):
    bak = path.with_suffix(path.suffix + ".bak")
    if not dry_run:
        import shutil

        shutil.copy2(path, bak)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    return bak


def activate_tiers(tier_selection: list[str], config_path: Path, dry_run: bool = False):
    config = load_config(config_path)
    servers = config.get("mcpServers", {})
    total = len(servers)

    to_enable = set()
    for t in tier_selection:
        if t in TIERS:
            to_enable.update(TIERS[t])
        elif t == "all":
            for srvs in TIERS.values():
                to_enable.update(srvs)
        else:
            print(f"  [WARN] Unknown tier: {t}")

    enabled_count = 0
    disabled_count = 0
    for name, srv in servers.items():
        should_enable = name in to_enable
        if srv.get("disabled") is (not should_enable):
            continue
        srv["disabled"] = not should_enable
        if should_enable:
            enabled_count += 1
        else:
            disabled_count += 1

    if enabled_count == 0 and disabled_count == 0:
        print("[SKIP] No servers changed.")
        return

    mode = "[DRY-RUN] " if dry_run else ""
    print(f"  {mode}{enabled_count} enabled, {disabled_count} disabled")

    bak = save_config(config_path, config, dry_run=dry_run) if (enabled_count + disabled_count > 0) else None

    print("\n  Summary:")
    print(f"    Config:  {config_path}")
    print(f"    Tiers:   {', '.join(tier_selection)}")
    print(f"    Enabled: {enabled_count}/{total}")
    print(f"    Backup:  {bak if bak else 'none'}")
    if not dry_run:
        print("  [INFO] Restart Antigravity to apply changes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antigravity MCP Tier Swapper")
    parser.add_argument("tiers", nargs="*", help="Tiers: tier1, tier2, tier3, all")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--list", action="store_true", help="List server tiers")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")

    args = parser.parse_args()

    if args.list:
        print("Available tiers:")
        for t, srvs in sorted(TIERS.items()):
            print(f"  {t}: {', '.join(sorted(srvs))}")
        print(f"  total: {TOTAL_SERVERS} servers")
        sys.exit(0)

    if not args.tiers:
        parser.print_help()
        sys.exit(1)

    activate_tiers(args.tiers, args.config, dry_run=args.dry_run)
