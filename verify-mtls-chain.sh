#!/bin/bash
# =====================================================
# mTLS Certificate Chain Verification Script
# Hospital Management System - Mosquitto + ESP32
# =====================================================
#
# Purpose: Verify end-to-end certificate chain integrity
# for mTLS authentication between ESP32 devices, Backend,
# and Mosquitto MQTT broker.
#
# Usage: bash verify-mtls-chain.sh
# Exit: 0 on success, 1 on any failure
#
# =====================================================

# ANSI Color Codes
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
RESET='\033[0m'

# Exit code tracker
EXIT_CODE=0

# Header
echo ""
echo "======================================================"
echo "  mTLS Certificate Chain Verification"
echo "======================================================"
echo ""

# =====================================================
# CHECK 1: File Existence
# =====================================================
echo -e "${BLUE}[CHECK 1]${RESET} Verifying certificate file existence..."
echo ""

MOSQUITTO_CA="mosquitto/certs/hospital_ca.crt"
MOSQUITTO_CA_KEY="mosquitto/certs/hospital_ca.key"
MOSQUITTO_SERVER_CERT="mosquitto/certs/server.crt"
MOSQUITTO_SERVER_KEY="mosquitto/certs/server.key"
MOSQUITTO_BACKEND_CERT="mosquitto/certs/backend.crt"
MOSQUITTO_BACKEND_KEY="mosquitto/certs/backend.key"
ESP32_CA="esp32_hospital_watch_complete/data/ca.crt"
BACKEND_SSL_CERT="hospital-backend/ssl/cert.pem"
BACKEND_SSL_KEY="hospital-backend/ssl/key.pem"

FILES_TO_CHECK=(
    "$MOSQUITTO_CA"
    "$MOSQUITTO_CA_KEY"
    "$MOSQUITTO_SERVER_CERT"
    "$MOSQUITTO_SERVER_KEY"
    "$MOSQUITTO_BACKEND_CERT"
    "$MOSQUITTO_BACKEND_KEY"
    "$ESP32_CA"
    "$BACKEND_SSL_CERT"
    "$BACKEND_SSL_KEY"
)

ALL_FILES_EXIST=true

for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}[OK]${RESET}   $file"
    else
        echo -e "  ${RED}[FAIL]${RESET} $file ${RED}(MISSING)${RESET}"
        ALL_FILES_EXIST=false
        EXIT_CODE=1
    fi
done

echo ""

if [ "$ALL_FILES_EXIST" = false ]; then
    echo -e "${RED}❌ CRITICAL: Missing certificate files. Cannot continue.${RESET}"
    exit 1
fi

# =====================================================
# CHECK 2: CA Fingerprint Comparison
# =====================================================
echo -e "${BLUE}[CHECK 2]${RESET} Comparing CA certificate fingerprints..."
echo ""

# Extract fingerprints
MOSQUITTO_CA_FP=$(openssl x509 -in "$MOSQUITTO_CA" -noout -fingerprint -sha256 2>/dev/null | cut -d'=' -f2)
ESP32_CA_FP=$(openssl x509 -in "$ESP32_CA" -noout -fingerprint -sha256 2>/dev/null | cut -d'=' -f2)

echo "  Mosquitto CA: $MOSQUITTO_CA_FP"
echo "  ESP32 CA:     $ESP32_CA_FP"
echo ""

if [ "$MOSQUITTO_CA_FP" = "$ESP32_CA_FP" ]; then
    echo -e "  ${GREEN}[OK]${RESET}   CA fingerprints match (Mosquitto ↔ ESP32)"
else
    echo -e "  ${RED}[FAIL]${RESET} CA fingerprints DO NOT match!"
    echo -e "  ${YELLOW}WARNING:${RESET} ESP32 will reject Mosquitto server certificate!"
    EXIT_CODE=1
fi

echo ""

# =====================================================
# CHECK 3: Certificate Chain Validation
# =====================================================
echo -e "${BLUE}[CHECK 3]${RESET} Validating certificate chains (signatures)..."
echo ""

# Verify server.crt is signed by hospital_ca.crt
echo "  Testing: server.crt signed by Hospital CA..."
if openssl verify -CAfile "$MOSQUITTO_CA" "$MOSQUITTO_SERVER_CERT" &>/dev/null; then
    echo -e "  ${GREEN}[OK]${RESET}   server.crt signed by Hospital CA"
else
    echo -e "  ${RED}[FAIL]${RESET} server.crt NOT signed by Hospital CA"
    EXIT_CODE=1
fi

# Verify backend.crt is signed by hospital_ca.crt
echo "  Testing: backend.crt signed by Hospital CA..."
if openssl verify -CAfile "$MOSQUITTO_CA" "$MOSQUITTO_BACKEND_CERT" &>/dev/null; then
    echo -e "  ${GREEN}[OK]${RESET}   backend.crt signed by Hospital CA"
else
    echo -e "  ${RED}[FAIL]${RESET} backend.crt NOT signed by Hospital CA"
    EXIT_CODE=1
fi

echo ""

# =====================================================
# CHECK 4: Key-Certificate Modulus Matching
# =====================================================
echo -e "${BLUE}[CHECK 4]${RESET} Verifying private keys match certificates..."
echo ""

# Function to check cert-key pair
check_cert_key_match() {
    local cert=$1
    local key=$2
    local name=$3

    echo "  Testing: $name..."

    local cert_modulus=$(openssl x509 -noout -modulus -in "$cert" 2>/dev/null | openssl md5 | cut -d' ' -f2)
    local key_modulus=$(openssl rsa -noout -modulus -in "$key" 2>/dev/null | openssl md5 | cut -d' ' -f2)

    if [ "$cert_modulus" = "$key_modulus" ]; then
        echo -e "  ${GREEN}[OK]${RESET}   $name modulus match"
    else
        echo -e "  ${RED}[FAIL]${RESET} $name modulus MISMATCH (wrong key?)"
        EXIT_CODE=1
    fi
}

check_cert_key_match "$MOSQUITTO_SERVER_CERT" "$MOSQUITTO_SERVER_KEY" "server.crt ↔ server.key"
check_cert_key_match "$MOSQUITTO_BACKEND_CERT" "$MOSQUITTO_BACKEND_KEY" "backend.crt ↔ backend.key"
check_cert_key_match "$MOSQUITTO_CA" "$MOSQUITTO_CA_KEY" "hospital_ca.crt ↔ hospital_ca.key"

echo ""

# =====================================================
# CHECK 5: Certificate Details Display
# =====================================================
echo -e "${BLUE}[CHECK 5]${RESET} Certificate details (CN, Issuer, Validity)..."
echo ""

# Function to display certificate details
show_cert_details() {
    local cert=$1
    local name=$2

    echo "────────────────────────────────────────────────────"
    echo "Certificate: $name"
    echo "────────────────────────────────────────────────────"

    # Extract details
    local subject=$(openssl x509 -in "$cert" -noout -subject 2>/dev/null | sed 's/subject=//')
    local issuer=$(openssl x509 -in "$cert" -noout -issuer 2>/dev/null | sed 's/issuer=//')
    local not_before=$(openssl x509 -in "$cert" -noout -startdate 2>/dev/null | cut -d'=' -f2)
    local not_after=$(openssl x509 -in "$cert" -noout -enddate 2>/dev/null | cut -d'=' -f2)
    local key_size=$(openssl x509 -in "$cert" -noout -text 2>/dev/null | grep "Public-Key:" | sed 's/.*(\([0-9]*\) bit).*/\1/')

    echo "Subject:    $subject"
    echo "Issuer:     $issuer"
    echo "Not Before: $not_before"
    echo "Not After:  $not_after"
    echo "Key Size:   ${key_size} bit"

    # Check if expired
    if openssl x509 -in "$cert" -noout -checkend 0 &>/dev/null; then
        echo -e "Status:     ${GREEN}Valid (not expired)${RESET}"
    else
        echo -e "Status:     ${RED}EXPIRED${RESET}"
        EXIT_CODE=1
    fi

    echo ""
}

show_cert_details "$MOSQUITTO_CA" "Hospital CA (Mosquitto)"
show_cert_details "$MOSQUITTO_SERVER_CERT" "Mosquitto Server Certificate"
show_cert_details "$MOSQUITTO_BACKEND_CERT" "Backend Client Certificate"
show_cert_details "$ESP32_CA" "ESP32 SPIFFS CA Certificate"

# =====================================================
# SUMMARY
# =====================================================
echo "======================================================"
echo "  VERIFICATION SUMMARY"
echo "======================================================"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED${RESET}"
    echo ""
    echo "Certificate chain is valid and ready for mTLS:"
    echo "  • All certificate files exist"
    echo "  • CA certificates match (Mosquitto ↔ ESP32)"
    echo "  • Server and backend certs signed by Hospital CA"
    echo "  • All private keys match their certificates"
    echo "  • All certificates are valid (not expired)"
    echo ""
    echo "ESP32 should be able to connect to Mosquitto."
else
    echo -e "${RED}❌ FAILURES DETECTED${RESET}"
    echo ""
    echo "Review the failures above and fix them before attempting"
    echo "to connect ESP32 devices to Mosquitto."
    echo ""
    echo "Common fixes:"
    echo "  • Mismatched CAs: Copy mosquitto/certs/hospital_ca.crt"
    echo "    to esp32_hospital_watch_complete/data/ca.crt"
    echo "  • Invalid chains: Re-generate certificates using"
    echo "    hospital-backend/generate_all_certificates.py"
    echo "  • Key mismatches: Ensure cert/key pairs are from same generation"
    echo ""
fi

echo "======================================================"
echo ""

exit $EXIT_CODE
