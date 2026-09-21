FROM python:3.14.5-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

COPY backend/app ./app
COPY backend/app/main.py .
COPY backend/alembic ./alembic
COPY backend/alembic.ini .
COPY deployment ./deployment

EXPOSE 8300

CMD ["python", "main.py"]
