import os
import json
import logging
import boto3
from flask import Flask, render_template, request, jsonify

import sys
from configparser import ConfigParser

# Add parent directory to path to import messaging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from messaging import MessagingFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebControl")

def read_config():
    config_path = os.path.expanduser("~/.config/py-radio/config.ini")
    logger.info(f"Reading config from {config_path}")
    
    config_parser = ConfigParser()
    config_parser.read(config_path)
    
    config = dict(config_parser["default"]) if "default" in config_parser else {}
    
    if "aws" in config_parser.sections():
        config.update(config_parser["aws"])
        
    if "rabbitmq" in config_parser.sections():
        config.update(config_parser["rabbitmq"])
        
    return config

# Load config once at startup
CONFIG = read_config()

app = Flask(__name__)

def send_message(action, station_name=None, station_url=None, volume=100):
    producer = MessagingFactory.get_producer(CONFIG)
    return producer.send_message(action, station_name, station_url, volume)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/control', methods=['POST'])
def control():
    data = request.json
    action = data.get('action')
    station_name = data.get('name')
    station_url = data.get('station')
    volume = data.get('volume', 100)
    
    if not action:
        return jsonify({"status": "error", "message": "Action is required"}), 400
        
    success, result = send_message(action, station_name, station_url, volume)
    
    if success:
        return jsonify({"status": "success", "message_id": result}), 200
    else:
        return jsonify({"status": "error", "message": result}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
