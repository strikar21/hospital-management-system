-- Fix missing database schema issues
-- Run this to fix the "column da.is_active does not exist" error

-- Add missing is_active column to device_assignments table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'device_assignments' 
        AND column_name = 'is_active'
    ) THEN
        ALTER TABLE device_assignments ADD COLUMN is_active BOOLEAN DEFAULT true;
        
        -- Update existing records to be active
        UPDATE device_assignments SET is_active = true WHERE is_active IS NULL;
        
        RAISE NOTICE 'Added is_active column to device_assignments table';
    ELSE
        RAISE NOTICE 'is_active column already exists in device_assignments table';
    END IF;
END $$;

-- Add missing columns to other tables if needed
DO $$ 
BEGIN
    -- Ensure patients table has is_active column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'patients' 
        AND column_name = 'is_active'
    ) THEN
        ALTER TABLE patients ADD COLUMN is_active BOOLEAN DEFAULT true;
        UPDATE patients SET is_active = true WHERE is_active IS NULL;
        RAISE NOTICE 'Added is_active column to patients table';
    END IF;

    -- Ensure staff table has proper columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'staff' 
        AND column_name = 'is_active'
    ) THEN
        ALTER TABLE staff ADD COLUMN is_active BOOLEAN DEFAULT true;
        UPDATE staff SET is_active = true WHERE is_active IS NULL;
        RAISE NOTICE 'Added is_active column to staff table';
    END IF;
END $$;

-- Create indexes for performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_device_assignments_is_active 
ON device_assignments (is_active) WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patients_is_active 
ON patients (is_active) WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_staff_is_active 
ON staff (is_active) WHERE is_active = true;

-- Show table structure for verification
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name IN ('device_assignments', 'patients', 'staff')
  AND column_name IN ('is_active', 'staff_id', 'id')
ORDER BY table_name, ordinal_position;