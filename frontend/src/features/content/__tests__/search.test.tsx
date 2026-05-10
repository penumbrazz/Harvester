import '@testing-library/jest-dom/vitest'

import { cleanup, render, screen, waitFor } from '@testing-library/react'
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

function mockJsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  })
}

const keywordSearchResponse = {
  items: [
    {
      item_id: 'ci-1',
      version_id: 'iv-1',
      source_id: 'src-1',
      title: 'TypeScript Best Practices',
      canonical_url: 'https://example.com/ts-best',
      created_at: '2026-01-01T10:00:00Z',
      mode: 'keyword',
    },
    {
      item_id: 'ci-2',
      version_id: 'iv-2',
      source_id: 'src-1',
      title: 'Advanced TypeScript Patterns',
      canonical_url: 'https://example.com/ts-advanced',
      created_at: '2026-01-02T10:00:00Z',
      mode: 'keyword',
    },
  ],
}

const vectorSearchResponse = {
  items: [
    {
      chunk_id: 'ch-1',
      item_version_id: 'iv-1',
      content_item_id: 'ci-1',
      title: 'TypeScript Generics Deep Dive',
      text: 'Generics allow you to create reusable components...',
      distance: 0.15,
      mode: 'vector',
    },
    {
      chunk_id: 'ch-2',
      item_version_id: 'iv-2',
      content_item_id: 'ci-2',
      title: 'TypeScript Utility Types',
      text: 'Utility types like Partial, Required, and Pick...',
      distance: 0.32,
      mode: 'vector',
    },
  ],
}

describe('ContentLibraryPage - keyword search', () => {
  it('performs keyword search when query is entered', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 }),
    )
    mockFetch.mockResolvedValueOnce(mockJsonResponse(keywordSearchResponse))

    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('search-input')).toBeInTheDocument()
    })

    await user.type(screen.getByTestId('search-input'), 'TypeScript')
    await user.click(screen.getByTestId('search-button'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/items/search?q=TypeScript&mode=keyword'),
        expect.any(Object),
      )
    })
  })

  it('displays keyword search results with traceable fields', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 }),
    )
    mockFetch.mockResolvedValueOnce(mockJsonResponse(keywordSearchResponse))

    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('search-input')).toBeInTheDocument()
    })

    await user.type(screen.getByTestId('search-input'), 'TypeScript')
    await user.click(screen.getByTestId('search-button'))

    await waitFor(() => {
      expect(screen.getByTestId('search-results')).toBeInTheDocument()
    })

    expect(screen.getByText('TypeScript Best Practices')).toBeInTheDocument()
    expect(screen.getByText('Advanced TypeScript Patterns')).toBeInTheDocument()
  })
})

describe('ContentLibraryPage - vector search', () => {
  it('switches to vector mode and performs vector search', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 }),
    )
    mockFetch.mockResolvedValueOnce(mockJsonResponse(vectorSearchResponse))

    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('search-mode-select')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('search-mode-select'), 'vector')
    await user.type(screen.getByTestId('search-input'), 'generics')
    await user.click(screen.getByTestId('search-button'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('mode=vector'),
        expect.any(Object),
      )
    })
  })

  it('displays vector search results with distance', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 }),
    )
    mockFetch.mockResolvedValueOnce(mockJsonResponse(vectorSearchResponse))

    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('search-mode-select')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('search-mode-select'), 'vector')
    await user.type(screen.getByTestId('search-input'), 'generics')
    await user.click(screen.getByTestId('search-button'))

    await waitFor(() => {
      expect(screen.getByTestId('search-results')).toBeInTheDocument()
    })

    expect(screen.getByText('TypeScript Generics Deep Dive')).toBeInTheDocument()
    expect(screen.getByText(/0\.15/)).toBeInTheDocument()
    expect(screen.getByText(/0\.32/)).toBeInTheDocument()
  })

  it('shows chunk text for vector results', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 }),
    )
    mockFetch.mockResolvedValueOnce(mockJsonResponse(vectorSearchResponse))

    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('search-mode-select')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('search-mode-select'), 'vector')
    await user.type(screen.getByTestId('search-input'), 'generics')
    await user.click(screen.getByTestId('search-button'))

    await waitFor(() => {
      expect(screen.getByTestId('search-results')).toBeInTheDocument()
    })

    expect(
      screen.getByText('Generics allow you to create reusable components...'),
    ).toBeInTheDocument()
  })
})

describe('ContentLibraryPage - embedding unavailable', () => {
  it('shows 503 error when embedding adapter is unavailable', async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ items: [], total: 0, limit: 20, offset: 0 }),
    )
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      text: () => Promise.resolve('Embedding adapter unavailable: No service'),
    })

    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('search-mode-select')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('search-mode-select'), 'vector')
    await user.type(screen.getByTestId('search-input'), 'test')
    await user.click(screen.getByTestId('search-button'))

    await waitFor(() => {
      expect(screen.getByTestId('search-error')).toBeInTheDocument()
    })

    expect(screen.getByText(/unavailable/i)).toBeInTheDocument()
  })
})

describe('ContentLibraryPage - search clear', () => {
  it('returns to list view when search is cleared', async () => {
    const mockItems = {
      items: [
        {
          id: 'ci-1',
          item_type: 'article',
          source_id: 'src-1',
          source_name: 'TechBlog',
          title: 'TypeScript Article',
          canonical_url: 'https://example.com/ts',
          status: 'active',
          created_at: '2026-01-01T10:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    }
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockItems))
    mockFetch.mockResolvedValueOnce(mockJsonResponse(keywordSearchResponse))
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockItems))

    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    await user.type(screen.getByTestId('search-input'), 'TypeScript')
    await user.click(screen.getByTestId('search-button'))

    await waitFor(() => {
      expect(screen.getByTestId('search-results')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('search-clear'))

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })
  })
})
