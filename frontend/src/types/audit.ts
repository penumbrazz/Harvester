/** A single audit event returned from the API. */
export interface AuditEvent {
  id: string
  actor: string | null
  action: string
  entity_type: string
  entity_id: string | null
  before_summary: string | null
  after_summary: string | null
  reason: string | null
  created_at: string
}

/** Paginated audit event list response. */
export interface AuditEventListResponse {
  items: AuditEvent[]
  total: number
}

/** Filters for querying audit events. */
export interface AuditEventFilters {
  entity_type?: string
  entity_id?: string
  action?: string
  actor?: string
  time_from?: string
  time_to?: string
  limit?: number
  offset?: number
}
