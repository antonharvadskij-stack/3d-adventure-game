FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
COPY aion-server/requirements.txt /tmp/aion-requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/aion-requirements.txt
COPY . .
WORKDIR /app/aion-server
EXPOSE 8000
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
