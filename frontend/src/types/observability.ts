/** Dashboard summary response from the backend. */
export interface DashboardSummary {
  sources: CountByStatus
  crawl_runs: CountByStatus
  jobs: CountByStatus
  content_items: CountByStatus
  failures: CountByStatus
  audit_events: CountByStatus
}

/** Entity count grouped by status. */
export interface CountByStatus {
  total: number
  by_status: Record<string, number>
}

/** A single crawl run record. */
export interface CrawlRun {
  id: string
  source_id: string | null
  recipe_id: string | null
  status: string
  http_status: number | null
  error_message: string | null
  raw_object_id: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

/** Paginated crawl run list response. */
export interface CrawlRunListResponse {
  items: CrawlRun[]
  total: number
  limit: number
  offset: number
}

/** A single job record. */
export interface Job {
  id: string
  job_type: string
  status: string
  priority: number
  attempts: number
  max_attempts: number
  run_after: string | null
  locked_by: string | null
  locked_until: string | null
  lane: string | null
  source_id: string | null
  last_error: string | null
  created_at: string
  updated_at: string
}

/** Paginated job list response. */
export interface JobListResponse {
  items: Job[]
  total: number
  limit: number
  offset: number
}

/** A single failure item from the failures API. */
export interface FailureItem {
  id: string
  entity_type: string
  status: string
  error_message: string | null
  created_at: string
}

/** Recent failures response. */
export interface FailuresResponse {
  crawl_runs: FailureItem[]
  jobs: FailureItem[]
}

/** Crawl run trigger request payload. */
export interface TriggerCrawlRequest {
  source_id: string
  recipe_id: string
}

/** Crawl run trigger response. */
export interface TriggerCrawlResponse {
  crawl_run_id: string
  status: string
  raw_object_id: string | null
  error_message: string | null
}
