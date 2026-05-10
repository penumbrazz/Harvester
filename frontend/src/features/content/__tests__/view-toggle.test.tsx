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
  ],
  total: 2,
  limit: 20,
  offset: 0,
}

describe('ContentLibraryPage - grid/list toggle', () => {
  it('defaults to list view', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockContentItems))
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })
  })

  it('switches to grid view when grid button is clicked', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockContentItems))
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('view-grid')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('view-grid'))

    await waitFor(() => {
      expect(screen.getByTestId('content-grid')).toBeInTheDocument()
    })
  })

  it('switches back to list view when list button is clicked', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockContentItems))
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('view-grid')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('view-grid'))

    await waitFor(() => {
      expect(screen.getByTestId('content-grid')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('view-list'))

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })
  })

  it('uses the same data for both views', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockContentItems))
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    // Both items should be visible in list view
    expect(screen.getByText('Understanding TypeScript Generics')).toBeInTheDocument()
    expect(screen.getByText('React Server Components Guide')).toBeInTheDocument()

    // Switch to grid view
    await user.click(screen.getByTestId('view-grid'))

    await waitFor(() => {
      expect(screen.getByTestId('content-grid')).toBeInTheDocument()
    })

    // Same items should be visible in grid view
    expect(screen.getByText('Understanding TypeScript Generics')).toBeInTheDocument()
    expect(screen.getByText('React Server Components Guide')).toBeInTheDocument()
  })

  it('does not re-fetch data when switching views', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockContentItems))
    const user = userEvent.setup()
    render(<ContentLibraryPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('content-table')).toBeInTheDocument()
    })

    const fetchCallCount = mockFetch.mock.calls.length

    await user.click(screen.getByTestId('view-grid'))

    await waitFor(() => {
      expect(screen.getByTestId('content-grid')).toBeInTheDocument()
    })

    // No additional fetch calls should be made
    expect(mockFetch.mock.calls.length).toBe(fetchCallCount)
  })
})
