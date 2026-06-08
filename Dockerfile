FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/
COPY models/ models/
COPY policies.yaml .

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "umcp.gateway.server:app", "--host", "0.0.0.0", "--port", "8000"]