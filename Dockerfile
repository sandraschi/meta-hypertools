FROM python:3.12-slim-bookworm

# Install UV for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies (without the project itself)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src ./src
# Install the project itself
RUN uv sync --frozen --no-dev

# Set python path
ENV PYTHONPATH=/app/src

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=10718

# Expose port
EXPOSE 10718

# Run the application
CMD ["uv", "run", "meta-mcp"]
