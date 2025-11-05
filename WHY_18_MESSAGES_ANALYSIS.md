# Why Exactly 18 Queued Waveform Messages?

## The Evidence

Looking at your ESP32 serial log:

```
09:09:14.196 -> 📤 Processing offline queue...
09:09:14.243 -> ... [10 vitals messages sent]
09:09:15.539 -> 📤 Sent 18 queued messages from /queue/waveforms
09:09:15.539 -> ✅ Offline queue processing complete
```

**Every 30 seconds, exactly 18 waveform messages are sent.**

## The Mystery

**Code says:** `const int MAX_WAVEFORMS = 10;` (line 289)

**Reality shows:** 18 messages sent

**This doesn't add up!**

## Hypothesis 1: MAX_WAVEFORMS Limit Not Working

The `saveToFile()` function (lines 291-325) has this logic:

```cpp
// Check file count and delete oldest if limit reached
int fileCount = getFileCount(dir);
int maxFiles = (dir.indexOf("vitals") >= 0) ? MAX_VITALS :
               (dir.indexOf("alerts") >= 0) ? MAX_ALERTS : MAX_WAVEFORMS;

if (fileCount >= maxFiles) {
    deleteOldestFile(dir);  // ← Should prevent more than 10 files
}
```

**If this works correctly, there should NEVER be more than 10 waveform files.**

## Hypothesis 2: The "18" Pattern Reveals the Bug

Let me calculate what 18 messages represents:

**Option A: Time-based accumulation**
- Waveforms stream: 10 messages/second
- 18 messages = 1.8 seconds of data
- **This suggests waveforms are being queued for 1.8 seconds**

**Option B: Two different sessions**
- 10 messages from first disconnection
- 8 messages from second disconnection
- Total: 18 messages

**Option C: MAX_WAVEFORMS bug**
- Code allows 10 files
- But somehow 18 files accumulate
- `getFileCount()` or `deleteOldestFile()` not working?

## Let Me Check The Actual Timestamps

Looking at the filenames in your log:

```
4612194.json  ← timestamp: 4612194 ms = 4.6 seconds after boot
4670228.json  ← timestamp: 4670228 ms = 4.7 seconds after boot
4650720.json
4651312.json
4670823.json
4689740.json
4708842.json
4709465.json
4728575.json
4729200.json
4748288.json
4767389.json
20445.json    ← timestamp: 20445 ms = 20 seconds after boot (?!)
4806414.json
4768019.json
4787104.json
4631208.json
4631798.json
```

**Wait! One file is named `20445.json` - this is from 20 seconds after boot!**

This means:
- Files are being saved from EARLY in the boot process
- They're persisting across multiple queue processing cycles
- **The deleteOldestFile() function is NOT working!**

## The Root Cause - FOUND!

**The `deleteOldestFile()` function is failing to delete old waveforms!**

Let me check why:

### Possibility 1: SPIFFS Directory Listing Bug

```cpp
int getFileCount(String dir) {
    File root = SPIFFS.open(dir, "r");
    if (!root || !root.isDirectory()) {
        return 0;
    }

    int count = 0;
    File file = root.openNextFile();
    while (file) {
        if (!file.isDirectory()) {
            count++;
        }
        file = root.openNextFile();
    }
    root.close();
    return count;
}
```

**Bug:** If SPIFFS fails to open directory properly, `getFileCount()` returns 0, so limit check never triggers!

### Possibility 2: deleteOldestFile() Not Deleting

```cpp
void deleteOldestFile(String dir) {
    File root = SPIFFS.open(dir, "r");
    // ... find oldest file ...
    if (oldestFilename != "") {
        SPIFFS.remove(oldestFilename);  // ← Does this work?
    }
}
```

**Bug:** `SPIFFS.remove()` might fail silently if file is locked or path is incorrect.

## Why This Causes V-Lead Compression

**The accumulation pattern:**
1. ESP32 boots → waveforms queued during initialization (files: 20445.json, etc.)
2. MQTT connects → waveforms stream normally
3. Occasional glitches → more waveforms queued (files: 4612194.json, 4670228.json, etc.)
4. MAX_WAVEFORMS limit NOT enforced → 18 files accumulate over time
5. Every 30 seconds → ALL 18 files sent in BURST
6. Frontend receives burst → **V-leads accumulate extra data**
7. Files NOT deleted → same 18 files sent AGAIN next cycle!

**Look at your log - the SAME filenames repeat every 30 seconds!**

```
09:09:14 -> ✅ Sent queued: 4651482.json
09:09:45 -> ✅ Sent queued: 4651482.json  // ← SAME FILE AGAIN!
09:10:17 -> ✅ Sent queued: 4651482.json  // ← SAME FILE AGAIN!
```

**THE FILES ARE NOT BEING DELETED AFTER SENDING!**

## The REAL Bug

Looking at `sendBatch()` (lines 332-380):

```cpp
if (publishWithRetry(topic.c_str(), payload.c_str(), 2)) {
    // Success - delete file
    file.close();
    SPIFFS.remove(filename);  // ← BUG: Wrong path!
    sentCount++;
}
```

**BUG FOUND:** `filename` is just the basename (e.g., "4651482.json"), but SPIFFS needs full path (e.g., "/queue/waveforms/4651482.json")!

**The file.close() happens, but SPIFFS.remove() fails because path is wrong!**

## The Fix

```cpp
bool sendBatch(String queueDir, String topic) {
    // ... existing code ...

    File file = root.openNextFile();
    while (file) {
        if (!file.isDirectory()) {
            String filename = String(file.name());
            String fullPath = queueDir + "/" + filename;  // ✅ NEW: Build full path
            String payload = file.readString();

            if (publishWithRetry(topic.c_str(), payload.c_str(), 2)) {
                // Success - delete file
                file.close();
                SPIFFS.remove(fullPath);  // ✅ FIXED: Use full path
                sentCount++;
                Serial.println("✅ Sent queued: " + filename);
            } else {
                // Failed - keep file for next attempt
                failCount++;
                Serial.println("⚠️  Failed to send queued: " + filename);
                file.close();
                break;
            }
        }

        file = root.openNextFile();
    }
    // ...
}
```

## Conclusion

**Why exactly 18 messages?**
- Because 18 waveforms were queued during ESP32 boot + early glitches
- **They've NEVER been deleted** due to wrong SPIFFS path in remove()
- Same 18 files sent every 30 seconds forever
- This causes V-lead compression EVERY 30 SECONDS

**The fix:** Use full SPIFFS path when deleting files: `SPIFFS.remove(fullPath)`

**After fix:**
- Files will actually be deleted after sending
- Queue will stay empty during normal streaming
- No more burst uploads
- V-lead compression fixed!

**Shall I implement this fix?**
