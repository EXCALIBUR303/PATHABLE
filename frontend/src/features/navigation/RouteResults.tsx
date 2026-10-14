import { Check, Info, Route as RouteIcon } from 'lucide-react'
import { Badge, Button } from '../../components/ui'
import type { RouteResult } from '../../services/api'

export function RouteResults({
  result,
  selectedIndex,
  onSelect,
  staleReason,
  recalculate,
  pending,
  needsConfirmation = false,
  confirm,
  affected = false,
}: {
  result: RouteResult
  selectedIndex: number
  onSelect: (index: number) => void
  staleReason?: string
  recalculate: () => void
  pending: boolean
  needsConfirmation?: boolean
  confirm?: () => void
  affected?: boolean
}) {
  if (staleReason)
    return (
      <section id="route-result" className="route-results" aria-label="Route result">
        <div className="notice notice-warning" role="status">
          <strong>Recalculate before continuing</strong>
          <p>{staleReason} The previous result is no longer displayed as a route.</p>
          <Button variant="secondary" busy={pending} onClick={recalculate}>
            Recalculate route
          </Button>
        </div>
      </section>
    )
  if (needsConfirmation && result.status === 'found')
    return (
      <section id="route-result" className="route-results" aria-label="Route result">
        <div className="notice notice-warning" role="status">
          <strong>Updated route ready</strong>
          <p>
            {affected
              ? 'A mapped change affects your previous route.'
              : 'Campus conditions have been checked again.'}{' '}
            Your requirements have been kept. The recalculated route is{' '}
            {result.primary.total_distance_m.toFixed(1)} m. Confirm before continuing.
          </p>
          <Button onClick={confirm}>Use updated route</Button>
        </div>
      </section>
    )
  const routes = result.status === 'found' ? [result.primary, ...result.alternatives] : []
  const selected = routes[selectedIndex] ?? routes[0]
  const warnings = [...result.warnings, ...(selected?.warnings ?? [])].filter(
    (warning, index, all) =>
      all.findIndex((value) => value.code === warning.code && value.message === warning.message) ===
      index,
  )
  return (
    <section id="route-result" className="route-results" aria-label="Route result">
      <div className="route-result-heading" role="status">
        <div>
          <span className="eyebrow">Your journey</span>
          <h2>
            {result.status === 'found'
              ? 'A path for your preferences.'
              : 'No matching route found.'}
          </h2>
        </div>
        <Badge tone={result.status === 'found' ? 'good' : 'warning'}>
          {result.status === 'found' ? (
            <>
              <Check size={13} />
              Calculated route
            </>
          ) : (
            'No route'
          )}
        </Badge>
      </div>
      {result.status === 'no_route' ? (
        <div className="no-route-state">
          <p>
            {result.reason === 'disconnected'
              ? 'These mapped entrances are not connected in this campus graph.'
              : 'The available pathways cannot connect these entrances with your current requirements.'}
          </p>
          <p>
            Your requirements have been kept. You can choose different entrances or review your
            preferences.
          </p>
          {Object.values(result.excluded_edge_counts).some((count) => count > 0) && (
            <details>
              <summary>Why pathways were excluded</summary>
              <p className="helper">
                Counts describe the whole graph. Reasons can overlap; changing one requirement does
                not guarantee a route.
              </p>
              <dl className="path-details">
                {Object.entries(result.excluded_edge_counts)
                  .filter(([, count]) => count > 0)
                  .map(([reason, count]) => (
                    <div key={reason}>
                      <dt>{reason.toLowerCase().replaceAll('_', ' ')}</dt>
                      <dd>{count}</dd>
                    </div>
                  ))}
              </dl>
            </details>
          )}
        </div>
      ) : (
        selected && (
          <>
            <fieldset className="route-options">
              <legend>Choose a route</legend>
              {routes.map((route, index) => (
                <label className={selectedIndex === index ? 'selected' : ''} key={index}>
                  <input
                    type="radio"
                    name="route-choice"
                    checked={selectedIndex === index}
                    onChange={() => onSelect(index)}
                  />
                  <span>
                    <strong>{index === 0 ? 'Lowest effort' : `Alternative ${index}`}</strong>
                    <small>
                      {route.total_distance_m.toFixed(1)} m ·{' '}
                      {route.estimated_duration_s === 0
                        ? '0'
                        : Math.max(1, Math.ceil(route.estimated_duration_s / 60))}{' '}
                      min estimate
                    </small>
                  </span>
                </label>
              ))}
            </fieldset>
            <div className="route-totals">
              <div>
                <span>Distance</span>
                <strong>
                  {selected.total_distance_m.toFixed(1)} <small>m</small>
                </strong>
              </div>
              <div>
                <span>Estimated time</span>
                <strong>
                  {selected.estimated_duration_s === 0
                    ? '0'
                    : Math.max(1, Math.ceil(selected.estimated_duration_s / 60))}{' '}
                  <small>min</small>
                </strong>
              </div>
              <div>
                <span>Observations</span>
                <strong className="route-observation">
                  {selected.verification.summary === 'observations_current'
                    ? 'Current when checked'
                    : 'Contains uncertainty'}
                </strong>
              </div>
            </div>
            {selected.geometry.type === 'Point' ? (
              <p className="notice notice-soft">
                <RouteIcon size={18} />
                Both selections use the same mapped entrance. No travel is needed.
              </p>
            ) : (
              <div className="route-directions">
                <h3>Directions as text</h3>
                <ol>
                  {selected.instructions.map((instruction, index) => (
                    <li key={`${instruction.edge_id}-${index}`}>
                      <span>{instruction.text}</span>
                      <strong>{instruction.distance_m.toFixed(1)} m</strong>
                    </li>
                  ))}
                </ol>
              </div>
            )}
            {!result.alternatives_exhaustive && (
              <p className="helper">
                The alternative search reached its limit. More routes may exist.
              </p>
            )}
            <p className="helper">
              Alternatives are included only when sufficiently different and within the effort
              limit. Fewer routes may be available.
            </p>
          </>
        )
      )}
      {warnings.length > 0 && (
        <div className="route-warnings">
          <h3>
            <Info size={16} />
            Before you go
          </h3>
          <ul>
            {warnings.map((warning) => (
              <li key={`${warning.code}-${warning.message}`}>{warning.message}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="route-checked">
        Checked at{' '}
        {new Date(result.validated_at).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })}
        . Conditions are checked again while this page is open.
      </p>
      <details className="route-calculation-details">
        <summary>Calculation details and applied preferences</summary>
        <dl className="path-details">
          <div>
            <dt>Algorithm</dt>
            <dd>{result.algorithm === 'astar' ? 'A*' : 'Dijkstra'}</dd>
          </div>
          {selected && (
            <>
              <div>
                <dt>Weighted effort</dt>
                <dd>{selected.cost_m_equivalent.toFixed(2)} m-equivalent</dd>
              </div>
              <div>
                <dt>Current observation distance</dt>
                <dd>{selected.verification.verified_distance_m.toFixed(1)} m</dd>
              </div>
              <div>
                <dt>Uncertain observation distance</dt>
                <dd>{selected.verification.uncertain_distance_m.toFixed(1)} m</dd>
              </div>
            </>
          )}
          <div>
            <dt>Avoid stairs</dt>
            <dd>{result.accessibility_profile.avoid_stairs ? 'Yes' : 'No'}</dd>
          </div>
          <div>
            <dt>Maximum slope</dt>
            <dd>
              {result.accessibility_profile.max_slope_pct === null
                ? 'No numeric limit'
                : `${result.accessibility_profile.max_slope_pct}%`}
            </dd>
          </div>
          <div>
            <dt>Minimum width</dt>
            <dd>
              {result.accessibility_profile.min_width_m === null
                ? 'No numeric limit'
                : `${result.accessibility_profile.min_width_m} m`}
            </dd>
          </div>
          <div>
            <dt>Avoid surfaces</dt>
            <dd>{result.accessibility_profile.excluded_surfaces.join(', ') || 'None'}</dd>
          </div>
          <div>
            <dt>Unknown information</dt>
            <dd>
              {result.accessibility_profile.unknown_policy === 'exclude'
                ? 'Excluded'
                : 'Allowed with warning'}
            </dd>
          </div>
          <div>
            <dt>Estimated speed</dt>
            <dd>{result.accessibility_profile.travel_speed_mps} m/s</dd>
          </div>
          <div>
            <dt>Search work</dt>
            <dd>{result.stats.expansions} node expansions</dd>
          </div>
          <div>
            <dt>Calculation time</dt>
            <dd>{result.stats.elapsed_ms.toFixed(2)} ms</dd>
          </div>
          <div>
            <dt>Graph revision</dt>
            <dd>{result.graph_version}</dd>
          </div>
          <div>
            <dt>Effort model</dt>
            <dd>{result.cost_model_version}</dd>
          </div>
        </dl>
        <p className="helper">
          Weighted effort compares slope, surface and uncertainty; it is not distance or travel
          time. Observation status is not a guarantee of accessibility.
        </p>
      </details>
    </section>
  )
}
