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

/** Wrap an array in a paginated response shape. */
function paginate<T>(items: T[]) {
  return { items, total: items.length, limit: 20, offset: 0 }
}

describe('RecipesPage', () => {
  it('renders the page title and lifecycle hint', () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
    render(<RecipesPage config={config} />)

    expect(screen.getByText('采集配方')).toBeInTheDocument()
    expect(screen.getByText(/待审批.*已批准.*已废弃/)).toBeInTheDocument()
  })

  it('shows loading state while fetching recipes', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<RecipesPage config={config} />)

    expect(screen.getByTestId('recipes-loading')).toBeInTheDocument()
    expect(screen.getByText('加载配方中...')).toBeInTheDocument()
  })

  it('displays recipes in a table after loading', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate(mockRecipes)))
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    expect(screen.getByText('TechNews Scraper')).toBeInTheDocument()
    expect(screen.getByText('BlogFeed Parser')).toBeInTheDocument()
    expect(screen.getByText('Static Scraper')).toBeInTheDocument()
  })

  it('shows approval status pills with correct text', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate(mockRecipes)))
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    const table = screen.getByTestId('recipes-table')
    expect(within(table).getAllByText('待审批').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getAllByText('已批准').length).toBeGreaterThanOrEqual(1)
    expect(within(table).getAllByText('已拒绝').length).toBeGreaterThanOrEqual(1)
  })

  it('shows empty state when no recipes exist', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-empty')).toBeInTheDocument()
    })

    expect(screen.getByText('未找到配方')).toBeInTheDocument()
    expect(screen.getByText(/点击"新建配方"来创建第一个配方/)).toBeInTheDocument()
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
    mockFetch.mockResolvedValue(mockJsonResponse(paginate(mockRecipes)))
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
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockRecipes[1]])))
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
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockRecipes[0]])))
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
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
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
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
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
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockRecipes[0]])))
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    expect(screen.getByTestId('action-approve-recipe-1')).toBeInTheDocument()
    expect(screen.queryByTestId('action-approve-recipe-2')).not.toBeInTheDocument()
  })
})

describe('Create Recipe Form', () => {
  it('submits the form with valid data', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(paginate([])))
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
      .mockResolvedValueOnce(mockJsonResponse(paginate([])))

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
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
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
    expect(screen.getByText(/名称为必填项/)).toBeInTheDocument()
  })

  it('shows validation error for invalid JSON config', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([])))
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
    expect(screen.getByText(/配置必须是有效的 JSON/)).toBeInTheDocument()
  })

  it('shows API error when creation fails', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(paginate([])))
      .mockResolvedValueOnce({
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

describe('RecipeRow management actions', () => {
  it('shows reject and edit buttons for pending recipe', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockRecipes[0]])))
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    expect(screen.getByTestId('action-approve-recipe-1')).toBeInTheDocument()
    expect(screen.getByTestId('action-reject-recipe-1')).toBeInTheDocument()
    expect(screen.getByTestId('action-edit-recipe-1')).toBeInTheDocument()
  })

  it('opens edit form and submits changes', async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse(paginate([mockRecipes[0]])))
      .mockResolvedValueOnce(
        mockJsonResponse({ ...mockRecipes[0], name: 'RenamedScraper' }),
      )
      .mockResolvedValueOnce(
        mockJsonResponse(paginate([{ ...mockRecipes[0], name: 'RenamedScraper' }])),
      )

    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('action-edit-recipe-1'))
    expect(screen.getByTestId('recipe-edit-row-recipe-1')).toBeInTheDocument()

    const nameInput = screen.getByTestId('edit-recipe-name')
    await user.clear(nameInput)
    await user.type(nameInput, 'RenamedScraper')
    await user.click(screen.getByTestId('edit-recipe-save'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/recipes/recipe-1'),
        expect.objectContaining({ method: 'PATCH' }),
      )
    })
  })

  it('cancels edit without making API call', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockRecipes[0]])))
    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('action-edit-recipe-1'))
    await user.click(screen.getByTestId('edit-recipe-cancel'))

    expect(screen.queryByTestId('recipe-edit-row-recipe-1')).not.toBeInTheDocument()
  })

  it('shows confirm dialog for reject action', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([mockRecipes[0]])))
    const user = userEvent.setup()
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('action-reject-recipe-1'))
    expect(screen.getByTestId('confirm-ok')).toBeInTheDocument()
    expect(screen.getByText(/拒绝.*TechNews Scraper/)).toBeInTheDocument()
  })

  it('shows no action buttons for deprecated recipe', async () => {
    const deprecatedRecipe: Recipe = {
      ...mockRecipes[0],
      id: 'recipe-dep',
      approval_status: 'deprecated',
    }
    mockFetch.mockResolvedValue(mockJsonResponse(paginate([deprecatedRecipe])))
    render(<RecipesPage config={config} />)

    await waitFor(() => {
      expect(screen.getByTestId('recipes-table')).toBeInTheDocument()
    })

    const row = screen.getByTestId('recipe-row-recipe-dep')
    expect(row).toBeInTheDocument()
    expect(within(row).queryByRole('button')).not.toBeInTheDocument()
  })
})
