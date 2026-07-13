FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV AGENTIC_RAG_HOST=0.0.0.0
ENV AGENTIC_RAG_PORT=8000

COPY pyproject.toml README.md ./
COPY src ./src
COPY frontend ./frontend
COPY data ./data
COPY template ./template

EXPOSE 8000

CMD ["python", "-m", "agentic_rag_template.app"]
