import '@testing-library/jest-dom/vitest'

import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { JobsPage } from '../jobs-page'

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

const mockJobs = {
  items: [
    {
      id: 'job-001',
      job_type: 'crawl',
      status: 'pending',
      priority: 0,
      attempts: 0,
      max_attempts: 3,
      run_after: null,
      locked_by: null,
      locked_until: null,
      lane: 'default',
      source_id: 'src-001',
      last_error: null,
      created_at: '2026-01-01T10:00:00Z',
      updated_at: '2026-01-01T10:00:00Z',
    },
    {
      id: 'job-002',
      job_type: 'extract',
      status: 'failed',
      priority: 1,
      attempts: 3,
      max_attempts: 3,
      run_after: null,
      locked_by: null,
      locked_until: null,
      lane: 'priority',
      source_id: 'src-002',
      last_error: 'Processing failed',
      created_at: '2026-01-01T11:00:00Z',
      updated_at: '2026-01-01T11:00:00Z',
    },
    {
      id: 'job-003',
      job_type: 'crawl',
      status: 'dead',
      priority: 0,
      attempts: 3,
      max_attempts: 3,
      run_after: null,
      locked_by: null,
      locked_until: null,
      lane: null,
      source_id: null,
      last_error: 'Max retries exceeded',
      created_at: '2026-01-01T12:00:00Z',
      updated_at: '2026-01-01T12:00:00Z',
    },
  ],
  total: 3,
}

describe('JobsPage', () => {
  it('renders the page title and refresh button', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<JobsPage config={config} />)

    expect(screen.getByText('作业队列')).toBeInTheDocument()
    expect(screen.getByTestId('refresh-jobs')).toBeInTheDocument()
  })

  it('shows loading state while fetching jobs', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<JobsPage config={config} />)

    expect(screen.getByTestId('jobs-loading')).toBeInTheDocument()
  })

  it('displays summary cards after loading', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockJobs))
    render(<JobsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('jobs-summary')).toBeInTheDocument()
    })
  })

  it('displays jobs in a table after loading', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockJobs))
    render(<JobsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('jobs-table')).toBeInTheDocument()
    })

    const table = screen.getByTestId('jobs-table')
    expect(within(table).getAllByText('crawl').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getAllByText('failed').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getByText('Processing failed')).toBeInTheDocument()
    expect(within(table).getByText('Max retries exceeded')).toBeInTheDocument()
  })

  it('shows empty state when no jobs exist', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({ items: [], total: 0 }))
    render(<JobsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('jobs-empty')).toBeInTheDocument()
    })
  })

  it('shows error state when API fails', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error'),
    })
    render(<JobsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('jobs-error')).toBeInTheDocument()
    })
  })

  it('filters by job type when filter is changed', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockJobs))
    const user = userEvent.setup()
    render(<JobsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-job-type-filter')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-job-type-filter'), 'crawl')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('job_type=crawl'),
        expect.any(Object),
      )
    })
  })

  it('filters by status when status filter is changed', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockJobs))
    const user = userEvent.setup()
    render(<JobsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-job-status-filter')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-job-status-filter'), 'failed')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('status=failed'),
        expect.any(Object),
      )
    })
  })

  it('filters by lane when lane filter is changed', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockJobs))
    const user = userEvent.setup()
    render(<JobsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-job-lane-filter')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-job-lane-filter'), 'default')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('lane=default'),
        expect.any(Object),
      )
    })
  })

  it('displays attempts as fraction of max_attempts', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockJobs))
    render(<JobsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('jobs-table')).toBeInTheDocument()
    })

    expect(screen.getByText('0/3')).toBeInTheDocument()
    expect(screen.getAllByText('3/3').length).toBeGreaterThanOrEqual(1)
  })

  it('shows dead status with error variant', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockJobs))
    render(<JobsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('jobs-table')).toBeInTheDocument()
    })

    const table = screen.getByTestId('jobs-table')
    expect(within(table).getAllByText('dead').length).toBeGreaterThanOrEqual(1)
  })

  it('refreshes data when refresh button is clicked', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(mockJobs))
      .mockResolvedValueOnce(mockJsonResponse(mockJobs))

    const user = userEvent.setup()
    render(<JobsPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('jobs-table')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('refresh-jobs'))

    expect(mockFetch.mock.calls.length).toBeGreaterThan(1)
  })
})
