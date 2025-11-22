"""
Run MQTT Consumer Service

Starts the MQTT consumer to listen for device messages
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.mqtt_consumer import MQTTConsumerService

# Load environment variables
load_dotenv()


def main():
    """Start MQTT consumer service"""

    print("=" * 70)
    print("MQTT CONSUMER SERVICE")
    print("=" * 70)

    # Get configuration from environment
    mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    fhir_api_base = os.getenv("FHIR_API_BASE", "http://localhost:8000")

    # Optional: Get JWT token for API authentication
    # You can get this by logging in first:
    # curl -X POST http://localhost:8000/auth/login \
    #   -H "Content-Type: application/json" \
    #   -d '{"staffId": "STF000001", "pin": "1234"}'
    auth_token = os.getenv("AUTH_TOKEN")

    print(f"\nConfiguration:")
    print(f"  MQTT Broker: {mqtt_broker}:{mqtt_port}")
    print(f"  MQTT Auth: {'Yes' if mqtt_username else 'No'}")
    print(f"  FHIR API: {fhir_api_base}")
    print(f"  API Auth: {'Yes' if auth_token else 'No (optional)'}")
    print()

    # Create MQTT consumer
    consumer = MQTTConsumerService(
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        fhir_api_base=fhir_api_base,
        auth_token=auth_token
    )

    # Start consumer (blocking - runs forever until Ctrl+C)
    try:
        consumer.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        consumer.stop()


if __name__ == "__main__":
    main()
