-- ============================================
-- EXACT QUERY USED BY DASHBOARD FOR SCAN COUNT
-- ============================================
-- Use this query to verify scan count matches dashboard

-- Replace these values with your actual filter values:
-- @COMPANY_ID = 312 (default)
-- @DATE_FROM = your start date (e.g., '2025-01-01')
-- @DATE_TO = your end date (e.g., '2026-05-12')
-- @DEVICES = comma-separated device serial numbers (e.g., 'AGFW26010', 'CFSO13')

SELECT 
    COUNT(*) AS total_scans,
    COUNT(DISTINCT CASE 
        WHEN device_serial_no IS NOT NULL AND device_serial_no <> '' 
        THEN device_serial_no 
    END) AS total_devices,
    ROUND(COALESCE(SUM(
        COALESCE(
            NULLIF(CAST(
                CASE WHEN JSON_VALID(request) 
                THEN JSON_UNQUOTE(JSON_EXTRACT(request, '$.scan_data.weight')) 
                ELSE NULL END 
            AS DECIMAL(18, 3)), 0), 
            COALESCE(weight, 0) * 100
        )
    ), 0), 3) AS total_waste
FROM scm_scans
WHERE 
    company_id = 312                        -- REQUIRED
    AND commodity_name IS NOT NULL          -- REQUIRED (filters out test/incomplete scans)
    AND created_on_date IS NOT NULL         -- REQUIRED (filters out invalid dates)
    -- AND created_on_date >= '2025-01-01'  -- OPTIONAL: Uncomment and set your date range
    -- AND created_on_date <= '2026-05-12'  -- OPTIONAL: Uncomment and set your date range
    -- AND device_serial_no IN ('AGFW26010', 'CFSO13')  -- OPTIONAL: Uncomment and add your devices
;

-- ============================================
-- DEBUGGING QUERIES
-- ============================================

-- 1. Check records WITHOUT commodity_name (these are EXCLUDED from dashboard)
SELECT COUNT(*) AS scans_without_commodity
FROM scm_scans
WHERE company_id = 312
  AND commodity_name IS NULL;

-- 2. Check records WITHOUT created_on_date (these are EXCLUDED from dashboard)
SELECT COUNT(*) AS scans_without_date
FROM scm_scans
WHERE company_id = 312
  AND created_on_date IS NULL;

-- 3. Check records with BOTH NULL (excluded)
SELECT COUNT(*) AS scans_with_both_null
FROM scm_scans
WHERE company_id = 312
  AND (commodity_name IS NULL OR created_on_date IS NULL);

-- 4. Compare: ALL scans vs VALID scans
SELECT 
    'All Scans' AS category,
    COUNT(*) AS count
FROM scm_scans
WHERE company_id = 312

UNION ALL

SELECT 
    'Valid Scans (Dashboard)' AS category,
    COUNT(*) AS count
FROM scm_scans
WHERE company_id = 312
  AND commodity_name IS NOT NULL
  AND created_on_date IS NOT NULL;
