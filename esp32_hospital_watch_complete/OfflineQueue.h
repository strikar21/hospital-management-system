/**
 * OfflineQueue.h
 *
 * SPIFFS-based offline message queue for the ESP32 Hospital Watch.
 * Buffers vitals, alerts, and waveform payloads when MQTT is unavailable
 * and replays them in order once connectivity is restored.
 *
 * Directories:
 *   /queue/vitals    — up to 50 messages (50 s of vitals at 1s interval)
 *   /queue/alerts    — up to 20 messages
 *   /queue/waveforms — up to 10 messages (lowest priority, dropped first)
 *
 * Dependencies (defined in the main .ino sketch):
 *   extern PubSubClient mqttClient
 *   extern String deviceId
 *   bool publishWithRetry(const char* topic, const char* payload, int maxRetries)
 */

#ifndef OFFLINE_QUEUE_H
#define OFFLINE_QUEUE_H

#include <Arduino.h>
#include <SPIFFS.h>
#include <PubSubClient.h>
#include "SPIFFSManager.h"

// ── Globals defined in the main .ino sketch ──────────────────────────────────
extern PubSubClient mqttClient;
extern String deviceId;

// Forward declaration — defined in the main .ino sketch
bool publishWithRetry(const char* topic, const char* payload, int maxRetries = 3);

// ─────────────────────────────────────────────────────────────────────────────

class OfflineQueue {
public:

    bool saveVitals(String payload)   { return saveToFile("/queue/vitals",    payload); }
    bool saveAlert(String payload)    { return saveToFile("/queue/alerts",    payload); }
    bool saveWaveform(String payload) { return saveToFile("/queue/waveforms", payload); }

    bool saveVitalsBinary(const uint8_t* data, size_t len) {
        return saveBinaryToFile("/queue/vitals", data, len);
    }

    /**
     * Replay all queued messages over MQTT.
     * Call when MQTT reconnects (e.g., every 30 s from the main loop).
     */
    void processPendingMessages() {
        if (!mqttClient.connected()) {
            Serial.println("Cannot process queue — MQTT disconnected");
            return;
        }

        Serial.println("Processing offline queue...");

        sendBatch("/queue/vitals",    "hospital/devices/" + deviceId + "/vitals");
        sendBatch("/queue/alerts",    "hospital/devices/" + deviceId + "/alerts");
        sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");

        Serial.println("Offline queue processing complete");
    }

    /**
     * Delete every queued message.
     * Call on patient unassign to prevent data leakage to the next patient.
     */
    void clearAll() {
        if (!SPIFFSManager::isMounted()) {
            Serial.println("SPIFFS not mounted — cannot clear queue");
            return;
        }

        int total = 0;
        total += clearDirectory("/queue/vitals");
        total += clearDirectory("/queue/alerts");
        total += clearDirectory("/queue/waveforms");

        Serial.printf("Cleared %d queued messages (patient data removed)\n", total);
    }

private:
    static const int MAX_VITALS    = 50;
    static const int MAX_ALERTS    = 20;
    static const int MAX_WAVEFORMS = 10;

    // ── SPIFFS health ─────────────────────────────────────────────────────────

    void checkSPIFFSUsage() {
        size_t total = SPIFFS.totalBytes();
        size_t used  = SPIFFS.usedBytes();
        float  usage = (used * 100.0f) / total;

        if (usage <= 60.0f) return;

        Serial.printf("SPIFFS critically full: %.1f%% — emergency cleanup\n", usage);

        int waveforms = getFileCount("/queue/waveforms");
        int vitals    = getFileCount("/queue/vitals");
        int alerts    = getFileCount("/queue/alerts");
        int deleted   = 0;

        while (usage > 50.0f && deleted < 50 && (waveforms > 0 || vitals > 0 || alerts > 0)) {
            if (waveforms > 0) {
                deleteOldestFile("/queue/waveforms");
                waveforms--;
            } else if (vitals > 5) {
                deleteOldestFile("/queue/vitals");
                vitals--;
            } else if (alerts > 2) {
                deleteOldestFile("/queue/alerts");
                alerts--;
            } else {
                break;
            }
            deleted++;
            if (deleted % 10 == 0) {
                used  = SPIFFS.usedBytes();
                usage = (used * 100.0f) / total;
            }
        }

        used  = SPIFFS.usedBytes();
        usage = (used * 100.0f) / total;
        Serial.printf("SPIFFS cleanup: %d files deleted, %.1f%% used\n", deleted, usage);
    }

    // ── Save ──────────────────────────────────────────────────────────────────

    bool saveBinaryToFile(String dir, const uint8_t* data, size_t len) {
        if (!SPIFFSManager::isMounted()) {
            Serial.println("SPIFFS not mounted — cannot save offline data");
            return false;
        }
        if (len == 0 || len > 512) return false;

        checkSPIFFSUsage();

        if (getFileCount(dir) >= MAX_VITALS) {
            deleteOldestFile(dir);
        }

        // Use .bin suffix so sendBatch knows to use binary publish
        String filename = dir + "/" + String(millis()) + ".bin";
        File file = SPIFFS.open(filename, "w");
        if (!file) {
            checkSPIFFSUsage();
            file = SPIFFS.open(filename, "w");
            if (!file) {
                Serial.println("Cannot create binary queue file — SPIFFS may be full");
                return false;
            }
        }

        size_t written = file.write(data, len);
        file.close();

        if (written != len) {
            SPIFFS.remove(filename);
            return false;
        }

        Serial.printf("Queued binary vitals offline: %s (%u bytes)\n",
                      filename.c_str(), (unsigned)written);
        return true;
    }

    bool saveToFile(String dir, String payload) {
        if (!SPIFFSManager::isMounted()) {
            Serial.println("SPIFFS not mounted — cannot save offline data");
            return false;
        }

        checkSPIFFSUsage();

        int maxFiles = (dir.indexOf("vitals") >= 0) ? MAX_VITALS :
                       (dir.indexOf("alerts") >= 0) ? MAX_ALERTS : MAX_WAVEFORMS;

        if (getFileCount(dir) >= maxFiles) {
            deleteOldestFile(dir);
        }

        String filename = dir + "/" + String(millis()) + ".json";
        File file = SPIFFS.open(filename, "w");

        if (!file) {
            // One emergency retry after cleanup
            checkSPIFFSUsage();
            file = SPIFFS.open(filename, "w");
            if (!file) {
                Serial.println("Cannot create queue file — SPIFFS may be full");
                return false;
            }
        }

        if (payload.length() > 2048) {
            payload = payload.substring(0, 2048);
        }

        size_t written = file.print(payload);
        file.close();

        if (written == 0) {
            SPIFFS.remove(filename);
            return false;
        }

        Serial.printf("Queued offline: %s (%u bytes)\n", filename.c_str(), (unsigned)written);
        return true;
    }

    // ── Replay ────────────────────────────────────────────────────────────────

    bool sendBatch(String queueDir, String topic) {
        if (!SPIFFSManager::isMounted()) return false;

        File root = SPIFFS.open(queueDir, "r");
        if (!root || !root.isDirectory()) return false;

        int sent = 0, failed = 0;

        File file = root.openNextFile();
        while (file) {
            if (!file.isDirectory()) {
                String fullPath = String(file.path());
                bool isBinary = fullPath.endsWith(".bin");
                bool ok = false;

                if (isBinary) {
                    // Binary frame (e.g. 40-byte HPROT vitals) — publish as bytes
                    size_t flen = file.size();
                    if (flen > 0 && flen <= 512) {
                        uint8_t buf[512];
                        size_t rd = file.read(buf, flen);
                        file.close();
                        if (rd == flen) {
                            ok = mqttClient.publish(topic.c_str(), buf, (unsigned int)flen, false);
                        }
                    } else {
                        file.close();
                    }
                } else {
                    String payload = file.readString();
                    file.close();
                    ok = publishWithRetry(topic.c_str(), payload.c_str(), 2);
                }

                if (ok) {
                    SPIFFS.remove(fullPath);
                    sent++;
                    Serial.printf("Sent queued: %s (deleted)\n", fullPath.c_str());
                } else {
                    failed++;
                    break;
                }
            } else {
                file = root.openNextFile();
                continue;
            }
            file = root.openNextFile();
        }
        root.close();

        if (sent   > 0) Serial.printf("Sent %d queued messages from %s\n",   sent,   queueDir.c_str());
        if (failed > 0) Serial.printf("%d messages remain in %s\n", failed, queueDir.c_str());

        return (failed == 0);
    }

    // ── Directory helpers ─────────────────────────────────────────────────────

    int getFileCount(String dir) {
        if (!SPIFFSManager::isMounted()) return 0;

        File root = SPIFFS.open(dir, "r");
        if (!root || !root.isDirectory()) return 0;

        int count = 0;
        File file = root.openNextFile();
        while (file) {
            if (!file.isDirectory()) count++;
            file = root.openNextFile();
        }
        root.close();
        return count;
    }

    void deleteOldestFile(String dir) {
        if (!SPIFFSManager::isMounted()) return;

        File root = SPIFFS.open(dir, "r");
        if (!root || !root.isDirectory()) return;

        String oldest;
        unsigned long oldestTime = 0xFFFFFFFF;

        File file = root.openNextFile();
        while (file) {
            if (!file.isDirectory()) {
                String name = String(file.name());
                int slash   = name.lastIndexOf('/');
                int dot     = name.lastIndexOf('.');
                if (slash >= 0 && dot > slash) {
                    unsigned long ts = name.substring(slash + 1, dot).toInt();
                    if (ts < oldestTime) { oldestTime = ts; oldest = name; }
                }
            }
            file = root.openNextFile();
        }
        root.close();

        if (oldest.length() > 0) {
            SPIFFS.remove(oldest);
            Serial.printf("Deleted oldest queued file: %s\n", oldest.c_str());
        }
    }

    int clearDirectory(String dir) {
        File root = SPIFFS.open(dir, "r");
        if (!root || !root.isDirectory()) return 0;

        int count = 0;
        File file = root.openNextFile();
        while (file) {
            if (!file.isDirectory()) {
                String name = String(file.name());
                file.close();
                SPIFFS.remove(name);
                count++;
            } else {
                file = root.openNextFile();
            }
            // Re-open directory to get the next file after deletion
            // SPIFFS iteration is stable after remove in ESP-IDF
            file = root.openNextFile();
        }
        root.close();
        return count;
    }
};

#endif // OFFLINE_QUEUE_H
