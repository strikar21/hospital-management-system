#!/usr/bin/env python3
import hmac
import hashlib
import base64
import time

def generate_signature(method, url_path, body, timestamp, secret_key):
    """Generate HMAC-SHA256 signature for request"""
    canonical_string = f"{method}\n{url_path}\n{body}\n{timestamp}"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        canonical_string.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')

def test_request_signing():
    print("Testing Request Signing...")
    
    # Test data
    method = "POST"
    url_path = "/api/v1/patients/pat_001/case-entries"
    body = '{"entry_type":"note","description":"Test note","performed_by":"Dr. Smith"}'
    timestamp = str(int(time.time()))
    secret_key = "hospital-streaming-secret-key-change-in-production-2024"
    
    # Generate signature
    signature = generate_signature(method, url_path, body, timestamp, secret_key)
    
    print(f"Method: {method}")
    print(f"Path: {url_path}")
    print(f"Body: {body}")
    print(f"Timestamp: {timestamp}")
    print(f"Signature: {signature}")
    print()
    print("Headers to include:")
    print(f"X-Signature: {signature}")
    print(f"X-Timestamp: {timestamp}")
    print()
    print("[OK] Request signing test completed!")

if __name__ == "__main__":
    test_request_signing()