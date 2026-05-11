import '@testing-library/jest-dom/vitest'

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from '../App'

// Mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  localStorage.clear()
})

describe('App shell', () => {
  it('renders the Harvester admin console layout', () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    render(<App />)

    expect(screen.getByText('Harvester')).toBeInTheDocument()
    expect(screen.getByTestId('app-layout')).toBeInTheDocument()
    expect(screen.getByTestId('sidebar')).toBeInTheDocument()
  })

  it('shows the overview page by default', () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    render(<App />)

    expect(screen.getByTestId('page-overview')).toBeInTheDocument()
  })

  it('renders all navigation items', () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    render(<App />)

    const expectedNavItems = [
      'overview',
      'sources',
      'recipes',
      'schedules',
      'crawls',
      'jobs',
      'content',
      'audit',
    ]

    for (const key of expectedNavItems) {
      expect(screen.getByTestId(`nav-${key}`)).toBeInTheDocument()
    }
  })

  it('navigates to placeholder pages without full page reload', async () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByTestId('nav-sources'))
    expect(screen.getByTestId('page-sources')).toBeInTheDocument()
    expect(screen.queryByTestId('page-overview')).not.toBeInTheDocument()

    await user.click(screen.getByTestId('nav-recipes'))
    expect(screen.getByTestId('page-recipes')).toBeInTheDocument()

    await user.click(screen.getByTestId('nav-audit'))
    expect(screen.getByTestId('page-audit-log')).toBeInTheDocument()
  })

  it('renders the sources page with search and filters', async () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByTestId('nav-sources'))
    expect(screen.getByTestId('page-sources')).toBeInTheDocument()
    expect(screen.getByTestId('input-source-search')).toBeInTheDocument()
    expect(screen.getByTestId('select-status-filter')).toBeInTheDocument()
    expect(screen.getByTestId('select-kind-filter')).toBeInTheDocument()
  })

  it('renders the content library page with search and filters', async () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByTestId('nav-content'))
    expect(screen.getByTestId('page-content-library')).toBeInTheDocument()
    expect(screen.getByTestId('search-input')).toBeInTheDocument()
    expect(screen.getByTestId('search-mode-select')).toBeInTheDocument()
  })

  it('renders the crawls page with filter and trigger button', async () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByTestId('nav-crawls'))
    expect(screen.getByTestId('page-crawls')).toBeInTheDocument()
    expect(screen.getByTestId('select-crawl-status-filter')).toBeInTheDocument()
    expect(screen.getByTestId('trigger-crawl-button')).toBeInTheDocument()
  })

  it('renders the jobs page with filters', async () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByTestId('nav-jobs'))
    expect(screen.getByTestId('page-jobs')).toBeInTheDocument()
    expect(screen.getByTestId('select-job-type-filter')).toBeInTheDocument()
    expect(screen.getByTestId('select-job-status-filter')).toBeInTheDocument()
  })
})

describe('API connection status', () => {
  it('shows connected status when /health returns ok', async () => {
    localStorage.setItem(
      'harvester-api-config',
      JSON.stringify({ baseUrl: 'http://localhost:8001', token: '' }),
    )
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' }),
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument()
    })
  })

  it('shows error status when /health fails', async () => {
    localStorage.setItem(
      'harvester-api-config',
      JSON.stringify({ baseUrl: 'http://localhost:8001', token: '' }),
    )
    mockFetch.mockRejectedValue(new Error('Network error'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('已断开')).toBeInTheDocument()
    })
  })

  it('shows error status when API base URL is not configured', async () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('已断开')).toBeInTheDocument()
    })
  })

  it('allows configuring API base URL and token', async () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    const user = userEvent.setup()
    render(<App />)

    const baseUrlInput = screen.getByTestId('input-api-base-url')
    const tokenInput = screen.getByTestId('input-api-token')

    await user.type(baseUrlInput, 'http://localhost:8001')
    await user.type(tokenInput, 'test-token')

    const saveButton = screen.getByTestId('save-config-button')
    await user.click(saveButton)

    // After saving, the config form should collapse and show the URL
    expect(screen.getByTestId('api-config-display')).toBeInTheDocument()
    expect(screen.getByText('http://localhost:8001')).toBeInTheDocument()
  })

  it('persists config to localStorage', async () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByTestId('input-api-base-url'), 'http://api.test')
    await user.type(screen.getByTestId('input-api-token'), 'my-token')
    await user.click(screen.getByTestId('save-config-button'))

    const stored = JSON.parse(localStorage.getItem('harvester-api-config') || '{}')
    expect(stored.baseUrl).toBe('http://api.test')
    expect(stored.token).toBe('my-token')
  })

  it('includes Authorization header when token is set', async () => {
    localStorage.setItem(
      'harvester-api-config',
      JSON.stringify({
        baseUrl: 'http://localhost:8001',
        token: 'secret-token',
      }),
    )
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' }),
    })

    render(<App />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8001/health',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer secret-token',
          }),
        }),
      )
    })
  })

  it('provides a retry button to re-check connection', async () => {
    localStorage.setItem(
      'harvester-api-config',
      JSON.stringify({ baseUrl: 'http://localhost:8001', token: '' }),
    )
    mockFetch.mockRejectedValueOnce(new Error('Network error'))
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' }),
    })

    const user = userEvent.setup()
    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('已断开')).toBeInTheDocument()
    })

    const retryButton = screen.getByTestId('retry-connection-button')
    await user.click(retryButton)

    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument()
    })
  })
})
