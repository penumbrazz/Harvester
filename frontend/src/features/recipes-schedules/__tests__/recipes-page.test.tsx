import '@testing-library/jest-dom/vitest'

import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Recipe } from '../../../types/recipe'
import { RecipesPage } from '../recipes-page'

const mockRecipes: Recipe[] = [
  {
    id: 'recipe-1',
    name: 'TechNews Scraper',
    executor: 'http_fetch',
    risk_level: 'low',
    approval_status: 'pending',
    version: 1,
    created_at: '2026-01-01T10:00:00Z',
    updated_at: '2026-01-01T10:00:00Z',
  },
  {
    id: 'recipe-2',
    name: 'BlogFeed Parser',
    executor: 'rss_parse',
    risk_level: 'medium',
    approval_status: 'approved',
    version: 1,
    created_at: '2026-01-02T10:00:00Z',
    updated_at: '2026-01-02T10:00:00Z',
  },
  {
    id: 'recipe-3',
    name: 'Static Scraper',
    executor: 'static',
    risk_level: 'high',
    approval_status: 'rejected',
    version: 1,
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
    statusText: status === 200 ? 'OK' : status === 201 ? 'Created' : 'Error',
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  })
}

describe('RecipesPage', () => {
  it('renders the page title and lifecycle hint', () => {
    mockFetch.mockResolvedValue(mockJsonResponse([]))
    render(<RecipesPage config={config} />)

    expect(screen.getByText('Recipes')).toBeInTheDocument()
    expect(screen.getByText(/Pending.*Approved.*Deprecated/)).toBeInTheDocument()
  })

  it('shows loading state while fetching recipes', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<RecipesPage config={config} />)

    expect(screen.getByTestId('recipes-loading')).toBeInTheDocument()
    expect(screen.getByText('Loading recipes...')).toBeInTheDocument()
  })

  it('displays recipes in a table after loading', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockRecipes))
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    expect(screen.getByText('TechNews Scraper')).toBeInTheDocument()
    expect(screen.getByText('BlogFeed Parser')).toBeInTheDocument()
    expect(screen.getByText('Static Scraper')).toBeInTheDocument()
  })

  it('shows approval status pills with correct text', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockRecipes))
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    const table = screen.getByTestId('recipes-table')
    expect(within(table).getAllByText('Pending').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getAllByText('Approved').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getAllByText('Rejected').length).toBeGreaterThanOrEqual(1)
  })

  it('shows empty state when no recipes exist', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse([]))
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-empty')).toBeInTheDocument()
    })

    expect(screen.getByText('No recipes found')).toBeInTheDocument()
    expect(
      screen.getByText(/Click "New Recipe" to create your first recipe/),
    ).toBeInTheDocument()
  })

  it('shows error state when API fails', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error'),
    })
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-error')).toBeInTheDocument()
    })
  })

  it('filters recipes by search text on client side', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(mockRecipes))
    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    const searchInput = screen.getByTestId('input-recipe-search')
    await user.type(searchInput, 'Tech')

    expect(screen.getByText('TechNews Scraper')).toBeInTheDocument()
    expect(screen.queryByText('BlogFeed Parser')).not.toBeInTheDocument()
    expect(screen.queryByText('Static Scraper')).not.toBeInTheDocument()
  })

  it('sends approval_status filter parameter to the API', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse([mockRecipes[1]]))
    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-approval-filter')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-approval-filter'), 'approved')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('approval_status=approved'),
        expect.any(Object),
      )
    })
  })

  it('sends executor filter parameter to the API', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse([mockRecipes[0]]))
    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('select-executor-filter')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId('select-executor-filter'), 'http_fetch')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('executor=http_fetch'),
        expect.any(Object),
      )
    })
  })

  it('shows the create recipe form when New Recipe is clicked', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse([]))
    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-recipe-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-recipe-button'))

    expect(screen.getByTestId('create-recipe-panel')).toBeInTheDocument()
    expect(screen.getByTestId('create-recipe-form')).toBeInTheDocument()
  })

  it('hides the form when cancel is clicked', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse([]))
    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-recipe-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-recipe-button'))
    expect(screen.getByTestId('create-recipe-form')).toBeInTheDocument()

    await user.click(screen.getByTestId('cancel-create-recipe'))
    expect(screen.queryByTestId('create-recipe-form')).not.toBeInTheDocument()
  })

  it('shows approve button for pending recipes', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse([mockRecipes[0]]))
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    expect(screen.getByTestId('approve-recipe-recipe-1')).toBeInTheDocument()
    expect(screen.queryByTestId('approve-recipe-recipe-2')).not.toBeInTheDocument()
  })
})

describe('Create Recipe Form', () => {
  it('submits the form with valid data', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse([]))
      .mockResolvedValueOnce(
        mockJsonResponse(
          {
            id: 'new-recipe-1',
            name: 'MyScraper',
            executor: 'http_fetch',
            risk_level: 'low',
            approval_status: 'pending',
            version: 1,
            created_at: '2026-01-01T10:00:00Z',
            updated_at: null,
          },
          201,
        ),
      )
      .mockResolvedValueOnce(mockJsonResponse([]))

    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-recipe-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-recipe-button'))

    await user.type(screen.getByTestId('input-recipe-name'), 'MyScraper')
    await user.click(screen.getByTestId('submit-create-recipe'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/recipes'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('shows validation error when name is empty', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse([]))
    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-recipe-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-recipe-button'))

    // Submit without filling in the name
    await user.click(screen.getByTestId('submit-create-recipe'))

    await waitFor(() => {
      expect(screen.getByTestId('create-recipe-error')).toBeInTheDocument()
    })
    expect(screen.getByText(/Name is required/)).toBeInTheDocument()
  })

  it('shows validation error for invalid JSON config', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse([]))
    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-recipe-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-recipe-button'))

    await user.type(screen.getByTestId('input-recipe-name'), 'TestRecipe')
    const configTextarea = screen.getByTestId('input-recipe-config')
    // Use fireEvent to bypass special character issues with textarea
    await user.click(configTextarea)
    await user.paste('not valid json')
    await user.click(screen.getByTestId('submit-create-recipe'))

    await waitFor(() => {
      expect(screen.getByTestId('create-recipe-error')).toBeInTheDocument()
    })
    expect(screen.getByText(/Config must be valid JSON/)).toBeInTheDocument()
  })

  it('shows API error when creation fails', async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse([])).mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      text: () => Promise.resolve("Unknown executor 'bad'"),
    })

    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('new-recipe-button')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('new-recipe-button'))
    await user.type(screen.getByTestId('input-recipe-name'), 'BadRecipe')
    await user.click(screen.getByTestId('submit-create-recipe'))

    await waitFor(() => {
      expect(screen.getByTestId('create-recipe-error')).toBeInTheDocument()
    })
  })
})
