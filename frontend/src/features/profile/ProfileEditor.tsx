import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, Info, RotateCcw, SlidersHorizontal } from 'lucide-react'
import { api, ApiError } from '../../services/api'
import type { Profile } from '../../services/api'
import { Button, Switch } from '../../components/ui'

export function ProfileEditor({ profile }: { profile: Profile }) {
  const queryClient = useQueryClient()
  const [snapshotVersion, setSnapshotVersion] = useState(profile.row_version)
  const [stairs, setStairs] = useState(profile.avoid_stairs)
  const [slope, setSlope] = useState(
    profile.max_slope_pct === null ? '' : String(profile.max_slope_pct),
  )
  const [width, setWidth] = useState(
    profile.min_width_m === null ? '' : String(profile.min_width_m),
  )
  const [speed, setSpeed] = useState(String(profile.travel_speed_mps))
  const [surfaces, setSurfaces] = useState(profile.excluded_surfaces)
  const [unknown, setUnknown] = useState(profile.unknown_policy)
  const [message, setMessage] = useState('')
  function loadValues(next: Profile) {
    setSnapshotVersion(next.row_version)
    setStairs(next.avoid_stairs)
    setSlope(next.max_slope_pct === null ? '' : String(next.max_slope_pct))
    setWidth(next.min_width_m === null ? '' : String(next.min_width_m))
    setSpeed(String(next.travel_speed_mps))
    setSurfaces(next.excluded_surfaces)
    setUnknown(next.unknown_policy)
  }
  const save = useMutation({
    mutationFn: api.saveProfile,
    onSuccess: (next) => {
      queryClient.setQueryData(['profile'], next)
      loadValues(next)
      setMessage('Your preferences have been saved.')
    },
  })
  const reload = useMutation({
    mutationFn: () => api.profile(),
    onSuccess: (next) => {
      queryClient.setQueryData(['profile'], next)
      loadValues(next)
      save.reset()
      setMessage('Latest preferences loaded. Review the values before editing.')
    },
  })
  function preset() {
    setStairs(true)
    setSlope('8')
    setWidth('0.9')
    setSpeed('1')
    setSurfaces(['uneven', 'gravel'])
    setUnknown('exclude')
    setMessage('Step-free preset applied. Review the values, then save.')
    save.reset()
  }
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMessage('')
    save.mutate({
      expected_version: snapshotVersion,
      avoid_stairs: stairs,
      max_slope_pct: slope === '' ? null : Number(slope),
      min_width_m: width === '' ? null : Number(width),
      travel_speed_mps: Number(speed),
      excluded_surfaces: surfaces as ('smooth' | 'uneven' | 'gravel')[],
      unknown_policy: unknown,
    })
  }
  return (
    <form className="preferences-form" onSubmit={(event) => void submit(event)}>
      <div className="form-section">
        <div className="form-section-heading">
          <span>
            <SlidersHorizontal size={20} />
          </span>
          <div>
            <h2>Pathway preferences</h2>
            <p>Choose the conditions that matter to you.</p>
          </div>
          <Button variant="secondary" size="small" type="button" onClick={preset}>
            <RotateCcw size={14} />
            Step-free preset
          </Button>
        </div>
        <div className="preference-setting">
          <div>
            <label htmlFor="avoid-stairs">Avoid stairs</label>
            <p>Exclude pathways that depend on steps.</p>
          </div>
          <Switch id="avoid-stairs" checked={stairs} onCheckedChange={setStairs} />
        </div>
        <div className="two-fields">
          <div className="field">
            <label htmlFor="max-slope">Maximum slope (%)</label>
            <input
              id="max-slope"
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={slope}
              onChange={(event) => setSlope(event.target.value)}
              aria-describedby="slope-hint"
            />
            <small id="slope-hint">Leave blank for no numeric limit.</small>
          </div>
          <div className="field">
            <label htmlFor="min-width">Minimum pathway width (m)</label>
            <input
              id="min-width"
              type="number"
              min="0.01"
              max="10"
              step="0.01"
              value={width}
              onChange={(event) => setWidth(event.target.value)}
              aria-describedby="width-hint"
            />
            <small id="width-hint">Leave blank for no numeric limit.</small>
          </div>
        </div>
        <fieldset className="surface-options">
          <legend>Avoid these surfaces</legend>
          {['smooth', 'uneven', 'gravel'].map((surface) => (
            <label key={surface}>
              <input
                type="checkbox"
                checked={surfaces.includes(surface)}
                onChange={(event) =>
                  setSurfaces((value) =>
                    event.target.checked
                      ? [...value, surface]
                      : value.filter((item) => item !== surface),
                  )
                }
              />
              <span>
                {surface[0]?.toUpperCase()}
                {surface.slice(1)}
              </span>
            </label>
          ))}
        </fieldset>
      </div>
      <div className="form-section">
        <div className="form-section-heading">
          <span>
            <Info size={20} />
          </span>
          <div>
            <h2>Unknown information</h2>
            <p>You choose how uncertainty is handled.</p>
          </div>
        </div>
        <fieldset className="policy-options">
          <legend className="sr-only">Unknown accessibility policy</legend>
          <label className={unknown === 'exclude' ? 'selected' : ''}>
            <input
              type="radio"
              name="unknown-policy"
              value="exclude"
              checked={unknown === 'exclude'}
              onChange={() => setUnknown('exclude')}
            />
            <span>
              <strong>Exclude unknown information</strong>
              <small>Keep unverified or incomplete pathways out of future route choices.</small>
            </span>
          </label>
          <label className={unknown === 'allow_with_warning' ? 'selected' : ''}>
            <input
              type="radio"
              name="unknown-policy"
              value="allow_with_warning"
              checked={unknown === 'allow_with_warning'}
              onChange={() => setUnknown('allow_with_warning')}
            />
            <span>
              <strong>Allow uncertainty with a warning</strong>
              <small>
                Missing information still cannot prove a hard stair, slope, width or surface
                requirement.
              </small>
            </span>
          </label>
        </fieldset>
        {unknown === 'allow_with_warning' && (
          <div className="notice notice-warning">
            <Info size={18} />
            <p>
              Unknown conditions may present barriers. They will never be described as verified
              safe.
            </p>
          </div>
        )}
      </div>
      <div className="form-section">
        <h2>Your pace</h2>
        <div className="field speed-field">
          <label htmlFor="travel-speed">Estimated travel speed (m/s)</label>
          <input
            id="travel-speed"
            type="number"
            min="0.1"
            max="3"
            step="0.1"
            required
            value={speed}
            onChange={(event) => setSpeed(event.target.value)}
          />
          <small>Used for duration estimates when route planning becomes available.</small>
        </div>
      </div>
      <div className="preference-save">
        <span>
          <Info size={16} />
          These are personal preferences, not a legal accessibility standard.
        </span>
        <Button type="submit" busy={save.isPending}>
          Save preferences <Check size={17} />
        </Button>
      </div>
      {message && (
        <p className="success-text" role="status">
          <Check size={16} />
          {message}
        </p>
      )}
      {save.error && (
        <div className="form-error-box" role="alert">
          <p>
            {save.error instanceof ApiError && save.error.status === 409
              ? 'These settings changed in another session. Your unsaved values are still here. Reload the latest settings before deciding what to keep.'
              : save.error.message}
          </p>
          {save.error instanceof ApiError && save.error.status === 409 && (
            <Button type="button" variant="secondary" size="small" onClick={() => reload.mutate()}>
              Reload latest settings
            </Button>
          )}
        </div>
      )}
      {profile.row_version !== snapshotVersion && !save.isPending && (
        <div className="notice notice-warning" role="status">
          <p>Preferences changed in another session. Your draft is preserved.</p>
          <Button
            type="button"
            variant="secondary"
            size="small"
            onClick={() => reload.mutate()}
            busy={reload.isPending}
          >
            Load latest values
          </Button>
        </div>
      )}
      {reload.error && (
        <p className="form-error" role="alert">
          {reload.error.message}
        </p>
      )}
    </form>
  )
}
