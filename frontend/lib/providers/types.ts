/**
 * Breaklytix Provider Registry — TypeScript Types
 *
 * Security rule: These types define the SHAPE of provider metadata only.
 * No secret values are ever stored, logged, or transmitted.
 * Evidence text always references environment variable NAMES, never values.
 */

// ---------------------------------------------------------------------------
// Core provider types
// ---------------------------------------------------------------------------

export type ProviderCategory =
  | "payment"
  | "communication"
  | "cloud"
  | "ai"
  | "analytics"
  | "database"
  | "devtools"
  | "media"
  | "other";

export type MonitoringStatus = "supported" | "planned" | "unavailable";

/** Server-reported monitoring health (provider_monitoring_status.status). */
export type ProviderHealthStatus =
  | "ACTIVE"
  | "LIMITED"
  | "SOURCE_UNAVAILABLE"
  | "ERROR";

export type ConfidenceLevel = "low" | "medium" | "high";

export type EvidenceType =
  | "env_var"
  | "import_statement"
  | "package_dependency"
  | "sdk_initialization"
  | "endpoint_usage"
  | "config_reference";

// ---------------------------------------------------------------------------
// Detection patterns for a provider
// ---------------------------------------------------------------------------

export interface DetectionPatterns {
  /** Environment variable NAMES to match (e.g. ["STRIPE_SECRET_KEY"]) */
  envVarNames: string[];
  /** Import/require patterns (regex strings) */
  importPatterns: string[];
  /** Package names from package.json / requirements.txt / go.mod */
  packageNames: string[];
  /** Endpoint/domain patterns to match in code */
  endpointPatterns: string[];
}

// ---------------------------------------------------------------------------
// Changelog configuration (Phase B — stored but inactive in Phase A)
// ---------------------------------------------------------------------------

export interface ChangelogConfig {
  /** Official changelog URL */
  changelogUrl: string;
  /** Official release notes URL */
  releaseNotesUrl: string;
  /** RSS/Atom feed URL if available */
  rssUrl?: string;
  /** How often to poll (e.g. "daily", "weekly") */
  pollingFrequency: string;
}

// ---------------------------------------------------------------------------
// Reserved for Phase B (typed but unimplemented)
// ---------------------------------------------------------------------------

export interface ChangelogParserStrategy {
  /** Parser strategy identifier */
  type: string;
  /** CSS selectors or extraction rules */
  selectors?: string[];
}

export interface BreakingChangeClassifierRule {
  /** Rule identifier */
  id: string;
  /** Pattern to match breaking changes */
  pattern: string;
  /** Severity impact */
  severity: "critical" | "high" | "medium" | "low";
}

export interface IntegrationMatchingRule {
  /** How to match changelog entries to code detections */
  strategy: "symbol" | "endpoint" | "import";
  /** Fields to match on */
  fields: string[];
}

export interface ConfidenceScoringRule {
  /** Evidence type */
  evidenceType: EvidenceType;
  /** Confidence boost */
  boost: ConfidenceLevel;
}

export interface SafeSuggestedActionTemplate {
  /** Action identifier */
  id: string;
  /** Human-readable description */
  description: string;
  /** Template for the action */
  template: string;
}

// ---------------------------------------------------------------------------
// Provider registry entry
// ---------------------------------------------------------------------------

export interface ProviderEntry {
  /** Unique provider identifier (lowercase, e.g. "stripe") */
  id: string;
  /** Human-readable name (e.g. "Stripe") */
  displayName: string;
  /** Provider category */
  category: ProviderCategory;
  /** Detection patterns for this provider */
  detectionPatterns: DetectionPatterns;
  /** Changelog monitoring config (Phase B — inactive in Phase A) */
  changelogConfig: ChangelogConfig;
  /** Current monitoring status */
  monitoringStatus: MonitoringStatus;
  /** Whether detection is enabled for this provider */
  detectionEnabled: boolean;

  // --- Reserved for Phase B (typed but empty/unimplemented) ---
  changelogParserStrategy?: ChangelogParserStrategy;
  breakingChangeClassifierRules?: BreakingChangeClassifierRule[];
  integrationMatchingRules?: IntegrationMatchingRule[];
  confidenceScoringRules?: ConfidenceScoringRule[];
  safeSuggestedActionTemplates?: SafeSuggestedActionTemplate[];
}

// ---------------------------------------------------------------------------
// Detection result types
// ---------------------------------------------------------------------------

export interface DetectionEvidence {
  /** Evidence type */
  type: EvidenceType;
  /** Safe evidence text (e.g. "Environment variable reference: STRIPE_SECRET_KEY") */
  text: string;
}

export interface ProviderDetection {
  /** Provider ID */
  provider: string;
  /** Provider display name */
  providerName: string;
  /** Provider category */
  category: ProviderCategory;
  /** Evidence for this detection */
  evidence: DetectionEvidence;
  /** Relative file path */
  filePath: string;
  /** Line number (1-based) */
  lineNumber: number;
  /** Confidence level */
  confidence: ConfidenceLevel;
  /** Monitoring status */
  monitoringStatus: MonitoringStatus;
}

export interface ProviderDetectionGroup {
  /** Provider ID */
  provider: string;
  /** Provider display name */
  providerName: string;
  /** Provider category */
  category: ProviderCategory;
  /** Monitoring status */
  monitoringStatus: MonitoringStatus;
  /** Whether detection is enabled */
  detectionEnabled: boolean;
  /** Total evidence count */
  evidenceCount: number;
  /** Unique files with detections */
  fileCount: number;
  /** Individual detections */
  detections: ProviderDetection[];
}

export interface ScanSummary {
  /** Total unique providers detected */
  totalProvidersDetected: number;
  /** Providers with high-confidence detections */
  highConfidenceProviders: number;
  /** Providers currently monitored (0 in Phase A) */
  providersMonitored: number;
  /** Providers detected but not monitored */
  providersDetectedNotMonitored: number;
  /** Total individual detections */
  totalDetections: number;
}

export interface ProviderCoverageEntry {
  /** Provider ID */
  provider: string;
  /** Provider display name */
  displayName: string;
  /** Category */
  category: ProviderCategory;
  /** Detection enabled */
  detectionEnabled: boolean;
  /** Official monitoring enabled (all false in Phase A) */
  monitoringEnabled: boolean;
  /** Monitoring status */
  monitoringStatus: MonitoringStatus;
  /** Whether this provider has detections in the repo */
  hasDetections: boolean;
}

// ---------------------------------------------------------------------------
// Provider changelog monitoring types (Phase C — real monitoring)
// ---------------------------------------------------------------------------

export type ChangelogChangeType =
  | "BREAKING_CHANGE"
  | "DEPRECATION"
  | "API_VERSION_CHANGE"
  | "ENDPOINT_CHANGE"
  | "REQUEST_SCHEMA_CHANGE"
  | "RESPONSE_SCHEMA_CHANGE"
  | "AUTH_CHANGE"
  | "SDK_CHANGE"
  | "MODEL_CHANGE"
  | "RATE_LIMIT_CHANGE"
  | "BEHAVIOR_CHANGE"
  | "SECURITY_CHANGE"
  | "NEW_FEATURE"
  | "BUG_FIX"
  | "OTHER";

export type ChangelogSeverity =
  | "CRITICAL"
  | "HIGH"
  | "MEDIUM"
  | "LOW"
  | "INFO"
  | "UNKNOWN";

export type ChangelogConfidence = "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";

export type ChangelogReviewState = "unreviewed" | "reviewed" | "dismissed";

export interface ChangelogEvent {
  id: string;
  api_name: string;
  provider_display?: string | null;
  title: string;
  description?: string | null;
  source_url?: string | null;
  change_type?: ChangelogChangeType | null;
  severity?: ChangelogSeverity | null;
  confidence?: ChangelogConfidence | null;
  confidence_evidence?: unknown;
  severity_evidence?: unknown;
  review_state?: ChangelogReviewState | null;
  detected_at?: string | null;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  external_id?: string | null;
  symbols?: string | null;
}

export interface MonitoringProviderRow {
  provider_id: string;
  display_name: string;
  status: ProviderHealthStatus;
  source_kind: string;
  source_url?: string | null;
  feed_url?: string | null;
  last_fetch_at?: string | null;
  last_success_at?: string | null;
  last_error?: string | null;
  consecutive_errors?: number | null;
  last_http_status?: number | null;
}
