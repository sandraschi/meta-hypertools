# 📦 Repository Packing Suite

**AI-first content consolidation.**

Inspired by `repomix`, this suite packs entire repositories into single, AI-digestible formats. It optimizes content for LLM consumption, effectively "zipping" a codebase into a prompt.

For **remote public GitHub** repos (no local path), use **[Repository Inspiration](repo-inspiration.md)** (`inspire_repo_*`, adapted from [Repomuse](https://www.npmjs.com/package/repomuse)).

## Tools

### `pack_repository`
Consolidate a repository into a single file.
- **Formats**: XML (Repomix style), Markdown, JSON, Plain Text.
- **Features**: `.gitignore` respect, binary file skipping, removing lockfiles.
- **Args**: `repo_path` (str), `output_format` (str), `include_patterns` (list), `exclude_patterns` (list)

### `pack_repository_for_ai`
Smart packing optimized for a specific token budget.
- **Logic**: Prioritizes source code over docs, core files over utils, until the token limit is reached.
- **Args**: `repo_path` (str), `max_tokens` (int)

## Key Features
- **Security**: Automatically filters known secrets and sensitive files (`.env`, private keys).
- **Metadata**: Adds file paths and structure info so the LLM understands the project layout.
- **Efficiency**: Reduces "fluff" (whitespace, comments if configured) to maximize information density.
