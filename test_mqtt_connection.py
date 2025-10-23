#!/usr/bin/env python3
"""
Test MQTT TLS connection from host machine to Mosquitto broker
This tests if the broker is accessible from the WiFi network (not just Docker network)
"""

import paho.mqtt.client as mqtt
import ssl
import time

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected successfully to Mosquitto!")
        print("✅ TLS handshake completed")
        print("✅ Authentication successful")
        client.subscribe("hospital/#")
        print("✅ Subscribed to hospital/#")
    else:
        print(f"❌ Connection failed with code {rc}")
        error_messages = {
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorized"
        }
        if rc in error_messages:
            print(f"   Error: {error_messages[rc]}")

def on_message(client, userdata, msg):
    print(f"📨 Message received: {msg.topic}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"⚠️ Unexpected disconnection (code {rc})")

print("=" * 60)
print("MQTT TLS Connection Test")
print("=" * 60)
print()
print("Testing connection from host machine to Mosquitto broker")
print("This simulates what the ESP32 is trying to do")
print()

# Create client
client = mqtt.Client("HostTestClient")

# Set credentials
username = "hospitalEsp32"
password = "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF+Q="
client.username_pw_set(username, password)
print(f"Username: {username}")
print(f"Password: {password[:20]}...")
print()

# TLS configuration
ca_cert_path = "mosquitto/certs/ca.crt"
print(f"CA Certificate: {ca_cert_path}")

try:
    client.tls_set(
        ca_certs=ca_cert_path,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    print("✅ TLS configured (TLS 1.2)")
except Exception as e:
    print(f"❌ TLS configuration failed: {e}")
    print("   Make sure ca.crt file exists in mosquitto/certs/")
    exit(1)

print()

# Set callbacks
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

# Connect
broker = "192.168.0.113"
port = 8883
print(f"Connecting to {broker}:{port}...")
print(f"   This is the same address the ESP32 is using")
print()

try:
    client.connect(broker, port, 60)
    print("Socket connected, starting TLS handshake...")

    # Start loop
    client.loop_start()

    # Wait for connection
    timeout = 10
    start = time.time()
    while not client.is_connected() and (time.time() - start) < timeout:
        time.sleep(0.1)

    if client.is_connected():
        print()
        print("=" * 60)
        print("SUCCESS! ✅")
        print("=" * 60)
        print()
        print("Mosquitto broker IS accessible from the WiFi network.")
        print("The issue is likely with the ESP32 TLS library configuration.")
        print()
        print("Recommended next steps:")
        print("1. Try using wifiClient.setInsecure() on ESP32 temporarily")
        print("2. Check ESP32 WiFiClientSecure library version")
        print("3. Verify ESP32 ca.crt file matches mosquitto ca.crt exactly")
        print()

        # Keep connection alive for a few seconds
        time.sleep(5)
    else:
        print()
        print("=" * 60)
        print("TIMEOUT ⏰")
        print("=" * 60)
        print()
        print("Connection timed out after TLS handshake.")
        print("This suggests TLS negotiation issues.")

    client.loop_stop()
    client.disconnect()

except ConnectionRefusedError:
    print()
    print("=" * 60)
    print("CONNECTION REFUSED ❌")
    print("=" * 60)
    print()
    print("Mosquitto is NOT accessible from this network.")
    print()
    print("Possible causes:")
    print("1. Mosquitto listener not bound to 0.0.0.0")
    print("2. Docker port binding issue")
    print("3. Windows Firewall blocking port 8883")
    print()
    print("Solutions:")
    print("1. Check mosquitto.conf: listener 8883 0.0.0.0")
    print("2. Restart Mosquitto: docker restart hospital-mosquitto")
    print("3. Allow firewall: netsh advfirewall firewall add rule name='Mosquitto' dir=in action=allow protocol=TCP localport=8883")

except ssl.SSLError as e:
    print()
    print("=" * 60)
    print("TLS ERROR ❌")
    print("=" * 60)
    print()
    print(f"TLS handshake failed: {e}")
    print()
    print("Possible causes:")
    print("1. CA certificate mismatch")
    print("2. Server certificate invalid for this IP")
    print("3. TLS protocol version mismatch")

except Exception as e:
    print()
    print("=" * 60)
    print("ERROR ❌")
    print("=" * 60)
    print()
    print(f"Connection failed: {e}")
    print()
    print("Check:")
    print("1. Mosquitto is running: docker ps | findstr mosquitto")
    print("2. Port 8883 is exposed: docker port hospital-mosquitto")
    print("3. Network connectivity: ping 192.168.0.113")

print()
print("Test complete.")
