-- Agency GitHub App flow: schema changes.
-- Apply in Supabase SQL editor.

-- Add github_installation_id to agency_clients (set once client installs the App).
alter table agency_clients add column if not exists github_installation_id text;

-- Make repos.user_id nullable (agency-owned repos use agency_client_id instead).
-- First drop the NOT NULL constraint if it exists.
alter table repos alter column user_id drop not null;

-- Add agency_client_id to repos (links to agency_clients.id for agency-owned repos).
alter table repos add column if not exists agency_client_id uuid references agency_clients(id) on delete cascade;

-- Index for fast lookups of agency-owned repos.
create index if not exists idx_repos_agency_client on repos(agency_client_id) where agency_client_id is not null;
