"""PyInstaller runtime hook: pin OpenTelemetry context implementation.

Frozen apps cannot discover the `opentelemetry_context` entry-points group
(dist-info stripped by design), so `_load_runtime_context` raises
StopIteration and kills startup. OTEL_PYTHON_CONTEXT selects the
contextvars implementation directly, no entry-points lookup.
"""

import os

os.environ.setdefault("OTEL_PYTHON_CONTEXT", "contextvars_context")
