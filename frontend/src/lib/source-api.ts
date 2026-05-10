import type { ApiConfig } from '../types/api'
import type { ProposeSourceRequest, Source } from '../types/source'
import { apiRequest } from './api-client'

/** Fetch the list of sources, optionally filtered by status and/or kind. */
export function listSources(
  config: ApiConfig,
  filters?: { status?: string; kind?: string },
): Promise<Source[]> {
  const params = new URLSearchParams()
  if (filters?.status) params.set('status', filters.status)
  if (filters?.kind) params.set('kind', filters.kind)
  const query = params.toString()
  const path = query ? `/sources?${query}` : '/sources'
  return apiRequest<Source[]>(config, path)
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
