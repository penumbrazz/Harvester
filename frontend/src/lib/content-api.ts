import type { ApiConfig } from '../types/api'
import type {
  ContentDetailResponse,
  ContentListResponse,
  SearchMode,
  SearchResponse,
} from '../types/content'
import { apiRequest } from './api-client'

/** Fetch paginated content items with optional filters. */
export function listContentItems(
  config: ApiConfig,
  params?: {
    source_id?: string
    topic_watch_id?: string
    item_type?: string
    status?: string
    limit?: number
    offset?: number
  },
): Promise<ContentListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.source_id) searchParams.set('source_id', params.source_id)
  if (params?.topic_watch_id) searchParams.set('topic_watch_id', params.topic_watch_id)
  if (params?.item_type) searchParams.set('item_type', params.item_type)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  const query = searchParams.toString()
  const path = query ? `/items/content?${query}` : '/items/content'
  return apiRequest<ContentListResponse>(config, path)
}

/** Search content items by keyword or vector similarity. */
export function searchContentItems(
  config: ApiConfig,
  q: string,
  mode: SearchMode = 'keyword',
  params?: {
    source_id?: string
    topic_watch_id?: string
    limit?: number
    offset?: number
  },
): Promise<SearchResponse> {
  const searchParams = new URLSearchParams()
  searchParams.set('q', q)
  searchParams.set('mode', mode)
  if (params?.source_id) searchParams.set('source_id', params.source_id)
  if (params?.topic_watch_id) searchParams.set('topic_watch_id', params.topic_watch_id)
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  return apiRequest<SearchResponse>(config, `/items/search?${searchParams.toString()}`)
}

/** Fetch a single content item detail with latest version text. */
export function getContentItemDetail(
  config: ApiConfig,
  contentItemId: string,
): Promise<ContentDetailResponse> {
  return apiRequest<ContentDetailResponse>(config, `/items/content/${contentItemId}`)
}
