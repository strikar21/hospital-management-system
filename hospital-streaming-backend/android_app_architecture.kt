// 🏥 HOSPITAL ANDROID APP ARCHITECTURE
// Kotlin implementation for ESP32 watch integration

// ===== MAIN ACTIVITY =====
class HospitalDisplayActivity : AppCompatActivity() {
    private lateinit var watchConnectionManager: WatchConnectionManager
    private lateinit var nfcAdapter: NfcAdapter
    private lateinit var apiClient: HospitalApiClient
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_hospital_display)
        
        // Initialize components
        watchConnectionManager = WatchConnectionManager(this)
        apiClient = HospitalApiClient(BASE_URL)
        
        // Setup NFC for tap-to-pair
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        setupNfcListener()
        
        // Start patient display
        loadPatientData()
    }
    
    private fun setupNfcListener() {
        val pendingIntent = PendingIntent.getActivity(
            this, 0, Intent(this, javaClass), PendingIntent.FLAG_MUTABLE
        )
        
        nfcAdapter?.enableForegroundDispatch(
            this, pendingIntent, 
            arrayOf(IntentFilter(NfcAdapter.ACTION_TAG_DISCOVERED)),
            null
        )
    }
    
    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        
        if (NfcAdapter.ACTION_TAG_DISCOVERED == intent?.action) {
            val tag = intent.getParcelableExtra<Tag>(NfcAdapter.EXTRA_TAG)
            handleNfcTap(tag)
        }
    }
    
    private fun handleNfcTap(tag: Tag?) {
        // Extract device ID from NFC tag
        val deviceId = extractDeviceId(tag) ?: return
        
        lifecycleScope.launch {
            try {
                // Start BLE pairing process
                val watchDevice = watchConnectionManager.discoverAndConnect(deviceId)
                if (watchDevice != null) {
                    pairWatchWithPatient(watchDevice)
                } else {
                    showError("Could not connect to watch. Please try again.")
                }
            } catch (e: Exception) {
                showError("Pairing failed: ${e.message}")
            }
        }
    }
    
    private suspend fun pairWatchWithPatient(watch: WatchDevice) {
        try {
            // Call backend to pair device with patient
            val pairResponse = apiClient.pairDevice(
                deviceId = watch.deviceId,
                patientId = getCurrentPatientId(),
                appSessionId = getSessionId(),
                location = getCurrentLocation()
            )
            
            if (pairResponse.success) {
                // Start real-time data streaming
                startVitalsStreaming(watch, pairResponse.streamingConfig)
                updatePatientDisplay(pairResponse.patient)
                showSuccess("Watch paired successfully!")
            }
            
        } catch (e: Exception) {
            showError("Pairing failed: ${e.message}")
        }
    }
}

// ===== WATCH CONNECTION MANAGER =====
class WatchConnectionManager(private val context: Context) {
    private val bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
    private val activeConnections = mutableMapOf<String, WatchConnection>()
    private val maxConnections = 10
    
    companion object {
        const val WATCH_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
        const val VITALS_CHARACTERISTIC_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
    }
    
    suspend fun discoverAndConnect(deviceId: String): WatchDevice? = withContext(Dispatchers.IO) {
        if (activeConnections.size >= maxConnections) {
            throw Exception("Maximum connections reached")
        }
        
        // Scan for BLE devices
        val scanner = bluetoothAdapter.bluetoothLeScanner
        val scanFilter = ScanFilter.Builder()
            .setServiceUuid(ParcelUuid.fromString(WATCH_SERVICE_UUID))
            .build()
        
        val scanSettings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()
        
        return@withContext suspendCancellableCoroutine { continuation ->
            val callback = object : ScanCallback() {
                override fun onScanResult(callbackType: Int, result: ScanResult?) {
                    result?.let { scanResult ->
                        if (matchesDeviceId(scanResult, deviceId)) {
                            scanner.stopScan(this)
                            
                            // Connect to device
                            val gatt = scanResult.device.connectGatt(
                                context, false, createGattCallback(deviceId, continuation)
                            )
                            
                            activeConnections[deviceId] = WatchConnection(deviceId, gatt)
                        }
                    }
                }
                
                override fun onScanFailed(errorCode: Int) {
                    continuation.resume(null)
                }
            }
            
            scanner.startScan(listOf(scanFilter), scanSettings, callback)
            
            // Timeout after 30 seconds
            continuation.invokeOnCancellation {
                scanner.stopScan(callback)
            }
        }
    }
    
    private fun createGattCallback(deviceId: String, continuation: CancellableContinuation<WatchDevice?>) = 
        object : BluetoothGattCallback() {
            override fun onConnectionStateChange(gatt: BluetoothGatt?, status: Int, newState: Int) {
                when (newState) {
                    BluetoothProfile.STATE_CONNECTED -> {
                        gatt?.discoverServices()
                    }
                    BluetoothProfile.STATE_DISCONNECTED -> {
                        activeConnections.remove(deviceId)
                    }
                }
            }
            
            override fun onServicesDiscovered(gatt: BluetoothGatt?, status: Int) {
                if (status == BluetoothGatt.GATT_SUCCESS) {
                    val watchDevice = WatchDevice(deviceId, gatt!!)
                    continuation.resume(watchDevice)
                } else {
                    continuation.resume(null)
                }
            }
            
            override fun onCharacteristicChanged(gatt: BluetoothGatt?, characteristic: BluetoothGattCharacteristic?) {
                characteristic?.let {
                    if (it.uuid.toString() == VITALS_CHARACTERISTIC_UUID) {
                        handleVitalData(deviceId, it.value)
                    }
                }
            }
        }
    
    private val vitalsBatches = mutableMapOf<String, MutableList<VitalReading>>()
    private val batchTimers = mutableMapOf<String, Timer>()
    
    private fun handleVitalData(deviceId: String, data: ByteArray) {
        try {
            // Parse ESP32 vital data packet
            val vitalReading = parseVitalData(data)
            
            // Add to batch for this device
            vitalsBatches.getOrPut(deviceId) { mutableListOf() }.add(vitalReading)
            
            // Send batch every 5 seconds or when 5 readings accumulated
            val batch = vitalsBatches[deviceId]!!
            if (batch.size >= 5) {
                sendBatch(deviceId, batch.toList())
                batch.clear()
                batchTimers[deviceId]?.cancel()
            } else if (batch.size == 1) {
                // Start 5-second timer for this batch
                batchTimers[deviceId] = Timer().apply {
                    schedule(object : TimerTask() {
                        override fun run() {
                            sendBatch(deviceId, batch.toList())
                            batch.clear()
                        }
                    }, 5000)
                }
            }
            
        } catch (e: Exception) {
            Log.e("WatchManager", "Error parsing vital data", e)
        }
    }
    
    private fun parseVitalData(data: ByteArray): VitalReading {
        // ESP32 sends binary packed data (24 bytes):
        // [4B timestamp][2B heart_rate][2B bp_sys][2B bp_dia][2B temp][2B o2_sat][2B resp_rate][6B reserved]
        
        val buffer = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)
        
        val timestamp = buffer.int.toLong() * 1000 // Convert to milliseconds
        val heartRate = buffer.short.toDouble()
        val bpSystolic = buffer.short.toDouble() 
        val bpDiastolic = buffer.short.toDouble()
        val temperature = buffer.short.toDouble() / 10.0 // ESP32 sends temp * 10
        val oxygenSat = buffer.short.toDouble()
        val respiratoryRate = buffer.short.toDouble()
        
        return VitalReading(
            timestamp = Instant.ofEpochMilli(timestamp).toString(),
            vitals = mapOf(
                "heart_rate" to heartRate,
                "blood_pressure_systolic" to bpSystolic,
                "blood_pressure_diastolic" to bpDiastolic,
                "temperature" to temperature,
                "oxygen_saturation" to oxygenSat,
                "respiratory_rate" to respiratoryRate
            ),
            quality = calculateSignalQuality(data),
            batteryLevel = null, // Can be added later
            signalStrength = null
        )
    }
    
    private fun sendBatch(deviceId: String, readings: List<VitalReading>) {
        val connection = activeConnections[deviceId] ?: return
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val apiClient = HospitalApiClient.instance
                val response = apiClient.sendVitalsBatch(
                    patientId = connection.patientId ?: return@launch,
                    batch = VitalsBatch(
                        deviceId = deviceId,
                        patientId = connection.patientId!!,
                        readings = readings,
                        sequence = connection.sequenceNumber++,
                        appInfo = AppInfo(
                            version = BuildConfig.VERSION_NAME,
                            deviceModel = Build.MODEL
                        )
                    )
                )
                
                // Handle alerts from server
                response.alerts.forEach { alert ->
                    handleServerAlert(alert)
                }
                
            } catch (e: Exception) {
                Log.e("WatchManager", "Error sending vitals batch", e)
                // Implement retry logic here
            }
        }
    }
}

// ===== DATA MODELS =====
data class WatchDevice(
    val deviceId: String,
    val gatt: BluetoothGatt,
    val patientId: String? = null
)

data class WatchConnection(
    val deviceId: String,
    val gatt: BluetoothGatt,
    var patientId: String? = null,
    var sequenceNumber: Int = 0,
    val connectedAt: Long = System.currentTimeMillis()
)

data class VitalReading(
    val timestamp: String,
    val vitals: Map<String, Double>,
    val quality: Double,
    val batteryLevel: Int?,
    val signalStrength: Int?
)

data class VitalsBatch(
    val deviceId: String,
    val patientId: String,
    val readings: List<VitalReading>,
    val sequence: Int,
    val appInfo: AppInfo
)

data class AppInfo(
    val version: String,
    val deviceModel: String,
    val buildNumber: Int = BuildConfig.VERSION_CODE
)

// ===== API CLIENT =====
class HospitalApiClient(private val baseUrl: String) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .addInterceptor(LoggingInterceptor())
        .build()
        
    private val gson = Gson()
    
    companion object {
        lateinit var instance: HospitalApiClient
    }
    
    suspend fun pairDevice(
        deviceId: String, 
        patientId: String, 
        appSessionId: String,
        location: String?
    ): PairResponse = withContext(Dispatchers.IO) {
        
        val request = PairRequest(deviceId, patientId, appSessionId, location)
        val response = client.newCall(
            Request.Builder()
                .url("$baseUrl/mobile/devices/pair")
                .post(gson.toJson(request).toRequestBody("application/json".toMediaType()))
                .build()
        ).execute()
        
        if (response.isSuccessful) {
            gson.fromJson(response.body!!.string(), PairResponse::class.java)
        } else {
            throw Exception("Pairing failed: ${response.code} ${response.message}")
        }
    }
    
    suspend fun sendVitalsBatch(
        patientId: String,
        batch: VitalsBatch
    ): BatchResponse = withContext(Dispatchers.IO) {
        
        val response = client.newCall(
            Request.Builder()
                .url("$baseUrl/mobile/vitals/batch/$patientId")
                .post(gson.toJson(batch).toRequestBody("application/json".toMediaType()))
                .build()
        ).execute()
        
        if (response.isSuccessful) {
            gson.fromJson(response.body!!.string(), BatchResponse::class.java)
        } else {
            throw Exception("Batch send failed: ${response.code} ${response.message}")
        }
    }
}

// ===== ESP32 INTEGRATION =====
/*
ESP32 Arduino Code Structure:

```cpp
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Service and characteristic UUIDs
#define SERVICE_UUID        "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define VITALS_CHAR_UUID    "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

struct VitalData {
    uint32_t timestamp;
    uint16_t heart_rate;
    uint16_t bp_systolic;
    uint16_t bp_diastolic; 
    uint16_t temperature;  // * 10 for decimal precision
    uint16_t oxygen_sat;
    uint16_t respiratory_rate;
    uint8_t reserved[6];
} __attribute__((packed));

void sendVitalData() {
    VitalData data = {
        .timestamp = (uint32_t)(millis() / 1000),
        .heart_rate = readHeartRate(),
        .bp_systolic = readBloodPressureSys(),
        .bp_diastolic = readBloodPressureDia(),
        .temperature = (uint16_t)(readTemperature() * 10),
        .oxygen_sat = readOxygenSaturation(),
        .respiratory_rate = readRespiratoryRate()
    };
    
    if (deviceConnected) {
        pVitalsCharacteristic->setValue((uint8_t*)&data, sizeof(data));
        pVitalsCharacteristic->notify();
    }
}

void setup() {
    // Initialize BLE
    BLEDevice::init("ESP32_WATCH_001");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());
    
    // Create service
    BLEService *pService = pServer->createService(SERVICE_UUID);
    
    // Create vitals characteristic
    pVitalsCharacteristic = pService->createCharacteristic(
        VITALS_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ |
        BLECharacteristic::PROPERTY_WRITE |
        BLECharacteristic::PROPERTY_NOTIFY
    );
    
    pService->start();
    pServer->getAdvertising()->start();
}

void loop() {
    // Send vitals every second (1Hz)
    if (millis() - lastVitalSent > 1000) {
        sendVitalData();
        lastVitalSent = millis();
    }
    
    delay(10);
}
```
*/