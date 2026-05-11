import type { ApiConfig } from '../types/api'
import type {
  ProposeSourceRequest,
  Source,
  SourceListResponse,
  UpdateSourceRequest,
} from '../types/source'
import { apiRequest } from './api-client'

/** Fetch the list of sources with pagination and optional filters. */
export function listSources(
  config: ApiConfig,
  params?: { status?: string; kind?: string; limit?: number; offset?: number },
): Promise<SourceListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.kind) searchParams.set('kind', params.kind)
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  const query = searchParams.toString()
  const path = query ? `/sources?${query}` : '/sources'
  return apiRequest<SourceListResponse>(config, path)
}

/** Propose a new candidate source. */
export function proposeSource(
  config: ApiConfig,
  data: ProposeSourceRequest,
): Promise<Source> {
  return apiRequest<Source>(config, '/sources/propose', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/** Promote a source to the next status in its lifecycle. */
export function promoteSource(config: ApiConfig, sourceId: string): Promise<Source> {
  return apiRequest<Source>(config, `/sources/${sourceId}/promote`, {
    method: 'POST',
  })
}

/** Pause a watched source. */
export function pauseSource(config: ApiConfig, sourceId: string): Promise<Source> {
  return apiRequest<Source>(config, `/sources/${sourceId}/pause`, {
    method: 'POST',
  })
}

/** Resume a paused source back to watched. */
export function resumeSource(config: ApiConfig, sourceId: string): Promise<Source> {
  return apiRequest<Source>(config, `/sources/${sourceId}/resume`, {
    method: 'POST',
  })
}

/** Archive a source. */
export function archiveSource(config: ApiConfig, sourceId: string): Promise<Source> {
  return apiRequest<Source>(config, `/sources/${sourceId}/archive`, {
    method: 'POST',
  })
}

/** Update editable fields on a source. */
export function updateSource(
  config: ApiConfig,
  sourceId: string,
  data: UpdateSourceRequest,
): Promise<Source> {
  return apiRequest<Source>(config, `/sources/${sourceId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}
