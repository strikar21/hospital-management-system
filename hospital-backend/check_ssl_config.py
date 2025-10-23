"""
Check if SSL is enabled in backend configuration
"""
from app.core.config import settings

print("\n[Backend SSL Configuration]")
print(f"  Enable SSL: {settings.enableSsl}")
print(f"  SSL Cert Path: {settings.sslCertPath}")
print(f"  SSL Key Path: {settings.sslKeyPath}")

import os
cert_exists = os.path.exists(settings.sslCertPath) if settings.sslCertPath else False
key_exists = os.path.exists(settings.sslKeyPath) if settings.sslKeyPath else False

print(f"\n[SSL Files]")
print(f"  Cert exists: {cert_exists}")
print(f"  Key exists: {key_exists}")

if settings.enableSsl and cert_exists and key_exists:
    print(f"\n[Result] SSL SHOULD BE ENABLED")
else:
    print(f"\n[Result] SSL DISABLED - Backend running HTTP")
