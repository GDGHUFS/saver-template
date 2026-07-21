FROM docker.io/library/python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY src ./src
COPY wellcome.html ./

EXPOSE 5055

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "5055"]
