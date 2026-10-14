import { useEffect, useMemo, useState } from 'react'
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Marker,
  Tooltip,
  Polygon,
  useMap,
} from 'react-leaflet'
import L from 'leaflet'
import type { LatLngTuple } from 'leaflet'
import { useReducedMotion } from 'motion/react'
import type { Edge, Graph, Infrastructure, Location, Route } from '../../services/api'
import { edgeAvailability, graphEdges } from './map-data'

function Viewport({
  graph,
  selected,
  locations,
  preview,
}: {
  graph: Graph
  selected?: string
  locations: Location[]
  preview: boolean
}) {
  const map = useMap()
  const reduced = useReducedMotion()
  useEffect(() => {
    const coordinates =
      preview && locations.length
        ? locations.map(
            (location) =>
              [location.point.coordinates[1], location.point.coordinates[0]] as LatLngTuple,
          )
        : graph.features.flatMap((feature) =>
            feature.geometry.type === 'Point'
              ? [[feature.geometry.coordinates[1], feature.geometry.coordinates[0]] as LatLngTuple]
              : feature.geometry.coordinates.map((point) => [point[1], point[0]] as LatLngTuple),
          )
    const bounds = L.latLngBounds(coordinates)
    if (bounds.isValid())
      map.fitBounds(bounds.pad(0.15), { padding: [36, 36], animate: false, maxZoom: 22 })
  }, [graph, map, locations, preview])
  useEffect(() => {
    const location = locations.find((item) => item.id === selected)
    if (location)
      map.panTo([location.point.coordinates[1], location.point.coordinates[0]], {
        animate: !reduced,
      })
  }, [selected, locations, map, reduced])
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize({ pan: false }))
    observer.observe(map.getContainer())
    return () => observer.disconnect()
  }, [map])
  return null
}

export default function CampusMap({
  graph,
  locations,
  infrastructure,
  selected,
  source,
  destination,
  onSelect,
  onEdgeSelect,
  route,
  alternative = false,
  preview = false,
}: {
  graph: Graph
  locations: Location[]
  infrastructure: Infrastructure[]
  selected?: string
  source?: string
  destination?: string
  onSelect?: (id: string) => void
  onEdgeSelect?: (edge: Edge) => void
  route?: Route
  alternative?: boolean
  preview?: boolean
}) {
  const edges = useMemo(() => graphEdges(graph), [graph])
  const [tileFailed, setTileFailed] = useState(false)
  const nodes = graph.features.filter((feature) => feature.geometry.type === 'Point')
  return (
    <div
      className={`campus-map ${preview ? 'campus-map-preview' : ''}`}
      aria-label="Interactive fictional campus map"
    >
      <MapContainer
        center={[0, 0]}
        zoom={20}
        zoomSnap={0.25}
        minZoom={17}
        maxZoom={23}
        zoomControl={!preview}
        scrollWheelZoom={false}
        attributionControl={true}
        keyboard={!preview}
        preferCanvas={false}
      >
        <Viewport graph={graph} selected={selected} locations={locations} preview={preview} />
        {import.meta.env.VITE_TILE_URL && import.meta.env.VITE_TILE_ATTRIBUTION && !tileFailed && (
          <TileLayer
            url={import.meta.env.VITE_TILE_URL}
            attribution={import.meta.env.VITE_TILE_ATTRIBUTION}
            eventHandlers={{ tileerror: () => setTileFailed(true) }}
          />
        )}
        {/* Decorative shapes describe the authored fictional demo, never surveyed footprints. */}
        <Polygon
          positions={[
            [0.00006, -0.000025],
            [0.00036, -0.000025],
            [0.00036, 0.000225],
            [0.00016, 0.000225],
            [0.00016, 0.00006],
            [0.00006, 0.00006],
          ]}
          pathOptions={{
            color: '#C7DACC',
            weight: 1,
            fillColor: '#DCE9DF',
            fillOpacity: 0.8,
            interactive: false,
          }}
        />
        <Polygon
          positions={[
            [-0.00022, 0.00002],
            [-0.00022, 0.00018],
            [-0.00005, 0.00018],
            [-0.00005, 0.00002],
          ]}
          pathOptions={{
            color: '#D2DED3',
            weight: 1,
            fillColor: '#E6EEE5',
            fillOpacity: 0.85,
            interactive: false,
          }}
        />
        {[
          [0.00023, 0.000055],
          [0.00023, 0.00015],
          [0.00002, 0.0001],
          [-0.00011, 0.00009],
          [-0.00013, 0.00013],
          [0.00027, 0.00027],
          [0.00017, -0.000065],
        ].map((point, index) => (
          <CircleMarker
            key={`tree-${index}`}
            center={point as LatLngTuple}
            radius={preview ? 8 : 12}
            pathOptions={{
              fillColor: '#B1CCB9',
              color: '#90B79C',
              weight: 1,
              fillOpacity: 0.7,
              interactive: false,
            }}
          />
        ))}
        {locations.map((location) => {
          const [lon, lat] = location.point.coordinates
          const size = preview ? 0.000025 : 0.000035
          return (
            <Polygon
              key={`building-${location.id}`}
              positions={[
                [lat + size, lon - size],
                [lat + size, lon + size],
                [lat - size, lon + size],
                [lat - size, lon - size],
              ]}
              pathOptions={{
                fillColor: '#F4F0E6',
                color: '#BEB8A9',
                weight: 1.5,
                fillOpacity: 1,
                interactive: false,
              }}
            />
          )
        })}
        {edges.map((edge) => {
          const availability = edgeAvailability(edge, infrastructure)
          const uncertain = edge.accessibility === 'unknown' || edge.verification !== 'verified'
          return (
            <Polyline
              key={edge.id}
              positions={edge.geometry.coordinates.map(
                (point) => [point[1], point[0]] as LatLngTuple,
              )}
              pathOptions={{
                color:
                  availability !== 'open'
                    ? '#A82D35'
                    : uncertain || edge.has_stairs
                      ? '#946312'
                      : '#698D83',
                weight: preview ? 4 : 6,
                opacity: 0.9,
                dashArray:
                  availability !== 'open'
                    ? '4 9'
                    : uncertain
                      ? '2 8'
                      : edge.has_stairs
                        ? '6 5'
                        : undefined,
              }}
              eventHandlers={{ click: () => onEdgeSelect?.(edge) }}
            >
              <Tooltip sticky>
                {edge.has_stairs
                  ? 'Steps walkway'
                  : edge.has_ramp
                    ? 'Ramp walkway'
                    : 'Campus pathway'}{' '}
                · {edge.distance_m.toFixed(1)} m · {availability.replaceAll('_', ' ')}
                {uncertain ? ' · observation uncertain' : ''}
              </Tooltip>
            </Polyline>
          )
        })}
        {nodes.map((feature) =>
          feature.geometry.type === 'Point' ? (
            <CircleMarker
              key={feature.id}
              center={[feature.geometry.coordinates[1], feature.geometry.coordinates[0]]}
              radius={3}
              pathOptions={{
                color: '#567F74',
                weight: 1,
                fillColor: '#FAF9F6',
                fillOpacity: 1,
                interactive: false,
              }}
            />
          ) : null,
        )}
        {route?.geometry.type === 'LineString' && (
          <Polyline
            className="route-line route-line-selected"
            positions={route.geometry.coordinates.map(
              (point) => [point[1], point[0]] as LatLngTuple,
            )}
            pathOptions={{
              color: alternative ? '#285F8F' : '#0B625A',
              dashArray: alternative ? '12 8' : undefined,
              weight: 9,
              opacity: 1,
              lineCap: 'round',
              lineJoin: 'round',
            }}
          >
            <Tooltip sticky>
              Selected calculated route · {route.total_distance_m.toFixed(1)} m
            </Tooltip>
          </Polyline>
        )}
        {route?.geometry.type === 'Point' && (
          <CircleMarker
            className="route-point"
            center={[route.geometry.coordinates[1], route.geometry.coordinates[0]]}
            radius={14}
            pathOptions={{
              color: '#0B625A',
              weight: 4,
              fillColor: '#D8EEE5',
              fillOpacity: 0.8,
            }}
          >
            <Tooltip>Same mapped entrance · no travel needed</Tooltip>
          </CircleMarker>
        )}
        {locations.map((location, index) => {
          const kind =
            location.id === source
              ? 'source'
              : location.id === destination
                ? 'destination'
                : location.id === selected
                  ? 'selected'
                  : ''
          const icon = L.divIcon({
            className: `place-pin ${kind}`,
            html: `<span>${kind === 'source' ? 'A' : kind === 'destination' ? 'B' : index + 1}</span>`,
            iconSize: [34, 34],
            iconAnchor: [17, 17],
          })
          return (
            <Marker
              key={location.id}
              position={[location.point.coordinates[1], location.point.coordinates[0]]}
              icon={icon}
              title={location.name}
              alt={location.name}
              eventHandlers={{ click: () => onSelect?.(location.id) }}
              keyboard={!preview}
            >
              <Tooltip direction="top" offset={[0, -18]} permanent className="place-label">
                {location.name.replace('Demo ', '')}
              </Tooltip>
            </Marker>
          )
        })}
        {infrastructure.map((item) => (
          <CircleMarker
            key={item.id}
            center={[item.point.coordinates[1] + 0.000025, item.point.coordinates[0] + 0.000025]}
            radius={preview ? 4 : 6}
            pathOptions={{
              color: item.availability === 'open' ? '#0B625A' : '#A82D35',
              fillColor: '#FFFFFF',
              fillOpacity: 1,
              weight: 2,
            }}
          >
            <Tooltip>
              {item.name} · {item.availability.replaceAll('_', ' ')} ·{' '}
              {item.verification.replaceAll('_', ' ')}
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
      <div className="map-label">
        <span className="map-label-dot" />
        Fictional campus<span>Illustrative grounds · live mapped paths</span>
      </div>
      {tileFailed && (
        <div className="tile-warning" role="status">
          Basemap unavailable. Campus geometry and place lists remain available.
        </div>
      )}
      <div className="map-legend" aria-label="Map legend">
        {route && (
          <span>
            <i className="legend-route" />
            Selected route
          </span>
        )}
        <span>
          <i className="legend-path" />
          Mapped path
        </span>
        <span>
          <i className="legend-steps" />
          Steps / uncertain
        </span>
        <span>
          <i className="legend-closed" />
          Closed / blocked
        </span>
      </div>
    </div>
  )
}
