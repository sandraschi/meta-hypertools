"""Tiiny.host static webpage scaffolder and publisher.

Scaffolds a single-page HTML site with optional CSS/JS and deploys it to
tiiny.host (free tier). The free plan requires an email address (tiiny sends
the link) and gives a ``{subdomain}.tiiny.host`` URL.

Usage:
    create_tiiny_site(site_name="my-site", title="Hello World", deploy=False)
    create_tiiny_site(site_name="my-site", title="Hello World", deploy=True, email="user@example.com")
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path
from typing import Any

_TIINY_API = "https://api.tiiny.host/v1/sites/upload"

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <main>
    <h1>{title}</h1>
    <div class="content">{content}</div>
  </main>
  <footer>
    <p>Hosted on <a href="https://tiiny.host">tiiny.host</a></p>
  </footer>
</body>
</html>"""

_CSS_TEMPLATE = """* {{
  margin: 0; padding: 0; box-sizing: border-box;
}}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f172a;
  color: #e2e8f0;
  line-height: 1.6;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}}
main {{
  flex: 1;
  max-width: 720px;
  margin: 0 auto;
  padding: 4rem 1.5rem;
}}
h1 {{
  font-size: 2rem;
  font-weight: 800;
  margin-bottom: 1.5rem;
  background: linear-gradient(135deg, #60a5fa, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}}
.content {{
  font-size: 1.1rem;
  color: #94a3b8;
}}
.content p {{ margin-bottom: 1rem; }}
footer {{
  text-align: center;
  padding: 2rem;
  font-size: 0.85rem;
  color: #475569;
}}
footer a {{ color: #60a5fa; text-decoration: none; }}
"""


def scaffold_tiiny_site(
    site_name: str,
    title: str = "My Page",
    content: str = "<p>Hello from tiiny.host!</p>",
    output_path: str | None = None,
    deploy: bool = False,
    email: str | None = None,
    open_browser: bool = False,
) -> dict[str, Any]:
    """Scaffold (and optionally deploy) a static page to tiiny.host.

    Args:
        site_name: Subdomain name for the tiiny.host URL (must be unique).
        title: Page title and h1 heading.
        content: HTML content for the page body.
        output_path: Local directory to write files (default: temp dir).
        deploy: Upload to tiiny.host after scaffolding.
        email: Required for free tiiny.host tier (they email the link).
        open_browser: Open the tiiny.host URL in the default browser after deploy.

    Returns:
        ``success``, ``site_name``, ``local_path``, ``tiiny_url``, ``message``.
    """
    # 1. Scaffold files
    site_slug = site_name.lower().replace(" ", "-").replace("_", "-")[:48]
    if output_path:
        out = Path(output_path) / site_slug
    else:
        out = Path(tempfile.gettempdir()) / f"tiiny-{site_slug}"
    out.mkdir(parents=True, exist_ok=True)

    (out / "index.html").write_text(_HTML_TEMPLATE.format(title=title, content=content), encoding="utf-8")
    (out / "styles.css").write_text(_CSS_TEMPLATE, encoding="utf-8")

    if not deploy:
        return {
            "success": True,
            "site_name": site_slug,
            "local_path": str(out),
            "tiiny_url": None,
            "message": f"Site scaffolded at {out}. Run with deploy=True to publish to tiiny.host.",
        }

    # 2. Zip + upload
    if not email:
        return {
            "success": False,
            "site_name": site_slug,
            "local_path": str(out),
            "error": "Email required for free tiiny.host tier (they email the link).",
            "error_type": "MissingParameter",
        }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in out.iterdir():
            if f.is_file():
                zf.write(f, f.name)
    buf.seek(0)

    try:
        import httpx

        resp = httpx.post(
            _TIINY_API,
            files={"file": ("site.zip", buf.getvalue(), "application/zip")},
            data={"subdomain": site_slug, "email": email},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            tiiny_url = data.get("url", f"https://{site_slug}.tiiny.host")
            result: dict[str, Any] = {
                "success": True,
                "site_name": site_slug,
                "local_path": str(out),
                "tiiny_url": tiiny_url,
                "message": f"Published at {tiiny_url}",
            }
            if open_browser:
                import webbrowser

                webbrowser.open(tiiny_url)
                result["browser_opened"] = True
            return result

        try:
            err_body = resp.json()
            err_msg = err_body.get("error", err_body.get("message", resp.text))
        except Exception:
            err_msg = resp.text[:500]
        return {
            "success": False,
            "site_name": site_slug,
            "local_path": str(out),
            "error": f"tiiny.host upload failed (HTTP {resp.status_code}): {err_msg}",
            "error_type": "UploadFailed",
        }
    except ImportError:
        return {
            "success": False,
            "site_name": site_slug,
            "local_path": str(out),
            "error": "httpx required for deployment. Install: uv add httpx",
            "error_type": "MissingDependency",
        }
    except Exception as e:
        return {
            "success": False,
            "site_name": site_slug,
            "local_path": str(out),
            "error": f"Deployment failed: {e}",
            "error_type": type(e).__name__,
        }
