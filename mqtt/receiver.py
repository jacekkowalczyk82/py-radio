import paho.mqtt.client as mqtt

# Konfiguracja
BROKER = "localhost"
TOPIC = "test/radio-control"

# Funkcja wywoływana przy odebraniu wiadomości
def on_message(client, userdata, msg):
    print(f" [v] Received: '{msg.payload.decode()}' from topic: {msg.topic}")

# Konfiguracja klienta
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

print(f" [*] Waiting for messages in {TOPIC}. Press Ctrl+C, for exit.")

try:
    client.connect(BROKER, 1883, 60)
    client.subscribe(TOPIC)
    
    # Pętla nasłuchująca (blokująca)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nReceiver stopped.")
except Exception as e:
    print(f"ERROR: {e}")

