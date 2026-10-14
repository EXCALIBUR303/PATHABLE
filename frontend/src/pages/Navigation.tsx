import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownUp, ArrowRight, Bookmark, Check, Compass, Info, MapPin, X } from 'lucide-react'
import CampusMap from '../features/navigation/CampusMap'
import { edgeAvailability, graphEdges } from '../features/navigation/map-data'
import { LocationSearch } from '../features/navigation/LocationSearch'
import { useCampusData } from '../hooks/queries'
import { useSession } from '../app/session-context'
import { api, ApiError } from '../services/api'
import type { Edge, RouteRequest, RouteResult } from '../services/api'
import { Badge, Button, ErrorNotice, Loading } from '../components/ui'
import { TripPreferences } from '../features/navigation/TripPreferences'
import { RouteResults } from '../features/navigation/RouteResults'
import { useRouteCalculation } from '../features/navigation/useRouteCalculation'
import { guestProfile, profileDraft, validateProfile } from '../features/navigation/route-profile'
import type { ProfileDraft } from '../features/navigation/route-profile'

export default function Navigation() {
  const data = useCampusData()
  const {
    session,
    loading: sessionLoading,
    error: sessionError,
    refresh: refreshSession,
  } = useSession()
  const queryClient = useQueryClient()
  const [params] = useSearchParams()
  const profile = useQuery({
    queryKey: ['profile'],
    queryFn: ({ signal }) => api.profile(signal),
    enabled: !!session?.user,
  })
  const [source, setSource] = useState('')
  const [destination, setDestination] = useState('')
  const [selected, setSelected] = useState(params.get('place') ?? '')
  const [selectedEdgeId, setSelectedEdgeId] = useState<string>()
  const [sourceEntrance, setSourceEntrance] = useState<string>()
  const [destinationEntrance, setDestinationEntrance] = useState<string>()
  const owner = session?.user?.id ?? 'guest'
  const [overrides, setOverrides] = useState<{ owner: string; values: Partial<ProfileDraft> }>({
    owner,
    values: {},
  })
  if (overrides.owner !== owner) setOverrides({ owner, values: {} })
  const baseProfile = session?.user && profile.data ? profileDraft(profile.data) : guestProfile
  const draft = { ...baseProfile, ...(overrides.owner === owner ? overrides.values : {}) }
  const validated = validateProfile(draft)
  const temporaryError = (error: unknown) =>
    error instanceof ApiError && (error.status === 0 || error.status >= 500)
  const profileReady =
    !sessionLoading &&
    (!sessionError || (!!session && temporaryError(sessionError))) &&
    (!session?.user || (!!profile.data && (!profile.error || temporaryError(profile.error))))
  const [algorithm, setAlgorithm] = useState<'astar' | 'dijkstra'>('astar')
  const [alternativesLimit, setAlternativesLimit] = useState(2)
  const [routeChoice, setRouteChoice] = useState<{ result?: RouteResult; index: number }>({
    index: 0,
  })
  const save = useMutation({
    mutationFn: api.saveDestination,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['saved'] }),
  })
  const locations = data.locations.data ?? []
  const place = locations.find((location) => location.id === selected)
  const edges = graphEdges(data.graph.data)
  const selectedEdge = edges.find((edge) => edge.id === selectedEdgeId)
  const sourcePlace = locations.find((location) => location.id === source)
  const destinationPlace = locations.find((location) => location.id === destination)
  const preferredSource =
    sourceEntrance ??
    sourcePlace?.access_points.find((point) => point.is_primary)?.node_id ??
    (sourcePlace?.access_points.length === 1 ? sourcePlace.access_points[0]?.node_id : '')
  const preferredDestination =
    destinationEntrance ??
    destinationPlace?.access_points.find((point) => point.is_primary)?.node_id ??
    (destinationPlace?.access_points.length === 1 ? destinationPlace.access_points[0]?.node_id : '')
  const sourceNode = sourcePlace?.access_points.some((point) => point.node_id === preferredSource)
    ? preferredSource!
    : ''
  const destinationNode = destinationPlace?.access_points.some(
    (point) => point.node_id === preferredDestination,
  )
    ? preferredDestination!
    : ''
  const routeRequest: RouteRequest | null =
    data.campus && sourceNode && destinationNode && profileReady && validated.profile
      ? {
          campus_id: data.campus.id,
          source_id: sourceNode,
          destination_id: destinationNode,
          accessibility_profile: validated.profile,
          selected_algorithm: algorithm,
          alternatives_limit: alternativesLimit,
        }
      : null
  const calculation = useRouteCalculation(
    routeRequest,
    data.graph.data?.graph_version,
    data.live,
    routeChoice,
  )
  const currentRoutes =
    calculation.result?.status === 'found'
      ? [calculation.result.primary, ...calculation.result.alternatives]
      : []
  const selectedRouteIndex =
    routeChoice.result === calculation.result && routeChoice.index < currentRoutes.length
      ? routeChoice.index
      : 0
  const selectedRoute =
    !calculation.staleReason && !calculation.needsConfirmation
      ? currentRoutes[selectedRouteIndex]
      : undefined
  function planRoute() {
    setRouteChoice({ index: 0 })
    void calculation.calculate()
  }
  function setSelectedEdge(edge?: Edge) {
    setSelectedEdgeId(edge?.id)
  }
  function chooseSource(id: string) {
    setSource(id)
    setSourceEntrance(undefined)
    selectPlace(id)
  }
  function chooseDestination(id: string) {
    setDestination(id)
    setDestinationEntrance(undefined)
    selectPlace(id)
  }
  function selectPlace(id: string) {
    setSelected(id)
    setSelectedEdge(undefined)
    save.reset()
  }
  return (
    <div className="workspace">
      <div className="workspace-heading">
        <div>
          <span className="eyebrow">Your campus, your pace</span>
          <h1>Find your next place.</h1>
        </div>
        <div className="workspace-meta">
          <Badge tone="good">
            <span className="status-dot" />
            Fictional campus
          </Badge>
          <span className="muted">
            {locations.length} places · {edges.length} paths
          </span>
        </div>
      </div>
      {data.error && data.graph.data && (
        <p role="status" className="notice notice-warning">
          Connection interrupted. Previously loaded records may be outdated.
        </p>
      )}
      <div className="workspace-grid">
        <aside className="planning-panel" aria-label="Explore and plan">
          <div className="panel-title">
            <Compass size={20} />
            <h2>Explore campus</h2>
          </div>
          <p className="muted panel-intro">
            Choose two places. Get to know the paths between them.
          </p>
          <LocationSearch
            label="Starting point"
            locations={locations}
            disabled={!data.locations.data}
            value={source}
            onChange={chooseSource}
            placeholder="Where are you starting?"
          />
          {sourcePlace && (
            <div className="entrance-select">
              <label htmlFor="source-entrance">Starting entrance</label>
              <select
                id="source-entrance"
                value={sourceNode}
                onChange={(event) => setSourceEntrance(event.target.value)}
              >
                <option value="">Choose a mapped entrance</option>
                {sourcePlace.access_points.map((point) => (
                  <option key={point.node_id} value={point.node_id}>
                    {point.label}
                    {point.is_primary ? ' · primary' : ''}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="swap-row">
            <span className="endpoint-connector" />
            <Button
              variant="ghost"
              size="icon"
              aria-label="Swap starting point and destination"
              onClick={() => {
                setSource(destination)
                setDestination(source)
                setSourceEntrance(destinationEntrance)
                setDestinationEntrance(sourceEntrance)
              }}
            >
              <ArrowDownUp size={17} />
            </Button>
          </div>
          <LocationSearch
            label="Destination"
            locations={locations}
            disabled={!data.locations.data}
            value={destination}
            onChange={chooseDestination}
            placeholder="Where would you like to go?"
          />
          {destinationPlace && (
            <div className="entrance-select">
              <label htmlFor="destination-entrance">Destination entrance</label>
              <select
                id="destination-entrance"
                value={destinationNode}
                onChange={(event) => setDestinationEntrance(event.target.value)}
              >
                <option value="">Choose a mapped entrance</option>
                {destinationPlace.access_points.map((point) => (
                  <option key={point.node_id} value={point.node_id}>
                    {point.label}
                    {point.is_primary ? ' · primary' : ''}
                  </option>
                ))}
              </select>
            </div>
          )}
          <TripPreferences
            value={draft}
            saved={!!session?.user && !!profile.data}
            overridden={Object.keys(overrides.values).length > 0}
            onChange={(change) =>
              setOverrides((previous) => ({
                owner,
                values: { ...(previous.owner === owner ? previous.values : {}), ...change },
              }))
            }
            reset={() => setOverrides({ owner, values: {} })}
          />
          {sessionLoading || (session?.user && profile.isPending) ? (
            <p role="status" className="helper">
              Loading your preferences…
            </p>
          ) : null}
          {sessionError && <ErrorNotice error={sessionError} retry={() => void refreshSession()} />}
          {session?.user && profile.error && (
            <ErrorNotice error={profile.error} retry={() => void profile.refetch()} />
          )}
          {validated.error && (
            <p className="form-error" role="alert">
              {validated.error}
            </p>
          )}
          <div className="route-planning-options">
            <div className="field">
              <label htmlFor="route-algorithm">Routing algorithm</label>
              <select
                id="route-algorithm"
                value={algorithm}
                onChange={(event) => setAlgorithm(event.target.value as 'astar' | 'dijkstra')}
              >
                <option value="astar">A* — guided search</option>
                <option value="dijkstra">Dijkstra — shortest-path search</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="route-alternatives">Additional routes</label>
              <select
                id="route-alternatives"
                value={alternativesLimit}
                onChange={(event) => setAlternativesLimit(Number(event.target.value))}
              >
                <option value={0}>Primary route only</option>
                <option value={1}>Up to 1 alternative</option>
                <option value={2}>Up to 2 alternatives</option>
              </select>
            </div>
          </div>
          <Button
            disabled={!routeRequest}
            busy={calculation.pending}
            className="full-width"
            onClick={planRoute}
          >
            Plan a route <ArrowRight size={17} />
          </Button>
          {!sourceNode || !destinationNode ? (
            <p className="helper">Choose both mapped entrances to calculate a route.</p>
          ) : null}
          {calculation.result && (
            <a className="text-link route-ready-link" href="#route-result">
              {selectedRoute
                ? `${selectedRoute.total_distance_m.toFixed(1)} m · View route details`
                : 'View route result'}{' '}
              <ArrowRight size={14} />
            </a>
          )}
          {calculation.error && <ErrorNotice error={calculation.error} retry={planRoute} />}
          <p className="helper">
            Routes use recorded observations and your explicit preferences. Conditions may change.
          </p>
          <div className="places-heading">
            <h3>Places to explore</h3>
            <span>{locations.length}</span>
          </div>
          <div className="place-list">
            {locations.map((location, index) => (
              <button
                key={location.id}
                className={selected === location.id ? 'selected' : ''}
                onClick={() => selectPlace(location.id)}
              >
                <span className="place-number">{index + 1}</span>
                <span>
                  <strong>{location.name.replace('Demo ', '')}</strong>
                  <small>{location.access_points.length} mapped entrance</small>
                </span>
                <ArrowRight size={15} />
              </button>
            ))}
          </div>
        </aside>
        <section className="map-workspace" aria-label="Campus map and details">
          {data.error ? (
            <ErrorNotice error={data.error} retry={() => void data.refresh()} />
          ) : data.loading ? (
            <Loading />
          ) : data.graph.data ? (
            <CampusMap
              graph={data.graph.data}
              route={selectedRoute}
              alternative={selectedRouteIndex > 0}
              locations={locations}
              infrastructure={data.infrastructure.data ?? []}
              selected={selected}
              source={source}
              destination={destination}
              onSelect={selectPlace}
              onEdgeSelect={(edge) => {
                setSelectedEdge(edge)
                setSelected('')
              }}
            />
          ) : (
            <div className="empty-state">No mapped campus is available.</div>
          )}
          <div className="map-provenance">
            <Info size={15} />
            <span>
              This is fictional demonstration infrastructure, not a verified Woxsen University map.
            </span>
            <Badge>Observation data</Badge>
          </div>
        </section>
        <aside className="context-panel" aria-label="Selected place or pathway">
          <div className="context-top">
            <span className="eyebrow">A little more context</span>
            {(place || selectedEdge) && (
              <Button
                variant="ghost"
                size="icon"
                aria-label="Close details"
                onClick={() => {
                  setSelected('')
                  setSelectedEdge(undefined)
                }}
              >
                <X size={18} />
              </Button>
            )}
          </div>
          {place ? (
            <>
              <span className="context-icon">
                <MapPin size={26} />
              </span>
              <h2>{place.name.replace('Demo ', '')}</h2>
              <Badge tone="blue">Mapped building</Badge>
              <p className="muted">{place.description}</p>
              <div className="detail-block">
                <h3>Mapped entrances</h3>
                {place.access_points.map((point) => (
                  <div className="entrance-row" key={point.node_id}>
                    <span className="small-icon">
                      <MapPin size={16} />
                    </span>
                    <span>
                      {point.label}
                      {point.is_primary && <small>Primary mapped entrance</small>}
                    </span>
                  </div>
                ))}
              </div>
              <Button
                className="full-width"
                variant="secondary"
                onClick={() => chooseDestination(place.id)}
              >
                Set as destination <ArrowRight size={16} />
              </Button>
              {session?.user ? (
                <Button
                  className="full-width"
                  variant="ghost"
                  busy={save.isPending}
                  onClick={() => save.mutate(place.id)}
                >
                  <Bookmark size={16} />
                  Save this place
                </Button>
              ) : (
                <Link className="save-signin" to="/login?returnTo=%2Fnavigate">
                  <Bookmark size={15} />
                  Sign in to save this place
                </Link>
              )}
              {save.isSuccess && (
                <p className="success-text" role="status">
                  <Check size={15} />
                  Place saved to your dashboard.
                </p>
              )}
              {save.error && (
                <p role="alert" className="form-error">
                  {save.error.message}
                </p>
              )}
            </>
          ) : selectedEdge ? (
            <>
              <span className="context-icon">
                <Compass size={26} />
              </span>
              <h2>
                {selectedEdge.has_stairs
                  ? 'Steps walkway'
                  : selectedEdge.has_ramp
                    ? 'Ramp walkway'
                    : 'Campus pathway'}
              </h2>
              <Badge
                tone={
                  edgeAvailability(selectedEdge, data.infrastructure.data ?? []) === 'open'
                    ? 'good'
                    : 'danger'
                }
              >
                {edgeAvailability(selectedEdge, data.infrastructure.data ?? []).replaceAll(
                  '_',
                  ' ',
                )}
              </Badge>
              <dl className="path-details">
                <div>
                  <dt>Measured distance</dt>
                  <dd>{selectedEdge.distance_m.toFixed(1)} m</dd>
                </div>
                <div>
                  <dt>Width</dt>
                  <dd>{selectedEdge.width_m === null ? 'Unknown' : `${selectedEdge.width_m} m`}</dd>
                </div>
                <div>
                  <dt>Slope</dt>
                  <dd>
                    {selectedEdge.slope_pct === null
                      ? 'Unknown'
                      : `${Math.abs(selectedEdge.slope_pct)}%`}
                  </dd>
                </div>
                <div>
                  <dt>Surface</dt>
                  <dd>{selectedEdge.surface}</dd>
                </div>
                <div>
                  <dt>Steps</dt>
                  <dd>
                    {selectedEdge.has_stairs === null
                      ? 'Unknown'
                      : selectedEdge.has_stairs
                        ? 'Present'
                        : 'Not observed'}
                  </dd>
                </div>
                <div>
                  <dt>Observation</dt>
                  <dd>{selectedEdge.verification.replaceAll('_', ' ')}</dd>
                </div>
              </dl>
              <div className="notice notice-soft">
                <Info size={17} />
                <p>
                  Observation status describes this fictional record. It is not a guarantee of
                  individual accessibility.
                </p>
              </div>
            </>
          ) : (
            <>
              <span className="context-icon">
                <Compass size={28} />
              </span>
              <h2>Room to explore.</h2>
              <p className="muted">Select a place or pathway on the map to see its details.</p>
              <div className="context-checklist">
                <div>
                  <Check size={16} />
                  <span>Mapped entrances</span>
                </div>
                <div>
                  <Check size={16} />
                  <span>Pathway measurements</span>
                </div>
                <div>
                  <Check size={16} />
                  <span>Clear observation status</span>
                </div>
              </div>
              <div className="context-tip">
                <span>GOOD TO KNOW</span>
                <p>
                  Unknown information is always shown as unknown. Nothing is assumed accessible.
                </p>
              </div>
            </>
          )}
        </aside>
      </div>
      <p className="live-update-status" role="status">
        {data.live.status === 'connected'
          ? 'Live campus updates connected.'
          : (data.live.disconnectedReason ?? 'Connecting to live campus updates…')}
      </p>
      {calculation.result && (
        <RouteResults
          result={calculation.result}
          selectedIndex={selectedRouteIndex}
          onSelect={(index) => setRouteChoice({ result: calculation.result, index })}
          staleReason={calculation.staleReason}
          recalculate={planRoute}
          pending={calculation.pending}
          needsConfirmation={calculation.needsConfirmation}
          confirm={calculation.confirm}
          affected={calculation.affected}
        />
      )}
      <details className="pathway-list">
        <summary>
          Explore all pathways as text <span>Accessible alternative to the map</span>
        </summary>
        <div className="table-scroll">
          <table>
            <caption className="sr-only">Fictional campus pathway measurements</caption>
            <thead>
              <tr>
                <th>Pathway</th>
                <th>Distance</th>
                <th>Width</th>
                <th>Slope</th>
                <th>Surface</th>
                <th>Availability</th>
                <th>Observation</th>
              </tr>
            </thead>
            <tbody>
              {edges.map((edge, index) => (
                <tr key={edge.id}>
                  <th>
                    <button
                      className="text-link"
                      onClick={() => {
                        setSelectedEdge(edge)
                        setSelected('')
                      }}
                    >
                      Pathway {index + 1}
                    </button>
                  </th>
                  <td>{edge.distance_m.toFixed(1)} m</td>
                  <td>{edge.width_m === null ? 'Unknown' : `${edge.width_m} m`}</td>
                  <td>{edge.slope_pct === null ? 'Unknown' : `${Math.abs(edge.slope_pct)}%`}</td>
                  <td>{edge.surface}</td>
                  <td>
                    {edgeAvailability(edge, data.infrastructure.data ?? []).replaceAll('_', ' ')}
                  </td>
                  <td>{edge.verification.replaceAll('_', ' ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  )
}
