-- Legal consent gate (master pass §2): privacy policy + terms acceptance tracking.
-- Safe strategy: NEW columns only — no data backfill required. Existing users (NULL
-- consent columns) see a one-time consent gate on next login, they are NOT hard-locked
-- (dashboard keeps working; consent_required flag computed server-side from NULL rows).

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS privacy_policy_version TEXT,
  ADD COLUMN IF NOT EXISTS terms_version TEXT,
  ADD COLUMN IF NOT EXISTS legal_consent_version TEXT,
  ADD COLUMN IF NOT EXISTS legal_consent_accepted_at TIMESTAMPTZ;

-- Useful for admin audits: find users who accepted a specific version.
CREATE INDEX IF NOT EXISTS idx_users_legal_consent_accepted_at
  ON users (legal_consent_accepted_at);