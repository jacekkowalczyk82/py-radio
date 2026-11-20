#!/bin/bash
echo "Installing dependencies..."
pip3 install -r requirements.txt

echo "Starting Web Control Panel..."
echo "Open http://localhost:5000 in your browser"
python3 app.py
