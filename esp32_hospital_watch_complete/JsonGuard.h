/**
 * JsonGuard.h
 * Hospital Watch - Smart JSON Memory Manager
 *
 * PURPOSE:
 * - Prevents stack overflow from oversized StaticJsonDocument allocations
 * - Provides dynamic allocation with bounds checking
 * - Tracks JSON memory usage for diagnostics
 * - Fails gracefully on OOM conditions
 *
 * PROBLEM SOLVED:
 * - Current code has 15.5 KB of static JSON buffers on stack
 * - waveformDoc (8KB) + statusDoc (4KB) + vitalsDoc (2KB) + commandDoc (1KB) + alertDoc (512B)
 * - ESP32 has only 320KB RAM total, ~40KB stack per task
 * - Large stack allocations risk stack overflow
 *
 * SOLUTION:
 * - Use heap allocation for large (>1KB) documents
 * - Stack allocation for small (<1KB) documents
 * - Automatic cleanup with RAII pattern
 * - Memory usage tracking
 *
 * USAGE:
 *   // Small documents (<1KB) - use stack:
 *   StaticJsonDocument<512> doc;
 *
 *   // Large documents (>1KB) - use JsonGuard:
 *   JsonGuard<4096> doc;
 *   if (!doc.isValid()) {
 *       Serial.println("❌ Out of memory");
 *       return;
 *   }
 *   doc->["key"] = "value";  // Use like normal JsonDocument
 *
 * Author: ESP32 Hospital Watch Team
 * Date: 2025-01-23
 * Version: 1.0.0
 */

#pragma once

#include <ArduinoJson.h>

// Memory usage tracker
class JsonMemoryTracker {
private:
    static size_t totalAllocated;
    static size_t peakAllocated;
    static uint32_t allocationCount;
    static uint32_t failureCount;

public:
    static void allocated(size_t bytes) {
        totalAllocated += bytes;
        allocationCount++;
        if (totalAllocated > peakAllocated) {
            peakAllocated = totalAllocated;
        }
    }

    static void freed(size_t bytes) {
        if (totalAllocated >= bytes) {
            totalAllocated -= bytes;
        }
    }

    static void failed(size_t bytes) {
        failureCount++;
        Serial.printf("❌ JSON allocation failed: %u bytes (failures: %u)\n",
                     bytes, failureCount);
    }

    static void printStats() {
        Serial.println("📊 JSON Memory Statistics:");
        Serial.printf("   Current allocated: %u bytes\n", totalAllocated);
        Serial.printf("   Peak allocated: %u bytes\n", peakAllocated);
        Serial.printf("   Total allocations: %u\n", allocationCount);
        Serial.printf("   Failed allocations: %u\n", failureCount);
        Serial.printf("   Free heap: %u bytes\n", ESP.getFreeHeap());
    }

    static size_t getCurrentUsage() { return totalAllocated; }
    static size_t getPeakUsage() { return peakAllocated; }
    static uint32_t getFailureCount() { return failureCount; }
};

// Initialize static members
size_t JsonMemoryTracker::totalAllocated = 0;
size_t JsonMemoryTracker::peakAllocated = 0;
uint32_t JsonMemoryTracker::allocationCount = 0;
uint32_t JsonMemoryTracker::failureCount = 0;

// Smart JSON document with RAII and bounds checking
template<size_t capacity>
class JsonGuard {
private:
    DynamicJsonDocument* doc;
    size_t allocatedSize;
    bool valid;

public:
    // Constructor - allocate on heap
    JsonGuard() : doc(nullptr), allocatedSize(capacity), valid(false) {
        // Check if we have enough free heap
        size_t freeHeap = ESP.getFreeHeap();
        size_t requiredHeap = capacity + 512;  // Add safety margin for malloc overhead

        if (freeHeap < requiredHeap) {
            Serial.printf("⚠️  Insufficient heap for JSON: need %u, have %u\n",
                         requiredHeap, freeHeap);
            JsonMemoryTracker::failed(capacity);
            return;
        }

        try {
            doc = new DynamicJsonDocument(capacity);
            if (doc) {
                JsonMemoryTracker::allocated(capacity);
                valid = true;
            } else {
                JsonMemoryTracker::failed(capacity);
            }
        } catch (const std::bad_alloc& e) {
            Serial.printf("❌ JSON allocation exception: %s\n", e.what());
            JsonMemoryTracker::failed(capacity);
            doc = nullptr;
        }
    }

    // Destructor - automatic cleanup
    ~JsonGuard() {
        if (doc) {
            delete doc;
            JsonMemoryTracker::freed(allocatedSize);
        }
    }

    // No copy (prevent double-free)
    JsonGuard(const JsonGuard&) = delete;
    JsonGuard& operator=(const JsonGuard&) = delete;

    // Move semantics (allow transfer of ownership)
    JsonGuard(JsonGuard&& other) noexcept
        : doc(other.doc), allocatedSize(other.allocatedSize), valid(other.valid) {
        other.doc = nullptr;
        other.valid = false;
    }

    // Check if allocation succeeded
    bool isValid() const { return valid && doc != nullptr; }

    // Get document (use with care)
    DynamicJsonDocument* get() { return doc; }

    // Arrow operator for easy access
    DynamicJsonDocument* operator->() { return doc; }

    // Dereference operator
    DynamicJsonDocument& operator*() { return *doc; }

    // Serialize to string with size check
    bool serializeTo(String& output, size_t maxSize = 0) {
        if (!valid || !doc) return false;

        size_t estimatedSize = measureJson(*doc);
        if (maxSize > 0 && estimatedSize > maxSize) {
            Serial.printf("⚠️  JSON too large: %u bytes (max: %u)\n",
                         estimatedSize, maxSize);
            return false;
        }

        serializeJson(*doc, output);
        return true;
    }

    // Get size information
    size_t getCapacity() const { return capacity; }
    size_t getSize() const { return doc ? measureJson(*doc) : 0; }
    size_t getUsagePercent() const {
        return doc ? (measureJson(*doc) * 100 / capacity) : 0;
    }
};

// Convenience macro for critical sections
#define JSON_GUARD_OR_RETURN(guard, retval) \
    if (!guard.isValid()) { \
        Serial.println("❌ JSON allocation failed - insufficient memory"); \
        return retval; \
    }

#define JSON_GUARD_OR_CONTINUE(guard) \
    if (!guard.isValid()) { \
        Serial.println("❌ JSON allocation failed - skipping"); \
        continue; \
    }
