import '@testing-library/jest-dom/vitest'

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AuditEventListResponse } from '../../../types/audit'
import { AuditPage } from '../audit-page'

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

const mockEvents: AuditEventListResponse = {
  items: [
    {
      id: 'evt-1',
      actor: 'api',
      action: 'source.propose',
      entity_type: 'source',
      entity_id: 'src-1',
      before_summary: null,
      after_summary: 'name=test, kind=web, status=candidate',
      reason: null,
      created_at: '2026-01-15T12:00:00Z',
    },
    {
      id: 'evt-2',
      actor: 'api',
      action: 'status_change',
      entity_type: 'source',
      entity_id: 'src-1',
      before_summary: 'status=candidate',
      after_summary: 'status=testing',
      reason: null,
      created_at: '2026-01-15T11:00:00Z',
    },
    {
      id: 'evt-3',
      actor: 'scheduler',
      action: 'crawl.trigger',
      entity_type: 'crawl_run',
      entity_id: 'crawl-1',
      before_summary: null,
      after_summary: 'status=pending, source_id=src-1',
      reason: 'Scheduled trigger',
      created_at: '2026-01-15T10:00:00Z',
    },
  ],
  total: 3,
}

describe('AuditPage', () => {
  it('renders the page title and testid', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<AuditPage config={config} />)

    expect(screen.getByTestId('page-audit-log')).toBeInTheDocument()
    expect(screen.getByText('审计日志')).toBeInTheDocument()
  })

  it('shows loading state while fetching events', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<AuditPage config={config} />)

    expect(screen.getByTestId('audit-loading')).toBeInTheDocument()
  })

  it('renders audit timeline events after loading', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockEvents))

    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-timeline')).toBeInTheDocument()
    })

    expect(screen.getByText('source.propose')).toBeInTheDocument()
    expect(screen.getByText('status_change')).toBeInTheDocument()
    expect(screen.getByText('crawl.trigger')).toBeInTheDocument()
  })

  it('renders event details including actor, entity type and reason', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockEvents))

    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-timeline')).toBeInTheDocument()
    })

    // Actor "api" appears twice (two events), "scheduler" once
    expect(screen.getAllByText('api').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('scheduler')).toBeInTheDocument()
    // Entity types
    expect(screen.getAllByText('source').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('crawl_run')).toBeInTheDocument()
    expect(screen.getByText(/Scheduled trigger/)).toBeInTheDocument()
  })

  it('shows empty state when no events exist', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse({ items: [], total: 0 }))

    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-empty')).toBeInTheDocument()
    })
  })

  it('shows error state when API fails', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error'),
    })

    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-error')).toBeInTheDocument()
    })
  })

  it('renders filter controls', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<AuditPage config={config} />)

    expect(screen.getByTestId('select-entity-type-filter')).toBeInTheDocument()
    expect(screen.getByTestId('select-action-filter')).toBeInTheDocument()
  })

  it('displays before/after state summaries, not raw payload', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockEvents))

    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-timeline')).toBeInTheDocument()
    })

    // Should display after_summary text
    expect(
      screen.getByText(/name=test, kind=web, status=candidate/),
    ).toBeInTheDocument()
    // Should NOT expose raw before_state/after_state JSONB keys in DOM
    const timeline = screen.getByTestId('audit-timeline')
    expect(timeline.textContent).not.toContain('"before_state"')
    expect(timeline.textContent).not.toContain('"after_state"')
  })

  it('renders load more button when more events are available', async () => {
    const manyEvents: AuditEventListResponse = {
      items: Array.from({ length: 20 }, (_, i) => ({
        id: `evt-${i}`,
        actor: 'api',
        action: 'source.propose',
        entity_type: 'source',
        entity_id: 'src-1',
        before_summary: null,
        after_summary: 'status=candidate',
        reason: null,
        created_at: `2026-01-15T${String(12 - Math.floor(i / 2)).padStart(2, '0')}:00:00Z`,
      })),
      total: 30,
    }
    mockFetch.mockResolvedValueOnce(mockJsonResponse(manyEvents))

    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-load-more')).toBeInTheDocument()
    })
  })

  it('hides load more button when all events are loaded', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockEvents))

    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-timeline')).toBeInTheDocument()
    })

    expect(screen.queryByTestId('audit-load-more')).not.toBeInTheDocument()
  })

  it('loads more events when load more button is clicked', async () => {
    const firstPage: AuditEventListResponse = {
      items: Array.from({ length: 20 }, (_, i) => ({
        id: `evt-${i}`,
        actor: 'api',
        action: 'source.propose',
        entity_type: 'source',
        entity_id: 'src-1',
        before_summary: null,
        after_summary: 'status=candidate',
        reason: null,
        created_at: '2026-01-15T12:00:00Z',
      })),
      total: 30,
    }
    const secondPage: AuditEventListResponse = {
      items: Array.from({ length: 10 }, (_, i) => ({
        id: `evt-extra-${20 + i}`,
        actor: 'api',
        action: 'status_change',
        entity_type: 'source',
        entity_id: 'src-1',
        before_summary: 'status=candidate',
        after_summary: 'status=testing',
        reason: null,
        created_at: '2026-01-14T12:00:00Z',
      })),
      total: 30,
    }
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(firstPage))
      .mockResolvedValueOnce(mockJsonResponse(secondPage))

    const user = userEvent.setup()
    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-load-more')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('audit-load-more'))

    // After loading more, the new action types should be present
    await waitFor(() => {
      expect(screen.getAllByText('status_change').length).toBeGreaterThanOrEqual(10)
    })
  })

  it('filters events by entity type when filter is changed', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockEvents)).mockResolvedValueOnce(
      mockJsonResponse({
        items: [mockEvents.items[0]],
        total: 1,
      }),
    )

    const user = userEvent.setup()
    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-timeline')).toBeInTheDocument()
    })

    const select = screen.getByTestId('select-entity-type-filter')
    await user.selectOptions(select, 'source')

    await waitFor(() => {
      expect(mockFetch.mock.calls.length).toBeGreaterThanOrEqual(2)
    })

    // Find the last call URL which should have the filter
    const lastCallUrl = mockFetch.mock.calls[
      mockFetch.mock.calls.length - 1
    ][0] as string
    expect(lastCallUrl).toContain('entity_type=source')
  })

  it('filters events by action when action filter is changed', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse(mockEvents)).mockResolvedValueOnce(
      mockJsonResponse({
        items: [mockEvents.items[0]],
        total: 1,
      }),
    )

    const user = userEvent.setup()
    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-timeline')).toBeInTheDocument()
    })

    const select = screen.getByTestId('select-action-filter')
    await user.selectOptions(select, 'source.propose')

    await waitFor(() => {
      expect(mockFetch.mock.calls.length).toBeGreaterThanOrEqual(2)
    })

    const lastCallUrl = mockFetch.mock.calls[
      mockFetch.mock.calls.length - 1
    ][0] as string
    expect(lastCallUrl).toContain('action=source.propose')
  })

  it('refreshes events when refresh button is clicked', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(mockEvents))
      .mockResolvedValueOnce(mockJsonResponse(mockEvents))

    const user = userEvent.setup()
    render(<AuditPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('audit-timeline')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('refresh-audit'))

    expect(mockFetch.mock.calls.length).toBeGreaterThanOrEqual(2)
  })
})
