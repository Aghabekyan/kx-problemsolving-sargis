FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
ENV PIP_PROGRESS_BAR=off
RUN pip install --no-cache-dir --progress-bar off -r requirements.txt

COPY src ./src

WORKDIR /app/src

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
