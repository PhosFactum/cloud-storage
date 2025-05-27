FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY run.sh ./run.sh
COPY alembic.ini .
COPY alembic ./alembic
COPY client ./client

RUN chmod +x ./run.sh

ENV PYTHONPATH=/app/src

EXPOSE 8002

CMD ["./run.sh"]
