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

/** Human-readable labels for content item statuses. */
export const CONTENT_STATUS_LABELS: Record<string, string> = {
  active: '活跃',
  deduped: '已去重',
  archived: '已归档',
  error: '错误',
}

/** Item type filter options. */
export const ITEM_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '全部类型' },
  { value: 'article', label: '文章' },
  { value: 'page', label: '页面' },
  { value: 'post', label: '帖子' },
]

/** Content status filter options. */
export const CONTENT_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '活跃' },
  { value: 'deduped', label: '已去重' },
  { value: 'archived', label: '已归档' },
]
