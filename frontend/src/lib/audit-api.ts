import type { ApiConfig } from '../types/api'
import type { AuditEventFilters, AuditEventListResponse } from '../types/audit'
import { apiRequest } from './api-client'

/** Fetch paginated audit events with optional filters. */
export function listAuditEvents(
  config: ApiConfig,
  filters?: AuditEventFilters,
): Promise<AuditEventListResponse> {
  const params = new URLSearchParams()
  if (filters?.entity_type) params.set('entity_type', filters.entity_type)
  if (filters?.entity_id) params.set('entity_id', filters.entity_id)
  if (filters?.action) params.set('action', filters.action)
  if (filters?.actor) params.set('actor', filters.actor)
  if (filters?.time_from) params.set('time_from', filters.time_from)
  if (filters?.time_to) params.set('time_to', filters.time_to)
  if (filters?.limit) params.set('limit', String(filters.limit))
  if (filters?.offset) params.set('offset', String(filters.offset))
  const query = params.toString()
  const path = query ? `/audit/events?${query}` : '/audit/events'
  return apiRequest<AuditEventListResponse>(config, path)
}
