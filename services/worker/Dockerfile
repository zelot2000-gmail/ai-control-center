FROM python:3.11-slim

WORKDIR /app

# git + patch required by self-modify workflow (code_edit/git_ops.py)
RUN apt-get update \
 && apt-get install -y --no-install-recommends git patch \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN mkdir -p /app/data/exports

ENV PYTHONUNBUFFERED=1

EXPOSE 8095

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8095"]
