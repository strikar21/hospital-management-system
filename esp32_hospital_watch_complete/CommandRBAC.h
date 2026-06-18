/**
 * CommandRBAC.h
 * Hospital Watch - Role-Based Access Control for MQTT Commands
 *
 * PURPOSE:
 * - Enforces access control on management commands
 * - Prevents unauthorized device control
 * - Validates command origin and user permissions
 *
 * SECURITY THREAT MODEL:
 * 1. Attacker publishes malicious command to MQTT topic
 * 2. Device executes command without authorization check
 * 3. Example attacks:
 *    - Unassign device from patient → data loss
 *    - Modify alert thresholds → missed critical alerts
 *    - Trigger false alarms → alert fatigue
 *
 * SOLUTION:
 * - Commands must include userId and signature
 * - Backend validates user has permission before forwarding
 * - Device verifies signature using shared secret
 * - Role hierarchy: ADMIN > DOCTOR > NURSE > DEVICE
 *
 * REGULATORY COMPLIANCE:
 * - HIPAA: Access control for PHI modifications
 * - ISO 27001: Authentication and authorization
 * - FDA Cybersecurity: Device management security
 *
 * USAGE:
 *   CommandRBAC rbac;
 *
 *   void handleMQTTCommand(char* topic, byte* payload, unsigned int length) {
 *       StaticJsonDocument<512> cmd;
 *       deserializeJson(cmd, payload, length);
 *
 *       // Verify command authorization
 *       if (!rbac.isAuthorized(cmd, CommandRBAC::ROLE_ADMIN)) {
 *           Serial.println("❌ Unauthorized command");
 *           sendCommandAck(cmd["command"], "unauthorized");
 *           return;
 *       }
 *
 *       // Execute command...
 *   }
 *
 * Author: ESP32 Hospital Watch Security Team
 * Date: 2025-01-23
 * Version: 1.0.0
 */

#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <mbedtls/md.h>
#include <mbedtls/base64.h>

class CommandRBAC {
public:
    // Role hierarchy (higher number = more privileges)
    enum Role {
        ROLE_NONE = 0,      // No permissions
        ROLE_DEVICE = 1,    // Device self-operations only
        ROLE_NURSE = 2,     // View vitals, acknowledge alerts
        ROLE_DOCTOR = 3,    // All NURSE + modify thresholds
        ROLE_ADMIN = 4      // All DOCTOR + device management
    };

    // Command categories and required roles
    struct CommandPermission {
        const char* command;
        Role requiredRole;
        bool requiresSignature;
    };

private:
    // Shared secret for command signing (from provisioning)
    uint8_t sharedSecret[32];
    bool initialized;

    // Statistics
    uint32_t totalCommands;
    uint32_t authorizedCommands;
    uint32_t unauthorizedCommands;
    uint32_t signatureFailures;

    // Command permission table
    static const CommandPermission permissions[];
    static const int permissionsCount;

    /**
     * Load shared secret from NVS
     * In production, this would be provisioned during device registration
     */
    void loadSharedSecret() {
        // TODO: Load from secure NVS storage
        // For now, derive from chip ID (same as HMAC key)
        uint64_t chipId = ESP.getEfuseMac();
        for (int i = 0; i < 32; i++) {
            sharedSecret[i] = (chipId >> (i % 8 * 8)) & 0xFF;
            sharedSecret[i] ^= (i * 0xA5);  // Different mixing than HMAC
        }

        Serial.println("✅ Command shared secret loaded");
        initialized = true;
    }

    /**
     * Compute command signature
     * Signature = HMAC-SHA256(command + userId + timestamp, sharedSecret)
     */
    String computeSignature(const String& command, const String& userId,
                           unsigned long timestamp) {
        // Create message to sign
        String message = command + "|" + userId + "|" + String(timestamp);

        uint8_t hmac[32];

        mbedtls_md_context_t ctx;
        mbedtls_md_init(&ctx);
        const mbedtls_md_info_t* mdInfo = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
        mbedtls_md_setup(&ctx, mdInfo, 1);

        mbedtls_md_hmac_starts(&ctx, sharedSecret, sizeof(sharedSecret));
        mbedtls_md_hmac_update(&ctx, (const uint8_t*)message.c_str(), message.length());
        mbedtls_md_hmac_finish(&ctx, hmac);
        mbedtls_md_free(&ctx);

        // Base64 encode
        uint8_t b64[64];
        size_t olen;
        mbedtls_base64_encode(b64, sizeof(b64), &olen, hmac, 32);

        return String((char*)b64);
    }

    /**
     * Get required role for command
     */
    Role getRequiredRole(const String& command) {
        for (int i = 0; i < permissionsCount; i++) {
            if (strcmp(permissions[i].command, command.c_str()) == 0) {
                return permissions[i].requiredRole;
            }
        }

        // Unknown command - require admin
        Serial.printf("⚠️  Unknown command: %s (requiring ADMIN)\n", command.c_str());
        return ROLE_ADMIN;
    }

    /**
     * Check if signature is required for command
     */
    bool requiresSignature(const String& command) {
        for (int i = 0; i < permissionsCount; i++) {
            if (strcmp(permissions[i].command, command.c_str()) == 0) {
                return permissions[i].requiresSignature;
            }
        }

        // Unknown command - require signature
        return true;
    }

public:
    CommandRBAC() : initialized(false), totalCommands(0), authorizedCommands(0),
                    unauthorizedCommands(0), signatureFailures(0) {
        loadSharedSecret();
    }

    /**
     * Check if command is authorized
     *
     * @param cmdDoc JSON command document with:
     *               - command: Command name
     *               - userId: User ID issuing command
     *               - role: User's role (from backend)
     *               - timestamp: Unix timestamp
     *               - signature: HMAC signature (optional)
     * @param minimumRole Minimum role required (optional override)
     * @return true if authorized
     */
    bool isAuthorized(JsonDocument& cmdDoc, Role minimumRole = ROLE_NONE) {
        totalCommands++;

        if (!initialized) {
            Serial.println("❌ CommandRBAC not initialized");
            unauthorizedCommands++;
            return false;
        }

        // Extract command fields
        const char* command = cmdDoc["command"] | "";
        const char* userId = cmdDoc["userId"] | "";
        Role userRole = static_cast<Role>(cmdDoc["role"].as<int>());
        unsigned long timestamp = cmdDoc["timestamp"] | 0;
        const char* signature = cmdDoc["signature"] | "";

        // Validate required fields
        if (strlen(command) == 0) {
            Serial.println("❌ Missing command field");
            unauthorizedCommands++;
            return false;
        }

        // Get required role for command
        Role requiredRole = getRequiredRole(command);
        if (minimumRole > requiredRole) {
            requiredRole = minimumRole;  // Use override if stricter
        }

        // Check role hierarchy
        if (userRole < requiredRole) {
            Serial.printf("❌ Insufficient permissions: %s requires %d, user has %d\n",
                         command, requiredRole, userRole);
            unauthorizedCommands++;
            return false;
        }

        // Verify timestamp (prevent replay attacks)
        unsigned long now = millis();
        unsigned long age = (now > timestamp) ? (now - timestamp) : (timestamp - now);
        const unsigned long MAX_AGE = 300000;  // 5 minutes

        if (age > MAX_AGE) {
            Serial.printf("❌ Command too old: %lu ms (max: %lu ms)\n", age, MAX_AGE);
            unauthorizedCommands++;
            return false;
        }

        // Verify signature if required
        if (requiresSignature(command)) {
            if (strlen(signature) == 0) {
                Serial.printf("❌ Missing signature for: %s\n", command);
                signatureFailures++;
                unauthorizedCommands++;
                return false;
            }

            String expectedSig = computeSignature(command, userId, timestamp);
            if (strcmp(signature, expectedSig.c_str()) != 0) {
                Serial.printf("❌ Invalid signature for: %s\n", command);
                Serial.printf("   Expected: %s\n", expectedSig.c_str());
                Serial.printf("   Received: %s\n", signature);
                signatureFailures++;
                unauthorizedCommands++;
                return false;
            }
        }

        // All checks passed
        authorizedCommands++;
        Serial.printf("✅ Authorized: %s by user %s (role: %d)\n",
                     command, userId, userRole);
        return true;
    }

    /**
     * Create signed command (for device→backend commands)
     */
    void signCommand(JsonDocument& cmd, const String& command, const String& userId) {
        unsigned long timestamp = millis();
        cmd["command"] = command;
        cmd["userId"] = userId;
        cmd["timestamp"] = timestamp;
        cmd["signature"] = computeSignature(command, userId, timestamp);
    }

    /**
     * Get statistics
     */
    void printStats() {
        Serial.println("📊 Command RBAC Statistics:");
        Serial.printf("   Total commands: %u\n", totalCommands);
        Serial.printf("   Authorized: %u (%.1f%%)\n",
                     authorizedCommands,
                     totalCommands > 0 ? (authorizedCommands * 100.0 / totalCommands) : 0);
        Serial.printf("   Unauthorized: %u (%.1f%%)\n",
                     unauthorizedCommands,
                     totalCommands > 0 ? (unauthorizedCommands * 100.0 / totalCommands) : 0);
        Serial.printf("   Signature failures: %u\n", signatureFailures);

        if (unauthorizedCommands > 0) {
            Serial.println("   ⚠️  Unauthorized command attempts detected - possible attack");
        }
    }

    uint32_t getUnauthorizedAttempts() const { return unauthorizedCommands; }
    uint32_t getSignatureFailures() const { return signatureFailures; }
};

// Command permission table
const CommandRBAC::CommandPermission CommandRBAC::permissions[] = {
    // Device self-operations (no signature needed - internal use)
    {"HEARTBEAT", CommandRBAC::ROLE_DEVICE, false},
    {"STATUS", CommandRBAC::ROLE_DEVICE, false},

    // Nurse operations (view/acknowledge only)
    {"GET_VITALS", CommandRBAC::ROLE_NURSE, false},
    {"ACK_ALERT", CommandRBAC::ROLE_NURSE, true},

    // Doctor operations (modify settings)
    {"SET_THRESHOLD", CommandRBAC::ROLE_DOCTOR, true},
    {"CALIBRATE", CommandRBAC::ROLE_DOCTOR, true},
    {"SET_PATIENT", CommandRBAC::ROLE_DOCTOR, true},

    // Admin operations (device management)
    {"ASSIGN", CommandRBAC::ROLE_ADMIN, true},
    {"UNASSIGN", CommandRBAC::ROLE_ADMIN, true},
    {"FACTORY_RESET", CommandRBAC::ROLE_ADMIN, true},
    {"UPDATE_FIRMWARE", CommandRBAC::ROLE_ADMIN, true},
    {"SET_CONFIG", CommandRBAC::ROLE_ADMIN, true},
    {"REBOOT", CommandRBAC::ROLE_ADMIN, true}
};

const int CommandRBAC::permissionsCount = sizeof(CommandRBAC::permissions) / sizeof(CommandRBAC::CommandPermission);
