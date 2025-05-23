#!/bin/bash

# Activating venv
source .venv/bin/activate

# Installing PYTHONPATH on ./src for uvicorn
export PYTHONPATH="./src"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
