import '@testing-library/jest-dom/vitest'

import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Source } from '../../../types/source'
import { SourcesPage } from '../sources-page'

// Mock source data
const mockSources: Source[] = [
  {
    id: 'src-1',
    name: 'TechNews',
    kind: 'web',
    status: 'candidate',
    url: 'https://tech.example.com',
    trust_level: 'medium',
    failure_count: 0,
    created_at: '2026-01-01T10:00:00Z',
    updated_at: '2026-01-01T10:00:00Z',
  },
  {
    id: 'src-2',
    name: 'BlogFeed',
    kind: 'rss',
    status: 'watched',
    url: 'https://blog.example.com/feed',
    trust_level: 'high',
    failure_count: 2,
    created_at: '2026-01-02T10:00:00Z',
    updated_at: '2026-01-02T10:00:00Z',
  },
  {
    id: 'src-3',
    name: 'DataAPI',
    kind: 'api',
    status: 'paused',
    url: 'https://api.data.io/v1',
    trust_level: 'low',
    failure_count: 5,
    created_at: '2026-01-03T10:00:00Z',
    updated_at: '2026-01-03T10:00:00Z',
  },
]

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

/** Wrap an array in a paginated response shape. */
function paginate<T>(items: T[]) {
  return { items, total: items.length, limit: 20, offset: 0 }
}

describe('SourcesPage', () => {
  it('renders the page title and lifecycle hint', () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
    render(<SourcesPage config={config} />)

    expect(screen.getByText('信息源')).toBeInTheDocument()
    expect(screen.getByText(/候选.*测试中.*监控中.*已暂停.*已归档/)).toBeInTheDocument()
  })

  it('shows loading state while fetching sources', () => {
    // Never resolves so loading stays
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<SourcesPage config={config} />)

    expect(screen.getByTestId('sources-loading')).toBeInTheDocument()
    expect(screen.getByText('加载信息源中...')).toBeInTheDocument()
  })

  it('displays sources in a table after loading', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate(mockSources)))
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    // Verify source names appear
    expect(screen.getByText('TechNews')).toBeInTheDocument()
    expect(screen.getByText('BlogFeed')).toBeInTheDocument()
    expect(screen.getByText('DataAPI')).toBeInTheDocument()
  })

  it('shows status pills with correct variants', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate(mockSources)))
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    // Check status pills — text may appear in both filter options and pills
    const table = screen.getByTestId('sources-table')
    expect(within(table).getAllByText('候选').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getAllByText('监控中').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getAllByText('已暂停').length).toBeGreaterThanOrEqual(1)
  })

  it('shows empty state when no sources exist', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-empty')).toBeInTheDocument()
    })

    expect(screen.getByText('未找到信息源')).toBeInTheDocument()
    expect(screen.getByText(/点击"新建信息源"来创建第一个信息源/)).toBeInTheDocument()
  })

  it('shows error state when API fails', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error'),
    })
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-error')).toBeInTheDocument()
    })
  })

  it('filters sources by search text on client side', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate(mockSources)))
    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    // Type in search
    const searchInput = screen.getByTestId('input-source-search')
    await user.type(searchInput, 'Tech')

    // Only TechNews should be visible in the table
    expect(screen.getByText('TechNews')).toBeInTheDocument()
    expect(screen.queryByText('BlogFeed')).not.toBeInTheDocument()
    expect(screen.queryByText('DataAPI')).not.toBeInTheDocument()
  })

  it('sends status filter parameter to the API', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockSources[0]])))
    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-status-filter')).toBeInTheDocument()
    })

    // Select status filter
    await user.selectOptions(screen.getByTestId('select-status-filter'), 'candidate')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('status=candidate'),
        expect.any(Object),
      )
    })
  })

  it('shows the propose source form when New Source is clicked', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-source-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-source-button'))

    expect(screen.getByTestId('propose-source-panel')).toBeInTheDocument()
    expect(screen.getByTestId('propose-source-form')).toBeInTheDocument()
  })

  it('hides the form when cancel is clicked', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-source-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-source-button'))
    expect(screen.getByTestId('propose-source-form')).toBeInTheDocument()

    await user.click(screen.getByTestId('cancel-propose-source'))
    expect(screen.queryByTestId('propose-source-form')).not.toBeInTheDocument()
  })
})

describe('ProposeSourceForm', () => {
  it('submits the form with valid data', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(paginate([])))
      .mockResolvedValueOnce(
        mockJsonResponse(
          {
            id: 'new-1',
            name: 'NewSource',
            kind: 'web',
            status: 'candidate',
            url: 'https://new.example.com',
            trust_level: 'medium',
            failure_count: 0,
            created_at: '2026-01-01T10:00:00Z',
            updated_at: '2026-01-01T10:00:00Z',
          },
          201,
        ),
      )
    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-source-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-source-button'))

    // Fill in form
    await user.type(screen.getByTestId('input-source-name'), 'NewSource')
    await user.type(screen.getByTestId('input-source-url'), 'https://new.example.com')
    await user.click(screen.getByTestId('submit-propose-source'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/sources/propose'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('shows validation error when name is empty', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-source-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-source-button'))

    // Submit without filling in the name
    await user.click(screen.getByTestId('submit-propose-source'))

    await waitFor(() => {
      expect(screen.getByTestId('propose-source-error')).toBeInTheDocument()
    })
    expect(screen.getByText(/名称为必填项/)).toBeInTheDocument()
  })

  it('shows conflict error when name already exists', async () => {
    // First call: list sources. Second call: propose (returns 409).
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(paginate([])))
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        statusText: 'Conflict',
        text: () => Promise.resolve("Source 'ExistingSource' already exists"),
      })
    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-source-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-source-button'))
    await user.type(screen.getByTestId('input-source-name'), 'ExistingSource')
    await user.click(screen.getByTestId('submit-propose-source'))

    await waitFor(() => {
      expect(screen.getByTestId('propose-source-error')).toBeInTheDocument()
      expect(screen.getByText(/已存在/)).toBeInTheDocument()
    })
  })
})

describe('SourceRow actions', () => {
  it('shows promote and archive buttons for candidate sources', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockSources[0]])))
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    expect(screen.getByTestId(`action-promote-src-1`)).toBeInTheDocument()
    expect(screen.getByTestId(`action-archive-src-1`)).toBeInTheDocument()
  })

  it('shows resume and archive buttons for paused sources', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockSources[2]])))
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    expect(screen.getByTestId(`action-resume-src-3`)).toBeInTheDocument()
    expect(screen.getByTestId(`action-archive-src-3`)).toBeInTheDocument()
  })

  it('shows no action buttons for archived sources', async () => {
    const archivedSource: Source = {
      ...mockSources[0],
      id: 'src-arch',
      name: 'ArchivedSource',
      status: 'archived',
    }
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([archivedSource])))
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    // No action buttons should exist for archived source
    const row = screen.getByTestId('source-row-src-arch')
    expect(row).toBeInTheDocument()
    // Check that no action buttons are present
    expect(within(row).queryByRole('button')).not.toBeInTheDocument()
  })

  it('calls promote API and refreshes list', async () => {
    // First call: list sources. Second call: promote. Third call: refresh list.
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(paginate([mockSources[0]])))
      .mockResolvedValueOnce(
        mockJsonResponse({
          ...mockSources[0],
          status: 'testing',
        }),
      )
      .mockResolvedValueOnce(
        mockJsonResponse(paginate([{ ...mockSources[0], status: 'testing' }])),
      )

    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('action-promote-src-1'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/sources/src-1/promote'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('shows edit button for candidate source and opens edit form', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockSources[0]])))
    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    expect(screen.getByTestId('action-edit-src-1')).toBeInTheDocument()

    await user.click(screen.getByTestId('action-edit-src-1'))
    expect(screen.getByTestId('source-edit-row-src-1')).toBeInTheDocument()
    expect(screen.getByTestId('edit-source-name')).toBeInTheDocument()
    expect(screen.getByTestId('edit-source-url')).toBeInTheDocument()
  })

  it('cancels edit form without making API call', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockSources[0]])))
    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('action-edit-src-1'))
    await user.click(screen.getByTestId('edit-source-cancel'))

    expect(screen.queryByTestId('source-edit-row-src-1')).not.toBeInTheDocument()
    expect(screen.getByTestId('source-row-src-1')).toBeInTheDocument()
  })

  it('submits edit form and refreshes list', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(paginate([mockSources[0]])))
      .mockResolvedValueOnce(
        mockJsonResponse({ ...mockSources[0], name: 'UpdatedName' }),
      )
      .mockResolvedValueOnce(
        mockJsonResponse(paginate([{ ...mockSources[0], name: 'UpdatedName' }])),
      )

    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('action-edit-src-1'))
    const nameInput = screen.getByTestId('edit-source-name')
    await user.clear(nameInput)
    await user.type(nameInput, 'UpdatedName')
    await user.click(screen.getByTestId('edit-source-save'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/sources/src-1'),
        expect.objectContaining({ method: 'PATCH' }),
      )
    })
  })

  it('shows confirm dialog for archive action', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockSources[0]])))
    const user = userEvent.setup()
    render(<SourcesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('sources-table')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('action-archive-src-1'))

    // ConfirmDialog should appear
    expect(screen.getByTestId('confirm-ok')).toBeInTheDocument()
    expect(screen.getByText(/归档.*TechNews/)).toBeInTheDocument()
  })
})
