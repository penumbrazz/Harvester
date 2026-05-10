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

  it('shows placeholder text for unimplemented pages', async () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByTestId('nav-sources'))
    expect(
      screen.getByText(/This page will be implemented in a future update/),
    ).toBeInTheDocument()
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
      expect(screen.getByText('Connected')).toBeInTheDocument()
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
      expect(screen.getByText('Disconnected')).toBeInTheDocument()
    })
  })

  it('shows error status when API base URL is not configured', async () => {
    mockFetch.mockRejectedValue(new Error('Not configured'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Disconnected')).toBeInTheDocument()
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
      expect(screen.getByText('Disconnected')).toBeInTheDocument()
    })

    const retryButton = screen.getByTestId('retry-connection-button')
    await user.click(retryButton)

    await waitFor(() => {
      expect(screen.getByText('Connected')).toBeInTheDocument()
    })
  })
})
