FROM python:3.11-slim

WORKDIR /app_root

# Copy the entire galaxy project structure
COPY . .

# Install dependencies (assuming pyproject.toml or requirements.txt exists)
# If using pyproject.toml with uv, use: RUN uv sync --frozen
# If using requirements.txt, use: RUN pip install --no-cache-dir -r requirements.txt
# For this example, let's assume uv is used and pyproject.toml is present
RUN pip install uv && uv sync --frozen

EXPOSE 8080

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8080"]
