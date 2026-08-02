from pathlib import Path
from typing import Any

from meta_mcp.services.base import MetaMCPService


class TokenAnalysisService(MetaMCPService):
    """
    Service for analyzing token usage in repositories.

    Provides token counting and analysis capabilities similar to repomix,
    helping users understand LLM context limits and optimize content for AI consumption.
    """

    def __init__(self):
        # Simple token estimation - in production you'd use tiktoken or similar
        self.token_counts = {}

    async def analyze_file_tokens(self, file_path: str) -> dict[str, Any]:
        """Analyze token usage in a specific file."""
        try:
            path = Path(file_path)

            if not path.exists():
                return self.create_response(False, f"File not found: {file_path}")

            # Read file content
            with open(path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Simple token estimation (words + punctuation)
            # In production, use tiktoken for accurate GPT token counting
            tokens = self._estimate_tokens(content)

            file_info = {
                "file_path": str(path),
                "file_name": path.name,
                "file_size": len(content),
                "line_count": len(content.split("\n")),
                "token_count": tokens,
                "token_density": tokens / max(1, len(content.split())),
                "language": self._detect_language(path),
            }

            return self.create_response(True, f"Token analysis completed for {path.name}", file_info)

        except Exception as e:
            return self.create_response(False, f"Token analysis failed: {e!s}")

    async def analyze_directory_tokens(self, dir_path: str, extensions: list[str] | None = None) -> dict[str, Any]:
        """Analyze token usage across all files in a directory."""
        try:
            path = Path(dir_path)

            if not path.exists() or not path.is_dir():
                return self.create_response(False, f"Directory not found: {dir_path}")

            if extensions is None:
                extensions = [
                    ".py",
                    ".js",
                    ".ts",
                    ".java",
                    ".cpp",
                    ".c",
                    ".go",
                    ".rs",
                    ".php",
                    ".rb",
                ]

            total_tokens = 0
            total_size = 0
            file_analyses = []

            for ext in extensions:
                for file_path in path.rglob(f"*{ext}"):
                    if file_path.is_file():
                        try:
                            result = await self.analyze_file_tokens(str(file_path))
                            if result.get("success"):
                                file_data = result.get("data", {})
                                total_tokens += file_data.get("token_count", 0)
                                total_size += file_data.get("file_size", 0)
                                file_analyses.append(file_data)
                        except Exception:
                            # Skip files that can't be analyzed
                            continue

            # Sort by token count
            file_analyses.sort(key=lambda x: x.get("token_count", 0), reverse=True)

            analysis = {
                "directory": str(path),
                "total_files": len(file_analyses),
                "total_tokens": total_tokens,
                "total_size_bytes": total_size,
                "average_tokens_per_file": total_tokens / max(1, len(file_analyses)),
                "largest_files": file_analyses[:10],  # Top 10 by token count
                "extensions_analyzed": extensions,
                "token_distribution": self._analyze_token_distribution(file_analyses),
            }

            return self.create_response(True, f"Directory token analysis completed for {path.name}", analysis)

        except Exception as e:
            return self.create_response(False, f"Directory token analysis failed: {e!s}")

    async def estimate_context_limits(self, token_count: int) -> dict[str, Any]:
        """Estimate how the token count fits within various LLM context limits."""
        limits = {
            "gpt-3.5-turbo": 4096,
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "claude-3-haiku": 200000,
            "claude-3-sonnet": 200000,
            "claude-3-opus": 200000,
            "gemini-pro": 32768,
            "llama-2-7b": 4096,
            "codellama": 16384,
        }

        analysis = {}
        for model, limit in limits.items():
            usage_percent = (token_count / limit) * 100
            analysis[model] = {
                "limit": limit,
                "tokens_used": token_count,
                "usage_percent": round(usage_percent, 1),
                "fits": token_count <= limit,
                "remaining": max(0, limit - token_count),
            }

        return self.create_response(
            True,
            "Context limit analysis completed",
            {
                "input_tokens": token_count,
                "model_analysis": analysis,
                "recommendations": self._generate_context_recommendations(token_count, analysis),
            },
        )

    def _estimate_tokens(self, content: str) -> int:
        """Simple token estimation. In production, use tiktoken."""
        # Rough estimation: ~4 characters per token for code
        # More accurate would use tiktoken library
        char_count = len(content)
        # Estimate: 1 token per 4 characters for code, adjusted for whitespace
        lines = content.split("\n")
        avg_line_length = sum(len(line) for line in lines) / max(1, len(lines))

        # Code tends to have more tokens per character than natural language
        if avg_line_length > 80:  # Likely code
            tokens_per_char = 0.3  # ~3-4 chars per token for code
        else:  # Likely natural language or comments
            tokens_per_char = 0.25  # ~4 chars per token

        estimated_tokens = int(char_count * tokens_per_char)

        # Adjust for special patterns
        estimated_tokens += content.count("\n") * 0.5  # Line breaks
        estimated_tokens += content.count(" ") * 0.2  # Spaces
        estimated_tokens += content.count("\t") * 0.3  # Tabs

        return max(1, estimated_tokens)

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".cs": "csharp",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".clj": "clojure",
            ".hs": "haskell",
            ".ml": "ocaml",
            ".fs": "fsharp",
            ".dart": "dart",
            ".lua": "lua",
            ".pl": "perl",
            ".r": "r",
            ".sh": "bash",
            ".ps1": "powershell",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".less": "less",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".ini": "ini",
            ".cfg": "config",
            ".md": "markdown",
            ".txt": "text",
        }

        return ext_map.get(file_path.suffix.lower(), "unknown")

    def _analyze_token_distribution(self, file_analyses: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze token distribution across files."""
        if not file_analyses:
            return {}

        token_counts = [f.get("token_count", 0) for f in file_analyses]
        total_tokens = sum(token_counts)

        # Calculate percentiles
        sorted_tokens = sorted(token_counts)
        n = len(sorted_tokens)

        percentiles = {}
        for p in [25, 50, 75, 90, 95, 99]:
            idx = int((p / 100) * (n - 1))
            percentiles[f"p{p}"] = sorted_tokens[idx]

        return {
            "total_files": n,
            "total_tokens": total_tokens,
            "average_tokens": total_tokens / max(1, n),
            "min_tokens": min(token_counts),
            "max_tokens": max(token_counts),
            "percentiles": percentiles,
            "distribution": {
                "small_files": len([t for t in token_counts if t < 100]),
                "medium_files": len([t for t in token_counts if 100 <= t < 1000]),
                "large_files": len([t for t in token_counts if 1000 <= t < 10000]),
                "very_large_files": len([t for t in token_counts if t >= 10000]),
            },
        }

    def _generate_context_recommendations(self, token_count: int, analysis: dict[str, Any]) -> list[str]:
        """Generate recommendations based on context limits."""
        recommendations = []

        # Check which models can handle this content
        viable_models = [model for model, data in analysis.items() if data["fits"]]

        if not viable_models:
            recommendations.append("warning:  Token count exceeds all major LLM context limits")
            recommendations.append("Consider splitting content or using compression")
            recommendations.append("Use file filtering to reduce scope")

        elif len(viable_models) < 3:
            recommendations.append(f"[ok]  Fits in {len(viable_models)} major LLM contexts")
            recommendations.append("Consider using compression for better compatibility")

        else:
            recommendations.append(f"[ok]  Fits in {len(viable_models)} LLM contexts - good compatibility")

        # Specific recommendations
        if token_count > 100000:
            recommendations.append("[fix]  Large token count - consider file filtering or compression")
        elif token_count > 50000:
            recommendations.append("[info]  Moderate token count - suitable for most advanced models")
        else:
            recommendations.append("[goal]  Optimal token count - compatible with all major LLMs")

        return recommendations
