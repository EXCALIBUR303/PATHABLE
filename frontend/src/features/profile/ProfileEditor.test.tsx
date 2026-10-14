import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { api, ApiError } from '../../services/api'
import { profile } from '../../test/fixtures'
import { ProfileEditor } from './ProfileEditor'

function setup() {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <ProfileEditor profile={profile} />
    </QueryClientProvider>,
  )
  return userEvent.setup()
}

describe('preference form behavior', () => {
  it('preserves a draft and its original version when background data changes', async () => {
    const save = vi
      .spyOn(api, 'saveProfile')
      .mockRejectedValue(new ApiError(409, 'STALE_VERSION', 'Conflict'))
    const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    const view = render(
      <QueryClientProvider client={client}>
        <ProfileEditor profile={profile} />
      </QueryClientProvider>,
    )
    const user = userEvent.setup()
    await user.clear(screen.getByLabelText('Minimum pathway width (m)'))
    await user.type(screen.getByLabelText('Minimum pathway width (m)'), '1.3')
    view.rerender(
      <QueryClientProvider client={client}>
        <ProfileEditor profile={{ ...profile, row_version: 2, min_width_m: 2 }} />
      </QueryClientProvider>,
    )
    expect(screen.getByLabelText('Minimum pathway width (m)')).toHaveValue(1.3)
    expect(screen.getByText(/Your draft is preserved/)).toBeVisible()
    await user.click(screen.getByRole('button', { name: /Save preferences/ }))
    await waitFor(() =>
      expect(save.mock.calls[0]?.[0]).toMatchObject({ expected_version: 1, min_width_m: 1.3 }),
    )
  })
  it('stores blank optional measurements as unknown, not zero', async () => {
    const save = vi
      .spyOn(api, 'saveProfile')
      .mockResolvedValue({ ...profile, max_slope_pct: null, row_version: 2 })
    const user = setup()
    await user.clear(screen.getByLabelText('Maximum slope (%)'))
    await user.click(screen.getByRole('button', { name: /Save preferences/ }))
    await waitFor(() =>
      expect(save.mock.calls[0]?.[0]).toMatchObject({ max_slope_pct: null, expected_version: 1 }),
    )
    expect(await screen.findByText('Your preferences have been saved.')).toBeVisible()
  })
  it('does not submit invalid numeric bounds', async () => {
    const save = vi.spyOn(api, 'saveProfile')
    const user = setup()
    await user.clear(screen.getByLabelText('Estimated travel speed (m/s)'))
    await user.type(screen.getByLabelText('Estimated travel speed (m/s)'), '0')
    await user.click(screen.getByRole('button', { name: /Save preferences/ }))
    expect(save).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Estimated travel speed (m/s)')).toBeInvalid()
  })
  it('warns when allowing unknown data and preserves edits after conflict', async () => {
    vi.spyOn(api, 'saveProfile').mockRejectedValue(new ApiError(409, 'STALE_VERSION', 'Conflict'))
    const user = setup()
    await user.click(screen.getByRole('radio', { name: /Allow uncertainty/ }))
    expect(screen.getByText(/never be described as verified safe/)).toBeVisible()
    await user.clear(screen.getByLabelText('Minimum pathway width (m)'))
    await user.type(screen.getByLabelText('Minimum pathway width (m)'), '1.2')
    await user.click(screen.getByRole('button', { name: /Save preferences/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Your unsaved values are still here')
    expect(screen.getByLabelText('Minimum pathway width (m)')).toHaveValue(1.2)
  })
})
