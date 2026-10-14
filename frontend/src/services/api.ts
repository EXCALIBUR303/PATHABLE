import type { components } from '../types/api.generated'

export type User = components['schemas']['UserOut']
export type Session = components['schemas']['SessionOut']
export type Profile = components['schemas']['ProfileOut']
export type ProfileInput = components['schemas']['ProfileInput']
export type Campus = components['schemas']['CampusOut']
export type Location = components['schemas']['LocationOut']
export type Infrastructure = components['schemas']['InfrastructureOut']
export type Graph = components['schemas']['GraphOut']
export type Edge = components['schemas']['EdgeOut']
export type Saved = components['schemas']['SavedOut']
export type InfrastructureEdit = components['schemas']['InfrastructureEdit']
export type Register = components['schemas']['Register']
export type Credentials = components['schemas']['Credentials']
export type RouteRequest = components['schemas']['RouteRequest']
export type RouteResult =
  components['schemas']['RouteFound'] | components['schemas']['RouteNoRoute']
export type Route = components['schemas']['Route']
export type GraphVersion = components['schemas']['VersionOut']
export type Report = components['schemas']['ReportOut']
export type ReportCreate = components['schemas']['ReportCreate']
export type ReportReview = components['schemas']['ReportReview']
export type ReportResolve = components['schemas']['ReportResolve']
export type Evidence = components['schemas']['EvidenceOut']
export type Analytics = components['schemas']['AnalyticsOut']
export type Audit = components['schemas']['AuditOut']
export type Prediction = components['schemas']['PredictionOut']
export type InferenceJob = components['schemas']['JobOut']
export type MLStatus = components['schemas']['MLStatus']
export type ReportPage = { items: Report[]; next_cursor: string | null }
export type AuditPage = { items: Audit[]; next_cursor: string | null }

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string,
    public currentVersion?: number,
    public currentGraphVersion?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

let sessionCache: Session | undefined
let sessionFlight: Promise<Session> | undefined
let sessionController: AbortController | undefined
let sessionEpoch = 0
export function setSession(session?: Session) {
  sessionEpoch++
  sessionController?.abort()
  sessionController = undefined
  sessionFlight = undefined
  sessionCache = session
}
export async function fetchSession(): Promise<Session> {
  // Serialize bootstrap across components; no tokens in browser storage or URLs.
  if (!sessionFlight) {
    const epoch = sessionEpoch
    const controller = new AbortController()
    sessionController = controller
    const promise = request<Session>('/auth/session', { signal: controller.signal })
      .then((value) => {
        if (epoch !== sessionEpoch) throw new DOMException('Session changed', 'AbortError')
        sessionCache = value
        return value
      })
      .finally(() => {
        if (sessionFlight === promise) {
          sessionFlight = undefined
          sessionController = undefined
        }
      })
    sessionFlight = promise
  }
  return sessionFlight
}

export async function request<T>(
  path: string,
  options: {
    method?: string
    body?: unknown
    signal?: AbortSignal
    csrf?: boolean
    headers?: Record<string, string>
  } = {},
): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = { Accept: 'application/json', ...options.headers }
  if (method !== 'GET') {
    if (options.csrf !== false) {
      const session = sessionCache ?? (await fetchSession())
      headers['X-CSRF-Token'] = session.csrf_token
    }
    if (options.body !== undefined && !(options.body instanceof FormData))
      headers['Content-Type'] = 'application/json'
  }
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      signal: options.signal,
      ...(options.body !== undefined
        ? { body: options.body instanceof FormData ? options.body : JSON.stringify(options.body) }
        : {}),
    })
  } catch (error) {
    if (
      options.signal?.aborted ||
      (typeof error === 'object' &&
        error !== null &&
        'name' in error &&
        error.name === 'AbortError')
    )
      throw error
    throw new ApiError(
      0,
      'NETWORK_UNAVAILABLE',
      'Cannot reach PathAble. Check your connection and try again.',
    )
  }
  if (!response.ok) {
    const problem: {
      detail?: string
      code?: string
      request_id?: string
      current_version?: number
      current_graph_version?: string
    } = await response.json().catch(() => ({}))
    if (response.status === 401) sessionCache = undefined
    throw new ApiError(
      response.status,
      problem.code ?? 'REQUEST_FAILED',
      problem.detail ?? 'The request could not be completed.',
      problem.request_id,
      problem.current_version,
      problem.current_graph_version,
    )
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}

async function collection<T>(path: string, signal?: AbortSignal): Promise<T[]> {
  const all: T[] = []
  let cursor: string | null = null
  let pages = 0
  do {
    const separator = path.includes('?') ? '&' : '?'
    const page: { items: T[]; next_cursor: string | null } = await request(
      `${path}${separator}limit=100${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`,
      { signal },
    )
    all.push(...page.items)
    cursor = page.next_cursor
    pages++
    if (cursor && pages >= 100)
      throw new ApiError(
        413,
        'DATA_TOO_LARGE',
        'There is too much data to display. Please narrow your search.',
      )
  } while (cursor)
  return all
}

const queryString = (values: Record<string, string | undefined>) =>
  new URLSearchParams(
    Object.entries(values).filter((entry): entry is [string, string] => entry[1] !== undefined),
  ).toString()

export const api = {
  mlStatus: (signal?: AbortSignal) => request<MLStatus>('/ml/status', { signal }),
  predictions: (reportId: string, signal?: AbortSignal) =>
    collection<Prediction>(`/reports/${reportId}/predictions`, signal),
  requestInference: (
    reportId: string,
    body: components['schemas']['InferenceRequest'],
    key: string,
  ) =>
    request<InferenceJob>(`/reports/${reportId}/inference`, {
      method: 'POST',
      body,
      headers: { 'Idempotency-Key': key },
    }),
  inferenceJob: (reportId: string, jobId: string, signal?: AbortSignal) =>
    request<InferenceJob>(`/reports/${reportId}/inference/${jobId}`, { signal }),
  reviewPrediction: (id: string, body: components['schemas']['PredictionReview'], key: string) =>
    request<Prediction>(`/admin/predictions/${id}/review`, {
      method: 'POST',
      body,
      headers: { 'Idempotency-Key': key },
    }),
  reports: (campusId: string, cursor?: string, signal?: AbortSignal) =>
    request<ReportPage>(`/reports?${queryString({ campus_id: campusId, cursor, limit: '25' })}`, {
      signal,
    }),
  report: (id: string, signal?: AbortSignal) => request<Report>(`/reports/${id}`, { signal }),
  submitReport: (body: ReportCreate, key: string) =>
    request<Report>('/reports', { method: 'POST', body, headers: { 'Idempotency-Key': key } }),
  adminReports: (
    campusId: string,
    status?: Report['status'],
    cursor?: string,
    signal?: AbortSignal,
  ) =>
    request<ReportPage>(
      `/admin/reports?${queryString({ campus_id: campusId, status, cursor, limit: '25' })}`,
      { signal },
    ),
  reviewReport: (id: string, body: ReportReview, key: string) =>
    request<Report>(`/admin/reports/${id}/review`, {
      method: 'POST',
      body,
      headers: { 'Idempotency-Key': key },
    }),
  resolveReport: (id: string, body: ReportResolve, key: string) =>
    request<Report>(`/admin/reports/${id}/resolve`, {
      method: 'POST',
      body,
      headers: { 'Idempotency-Key': key },
    }),
  uploadEvidence: (id: string, expectedVersion: number, file: File) => {
    const body = new FormData()
    body.append('expected_version', String(expectedVersion))
    body.append('file', file)
    return request<Evidence>(`/reports/${id}/evidence`, { method: 'POST', body })
  },
  removeEvidence: (reportId: string, id: string, expectedVersion: number) =>
    request<void>(`/reports/${reportId}/evidence/${id}`, {
      method: 'DELETE',
      body: { expected_version: expectedVersion },
    }),
  evidenceUrl: (reportId: string, id: string) =>
    `/api/v1/reports/${reportId}/evidence/${id}/content`,
  analytics: (campusId: string, from: string, to: string, signal?: AbortSignal) =>
    request<Analytics>(`/admin/analytics?${queryString({ campus_id: campusId, from, to })}`, {
      signal,
    }),
  audit: (campusId: string, cursor?: string, signal?: AbortSignal) =>
    request<AuditPage>(
      `/admin/audit?${queryString({ campus_id: campusId, cursor, limit: '25' })}`,
      { signal },
    ),
  campuses: (signal?: AbortSignal) => collection<Campus>('/campuses', signal),
  graph: (campusId: string, signal?: AbortSignal) =>
    request<Graph>(`/campuses/${campusId}/graph`, { signal }),
  graphVersion: (campusId: string, signal?: AbortSignal) =>
    request<GraphVersion>(`/campuses/${campusId}/graph-version`, { signal }),
  calculateRoute: (body: RouteRequest, signal?: AbortSignal) =>
    request<RouteResult>('/routes/calculate', { method: 'POST', body, signal, csrf: false }),
  locations: (campusId: string, signal?: AbortSignal) =>
    collection<Location>(`/locations?campus_id=${campusId}`, signal),
  infrastructure: (campusId: string, signal?: AbortSignal) =>
    collection<Infrastructure>(`/infrastructure?campus_id=${campusId}`, signal),
  register: (body: Register) => request<User>('/auth/register', { method: 'POST', body }),
  login: async (body: Credentials) => {
    const session = await request<Session>('/auth/login', { method: 'POST', body })
    setSession(session)
    return session
  },
  logout: async () => {
    await request<void>('/auth/logout', { method: 'POST' })
    setSession(undefined)
    return fetchSession()
  },
  profile: (signal?: AbortSignal) => request<Profile>('/me/accessibility-profile', { signal }),
  saveProfile: (body: ProfileInput) =>
    request<Profile>('/me/accessibility-profile', { method: 'PUT', body }),
  editUser: (body: components['schemas']['EditUser']) =>
    request<User>('/me', { method: 'PATCH', body }),
  saved: (signal?: AbortSignal) => collection<Saved>('/me/saved-destinations', signal),
  saveDestination: (location_id: string) =>
    request<Saved>('/me/saved-destinations', { method: 'POST', body: { location_id } }),
  removeDestination: (id: string) =>
    request<void>(`/me/saved-destinations/${id}`, { method: 'DELETE' }),
  editInfrastructure: (id: string, body: InfrastructureEdit) =>
    request<Infrastructure>(`/admin/infrastructure/${id}`, { method: 'PATCH', body }),
}
