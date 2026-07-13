FROM python:3.12-slim

WORKDIR /app

COPY requirements-api.txt /app/requirements-api.txt

RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install \
        --no-cache-dir \
        --timeout 300 \
        --retries 10 \
        -r /app/requirements-api.txt

COPY . /app

CMD ["uvicorn", "src.inference.api:app", "--host", "0.0.0.0", "--port", "8000"]