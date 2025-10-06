-- ========================================
-- OPERATIONAL TABLES CAMELCASE MIGRATION
-- Fix atomic_transactions and medical_operations tables
-- ========================================
-- Date: 2025-10-05
-- Purpose: Rename all snake_case columns to camelCase for consistency
--
-- Changes:
-- 1. atomic_transactions: 8 columns (transaction_id, patient_id, etc.)
-- 2. medical_operations: 5 columns (idempotency_key, operation_type, etc.)
-- ========================================

-- PHASE 1: FIX atomic_transactions TABLE
-- ========================================

-- Rename 8 snake_case columns to camelCase
ALTER TABLE atomic_transactions RENAME COLUMN transaction_id TO "transactionId";
ALTER TABLE atomic_transactions RENAME COLUMN patient_id TO "patientId";
ALTER TABLE atomic_transactions RENAME COLUMN operation_type TO "operationType";
ALTER TABLE atomic_transactions RENAME COLUMN operation_data TO "operationData";
ALTER TABLE atomic_transactions RENAME COLUMN started_at TO "startedAt";
ALTER TABLE atomic_transactions RENAME COLUMN completed_at TO "completedAt";
ALTER TABLE atomic_transactions RENAME COLUMN error_message TO "errorMessage";
ALTER TABLE atomic_transactions RENAME COLUMN retry_count TO "retryCount";

-- PHASE 2: FIX medical_operations TABLE
-- ========================================

-- Rename 5 snake_case columns to camelCase
ALTER TABLE medical_operations RENAME COLUMN idempotency_key TO "idempotencyKey";
ALTER TABLE medical_operations RENAME COLUMN operation_type TO "operationType";
ALTER TABLE medical_operations RENAME COLUMN patient_id TO "patientId";
ALTER TABLE medical_operations RENAME COLUMN created_at TO "createdAt";
ALTER TABLE medical_operations RENAME COLUMN completed_at TO "completedAt";

-- PHASE 3: VERIFICATION
-- ========================================

-- Verify atomic_transactions schema
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'atomic_transactions'
ORDER BY ordinal_position;

-- Verify medical_operations schema
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'medical_operations'
ORDER BY ordinal_position;

-- ========================================
-- ROLLBACK SCRIPT (IF NEEDED)
-- ========================================
--
-- To rollback this migration:
--
-- ALTER TABLE atomic_transactions RENAME COLUMN "transactionId" TO transaction_id;
-- ALTER TABLE atomic_transactions RENAME COLUMN "patientId" TO patient_id;
-- ALTER TABLE atomic_transactions RENAME COLUMN "operationType" TO operation_type;
-- ALTER TABLE atomic_transactions RENAME COLUMN "operationData" TO operation_data;
-- ALTER TABLE atomic_transactions RENAME COLUMN "startedAt" TO started_at;
-- ALTER TABLE atomic_transactions RENAME COLUMN "completedAt" TO completed_at;
-- ALTER TABLE atomic_transactions RENAME COLUMN "errorMessage" TO error_message;
-- ALTER TABLE atomic_transactions RENAME COLUMN "retryCount" TO retry_count;
--
-- ALTER TABLE medical_operations RENAME COLUMN "idempotencyKey" TO idempotency_key;
-- ALTER TABLE medical_operations RENAME COLUMN "operationType" TO operation_type;
-- ALTER TABLE medical_operations RENAME COLUMN "patientId" TO patient_id;
-- ALTER TABLE medical_operations RENAME COLUMN "createdAt" TO created_at;
-- ALTER TABLE medical_operations RENAME COLUMN "completedAt" TO completed_at;
