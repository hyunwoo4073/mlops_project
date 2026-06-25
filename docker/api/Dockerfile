FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY models /app/models

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.inference.api:app", "--host", "0.0.0.0", "--port", "8000"]
