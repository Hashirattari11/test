-- Admin account/repository management fields. Safe to apply more than once.
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_suspended boolean NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_at timestamptz;
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_reason text;
CREATE INDEX IF NOT EXISTS idx_users_suspended ON users(is_suspended);
