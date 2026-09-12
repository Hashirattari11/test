-- ============================================================================
-- AutoFix API — Combined migrations for invite fix + detection email + GitHub App
-- Apply ALL of this in the Supabase SQL editor.
-- ============================================================================

-- 1. Fix agency_clients column names (auth_token_hash → invite_token_hash)
-- Rename columns if they exist with the old names.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agency_clients' AND column_name='auth_token_hash') THEN
    ALTER TABLE agency_clients RENAME COLUMN auth_token_hash TO invite_token_hash;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agency_clients' AND column_name='auth_token_expires_at') THEN
    ALTER TABLE agency_clients RENAME COLUMN auth_token_expires_at TO invite_token_expires_at;
  END IF;
END $$;

-- Ensure the correct columns exist (idempotent)
ALTER TABLE agency_clients ADD COLUMN IF NOT EXISTS invite_token_hash text;
ALTER TABLE agency_clients ADD COLUMN IF NOT EXISTS invite_token_expires_at timestamptz;

-- 2. Detection confirmation email column
ALTER TABLE repos ADD COLUMN IF NOT EXISTS detection_email_sent boolean DEFAULT false;

-- 3. GitHub App flow: agency_clients gets installation_id
ALTER TABLE agency_clients ADD COLUMN IF NOT EXISTS github_installation_id text;

-- 4. Make repos.user_id nullable (agency-owned repos use agency_client_id)
ALTER TABLE repos ALTER COLUMN user_id DROP NOT NULL;

-- 5. Add agency_client_id to repos
ALTER TABLE repos ADD COLUMN IF NOT EXISTS agency_client_id uuid REFERENCES agency_clients(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_repos_agency_client ON repos(agency_client_id) WHERE agency_client_id IS NOT NULL;

-- 6. Alert columns from Phase 1 (idempotent)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='alerts' AND column_name='changelog_event_id') THEN
    ALTER TABLE alerts ALTER COLUMN changelog_event_id DROP NOT NULL;
  END IF;
END $$;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS severity text DEFAULT 'medium';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS severity_reason text;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS provider text DEFAULT 'resend';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS status text DEFAULT 'sent';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS is_test boolean DEFAULT false;
CREATE INDEX IF NOT EXISTS idx_alerts_repo ON alerts(repo_id);
