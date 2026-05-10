/** Content item entity matching the backend ContentItemResponse. */
export interface ContentItem {
  id: string
  item_type: string
  source_id: string | null
  source_name: string | null
  topic_watch_id: string | null
  title: string | null
  canonical_url: string | null
  status: string
  created_at: string
  updated_at: string
}

/** Paginated content item list response from the backend. */
export interface ContentListResponse {
  items: ContentItem[]
  total: number
  limit: number
  offset: number
}

/** Search result item matching the backend SearchItem. */
export interface SearchResultItem {
  item_id?: string
  version_id?: string
  source_id?: string
  title: string
  canonical_url?: string
  created_at?: string
  chunk_id?: string
  item_version_id?: string
  content_item_id?: string
  text?: string
  distance?: number
  mode?: string
}

/** Search response from the backend. */
export interface SearchResponse {
  items: SearchResultItem[]
}

/** Search mode options. */
export type SearchMode = 'keyword' | 'vector'

/** View mode options for content library. */
export type ViewMode = 'grid' | 'list'

/** Content item status variants for StatusPill. */
export const CONTENT_STATUS_VARIANTS: Record<
  string,
  'success' | 'error' | 'warning' | 'info' | 'default'
> = {
  active: 'success',
  deduped: 'default',
  archived: 'default',
  error: 'error',
}

/** Item type filter options. */
export const ITEM_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Types' },
  { value: 'article', label: 'Article' },
  { value: 'page', label: 'Page' },
  { value: 'post', label: 'Post' },
]

/** Content status filter options. */
export const CONTENT_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'deduped', label: 'Deduped' },
  { value: 'archived', label: 'Archived' },
]
