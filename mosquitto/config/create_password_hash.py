#!/usr/bin/env python3
"""Generate Mosquitto-compatible password hash"""
import hashlib
import base64
import os

# Password from generated_password.txt
password = b'ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q='
username = 'hospitalEsp32'

# Generate random salt (12 bytes - Mosquitto default)
salt = os.urandom(12)

# Generate PBKDF2-HMAC-SHA512 hash (101 iterations - Mosquitto default)
hash_value = hashlib.pbkdf2_hmac('sha512', password, salt, 101)

# Encode to base64
salt_b64 = base64.b64encode(salt).decode()
hash_b64 = base64.b64encode(hash_value).decode()

# Mosquitto password file format: username:$7$salt$hash
password_line = f"{username}:$7${salt_b64}${hash_b64}"

# Write to passwords.txt
with open('passwords.txt', 'w') as f:
    f.write(password_line + '\n')

print("Password file created: passwords.txt")
print(f"Username: {username}")
print(f"Password format: Mosquitto $7$ (PBKDF2-SHA512)")
