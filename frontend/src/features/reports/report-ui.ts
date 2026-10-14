import type { Report } from '../../services/api'

export const categories = [
  { value: 'blocked_ramp', label: 'Blocked ramp' },
  { value: 'inaccessible_entrance', label: 'Inaccessible entrance' },
  { value: 'damaged_pathway', label: 'Damaged pathway' },
  { value: 'elevator_unavailable', label: 'Elevator unavailable' },
  { value: 'temporary_obstacle', label: 'Temporary obstacle' },
  { value: 'other_accessibility_concern', label: 'Other accessibility concern' },
] as const
export const categoryLabel = (value: string) =>
  categories.find((category) => category.value === value)?.label ?? value.replaceAll('_', ' ')
export const statusLabel = (status: Report['status']) =>
  ({
    pending_review: 'Awaiting review',
    verified: 'Verified concern',
    rejected: 'Not verified',
    resolved: 'Resolved',
  })[status]
export function imageError(file: File) {
  return !['image/jpeg', 'image/png'].includes(file.type) ||
    file.size > 10 * 1024 * 1024 ||
    !file.size
    ? 'Choose a JPEG or PNG image between 1 byte and 10 MiB.'
    : ''
}
export function requestKey(
  reference: { current: { body: string; key: string } | null },
  body: unknown,
) {
  const serialized = JSON.stringify(body)
  if (reference.current?.body !== serialized)
    reference.current = { body: serialized, key: crypto.randomUUID() }
  return reference.current!.key
}
