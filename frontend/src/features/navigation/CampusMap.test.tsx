import { render, screen } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { expect, it, vi } from 'vitest'
import type { Graph, Route } from '../../services/api'
import CampusMap from './CampusMap'

// Inspect the React/Leaflet boundary; the live browser suite exercises Leaflet itself.
vi.mock('react-leaflet', () => {
  const map = {
    fitBounds: vi.fn(),
    panTo: vi.fn(),
    invalidateSize: vi.fn(),
    getContainer: () => document.body,
  }
  const children = ({ children }: PropsWithChildren) => <>{children}</>
  return {
    MapContainer: children,
    Tooltip: children,
    Marker: children,
    TileLayer: () => null,
    Polygon: () => null,
    useMap: () => map,
    Polyline: ({
      positions,
      className,
      pathOptions,
    }: {
      positions: unknown
      className?: string
      pathOptions: { dashArray?: string }
    }) =>
      className?.includes('route-line') ? (
        <output data-testid="route-line" data-dash={pathOptions.dashArray}>
          {JSON.stringify(positions)}
        </output>
      ) : null,
    CircleMarker: ({ center, className }: { center: unknown; className?: string }) =>
      className === 'route-point' ? (
        <output data-testid="route-point">{JSON.stringify(center)}</output>
      ) : null,
  }
})

const graph: Graph = {
  type: 'FeatureCollection',
  features: [],
  graph_version: '1',
  policy_version: 'accessibility-v1',
  cost_model_version: 'walking-effort-v1',
  validated_at: '2026-10-13T00:00:00Z',
  valid_until: null,
  data_origin: 'synthetic_demo',
}
const route: Route = {
  node_ids: ['source', 'junction', 'destination'],
  arcs: [],
  geometry: {
    type: 'LineString',
    coordinates: [
      [78.45, 17.42],
      [78.451, 17.4203],
      [78.4515, 17.4197],
      [78.452, 17.421],
    ],
  },
  total_distance_m: 310,
  estimated_duration_s: 310,
  cost_m_equivalent: 315,
  instructions: [],
  warnings: [],
  verification: {
    summary: 'observations_current',
    verified_distance_m: 310,
    uncertain_distance_m: 0,
    earliest_expiry_at: null,
  },
}
const props = { graph, locations: [], infrastructure: [] }

it('renders every backend route vertex in order, switches the selected alternative, and removes retired geometry', () => {
  const view = render(<CampusMap {...props} route={route} />)
  expect(JSON.parse(screen.getByTestId('route-line').textContent!)).toEqual([
    [17.42, 78.45],
    [17.4203, 78.451],
    [17.4197, 78.4515],
    [17.421, 78.452],
  ])
  expect(screen.getByTestId('route-line')).not.toHaveAttribute('data-dash')
  const alternative: Route = {
    ...route,
    geometry: {
      type: 'LineString',
      coordinates: [
        [78.45, 17.42],
        [78.45, 17.422],
        [78.452, 17.421],
      ],
    },
  }
  view.rerender(<CampusMap {...props} route={alternative} alternative />)
  expect(JSON.parse(screen.getByTestId('route-line').textContent!)).toEqual([
    [17.42, 78.45],
    [17.422, 78.45],
    [17.421, 78.452],
  ])
  expect(screen.getByTestId('route-line')).toHaveAttribute('data-dash', '12 8')
  view.rerender(<CampusMap {...props} />)
  expect(screen.queryByTestId('route-line')).not.toBeInTheDocument()
  expect(screen.queryByText('Selected route')).not.toBeInTheDocument()
})

it('renders a same-node response as its exact backend Point without inventing a line', () => {
  render(
    <CampusMap
      {...props}
      route={{
        ...route,
        geometry: { type: 'Point', coordinates: [78.45, 17.42] },
        node_ids: ['source'],
        total_distance_m: 0,
        estimated_duration_s: 0,
        cost_m_equivalent: 0,
      }}
    />,
  )
  expect(JSON.parse(screen.getByTestId('route-point').textContent!)).toEqual([17.42, 78.45])
  expect(screen.queryByTestId('route-line')).not.toBeInTheDocument()
})
