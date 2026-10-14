import type { Profile, ProfileInput } from '../../services/api'

export type RoutingProfile = Omit<ProfileInput, 'expected_version'>
export type ProfileDraft = {
  avoid_stairs: boolean
  max_slope_pct: string
  min_width_m: string
  excluded_surfaces: RoutingProfile['excluded_surfaces']
  unknown_policy: RoutingProfile['unknown_policy']
  travel_speed_mps: string
}

export const guestProfile: ProfileDraft = {
  avoid_stairs: true,
  max_slope_pct: '8',
  min_width_m: '0.9',
  excluded_surfaces: ['uneven', 'gravel'],
  unknown_policy: 'exclude',
  travel_speed_mps: '1',
}

export function profileDraft(profile: Profile): ProfileDraft {
  return {
    avoid_stairs: profile.avoid_stairs,
    max_slope_pct: profile.max_slope_pct === null ? '' : String(profile.max_slope_pct),
    min_width_m: profile.min_width_m === null ? '' : String(profile.min_width_m),
    excluded_surfaces: profile.excluded_surfaces.filter(
      (surface): surface is RoutingProfile['excluded_surfaces'][number] =>
        surface === 'smooth' || surface === 'uneven' || surface === 'gravel',
    ),
    unknown_policy: profile.unknown_policy,
    travel_speed_mps: String(profile.travel_speed_mps),
  }
}

export function validateProfile(
  draft: ProfileDraft,
): { profile: RoutingProfile; error?: undefined } | { profile?: undefined; error: string } {
  const slope = draft.max_slope_pct.trim() === '' ? null : Number(draft.max_slope_pct)
  const width = draft.min_width_m.trim() === '' ? null : Number(draft.min_width_m)
  const speed = draft.travel_speed_mps.trim() === '' ? NaN : Number(draft.travel_speed_mps)
  if (slope !== null && (!Number.isFinite(slope) || slope < 0 || slope > 100))
    return { error: 'Maximum slope must be between 0 and 100%, or blank for no limit.' }
  if (width !== null && (!Number.isFinite(width) || width <= 0 || width > 10))
    return {
      error: 'Minimum width must be greater than 0 and at most 10 m, or blank for no limit.',
    }
  if (!Number.isFinite(speed) || speed < 0.1 || speed > 3)
    return { error: 'Travel speed must be between 0.1 and 3 m/s.' }
  return {
    profile: {
      avoid_stairs: draft.avoid_stairs,
      max_slope_pct: slope,
      min_width_m: width,
      excluded_surfaces: [...draft.excluded_surfaces].sort(),
      unknown_policy: draft.unknown_policy,
      travel_speed_mps: speed,
    },
  }
}
