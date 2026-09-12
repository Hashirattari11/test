-- Phase 11: API Reliability & Health Intelligence
-- New tables for health scoring, issues, usage snapshots, and provider incidents.

-- Provider capabilities (what each provider supports)
CREATE TABLE IF NOT EXISTS public.provider_capabilities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  capability text NOT NULL,
  supported boolean NOT NULL DEFAULT false,
  api_base text,
  notes text,
  config jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  UNIQUE(provider, capability)
);

-- Health checks (individual check results per integration)
CREATE TABLE IF NOT EXISTS public.health_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_id uuid REFERENCES public.repos(id) ON DELETE CASCADE,
  provider text NOT NULL,
  check_type text NOT NULL,
  status text NOT NULL DEFAULT 'unknown' CHECK (status IN ('healthy','warning','critical','unavailable','unknown')),
  score numeric(5,1) DEFAULT 70,
  severity text DEFAULT 'info' CHECK (severity IN ('info','low','medium','high','critical')),
  message text,
  evidence text,
  recommendation text,
  source text DEFAULT 'scan',
  data jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Health scores (computed scores per integration per point in time)
CREATE TABLE IF NOT EXISTS public.health_scores (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_id uuid REFERENCES public.repos(id) ON DELETE CASCADE,
  provider text NOT NULL,
  overall numeric(5,1) NOT NULL,
  status text NOT NULL,
  breakdown jsonb DEFAULT '{}',
  checks jsonb DEFAULT '[]',
  repository_name text,
  computed_at timestamptz DEFAULT now()
);

-- Health history (historical snapshots for trend charts)
CREATE TABLE IF NOT EXISTS public.health_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_id uuid REFERENCES public.repos(id) ON DELETE CASCADE,
  provider text NOT NULL,
  overall numeric(5,1) NOT NULL,
  status text NOT NULL,
  snapshot jsonb DEFAULT '{}',
  recorded_at timestamptz DEFAULT now()
);

-- Reliability issues (unified issue model)
CREATE TABLE IF NOT EXISTS public.reliability_issues (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_id uuid REFERENCES public.repos(id) ON DELETE CASCADE,
  provider text NOT NULL,
  category text NOT NULL DEFAULT 'unknown' CHECK (category IN ('provider_problem','customer_code','customer_usage','provider_incident','dependency','configuration','unknown')),
  severity text NOT NULL DEFAULT 'medium' CHECK (severity IN ('critical','high','medium','low','info')),
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','acknowledged','in_progress','resolved','ignored')),
  confidence numeric(4,3) DEFAULT 0.5,
  title text NOT NULL,
  description text,
  evidence text,
  file text,
  line integer,
  source text DEFAULT 'scan',
  recommended_action text,
  auto_fix_available boolean DEFAULT false,
  auto_fix_rule_id text,
  content_hash text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  resolved_at timestamptz
);

-- Usage snapshots (quota/usage data over time)
CREATE TABLE IF NOT EXISTS public.usage_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_id uuid REFERENCES public.repos(id) ON DELETE CASCADE,
  provider text NOT NULL,
  used numeric(15,2),
  limit_value numeric(15,2),
  remaining numeric(15,2),
  percentage numeric(5,2),
  unit text,
  period text,
  raw_data jsonb DEFAULT '{}',
  recorded_at timestamptz DEFAULT now()
);

-- Rate limit snapshots
CREATE TABLE IF NOT EXISTS public.rate_limit_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_id uuid REFERENCES public.repos(id) ON DELETE CASCADE,
  provider text NOT NULL,
  limit_value integer,
  remaining integer,
  reset_at timestamptz,
  retry_after integer,
  raw_data jsonb DEFAULT '{}',
  recorded_at timestamptz DEFAULT now()
);

-- Provider incidents (from status pages)
CREATE TABLE IF NOT EXISTS public.provider_incidents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  external_id text,
  title text NOT NULL,
  status text NOT NULL DEFAULT 'investigating',
  impact text,
  components jsonb DEFAULT '[]',
  started_at timestamptz,
  resolved_at timestamptz,
  raw_data jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_health_checks_repo_provider ON public.health_checks(repo_id, provider, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_scores_repo_provider ON public.health_scores(repo_id, provider, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_history_repo ON public.health_history(repo_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_reliability_issues_repo_status ON public.reliability_issues(repo_id, status, severity);
CREATE INDEX IF NOT EXISTS idx_reliability_issues_provider ON public.reliability_issues(provider, category, severity);
CREATE INDEX IF NOT EXISTS idx_reliability_issues_hash ON public.reliability_issues(content_hash);
CREATE INDEX IF NOT EXISTS idx_usage_snapshots_repo_provider ON public.usage_snapshots(repo_id, provider, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_rate_limit_repo_provider ON public.rate_limit_snapshots(repo_id, provider, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_provider_incidents_provider ON public.provider_incidents(provider, status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_provider_capabilities_provider ON public.provider_capabilities(provider);