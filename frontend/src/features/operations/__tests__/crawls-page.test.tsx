import '@testing-library/jest-dom/vitest'

import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CrawlsPage } from '../crawls-page'

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

const mockRuns = {
  items: [
    {
      id: 'run-001',
      source_id: 'src-001',
      recipe_id: 'recipe-001',
      status: 'completed',
      http_status: 200,
      error_message: null,
      raw_object_id: 'raw-001',
      started_at: '2026-01-01T10:00:00Z',
      completed_at: '2026-01-01T10:01:00Z',
      created_at: '2026-01-01T10:00:00Z',
    },
    {
      id: 'run-002',
      source_id: 'src-002',
      recipe_id: 'recipe-002',
      status: 'failed',
      http_status: 500,
      error_message: 'Connection timeout',
      raw_object_id: null,
      started_at: '2026-01-01T11:00:00Z',
      completed_at: null,
      created_at: '2026-01-01T11:00:00Z',
    },
  ],
  total: 2,
}

describe('CrawlsPage', () => {
  it('renders the page title and trigger crawl button', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<CrawlsPage config={config} />)

    expect(screen.getByText('Crawls')).toBeInTheDocument()
    expect(screen.getByTestId('trigger-crawl-button')).toBeInTheDocument()
  })

  it('shows loading state while fetching crawl runs', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<CrawlsPage config={config} />)

    expect(screen.getByTestId('crawls-loading')).toBeInTheDocument()
  })

  it('displays crawl runs in a table after loading', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockRuns))
    render(<CrawlsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('crawls-table')).toBeInTheDocument()
    })

    // Check that status pills are rendered
    const table = screen.getByTestId('crawls-table')
    expect(within(table).getAllByText('completed').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getAllByText('failed').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getByText('Connection timeout')).toBeInTheDocument()
  })

  it('shows empty state when no crawl runs exist', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({ items: [], total: 0 }))
    render(<CrawlsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('crawls-empty')).toBeInTheDocument()
    })
  })

  it('shows error state when API fails', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error'),
    })
    render(<CrawlsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('crawls-error')).toBeInTheDocument()
    })
  })

  it('filters by status when status filter is changed', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockRuns))
    const user = userEvent.setup()
    render(<CrawlsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-crawl-status-filter')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-crawl-status-filter'), 'failed')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('status=failed'),
        expect.any(Object),
      )
    })
  })

  it('shows the trigger crawl form when button is clicked', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockRuns))
    const user = userEvent.setup()
    render(<CrawlsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('trigger-crawl-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('trigger-crawl-button'))
    expect(screen.getByTestId('trigger-crawl-form')).toBeInTheDocument()
    expect(screen.getByTestId('input-source-id')).toBeInTheDocument()
    expect(screen.getByTestId('input-recipe-id')).toBeInTheDocument()
  })

  it('shows validation error when submitting with empty fields', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockRuns))
    const user = userEvent.setup()
    render(<CrawlsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('trigger-crawl-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('trigger-crawl-button'))
    await user.click(screen.getByTestId('submit-trigger-crawl'))

    await waitFor(() => {
      expect(screen.getByTestId('trigger-crawl-error')).toBeInTheDocument()
    })
  })

  it('hides form when cancel is clicked', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockRuns))
    const user = userEvent.setup()
    render(<CrawlsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('trigger-crawl-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('trigger-crawl-button'))
    expect(screen.getByTestId('trigger-crawl-form')).toBeInTheDocument()

    await user.click(screen.getByTestId('cancel-trigger-crawl'))
    expect(screen.queryByTestId('trigger-crawl-form')).not.toBeInTheDocument()
  })

  it('submits trigger crawl and shows result', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(mockRuns))
      .mockResolvedValueOnce(
        mockJsonResponse({
          crawl_run_id: 'new-run-001',
          status: 'completed',
          raw_object_id: 'raw-001',
          error_message: null,
        }),
      )
      .mockResolvedValueOnce(mockJsonResponse(mockRuns))

    const user = userEvent.setup()
    render(<CrawlsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('trigger-crawl-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('trigger-crawl-button'))
    await user.type(screen.getByTestId('input-source-id'), 'src-001')
    await user.type(screen.getByTestId('input-recipe-id'), 'recipe-001')
    await user.click(screen.getByTestId('submit-trigger-crawl'))

    await waitFor(() => {
      expect(screen.getByTestId('trigger-crawl-result')).toBeInTheDocument()
    })
  })

  it('shows error when trigger crawl API fails', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockRuns)).mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      text: () => Promise.resolve('Invalid source'),
    })

    const user = userEvent.setup()
    render(<CrawlsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('trigger-crawl-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('trigger-crawl-button'))
    await user.type(screen.getByTestId('input-source-id'), 'bad-id')
    await user.type(screen.getByTestId('input-recipe-id'), 'bad-recipe')
    await user.click(screen.getByTestId('submit-trigger-crawl'))

    await waitFor(() => {
      expect(screen.getByTestId('trigger-crawl-error')).toBeInTheDocument()
    })
  })
})
