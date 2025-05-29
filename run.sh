#!/bin/bash

# Migrations of Alembic
echo "Running Alembic migrations..."
alembic upgrade head

# Installing PYTHONPATH on ./src for uvicorn
export PYTHONPATH="./src"
uvicorn main:app --reload --host 0.0.0.0 --port 8002
