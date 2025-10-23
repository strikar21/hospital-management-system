# -*- coding: utf-8 -*-
"""
MQTT Simple Test - Tests if Mosquitto is reachable from your PC
No username/password needed (anonymous mode enabled)
"""
import paho.mqtt.client as mqtt
import ssl
import time

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[OK] SUCCESS: Connected to Mosquitto!")
        print(f"     Server: 192.168.0.113:8883")
        print(f"     Client ID: python_test")
        print(f"     TLS: 1.2 (insecure mode)")
        print()

        # Subscribe to test topic
        client.subscribe("test/topic")
        print("[SUB] Subscribed to: test/topic")

        # Publish a test message
        client.publish("test/topic", "Hello from Python!")
        print("[PUB] Published: 'Hello from Python!'")
        print()
    else:
        errors = {
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorised"
        }
        print(f"[ERR] FAILED: {errors.get(rc, f'Unknown error {rc}')}")

def on_message(client, userdata, msg):
    print(f"[MSG] Received: {msg.topic} -> {msg.payload.decode()}")

# Create client (no username/password - anonymous mode)
client = mqtt.Client("python_test")

# Configure TLS - INSECURE MODE (bypass certificate validation)
client.tls_set(
    cert_reqs=ssl.CERT_NONE,  # Don't verify certificate
    tls_version=ssl.PROTOCOL_TLSv1_2
)
client.tls_insecure_set(True)  # Allow self-signed certs

client.on_connect = on_connect
client.on_message = on_message

print("=" * 60)
print("MQTT Test - Anonymous Mode (No Password)")
print("=" * 60)
print("Connecting to 192.168.0.113:8883...")
print()

try:
    client.connect("192.168.0.113", 8883, 60)
    client.loop_start()
    time.sleep(10)
    client.loop_stop()
    print("\n[BYE] Disconnected")
except Exception as e:
    print(f"[ERR] Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check Mosquitto: docker ps | findstr mosquitto")
    print("2. Check logs: docker logs hospital_mosquitto --tail 20")
