import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { LocationSearch } from './LocationSearch'
import { locations } from '../../test/fixtures'

describe('keyboard location selection', () => {
  it('filters and selects a real location with the keyboard', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <LocationSearch label="Destination" locations={locations} value="" onChange={onChange} />,
    )
    await user.click(screen.getByRole('combobox', { name: 'Destination' }))
    await user.type(screen.getByRole('combobox'), 'Library')
    expect(screen.getAllByRole('option')).toHaveLength(1)
    await user.keyboard('{Enter}')
    expect(onChange).toHaveBeenCalledWith(locations[0]?.id)
    expect(screen.getByRole('combobox')).toHaveAttribute('aria-expanded', 'false')
  })
  it('provides an empty state and closes on Escape without choosing a location', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<LocationSearch label="Start" locations={locations} value="" onChange={onChange} />)
    await user.type(screen.getByRole('combobox'), 'Nowhere')
    expect(screen.getByText(/No matching places/)).toBeVisible()
    await user.keyboard('{Escape}')
    expect(onChange).not.toHaveBeenCalled()
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })
})
