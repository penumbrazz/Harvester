import '@testing-library/jest-dom/vitest'

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ApiConfig } from '../../../types/api'
import { ApprovedRecipeSelector, SourceSelector } from '../components/selectors'

const config: ApiConfig = {
  baseUrl: 'http://localhost:8001',
  token: 'test-token',
}

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

function mockJsonResponse(data: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    statusText: 'OK',
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  })
}

describe('SourceSelector', () => {
  it('renders and fetches sources', async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse([
        {
          id: 'src-1',
          name: 'WatchedSource',
          status: 'watched',
          kind: 'rss',
          url: null,
          trust_level: 'medium',
          failure_count: 0,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'src-2',
          name: 'CandidateSource',
          status: 'candidate',
          kind: 'web',
          url: null,
          trust_level: 'low',
          failure_count: 0,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]),
    )

    const onChange = vi.fn()
    render(<SourceSelector config={config} value="" onChange={onChange} />)

    await waitFor(() => {
      expect(screen.getByText('WatchedSource (watched)')).toBeInTheDocument()
    })
    expect(screen.getByText('CandidateSource (candidate)')).toBeInTheDocument()
  })

  it('filters to schedulable sources only when schedulableOnly is true', async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse([
        {
          id: 'src-1',
          name: 'WatchedSource',
          status: 'watched',
          kind: 'rss',
          url: null,
          trust_level: 'medium',
          failure_count: 0,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'src-2',
          name: 'CandidateSource',
          status: 'candidate',
          kind: 'web',
          url: null,
          trust_level: 'low',
          failure_count: 0,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'src-3',
          name: 'ActiveSource',
          status: 'active',
          kind: 'api',
          url: null,
          trust_level: 'high',
          failure_count: 0,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]),
    )

    const onChange = vi.fn()
    render(
      <SourceSelector config={config} value="" onChange={onChange} schedulableOnly />,
    )

    await waitFor(() => {
      expect(screen.getByText('WatchedSource (watched)')).toBeInTheDocument()
    })

    // Candidate should NOT appear
    expect(screen.queryByText(/CandidateSource/)).not.toBeInTheDocument()
    // Active SHOULD appear
    expect(screen.getByText('ActiveSource (active)')).toBeInTheDocument()
  })

  it('calls onChange when a source is selected', async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse([
        {
          id: 'src-1',
          name: 'TestSource',
          status: 'watched',
          kind: 'rss',
          url: null,
          trust_level: 'medium',
          failure_count: 0,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]),
    )

    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<SourceSelector config={config} value="" onChange={onChange} />)

    await waitFor(() => {
      expect(screen.getByText('TestSource (watched)')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-source'), 'src-1')
    expect(onChange).toHaveBeenCalled()
  })
})

describe('ApprovedRecipeSelector', () => {
  it('renders and fetches recipes, marking non-approved as disabled', async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse([
        {
          id: 'recipe-1',
          name: 'ApprovedRecipe',
          executor: 'http_fetch',
          approval_status: 'approved',
          risk_level: 'low',
          version: 1,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: null,
        },
        {
          id: 'recipe-2',
          name: 'PendingRecipe',
          executor: 'rss_parse',
          approval_status: 'pending',
          risk_level: 'low',
          version: 1,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: null,
        },
      ]),
    )

    const onChange = vi.fn()
    render(<ApprovedRecipeSelector config={config} value="" onChange={onChange} />)

    await waitFor(() => {
      expect(screen.getByText(/ApprovedRecipe/)).toBeInTheDocument()
    })

    // Pending recipe option should be disabled
    const pendingOption = screen.getByText(/PendingRecipe.*pending/)
    expect(pendingOption.closest('option')).toHaveAttribute('disabled')
  })

  it('calls onChange when an approved recipe is selected', async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse([
        {
          id: 'recipe-1',
          name: 'ApprovedRecipe',
          executor: 'http_fetch',
          approval_status: 'approved',
          risk_level: 'low',
          version: 1,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: null,
        },
      ]),
    )

    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<ApprovedRecipeSelector config={config} value="" onChange={onChange} />)

    await waitFor(() => {
      expect(screen.getByText(/ApprovedRecipe/)).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-approved-recipe'), 'recipe-1')
    expect(onChange).toHaveBeenCalled()
  })
})
