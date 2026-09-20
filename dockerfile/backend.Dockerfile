FROM 192.168.111.40:88/group-one/python:3.12-slim

WORKDIR /opt/adpilot

COPY backend /opt/adpilot/backend
COPY deployment /opt/adpilot/deployment

WORKDIR /opt/adpilot/backend

ENV PIP_INDEX_URL=http://192.168.111.4:3141/root/prod/+simple/
ENV PIP_TRUSTED_HOST=192.168.111.4
ENV PYTHONPATH=/opt/adpilot/backend

RUN pip install --no-cache-dir .

CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
