#!/bin/bash

# Start the application on HTTP first
echo "Starting installer on HTTP port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000