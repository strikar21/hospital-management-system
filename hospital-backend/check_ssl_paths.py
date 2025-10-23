"""
Check if SSL certificate paths resolve correctly
"""
import os
from app.core.config import settings

print("\n[SSL Configuration from settings]")
print(f"  Enable SSL: {settings.enableSsl}")
print(f"  SSL Cert Path (config): {settings.sslCertPath}")
print(f"  SSL Key Path (config): {settings.sslKeyPath}")

print("\n[Checking if paths are absolute or relative]")
cert_is_absolute = os.path.isabs(settings.sslCertPath) if settings.sslCertPath else False
key_is_absolute = os.path.isabs(settings.sslKeyPath) if settings.sslKeyPath else False
print(f"  Cert path is absolute: {cert_is_absolute}")
print(f"  Key path is absolute: {key_is_absolute}")

print("\n[Current working directory]")
cwd = os.getcwd()
print(f"  CWD: {cwd}")

print("\n[Resolving paths]")
if settings.sslCertPath:
    cert_path = settings.sslCertPath if os.path.isabs(settings.sslCertPath) else os.path.join(cwd, settings.sslCertPath)
    print(f"  Resolved cert path: {cert_path}")
    print(f"  Cert exists: {os.path.exists(cert_path)}")

if settings.sslKeyPath:
    key_path = settings.sslKeyPath if os.path.isabs(settings.sslKeyPath) else os.path.join(cwd, settings.sslKeyPath)
    print(f"  Resolved key path: {key_path}")
    print(f"  Key exists: {os.path.exists(key_path)}")

print("\n[What main.py would check]")
cert_check = os.path.exists(settings.sslCertPath)
key_check = os.path.exists(settings.sslKeyPath)
print(f"  os.path.exists(settings.sslCertPath): {cert_check}")
print(f"  os.path.exists(settings.sslKeyPath): {key_check}")

if cert_check and key_check:
    print("\n[Result] SSL files found - backend SHOULD start with HTTPS")
else:
    print("\n[Result] SSL files NOT found at relative paths - backend starts HTTP")
