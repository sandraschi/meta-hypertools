import json
from pathlib import Path
from typing import Any

from meta_mcp.services.base import MetaMCPService


class RepoPackingService(MetaMCPService):
    """
    Service for packing repository contents into AI-friendly formats.

    Inspired by repomix, this service packs repository contents into single files
    optimized for AI consumption, with support for multiple output formats.
    """

    async def pack_repository(
        self,
        repo_path: str,
        output_format: str = "xml",
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Pack repository contents into a single AI-friendly file."""
        try:
            path = Path(repo_path).resolve()

            if not path.exists():
                return self.create_response(False, f"Repository path not found: {repo_path}")

            # Collect files based on patterns
            files_data = await self._collect_files(path, include_patterns, exclude_patterns)

            if not files_data:
                return self.create_response(False, "No files found matching criteria")

            # Generate packed content based on format
            if output_format.lower() == "xml":
                packed_content = self._generate_xml_output(files_data, path.name)
            elif output_format.lower() == "markdown":
                packed_content = self._generate_markdown_output(files_data, path.name)
            elif output_format.lower() == "json":
                packed_content = self._generate_json_output(files_data, path.name)
            else:
                packed_content = self._generate_plain_output(files_data, path.name)

            # Calculate token count (using our token analysis service)
            from meta_mcp.services.token_analysis_service import TokenAnalysisService

            token_service = TokenAnalysisService()

            # Estimate total tokens
            total_tokens = sum(
                await token_service._estimate_tokens_async(content) for content in [f["content"] for f in files_data]
            )

            result = {
                "repository_name": path.name,
                "repository_path": str(path),
                "output_format": output_format,
                "total_files": len(files_data),
                "total_tokens": total_tokens,
                "packed_content": packed_content,
                "file_summary": self._generate_file_summary(files_data),
                "token_analysis": await self._analyze_token_usage(files_data),
            }

            return self.create_response(True, f"Repository packed successfully in {output_format} format", result)

        except Exception as e:
            return self.create_response(False, f"Repository packing failed: {e!s}")

    async def pack_for_ai_consumption(self, repo_path: str, max_tokens: int = 100000) -> dict[str, Any]:
        """Pack repository optimized for AI consumption with token limits."""
        try:
            # First, analyze the repository
            analysis_result = await self.pack_repository(repo_path, "xml")

            if not analysis_result.get("success"):
                return analysis_result

            data = analysis_result.get("data", {})
            total_tokens = data.get("total_tokens", 0)

            if total_tokens <= max_tokens:
                return analysis_result

            # If too large, create a filtered version
            # Prioritize important files and truncate large ones
            filtered_data = await self._optimize_for_tokens(repo_path, max_tokens)

            optimized_result = {
                "repository_name": data["repository_name"],
                "repository_path": data["repository_path"],
                "output_format": "xml",
                "total_files": len(filtered_data),
                "total_tokens": sum(
                    await self._estimate_tokens_async(content) for content in [f["content"] for f in filtered_data]
                ),
                "packed_content": self._generate_xml_output(filtered_data, data["repository_name"]),
                "optimization_applied": True,
                "original_token_count": total_tokens,
                "max_tokens": max_tokens,
                "compression_ratio": len(filtered_data) / max(1, data["total_files"]),
            }

            return self.create_response(
                True,
                f"Repository optimized for AI consumption ({max_tokens} token limit)",
                optimized_result,
            )

        except Exception as e:
            return self.create_response(False, f"AI-optimized packing failed: {e!s}")

    async def _collect_files(
        self,
        repo_path: Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Collect files from repository based on patterns."""
        files_data = []

        # Default patterns
        if include_patterns is None:
            include_patterns = ["**/*"]
        if exclude_patterns is None:
            exclude_patterns = self._get_default_excludes()

        # Read .gitignore if it exists
        gitignore_patterns = []
        gitignore_file = repo_path / ".gitignore"
        if gitignore_file.exists():
            try:
                with open(gitignore_file, encoding="utf-8") as f:
                    gitignore_patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            except Exception:
                pass

        all_excludes = exclude_patterns + gitignore_patterns

        for pattern in include_patterns:
            for file_path in repo_path.glob(pattern):
                if file_path.is_file():
                    # Check if file should be excluded
                    relative_path = file_path.relative_to(repo_path)
                    should_exclude = any(self._matches_pattern(str(relative_path), excl) for excl in all_excludes)

                    if not should_exclude:
                        try:
                            # Read file content
                            with open(file_path, encoding="utf-8", errors="ignore") as f:
                                content = f.read()

                            # Skip binary files or very large files
                            if self._is_binary_file(content) or len(content) > 1000000:  # 1MB limit
                                continue

                            files_data.append(
                                {
                                    "path": str(relative_path),
                                    "name": file_path.name,
                                    "extension": file_path.suffix,
                                    "size": len(content),
                                    "content": content,
                                    "language": self._detect_language(file_path),
                                }
                            )

                        except Exception:
                            # Skip files that can't be read
                            continue

        # Sort files by path for consistent output
        files_data.sort(key=lambda x: x["path"])

        return files_data

    def _get_default_excludes(self) -> list[str]:
        """Get default exclusion patterns."""
        return [
            "**/node_modules/**",
            "**/.git/**",
            "**/.svn/**",
            "**/.hg/**",
            "**/.DS_Store",
            "**/Thumbs.db",
            "**/*.log",
            "**/*.tmp",
            "**/*.swp",
            "**/*.swo",
            "**/dist/**",
            "**/build/**",
            "**/__pycache__/**",
            "**/*.pyc",
            "**/*.pyo",
            "**/.next/**",
            "**/.nuxt/**",
            "**/.vite/**",
            "**/coverage/**",
            "**/.coverage",
            "**/htmlcov/**",
        ]

    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches glob pattern."""
        import fnmatch

        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, f"**/{pattern}")

    def _is_binary_file(self, content: str) -> bool:
        """Check if content appears to be binary."""
        # Simple heuristic: if many null bytes or high ratio of non-printable chars
        if "\x00" in content[:1024]:
            return True

        printable_chars = sum(1 for c in content[:1024] if c.isprintable() or c in "\n\r\t")
        return printable_chars / max(1, len(content[:1024])) < 0.7

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file path."""
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
            ".md": "markdown",
            ".txt": "text",
        }

        return ext_map.get(file_path.suffix.lower(), "unknown")

    def _generate_xml_output(self, files_data: list[dict[str, Any]], repo_name: str) -> str:
        """Generate XML output format."""
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_parts.append(f'<repository name="{repo_name}">')

        for file_data in files_data:
            xml_parts.append(f'  <file path="{file_data["path"]}" language="{file_data["language"]}">')
            xml_parts.append(f"    <content><![CDATA[{file_data['content']}]]></content>")
            xml_parts.append("  </file>")

        xml_parts.append("</repository>")

        return "\n".join(xml_parts)

    def _generate_markdown_output(self, files_data: list[dict[str, Any]], repo_name: str) -> str:
        """Generate Markdown output format."""
        md_parts = [f"# {repo_name}"]
        md_parts.append("")
        md_parts.append("Repository contents packed for AI consumption.")
        md_parts.append("")

        for file_data in files_data:
            md_parts.append(f"## {file_data['path']}")
            md_parts.append("")
            md_parts.append(f"**Language:** {file_data['language']}")
            md_parts.append(f"**Size:** {file_data['size']} characters")
            md_parts.append("")
            md_parts.append("```" + file_data["language"])
            md_parts.append(file_data["content"])
            md_parts.append("```")
            md_parts.append("")

        return "\n".join(md_parts)

    def _generate_json_output(self, files_data: list[dict[str, Any]], repo_name: str) -> str:
        """Generate JSON output format."""
        output_data = {
            "repository": repo_name,
            "description": "Repository contents packed for AI consumption",
            "files": files_data,
        }

        return json.dumps(output_data, indent=2, ensure_ascii=False)

    def _generate_plain_output(self, files_data: list[dict[str, Any]], repo_name: str) -> str:
        """Generate plain text output format."""
        plain_parts = [f"{repo_name} Repository Contents"]
        plain_parts.append("=" * 50)
        plain_parts.append("")

        for file_data in files_data:
            plain_parts.append(f"File: {file_data['path']}")
            plain_parts.append(f"Language: {file_data['language']}")
            plain_parts.append(f"Size: {file_data['size']} characters")
            plain_parts.append("-" * 40)
            plain_parts.append(file_data["content"])
            plain_parts.append("")
            plain_parts.append("=" * 50)
            plain_parts.append("")

        return "\n".join(plain_parts)

    def _generate_file_summary(self, files_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate summary statistics for files."""
        if not files_data:
            return {}

        languages = {}
        extensions = {}
        total_size = 0

        for file_data in files_data:
            lang = file_data["language"]
            ext = file_data["extension"]
            size = file_data["size"]

            languages[lang] = languages.get(lang, 0) + 1
            extensions[ext] = extensions.get(ext, 0) + 1
            total_size += size

        # Sort by frequency
        top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        top_extensions = sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_files": len(files_data),
            "total_size_bytes": total_size,
            "languages": dict(top_languages),
            "extensions": dict(top_extensions),
            "average_file_size": total_size / max(1, len(files_data)),
        }

    async def _analyze_token_usage(self, files_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze token usage across packed content."""
        from meta_mcp.services.token_analysis_service import TokenAnalysisService

        token_service = TokenAnalysisService()

        total_tokens = 0
        file_tokens = []

        for file_data in files_data:
            tokens = await token_service._estimate_tokens_async(file_data["content"])
            total_tokens += tokens
            file_tokens.append({"path": file_data["path"], "tokens": tokens, "size": file_data["size"]})

        # Sort by token count
        file_tokens.sort(key=lambda x: x["tokens"], reverse=True)

        return {
            "total_tokens": total_tokens,
            "average_tokens_per_file": total_tokens / max(1, len(files_data)),
            "largest_files": file_tokens[:5],
            "token_efficiency": total_tokens / max(1, sum(f["size"] for f in files_data)),
        }

    async def _optimize_for_tokens(self, repo_path: str, max_tokens: int) -> list[dict[str, Any]]:
        """Optimize file selection for token limits."""
        # Simple optimization: prioritize smaller, important files
        # In production, this would use more sophisticated heuristics

        path = Path(repo_path)
        important_files = [
            "README.md",
            "package.json",
            "pyproject.toml",
            "Cargo.toml",
            "main.py",
            "index.js",
            "app.py",
            "server.py",
        ]

        optimized_files = []

        # First, add important files
        for important_file in important_files:
            file_path = path / important_file
            if file_path.exists():
                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    if not self._is_binary_file(content) and len(content) < 50000:  # Reasonable size limit
                        optimized_files.append(
                            {
                                "path": important_file,
                                "name": file_path.name,
                                "extension": file_path.suffix,
                                "size": len(content),
                                "content": content,
                                "language": self._detect_language(file_path),
                            }
                        )
                except Exception:
                    continue

        # Then add other files until token limit
        current_tokens = sum(await self._estimate_tokens_async(f["content"]) for f in optimized_files)

        if current_tokens < max_tokens:
            # Add more files from common directories
            common_dirs = ["src", "lib", "app", "core", "utils"]

            for dir_name in common_dirs:
                dir_path = path / dir_name
                if dir_path.exists():
                    for file_path in dir_path.glob("**/*.py"):
                        if file_path.is_file() and current_tokens < max_tokens:
                            try:
                                with open(file_path, encoding="utf-8", errors="ignore") as f:
                                    content = f.read()

                                if not self._is_binary_file(content):
                                    tokens = await self._estimate_tokens_async(content)
                                    if current_tokens + tokens <= max_tokens:
                                        optimized_files.append(
                                            {
                                                "path": str(file_path.relative_to(path)),
                                                "name": file_path.name,
                                                "extension": file_path.suffix,
                                                "size": len(content),
                                                "content": content,
                                                "language": self._detect_language(file_path),
                                            }
                                        )
                                        current_tokens += tokens

                            except Exception:
                                continue

        return optimized_files

    async def _estimate_tokens_async(self, content: str) -> int:
        """Async wrapper for token estimation."""
        from meta_mcp.services.token_analysis_service import TokenAnalysisService

        token_service = TokenAnalysisService()
        return token_service._estimate_tokens(content)
