/** Health check response from the backend. */
export interface HealthResponse {
  status: string
}

/** API connection configuration stored in localStorage. */
export interface ApiConfig {
  baseUrl: string
  token: string
}
