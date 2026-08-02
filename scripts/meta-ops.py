#!/usr/bin/env python3
"""CLI bridge to meta-mcp internal services.

Usage:
  meta-ops.py analyze-runts --path /repos --format json
  meta-ops.py analyze-runts --deep
  meta-ops.py pack /path/to/repo
"""

import argparse
import asyncio
import json
import sys
import traceback


async def run_analyze_runts(args):
    from meta_mcp.tools.mcp_repo_analyzer import analyze_runts

    scan_path = args.path or None
    format = args.format
    try:
        result = await analyze_runts(scan_path=scan_path, format=format, deep_scan=args.deep)
    except Exception as e:
        print(f"[ERR] analyze_runts failed: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    if format == "json":
        import json

        print(json.dumps(result, indent=2))
    else:
        print(result)


async def run_emoji_buster(args):
    from meta_mcp.services.emoji_buster import EmojiBuster

    buster = EmojiBuster()
    try:
        buster.bust_path(args.path)
    except Exception as e:
        print(f"[ERR] Emoji bust failed: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


async def run_pack_repo(args):
    from meta_mcp.services.repo_packing_service import RepoPackingService

    svc = RepoPackingService()
    try:
        result = await svc.pack_repository(args.path)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"[ERR] Pack failed: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="MetaMCP CLI bridge")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("analyze-runts", help="Scan for outdated MCP servers")
    p.add_argument("--path", help="Scan path")
    p.add_argument("--format", default="markdown", choices=["json", "markdown"])
    p.add_argument("--deep", action="store_true")

    p = sub.add_parser("emoji-buster", help="Remove emoji from files")
    p.add_argument("path", help="File or directory")

    p = sub.add_parser("pack", help="Pack repo for LLM context")
    p.add_argument("path", help="Repo path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "analyze-runts": run_analyze_runts,
        "emoji-buster": run_emoji_buster,
        "pack": run_pack_repo,
    }
    if args.command in dispatch:
        asyncio.run(dispatch[args.command](args))
    else:
        print(f"[ERR] Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
