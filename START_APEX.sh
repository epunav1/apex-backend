#!/bin/bash
echo "Starting APEX backend..."
pip install -r requirements.txt -q
uvicorn main:app --reload --port 8000
