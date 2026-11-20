import paho.mqtt.client as mqtt
import time

# Konfiguracja
BROKER = "localhost"
TOPIC = "test/radio-control"

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

try:
    client.connect(BROKER, 1883, 60)
    message = f"Message sent at: {time.strftime('%H:%M:%S')}"
    
    # Publikacja wiadomości
    client.publish(TOPIC, message)
    print(f" [x] Sent: '{message}'")
    
    client.disconnect()
except Exception as e:
    print(f"ERROR: {e}")
