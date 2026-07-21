FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5055

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "5055"]
