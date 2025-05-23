#!/bin/bash

# Activating venv
source .venv/bin/activate

# Installing PYTHONPATH on ./src for uvicorn
export PYTHONPATH="./src"
uvicorn app.main:app --reload
