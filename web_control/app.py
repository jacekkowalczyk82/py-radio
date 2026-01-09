import os
import json
import logging
import boto3
from flask import Flask, render_template, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebControl")

app = Flask(__name__)

# AWS SQS Configuration (Hardcoded based on user request/config)
# In a real app, this should come from config file
QUEUE_URL = "https://sqs.us-east-2.amazonaws.com/347779256781/py-radio-control-queue"
REGION_NAME = "us-east-2"
PROFILE_NAME = "jacekmq" # Matches the profile used in radio-app

def send_sqs_message(action, station_name=None, station_url=None, volume=100):
    try:
        session = boto3.Session(profile_name=PROFILE_NAME, region_name=REGION_NAME)
        sqs = session.client('sqs')
        
        message_body = {
            "action": action,
            "name": station_name or "",
            "station": station_url or "",
            "volume": str(volume)
        }
        
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message_body)
        )
        logger.info(f"Message sent: {response.get('MessageId')}")
        return True, response.get('MessageId')
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False, str(e)

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
        
    success, result = send_sqs_message(action, station_name, station_url, volume)
    
    if success:
        return jsonify({"status": "success", "message_id": result}), 200
    else:
        return jsonify({"status": "error", "message": result}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
