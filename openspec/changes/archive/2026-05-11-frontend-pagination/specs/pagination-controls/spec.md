## ADDED Requirements

### Requirement: Reusable PaginationControls component
The system SHALL provide a reusable `PaginationControls` React component that accepts `total`, `offset`, `pageSize`, and `onPageChange` props and renders Previous/Next buttons with a range indicator.

#### Scenario: Component renders pagination controls
- **WHEN** `PaginationControls` receives `total=100`, `offset=0`, `pageSize=20`
- **THEN** it SHALL render a "上一页" button (disabled), a "1-20 of 100" text indicator, and a "下一页" button (enabled)

#### Scenario: Component hides when results fit in one page
- **WHEN** `total` is less than or equal to `pageSize`
- **THEN** `PaginationControls` SHALL render nothing (return null)

#### Scenario: Navigate to next page
- **WHEN** user clicks the "下一页" button with current `offset=0`, `pageSize=20`
- **THEN** `onPageChange` SHALL be called with `offset=20`

#### Scenario: Navigate to previous page
- **WHEN** user clicks the "上一页" button with current `offset=20`, `pageSize=20`
- **THEN** `onPageChange` SHALL be called with `offset=0`

#### Scenario: Previous button disabled on first page
- **WHEN** `offset` is 0
- **THEN** the "上一页" button SHALL be disabled

#### Scenario: Next button disabled on last page
- **WHEN** `offset + pageSize >= total`
- **THEN** the "下一页" button SHALL be disabled

#### Scenario: Range indicator on last partial page
- **WHEN** `total=55`, `offset=40`, `pageSize=20`
- **THEN** the text indicator SHALL show "41-55 of 55"

### Requirement: Frontend API client updates for paginated responses
All frontend API client functions that call paginated endpoints SHALL return the full paginated response object (including `items`, `total`, `limit`, `offset`) instead of unwrapping the items array.

#### Scenario: listSources returns paginated response
- **WHEN** `listSources()` is called with `{ limit: 20, offset: 0 }`
- **THEN** it SHALL return a Promise resolving to `{ items: Source[], total: number, limit: number, offset: number }`

#### Scenario: listRecipes returns paginated response
- **WHEN** `listRecipes()` is called with `{ limit: 20, offset: 0 }`
- **THEN** it SHALL return a Promise resolving to `{ items: Recipe[], total: number, limit: number, offset: number }`

#### Scenario: listSchedules returns paginated response
- **WHEN** `listSchedules()` is called with `{ limit: 20, offset: 0 }`
- **THEN** it SHALL return a Promise resolving to `{ items: Schedule[], total: number, limit: number, offset: number }`

### Requirement: List pages integrate PaginationControls
The Sources, Recipes, Schedules, Crawls, and Jobs pages SHALL integrate the `PaginationControls` component and manage `offset` state. Filter changes SHALL reset `offset` to 0.

#### Scenario: Sources page with pagination
- **WHEN** user visits the Sources page and there are more than 20 sources
- **THEN** the page SHALL display at most 20 sources and show PaginationControls at the bottom

#### Scenario: Filter resets pagination
- **WHEN** user changes a filter on any list page while on page 2 (offset=20)
- **THEN** the offset SHALL reset to 0 and the first page of filtered results SHALL be displayed

#### Scenario: Crawls page passes limit and offset to API
- **WHEN** user is on the Crawls page and navigates to page 2
- **THEN** the page SHALL call `listCrawlRuns` with `offset=20` and `limit=20`

#### Scenario: Jobs page passes limit and offset to API
- **WHEN** user is on the Jobs page and navigates to page 2
- **THEN** the page SHALL call `listJobs` with `offset=20` and `limit=20`

### Requirement: Content Library uses shared PaginationControls
The Content Library page SHALL replace its inline pagination UI with the shared `PaginationControls` component, maintaining identical behavior.

#### Scenario: Content Library pagination unchanged
- **WHEN** the Content Library page is refactored to use PaginationControls
- **THEN** the pagination behavior (Previous/Next buttons, range display) SHALL remain identical to the previous inline implementation
