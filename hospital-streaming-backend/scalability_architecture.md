# 🏥 HOSPITAL SCALABILITY: 500 WATCHES PER UNIT

## 📊 VOLUME CALCULATIONS

### Per Unit Load:
- **500 ESP32 watches** × **1Hz sampling** = **500 readings/second**
- **Per hour**: 500 × 3600 = **1.8 million readings/hour**  
- **Per day**: 1.8M × 24 = **43.2 million readings/day**
- **Per week**: 43.2M × 7 = **302.4 million readings/week**

### Android App Batching:
- **5-second batches** per watch = **100 API calls/second** to backend
- **Batch size**: 5 readings × 6 vital types = **30 values per batch**
- **Daily API calls**: 100 × 86400 = **8.64 million API calls/day**

---

## 🏗️ INFRASTRUCTURE SCALING

### 1. **TimescaleDB Scaling** 
```sql
-- Hypertable configuration for high throughput
ALTER TABLE vital_readings SET (
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Enable compression after 1 hour for optimal storage
SELECT add_compression_policy('vital_readings', INTERVAL '1 hour');

-- Partition by device for parallel processing
SELECT create_hypertable('vital_readings', 'timestamp', 
    partitioning_column => 'device_id', number_partitions => 50);
```

### 2. **Backend API Scaling**
```yaml
# docker-compose.yml - Scale backend horizontally  
services:
  hospital-backend:
    image: hospital-backend:latest
    deploy:
      replicas: 4  # Scale to 4 instances
    environment:
      - DB_POOL_SIZE=50
      - MAX_CONNECTIONS=200
    depends_on:
      - redis-cluster
      - timescaledb-cluster

  # Load balancer for API endpoints
  nginx-lb:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "8001:80"
```

### 3. **Database Connection Pooling**
```python
# Increase connection pool for high throughput
DATABASE_URL = "postgresql://hospital_user:hospital_pass@timescaledb:5432/hospital_vitals"
database = Database(
    DATABASE_URL,
    min_size=20,        # Minimum pool size
    max_size=100,       # Maximum pool size  
    max_queries=50000,  # Max queries per connection
    max_inactive_connection_lifetime=300
)
```

---

## 📱 ANDROID APP ARCHITECTURE

### **BLE Connection Management**
```kotlin
class WatchConnectionManager {
    private val maxConcurrentConnections = 10  // Per tablet
    private val connectionQueue = ArrayDeque<WatchDevice>()
    private val activeConnections = mutableMapOf<String, BluetoothGatt>()
    
    // Round-robin connection strategy
    suspend fun connectToWatch(deviceId: String): BluetoothGatt? {
        if (activeConnections.size >= maxConcurrentConnections) {
            // Queue for next available slot
            connectionQueue.offer(WatchDevice(deviceId))
            return null
        }
        
        return bluetoothAdapter.connectGatt(context, false, gattCallback)
    }
    
    // Data batching for efficiency
    private val vitalsBatch = mutableListOf<VitalReading>()
    private var lastBatchSent = System.currentTimeMillis()
    
    private fun handleVitalReading(reading: VitalReading) {
        vitalsBatch.add(reading)
        
        // Send batch every 5 seconds OR when 25 readings accumulated
        if (vitalsBatch.size >= 25 || 
            System.currentTimeMillis() - lastBatchSent > 5000) {
            sendBatchToServer()
        }
    }
}
```

### **Data Transmission Optimization**
```kotlin
data class VitalsBatch(
    val deviceId: String,
    val patientId: String,
    val readings: List<VitalReading>,
    val sequence: Int,
    val appInfo: AppInfo,
    val timestamp: Long = System.currentTimeMillis()
)

data class VitalReading(
    val timestamp: String,
    val vitals: Map<String, Double>,  // All 6 vital types
    val quality: Double,              // Signal quality 0.0-1.0
    val batteryLevel: Int?,
    val signalStrength: Int?
)
```

---

## ⚡ PERFORMANCE OPTIMIZATIONS

### 1. **Database Optimizations**
```sql
-- Materialized views for common queries
CREATE MATERIALIZED VIEW patient_current_vitals AS
SELECT DISTINCT ON (patient_id, vital_type)
    patient_id, device_id, vital_type, value, unit, timestamp
FROM vital_readings 
ORDER BY patient_id, vital_type, timestamp DESC;

-- Refresh every 30 seconds
SELECT add_continuous_aggregate_policy('patient_current_vitals',
    start_offset => INTERVAL '1 minute',
    end_offset => INTERVAL '30 seconds', 
    schedule_interval => INTERVAL '30 seconds');

-- Indexes for fast lookups
CREATE INDEX CONCURRENTLY idx_vitals_patient_recent 
ON vital_readings (patient_id, timestamp DESC) 
WHERE timestamp > NOW() - INTERVAL '24 hours';
```

### 2. **Caching Strategy** 
```python
import redis

# Redis cluster for caching frequently accessed data
redis_cluster = redis.RedisCluster(
    startup_nodes=[
        {"host": "redis-1", "port": "7000"},
        {"host": "redis-2", "port": "7000"},
        {"host": "redis-3", "port": "7000"}
    ],
    decode_responses=True,
    skip_full_coverage_check=True
)

async def get_patient_current_vitals(patient_id: str):
    # Check cache first
    cached = await redis_cluster.get(f"vitals:{patient_id}")
    if cached:
        return json.loads(cached)
    
    # Query database and cache for 30 seconds
    vitals = await database.fetch_all(current_vitals_query, {"patient_id": patient_id})
    await redis_cluster.setex(f"vitals:{patient_id}", 30, json.dumps(vitals))
    return vitals
```

### 3. **Alert Processing Pipeline**
```python
# Async alert processing to avoid blocking data ingestion
import asyncio
from asyncio import Queue

alert_queue = Queue(maxsize=1000)

async def alert_processor():
    """Background task for processing alerts"""
    while True:
        try:
            alert_data = await alert_queue.get()
            await process_alert(alert_data)
            alert_queue.task_done()
        except Exception as e:
            logger.error(f"Alert processing error: {e}")

async def check_vitals_and_queue_alerts(patient_id: str, vitals: dict):
    """Non-blocking alert check"""
    alerts = detect_alerts(vitals)
    for alert in alerts:
        try:
            alert_queue.put_nowait({
                "patient_id": patient_id,
                "alert": alert,
                "timestamp": datetime.utcnow()
            })
        except asyncio.QueueFull:
            logger.warning("Alert queue full, dropping alert")
```

---

## 🔄 DEPLOYMENT ARCHITECTURE

### **Multi-Tier Scaling**
```
┌─────────────────────────────────────────────────────────┐
│                    LOAD BALANCER                        │
│                  (NGINX/HAProxy)                        │  
└─────────────────────┬───────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼───┐         ┌───▼───┐         ┌───▼───┐
│API-1  │         │API-2  │         │API-3  │  Backend APIs
│Node   │         │Node   │         │Node   │  (Auto-scaling)
└───┬───┘         └───┬───┘         └───┬───┘
    │                 │                 │
    └─────────────────┼─────────────────┘
                      │
         ┌────────────┼────────────┐
         │                         │
    ┌────▼────┐              ┌─────▼─────┐
    │TimescaleDB│              │  Redis    │  
    │ Cluster   │              │ Cluster   │  Data Layer
    │(Primary + │              │(Caching)  │  (High availability)
    │ Replicas) │              │           │
    └───────────┘              └───────────┘
```

### **Resource Allocation**
- **TimescaleDB**: 32GB RAM, 8 cores, SSD storage
- **Backend APIs**: 16GB RAM, 4 cores each × 4 instances  
- **Redis Cache**: 8GB RAM, 2 cores
- **Load Balancer**: 4GB RAM, 2 cores

---

## 📈 MONITORING & ALERTS

### **Performance Metrics**
```python
# Prometheus metrics for monitoring
from prometheus_client import Counter, Histogram, Gauge

vitals_received = Counter('vitals_received_total', 'Total vitals received', ['device_id'])
processing_time = Histogram('vitals_processing_seconds', 'Vitals processing time')
active_devices = Gauge('active_devices_count', 'Number of active devices')
database_connections = Gauge('db_connections_active', 'Active DB connections')

# Alert thresholds
alerts = {
    "api_response_time": "> 500ms",
    "database_connections": "> 80% of pool", 
    "vitals_backlog": "> 1000 unprocessed",
    "device_offline": "> 5 minutes no heartbeat"
}
```

---

## 🎯 EXPECTED PERFORMANCE

### **Throughput Targets**:
- ✅ **500 watches/unit** at **1Hz** = **500 readings/second**
- ✅ **API latency** < 100ms for vital ingestion
- ✅ **Database writes** < 50ms average
- ✅ **Alert generation** < 2 seconds end-to-end
- ✅ **99.9% uptime** with redundancy

### **Storage Projections**:
- **Raw data**: ~50GB/month per unit (with compression)
- **Aggregated data**: ~5GB/month per unit  
- **Alert history**: ~1GB/month per unit
- **Total**: ~56GB/month per 500-watch unit

This architecture can easily scale to **multiple hospital units** with proper load balancing and database sharding! 🚀