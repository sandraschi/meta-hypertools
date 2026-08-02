"""
Repomix Analysis Tools for MetaMCP

Integration with repomix MCP server for repository analysis and optimization.
Provides tools to analyze codebases using repomix capabilities.
"""

import os
import shutil
from pathlib import Path
from typing import Any

import structlog

from meta_mcp.services.base import MetaMCPService

logger = structlog.get_logger(__name__)


class RepomixAnalysisService(MetaMCPService):
    """
    Service for analyzing repositories using Repomix capabilities.

    Integrates with the repomix MCP server to provide repository analysis
    and optimization recommendations.
    """

    def __init__(self):
        super().__init__()
        self.repomix_available = self._check_repomix_availability()

    def _check_repomix_availability(self) -> bool:
        """Check if repomix is available in the system."""
        try:
            import subprocess

            repomix_path = shutil.which("repomix") or "repomix"
            result = subprocess.run([repomix_path, "--version"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            subprocess.CalledProcessError,
        ):
            return False

    async def analyze_with_repomix(
        self,
        repo_path: str,
        analysis_type: str = "overview",
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        compression_enabled: bool = True,
    ) -> dict[str, Any]:
        """
        Analyze a repository using repomix capabilities.

        Args:
            repo_path: Path to the repository to analyze
            analysis_type: Type of analysis ("overview", "structure", "dependencies", "security")
            include_patterns: File patterns to include in analysis
            exclude_patterns: File patterns to exclude from analysis
            compression_enabled: Whether to use Tree-sitter compression

        Returns:
            Analysis results with repository insights
        """
        if not self.repomix_available:
            return {
                "success": False,
                "message": "Operation failed",
                "error": "Repomix is not available. Install with: npm install -g repomix",
                "install_command": "npm install -g repomix",
            }

        try:
            repo_path_obj = Path(repo_path).resolve()

            if not repo_path_obj.exists():
                return {
                    "success": False,
                    "message": "Operation failed",
                    "error": f"Repository path does not exist: {repo_path}",
                }

            # Determine output format based on analysis type
            if analysis_type == "overview":
                style = "markdown"
            elif analysis_type == "structure":
                style = "xml"
            elif analysis_type == "dependencies":
                style = "json"
                include_patterns = include_patterns or [
                    "package.json",
                    "requirements.txt",
                    "pyproject.toml",
                    "Cargo.toml",
                ]
            else:
                style = "plain"

            # Build repomix command arguments
            cmd_args = ["repomix", str(repo_path_obj), "--style", style]

            if compression_enabled:
                cmd_args.append("--compress")

            if include_patterns:
                for pattern in include_patterns:
                    cmd_args.extend(["--include", pattern])

            if exclude_patterns:
                for pattern in exclude_patterns:
                    cmd_args.extend(["--ignore", pattern])

            # Use resolved binary path
            repomix_path = shutil.which("repomix") or "repomix"
            cmd_args[0] = repomix_path

            # Execute repomix
            import subprocess

            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                timeout=300,  # 5 minute timeout for large repos
            )

            if result.returncode == 0:
                # Read the generated output file
                output_file = f"repomix-output.{style}"
                if os.path.exists(output_file):
                    with open(output_file, encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    # Get file stats
                    file_size = os.path.getsize(output_file)

                    # Clean up the temporary file
                    try:
                        os.remove(output_file)
                    except OSError:
                        pass  # Ignore cleanup errors

                    # Analyze content based on type
                    analysis = await self._analyze_content(content, analysis_type)

                    return {
                        "success": True,
                        "repository": str(repo_path_obj),
                        "analysis_type": analysis_type,
                        "format": style,
                        "compressed": compression_enabled,
                        "file_size": file_size,
                        "content_length": len(content),
                        "analysis": analysis,
                        "summary": self._generate_summary(analysis, analysis_type),
                    }
                else:
                    return {
                        "success": False,
                        "message": "Operation failed",
                        "error": f"Repomix completed but output file not found: {output_file}",
                    }
            else:
                return {
                    "success": False,
                    "message": "Operation failed",
                    "error": f"Repomix failed: {result.stderr}",
                    "stdout": result.stdout,
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Operation failed",
                "error": "Repomix analysis timed out (repository too large or complex)",
            }
        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Unexpected error during repomix analysis: {e!s}",
            }

    async def _analyze_content(self, content: str, analysis_type: str) -> dict[str, Any]:
        """Analyze the repomix-generated content based on type."""
        if analysis_type == "overview":
            return await self._analyze_overview(content)
        elif analysis_type == "structure":
            return await self._analyze_structure(content)
        elif analysis_type == "dependencies":
            return await self._analyze_dependencies(content)
        elif analysis_type == "security":
            return await self._analyze_security(content)
        else:
            return {"content_type": "raw", "length": len(content)}

    async def _analyze_overview(self, content: str) -> dict[str, Any]:
        """Generate repository overview analysis."""
        lines = content.split("\n")

        # Count files by extension
        extensions = {}
        total_files = 0

        for line in lines:
            if "|" in line and (".py" in line or ".js" in line or ".ts" in line or ".md" in line):
                total_files += 1
                # Extract file extension
                if ".py" in line:
                    extensions["python"] = extensions.get("python", 0) + 1
                elif ".js" in line:
                    extensions["javascript"] = extensions.get("javascript", 0) + 1
                elif ".ts" in line:
                    extensions["typescript"] = extensions.get("typescript", 0) + 1
                elif ".md" in line:
                    extensions["markdown"] = extensions.get("markdown", 0) + 1

        return {
            "total_files": total_files,
            "file_types": extensions,
            "content_lines": len(lines),
            "estimated_tokens": len(content) // 4,  # Rough token estimate
        }

    async def _analyze_structure(self, content: str) -> dict[str, Any]:
        """Analyze repository structure."""
        # Look for common structure patterns
        structure = {
            "has_src": "src/" in content,
            "has_tests": "test" in content.lower(),
            "has_docs": "docs/" in content or "README" in content,
            "has_config": "config" in content.lower() or ".toml" in content or ".json" in content,
            "has_scripts": "scripts/" in content,
        }

        return {
            "structure": structure,
            "structure_score": sum(structure.values()),  # Simple score
            "well_structured": sum(structure.values()) >= 3,
        }

    async def _analyze_dependencies(self, content: str) -> dict[str, Any]:
        """Analyze dependency information."""
        dependencies = []

        # Look for dependency declarations
        if "requirements.txt" in content:
            dependencies.append("python")
        if "package.json" in content:
            dependencies.append("node")
        if "Cargo.toml" in content:
            dependencies.append("rust")
        if "go.mod" in content:
            dependencies.append("go")

        return {
            "detected_languages": dependencies,
            "dependency_files": len(dependencies),
            "has_dependencies": len(dependencies) > 0,
        }

    async def _analyze_security(self, content: str) -> dict[str, Any]:
        """Analyze for security concerns."""
        security_issues = []

        # Look for potential security issues
        if "password" in content.lower() or "secret" in content.lower():
            security_issues.append("potential_credentials")

        if "api_key" in content.lower() or "apikey" in content.lower():
            security_issues.append("api_keys")

        if ".env" in content:
            security_issues.append("env_files")

        return {
            "security_issues": security_issues,
            "risk_level": "high" if len(security_issues) > 2 else "medium" if len(security_issues) > 0 else "low",
            "recommendations": self._generate_security_recommendations(security_issues),
        }

    def _generate_security_recommendations(self, issues: list[str]) -> list[str]:
        """Generate security recommendations based on issues found."""
        recommendations = []

        if "potential_credentials" in issues:
            recommendations.append("Review and remove hardcoded credentials")
        if "api_keys" in issues:
            recommendations.append("Move API keys to environment variables")
        if "env_files" in issues:
            recommendations.append("Ensure .env files are in .gitignore")

        return recommendations

    def _generate_summary(self, analysis: dict[str, Any], analysis_type: str) -> str:
        """Generate a human-readable summary of the analysis."""
        if analysis_type == "overview":
            files = analysis.get("total_files", 0)
            types = analysis.get("file_types", {})
            return f"Repository contains {files} analyzed files. Top languages: {', '.join(types.keys())[:50]}..."

        elif analysis_type == "structure":
            score = analysis.get("structure_score", 0)
            well_structured = analysis.get("well_structured", False)
            status = "well-structured" if well_structured else "needs organization"
            return f"Structure score: {score}/5 - {status}"

        elif analysis_type == "dependencies":
            langs = analysis.get("detected_languages", [])
            return f"Detected languages: {', '.join(langs) if langs else 'none identified'}"

        elif analysis_type == "security":
            risk = analysis.get("risk_level", "unknown")
            issues = len(analysis.get("security_issues", []))
            return f"Security risk: {risk} ({issues} potential issues)"

        return "Analysis completed"


# Module-level functions for easy importing
async def analyze_repository_with_repomix(
    repo_path: str,
    analysis_type: str = "overview",
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    compression_enabled: bool = True,
) -> dict[str, Any]:
    """
    Convenience function to analyze a repository with repomix.

    This function can be called directly or integrated into MetaMCP workflows.
    """
    service = RepomixAnalysisService()
    return await service.analyze_with_repomix(
        repo_path=repo_path,
        analysis_type=analysis_type,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        compression_enabled=compression_enabled,
    )
