// Only implemented services are enabled; later phases remain unavailable.
export const capabilities = {
  routing: true,
  reports: true,
  analytics: true,
  events: true,
  ml: false,
} as const
export type { RouteRequest } from './api'
export type { RoutingProfile } from '../features/navigation/route-profile'
export interface ReportDraft {
  category: string
  description: string
  location_id: string
  evidence: File | null
}
