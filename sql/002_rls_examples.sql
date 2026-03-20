-- Optional hardening example for production.
-- Enable RLS for payroll table.
ALTER TABLE IF EXISTS payroll_records ENABLE ROW LEVEL SECURITY;

-- Example policy skeleton. In production, map database session variables
-- to the authenticated user and manager flags.
CREATE POLICY payroll_manager_or_hr_policy ON payroll_records
    FOR SELECT
    USING (true);
