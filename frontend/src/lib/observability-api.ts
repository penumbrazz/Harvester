import type { ApiConfig } from '../types/api'
import type {
  CrawlRunListResponse,
  CrawlTargetListResponse,
  DashboardSummary,
  FailuresResponse,
  JobListResponse,
  TriggerCrawlRequest,
  TriggerCrawlResponse,
} from '../types/observability'
import { apiRequest } from './api-client'

/** Fetch the dashboard summary with aggregated metrics. */
export function getDashboardSummary(config: ApiConfig): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>(config, '/dashboard/summary')
}

/** Fetch paginated crawl run list with optional filters. */
export function listCrawlRuns(
  config: ApiConfig,
  filters?: {
    status?: string
    source_id?: string
    limit?: number
    offset?: number
  },
): Promise<CrawlRunListResponse> {
  const params = new URLSearchParams()
  if (filters?.status) params.set('status', filters.status)
  if (filters?.source_id) params.set('source_id', filters.source_id)
  if (filters?.limit) params.set('limit', String(filters.limit))
  if (filters?.offset) params.set('offset', String(filters.offset))
  const query = params.toString()
  const path = query ? `/crawl/runs?${query}` : '/crawl/runs'
  return apiRequest<CrawlRunListResponse>(config, path)
}

/** Trigger a new crawl run for a source and recipe. */
export function triggerCrawlRun(
  config: ApiConfig,
  data: TriggerCrawlRequest,
): Promise<TriggerCrawlResponse> {
  return apiRequest<TriggerCrawlResponse>(config, '/crawl/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/** Fetch recent failures from crawl runs and jobs. */
export function getRecentFailures(
  config: ApiConfig,
  limit?: number,
): Promise<FailuresResponse> {
  const path = limit ? `/failures/recent?limit=${limit}` : '/failures/recent'
  return apiRequest<FailuresResponse>(config, path)
}

/** Fetch paginated crawl target list with optional filters. */
export function listCrawlTargets(
  config: ApiConfig,
  filters?: {
    source_id?: string
    target_role?: string
    status?: string
    limit?: number
    offset?: number
  },
): Promise<CrawlTargetListResponse> {
  const params = new URLSearchParams()
  if (filters?.source_id) params.set('source_id', filters.source_id)
  if (filters?.target_role) params.set('target_role', filters.target_role)
  if (filters?.status) params.set('status', filters.status)
  if (filters?.limit) params.set('limit', String(filters.limit))
  if (filters?.offset) params.set('offset', String(filters.offset))
  const query = params.toString()
  const path = query ? `/crawl/targets?${query}` : '/crawl/targets'
  return apiRequest<CrawlTargetListResponse>(config, path)
}

/** Fetch paginated job list with optional filters. */
export function listJobs(
  config: ApiConfig,
  filters?: {
    job_type?: string
    status?: string
    lane?: string
    source_id?: string
    limit?: number
    offset?: number
  },
): Promise<JobListResponse> {
  const params = new URLSearchParams()
  if (filters?.job_type) params.set('job_type', filters.job_type)
  if (filters?.status) params.set('status', filters.status)
  if (filters?.lane) params.set('lane', filters.lane)
  if (filters?.source_id) params.set('source_id', filters.source_id)
  if (filters?.limit) params.set('limit', String(filters.limit))
  if (filters?.offset) params.set('offset', String(filters.offset))
  const query = params.toString()
  const path = query ? `/queue/jobs?${query}` : '/queue/jobs'
  return apiRequest<JobListResponse>(config, path)
}
