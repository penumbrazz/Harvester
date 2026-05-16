import '@testing-library/jest-dom/vitest'

import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ContentLibraryPage } from '../content-library-page'

const config = {
  baseUrl: 'http://localhost:8001',
  token: 'test-token',
}

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

/** Helper to mock a successful JSON response. */
function mockJsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  })
}

const mockContentItems = {
  items: [
    {
      id: 'ci-1',
      item_type: 'article',
      source_id: 'src-1',
      source_name: 'TechBlog',
      topic_watch_id: null,
      title: 'Understanding TypeScript Generics',
      canonical_url: 'https://example.com/ts-generics',
      status: 'active',
      created_at: '2026-01-01T10:00:00Z',
      updated_at: '2026-01-01T12:00:00Z',
    },
    {
      id: 'ci-2',
      item_type: 'article',
      source_id: 'src-2',
      source_name: 'DevWeekly',
      topic_watch_id: null,
      title: 'React Server Components Guide',
      canonical_url: 'https://example.com/rsc-guide',
      status: 'active',
      created_at: '2026-01-02T10:00:00Z',
      updated_at: '2026-01-02T12:00:00Z',
    },
    {
      id: 'ci-3',
      item_type: 'page',
      source_id: 'src-1',
      source_name: 'TechBlog',
      topic_watch_id: null,
      title: 'Python Async Patterns',
      canonical_url: 'https://example.com/python-async',
      status: 'deduped',
      created_at: '2026-01-03T10:00:00Z',
      updated_at: '2026-01-03T12:00:00Z',
    },
  ],
  total: 3,
  limit: 20,
  offset: 0,
}

describe('ContentLibraryPage - list loading', () => {
  it('renders the page title', () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 })
    })
    render(<ContentLibraryPage config={config} />)

    expect(screen.getByText('内容库')).toBeInTheDocument()
  })

  it('shows loading state while fetching content items', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<ContentLibraryPage config={config} />)

    expect(screen.getByTestId('content-loading')).toBeInTheDocument()
  })

  it('displays content items in a table after loading', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse(mockContentItems)
    })
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    expect(screen.getByText('Understanding TypeScript Generics')).toBeInTheDocument()
    expect(screen.getByText('React Server Components Guide')).toBeInTheDocument()
    expect(screen.getByText('Python Async Patterns')).toBeInTheDocument()
  })

  it('shows source name in the table', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse(mockContentItems)
    })
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    const table = screen.getByTestId('content-table')
    expect(within(table).getAllByText('TechBlog').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getAllByText('DevWeekly').length).toBeGreaterThanOrEqual(1)
  })

  it('shows status pills with correct variants', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse(mockContentItems)
    })
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    const table = screen.getByTestId('content-table')
    expect(within(table).getAllByText('活跃').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getAllByText('已去重').length).toBeGreaterThanOrEqual(1)
  })
})

describe('ContentLibraryPage - empty state', () => {
  it('shows empty state when no content items exist', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 })
    })
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-empty')).toBeInTheDocument()
    })

    expect(screen.getByText('未找到内容项')).toBeInTheDocument()
  })

  it('shows filter hint when filters are active but no results', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 })
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-empty')).toBeInTheDocument()
    })

    // Select a filter
    await user.selectOptions(screen.getByTestId('select-type-filter'), 'page')

    await waitFor(() => {
      expect(screen.getByText(/请尝试调整筛选条件/)).toBeInTheDocument()
    })
  })
})

describe('ContentLibraryPage - error state', () => {
  it('shows error state when API fails', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: () => Promise.resolve('Server error'),
      })
    })
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-error')).toBeInTheDocument()
    })
  })
})

describe('ContentLibraryPage - filters', () => {
  it('sends item_type filter to the API', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse(mockContentItems)
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-type-filter')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-type-filter'), 'page')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('item_type=page'),
        expect.any(Object),
      )
    })
  })

  it('sends status filter to the API', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse(mockContentItems)
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-status-filter')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-status-filter'), 'active')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('status=active'),
        expect.any(Object),
      )
    })
  })
})

describe('ContentLibraryPage - pagination', () => {
  it('shows pagination info when there are many items', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse({
        items: Array.from({ length: 20 }, (_, i) => ({
          id: `ci-${i}`,
          item_type: 'article',
          source_id: 'src-1',
          source_name: 'TestSource',
          title: `Article ${i}`,
          canonical_url: `https://example.com/${i}`,
          status: 'active',
          created_at: '2026-01-01T10:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
        })),
        total: 50,
        limit: 20,
        offset: 0,
      })
    })
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('pagination-controls')).toBeInTheDocument()
    })

    expect(screen.getByText(/1-20 of 50/)).toBeInTheDocument()
  })

  it('navigates to next page when Next is clicked', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse({
        items: Array.from({ length: 20 }, (_, i) => ({
          id: `ci-${i}`,
          item_type: 'article',
          source_id: 'src-1',
          source_name: 'TestSource',
          title: `Article ${i}`,
          canonical_url: `https://example.com/${i}`,
          status: 'active',
          created_at: '2026-01-01T10:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
        })),
        total: 50,
        limit: 20,
        offset: 0,
      })
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('pagination-next')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('pagination-next'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('offset=20'),
        expect.any(Object),
      )
    })
  })
})

describe('ContentLibraryPage - source filter', () => {
  it('renders source filter dropdown', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({
          items: [
            {
              id: 'src-1',
              name: 'TechBlog',
              kind: 'rss',
              status: 'watched',
              url: null,
              trust_level: 'medium',
              failure_count: 0,
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z',
            },
          ],
          total: 1,
          limit: 100,
          offset: 0,
        })
      }
      return mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 })
    })
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-source-filter')).toBeInTheDocument()
    })

    expect(screen.getByText('TechBlog')).toBeInTheDocument()
  })

  it('sends source_id filter to the API', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({
          items: [
            {
              id: 'src-1',
              name: 'TechBlog',
              kind: 'rss',
              status: 'watched',
              url: null,
              trust_level: 'medium',
              failure_count: 0,
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z',
            },
          ],
          total: 1,
          limit: 100,
          offset: 0,
        })
      }
      return mockJsonResponse(mockContentItems)
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-source-filter')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-source-filter'), 'src-1')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('source_id=src-1'),
        expect.any(Object),
      )
    })
  })
})

describe('ContentLibraryPage - content detail modal', () => {
  it('opens modal when a content row is clicked', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      return mockJsonResponse(mockContentItems)
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Understanding TypeScript Generics'))

    await waitFor(() => {
      expect(screen.getByTestId('content-detail-modal')).toBeInTheDocument()
    })
  })

  it('closes modal when close button is clicked', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      if (url.includes('/items/content/ci-1')) {
        return mockJsonResponse({
          id: 'ci-1',
          item_type: 'article',
          title: 'Understanding TypeScript Generics',
          canonical_url: 'https://example.com/ts-generics',
          status: 'active',
          source_name: 'TechBlog',
          created_at: '2026-01-01T10:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
          latest_version: {
            id: 'iv-1',
            normalized_text: 'Full text of the article.',
            language: 'en',
            content_hash: 'abc123',
            created_at: '2026-01-01T11:00:00Z',
          },
        })
      }
      return mockJsonResponse(mockContentItems)
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Understanding TypeScript Generics'))

    await waitFor(() => {
      expect(screen.getByTestId('content-detail-modal')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('close-content-detail-button'))

    await waitFor(() => {
      expect(screen.queryByTestId('content-detail-modal')).not.toBeInTheDocument()
    })
  })

  it('displays full article text in modal', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/sources')) {
        return mockJsonResponse({ items: [], total: 0, limit: 100, offset: 0 })
      }
      if (url.includes('/items/content/ci-1')) {
        return mockJsonResponse({
          id: 'ci-1',
          item_type: 'article',
          title: 'Understanding TypeScript Generics',
          canonical_url: 'https://example.com/ts-generics',
          status: 'active',
          source_name: 'TechBlog',
          created_at: '2026-01-01T10:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
          latest_version: {
            id: 'iv-1',
            normalized_text:
              'This is the full article body text that was previously hidden.',
            language: 'en',
            content_hash: 'abc123',
            created_at: '2026-01-01T11:00:00Z',
          },
        })
      }
      return mockJsonResponse(mockContentItems)
    })
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Understanding TypeScript Generics'))

    await waitFor(() => {
      expect(screen.getByTestId('content-detail-body')).toHaveTextContent(
        'This is the full article body text that was previously hidden.',
      )
    })
  })
})
