import { Link } from 'react-router-dom'
import { ArrowRight, SlidersHorizontal } from 'lucide-react'
import { Button, Switch } from '../../components/ui'
import { guestProfile } from './route-profile'
import type { ProfileDraft } from './route-profile'

export function TripPreferences({
  value,
  onChange,
  saved,
  overridden,
  reset,
}: {
  value: ProfileDraft
  onChange: (value: Partial<ProfileDraft>) => void
  saved: boolean
  overridden: boolean
  reset: () => void
}) {
  return (
    <div className="preference-preview trip-preferences">
      <div className="preference-heading">
        <SlidersHorizontal size={17} />
        <strong>This journey</strong>
        {saved && (
          <Link to="/profile" aria-label="Open all preferences">
            Saved <ArrowRight size={13} />
          </Link>
        )}
      </div>
      <div className="switch-row">
        <label htmlFor="quick-stairs">Avoid stairs</label>
        <Switch
          id="quick-stairs"
          checked={value.avoid_stairs}
          onCheckedChange={(avoid_stairs) => onChange({ avoid_stairs })}
        />
      </div>
      <details className="trip-settings">
        <summary>All route preferences</summary>
        <div className="field">
          <label htmlFor="trip-slope">Maximum slope (%)</label>
          <input
            id="trip-slope"
            type="number"
            min="0"
            max="100"
            step="any"
            value={value.max_slope_pct}
            onChange={(event) => onChange({ max_slope_pct: event.target.value })}
          />
          <small>Blank means no numeric limit.</small>
        </div>
        <div className="field">
          <label htmlFor="trip-width">Minimum width (m)</label>
          <input
            id="trip-width"
            type="number"
            min="0.000001"
            max="10"
            step="any"
            value={value.min_width_m}
            onChange={(event) => onChange({ min_width_m: event.target.value })}
          />
          <small>Blank means no numeric limit.</small>
        </div>
        <fieldset className="trip-surfaces">
          <legend>Avoid surfaces</legend>
          {(['smooth', 'uneven', 'gravel'] as const).map((surface) => (
            <label key={surface}>
              <input
                type="checkbox"
                checked={value.excluded_surfaces.includes(surface)}
                onChange={(event) =>
                  onChange({
                    excluded_surfaces: event.target.checked
                      ? [...value.excluded_surfaces, surface]
                      : value.excluded_surfaces.filter((item) => item !== surface),
                  })
                }
              />
              {surface.charAt(0).toUpperCase() + surface.slice(1)}
            </label>
          ))}
        </fieldset>
        <div className="field">
          <label htmlFor="trip-unknown">Unknown information</label>
          <select
            id="trip-unknown"
            value={value.unknown_policy}
            onChange={(event) =>
              onChange({ unknown_policy: event.target.value as ProfileDraft['unknown_policy'] })
            }
          >
            <option value="exclude">Exclude unknown information</option>
            <option value="allow_with_warning">Allow with a warning</option>
          </select>
        </div>
        {value.unknown_policy === 'allow_with_warning' && (
          <p className="helper">
            Unknown conditions may present barriers. Missing information cannot prove a stair,
            slope, width or surface requirement.
          </p>
        )}
        <div className="field">
          <label htmlFor="trip-speed">Estimated speed (m/s)</label>
          <input
            id="trip-speed"
            type="number"
            min="0.1"
            max="3"
            step="any"
            required
            value={value.travel_speed_mps}
            onChange={(event) => onChange({ travel_speed_mps: event.target.value })}
          />
        </div>
        <Button
          type="button"
          variant="secondary"
          size="small"
          onClick={() => onChange(guestProfile)}
        >
          Step-free preset
        </Button>
        <p className="helper">
          Personal preferences, not a legal accessibility standard or a guarantee.
        </p>
      </details>
      <p className="helper">
        {overridden
          ? 'Journey changes are not saved to your account.'
          : saved
            ? 'Using your saved preferences.'
            : 'Guest step-free preset. Review it for your needs.'}
      </p>
      {overridden && (
        <button type="button" className="text-link" onClick={reset}>
          Use {saved ? 'saved' : 'guest'} preferences
        </button>
      )}
    </div>
  )
}
