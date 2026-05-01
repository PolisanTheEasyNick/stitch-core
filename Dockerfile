FROM python:3-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential gcc g++ python3-dev

WORKDIR /app
COPY requirements.txt .

RUN pip install --prefix=/install -r requirements.txt


FROM python:3-slim

EXPOSE 4308
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ukr \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

WORKDIR /app

RUN adduser -u 5678 --disabled-password --gecos "" appuser && \
    chown -R appuser /app

USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:4308", "-k", "uvicorn.workers.UvicornWorker", "main:app"]