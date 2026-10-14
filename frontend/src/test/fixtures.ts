import type { Location, Profile, Session } from '../services/api'

export const profile: Profile = {
  id: '00000000-0000-4000-8000-000000000001',
  created_at: '2026-10-12T06:00:00Z',
  updated_at: '2026-10-12T06:00:00Z',
  row_version: 1,
  avoid_stairs: true,
  max_slope_pct: 8,
  min_width_m: 0.9,
  excluded_surfaces: ['uneven', 'gravel'],
  unknown_policy: 'exclude',
  travel_speed_mps: 1,
}
export const session: Session = {
  user: {
    id: '00000000-0000-4000-8000-000000000002',
    email: 'test@example.com',
    display_name: 'Test user',
    role: 'user',
    row_version: 1,
  },
  csrf_token: 'test-only-csrf',
  expires_at: '2026-10-13T06:00:00Z',
}
export const locations: Location[] = ['Library', 'Welcome Centre', 'Learning Hall'].map(
  (name, index) => ({
    id: `00000000-0000-4000-8000-00000000000${index + 3}`,
    campus_id: '00000000-0000-4000-8000-000000000009',
    created_at: '2026-10-12T06:00:00Z',
    updated_at: '2026-10-12T06:00:00Z',
    row_version: 1,
    name: `Demo ${name}`,
    kind: 'building',
    description: 'Synthetic test fixture',
    active: true,
    point: { type: 'Point', coordinates: [0, 0] },
    access_points: [
      {
        node_id: `00000000-0000-4000-8000-00000000001${index}`,
        label: 'Mapped entrance',
        kind: 'entrance',
        is_primary: true,
      },
    ],
  }),
)
