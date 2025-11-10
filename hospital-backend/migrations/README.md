# Database Migrations

## ⚠️ SQL Migration Files Removed

**Date**: 2025-11-10

All SQL migration files have been **removed** because they were never used by the system.

---

## Current Migration System

This project uses **code-based migrations** in `app/core/database.py`, **NOT** file-based SQL migrations.

### How It Works:

1. **Table Creation**: `createTables()` function in `database.py`
   - Uses `CREATE TABLE IF NOT EXISTS`
   - Safe to run multiple times (idempotent)
   - Creates ALL 40 PostgreSQL tables + 1 view

2. **Column Additions**: `migrate*Table()` functions in `database.py`
   - Uses `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
   - Safe to run multiple times (idempotent)
   - Adds missing columns to existing tables

3. **TimescaleDB Hypertables**: `createTimescaleTables()` function
   - Creates 4 hypertables (vitals_realtime, waveform_snapshots, neural_events, vitals_timeseries)
   - Uses `if_not_exists => TRUE`
   - Safe to run multiple times

### No Version Tracking Needed:

Because all operations use `IF NOT EXISTS`, there's no need for:
- Migration version numbers
- Migration tracking tables
- Applied migrations log

The system simply ensures all tables and columns exist on startup.

---

## How to Add Schema Changes

### Adding a New Table:

Edit `app/core/database.py` and add to the `tablesSql` string in `createTables()`:

```python
tablesSql = """
    -- Existing tables...

    -- Your new table
    CREATE TABLE IF NOT EXISTS your_new_table (
        id SERIAL PRIMARY KEY,
        "someField" TEXT NOT NULL,
        "createdAt" TIMESTAMPTZ DEFAULT NOW()
    );
"""
```

### Adding a New Column:

Edit `app/core/database.py` and add to the appropriate `migrate*Table()` function, or create a new one:

```python
async def migrateYourTable(conn):
    """Add missing columns to your table"""
    missingColumns = [
        ('"newColumn"', "TEXT"),
        ('"anotherColumn"', "INTEGER DEFAULT 0")
    ]

    for columnName, columnType in missingColumns:
        await conn.execute(
            f"ALTER TABLE yourtable ADD COLUMN IF NOT EXISTS {columnName} {columnType}"
        )
```

Then call it from `createTables()`:

```python
async with getDbConnection() as conn:
    await conn.execute(tablesSql)
    await migrateYourTable(conn)  # Add this line
```

### Adding a TimescaleDB Hypertable:

Edit `app/core/database.py` and add to the `timescaleSql` string in `createTimescaleTables()`:

```python
timescaleSql = """
    -- Existing tables...

    CREATE TABLE IF NOT EXISTS your_timeseries (
        time TIMESTAMPTZ NOT NULL,
        "patientId" UUID NOT NULL,
        value DOUBLE PRECISION
    );

    SELECT create_hypertable('your_timeseries', 'time', if_not_exists => TRUE);
"""
```

---

## Why This Approach?

### Advantages ✅:
- Simple and straightforward
- No migration runner needed
- No version tracking complexity
- Idempotent (safe to run multiple times)
- Works on fresh AND existing databases
- All schema in one place (database.py)

### Disadvantages ❌:
- Can't rollback changes (but we never rolled back anyway)
- No historical record of changes (use git history instead)
- Migrations run on every startup (fast with IF NOT EXISTS)

---

## For Fresh Server Deployments

When deploying to a fresh server:

1. Start backend: `python main.py`
2. Backend automatically creates:
   - ✅ All 40 PostgreSQL tables
   - ✅ All columns with correct data types
   - ✅ All indexes for performance
   - ✅ devices_enriched view
   - ✅ All 4 TimescaleDB hypertables (if TimescaleDB configured)

**Result**: Fresh server is production-ready immediately!

---

## Migration History

For historical changes, check git history:
```bash
git log --oneline -- app/core/database.py
```

---

## Questions?

If you need to understand what schema exists:
- Check `app/core/database.py` - single source of truth
- Query database: `\dt` in psql shows all tables
- Check git history for past changes

**Do NOT create SQL migration files** - they won't be executed!
