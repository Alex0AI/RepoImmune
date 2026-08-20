export type EvidenceClass = "verified" | "externally_reported" | "heuristic" | "inconclusive";

export interface AffectedSymbol {
  path: string;
  symbol: string;
  language?: "python" | "typescript" | "javascript" | string;
}

export interface CodePattern {
  code: string;
  kind: string;
  ast?: string;
  calls?: string[];
}

export interface Evidence {
  type: string;
  url: string;
  sha?: string;
  observed_at?: string;
}

export interface BehaviorCardV1 {
  schema_version: "1.0.0";
  id: string;
  title: string;
  bug_trigger: string;
  observed_failure: string;
  affected_symbols: AffectedSymbol[];
  buggy_pattern: CodePattern;
  fixed_pattern: CodePattern;
  invariant: string;
  reproducer: { capsule_id: string; status: EvidenceClass; [key: string]: unknown };
  regression_tests: Array<{ path: string; name: string; [key: string]: unknown }>;
  applicability: Record<string, unknown>;
  evidence: Evidence[];
  confidence: { score: number; classification: EvidenceClass; rationale?: string };
  limitations: string[];
  source_commit: string;
  fixed_commit: string;
  content_hash: `sha256:${string}`;
  repository?: string;
  license?: Record<string, unknown>;
  timestamps?: Record<string, unknown>;
}

