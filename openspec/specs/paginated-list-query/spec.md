## ADDED Requirements

### Requirement: Unified paginated response format
All list API endpoints SHALL return a JSON object with the following fields: `items` (array of resource objects), `total` (integer count of all matching records), `limit` (integer, actual page size used), and `offset` (integer, actual offset used).

#### Scenario: Default pagination parameters
- **WHEN** a client calls a list endpoint without `limit` or `offset` query parameters
- **THEN** the API SHALL return results with `limit=20`, `offset=0`, and `total` equal to the count of all matching records

#### Scenario: Custom pagination parameters
- **WHEN** a client calls a list endpoint with `limit=50` and `offset=100`
- **THEN** the API SHALL return `limit=50`, `offset=100`, `items` containing at most 50 records starting from position 100, and `total` equal to the total count of matching records

#### Scenario: Offset beyond result set
- **WHEN** a client calls a list endpoint with `offset` greater than the total matching records
- **THEN** the API SHALL return an empty `items` array, the correct `total`, and the requested `limit` and `offset`

### Requirement: Sources API pagination
The `GET /sources` endpoint SHALL accept `limit` and `offset` query parameters and return the unified paginated response format instead of a flat array.

#### Scenario: List sources with pagination
- **WHEN** a client calls `GET /sources?limit=10&offset=0`
- **THEN** the response SHALL be `{ items: [...], total: N, limit: 10, offset: 0 }` where `items` contains at most 10 Source objects ordered by `created_at` descending

#### Scenario: List sources with filters and pagination
- **WHEN** a client calls `GET /sources?status=active&limit=10&offset=0`
- **THEN** only sources with `status=active` SHALL be included in the count and results, with `total` reflecting only matching records

### Requirement: Recipes API pagination
The `GET /recipes` endpoint SHALL accept `limit` and `offset` query parameters and return the unified paginated response format instead of a flat array.

#### Scenario: List recipes with pagination
- **WHEN** a client calls `GET /recipes?limit=15&offset=30`
- **THEN** the response SHALL be `{ items: [...], total: N, limit: 15, offset: 30 }` with at most 15 Recipe objects ordered by `created_at` descending

### Requirement: Schedules API pagination
The `GET /schedules` endpoint SHALL accept `limit` and `offset` query parameters and return the unified paginated response format instead of a flat array.

#### Scenario: List schedules with pagination
- **WHEN** a client calls `GET /schedules?limit=20&offset=0`
- **THEN** the response SHALL be `{ items: [...], total: N, limit: 20, offset: 0 }` with at most 20 Schedule objects ordered by `created_at` descending

### Requirement: Crawl runs API response includes limit and offset
The `GET /crawl/runs` endpoint response SHALL include `limit` and `offset` fields in addition to the existing `items` and `total` fields.

#### Scenario: Crawl runs response format
- **WHEN** a client calls `GET /crawl/runs?limit=20&offset=0`
- **THEN** the response SHALL be `{ items: [...], total: N, limit: 20, offset: 0 }`

### Requirement: Jobs API response includes limit and offset
The `GET /queue/jobs` endpoint response SHALL include `limit` and `offset` fields in addition to the existing `items` and `total` fields.

#### Scenario: Jobs response format
- **WHEN** a client calls `GET /queue/jobs?limit=20&offset=0`
- **THEN** the response SHALL be `{ items: [...], total: N, limit: 20, offset: 0 }`

### Requirement: Pagination parameter validation
All paginated endpoints SHALL validate `limit` to be between 1 and 100 (inclusive) and `offset` to be >= 0. Invalid values SHALL result in a 422 Unprocessable Entity response.

#### Scenario: Limit exceeds maximum
- **WHEN** a client calls a list endpoint with `limit=200`
- **THEN** the API SHALL return HTTP 422 with a validation error message

#### Scenario: Negative offset
- **WHEN** a client calls a list endpoint with `offset=-1`
- **THEN** the API SHALL return HTTP 422 with a validation error message
