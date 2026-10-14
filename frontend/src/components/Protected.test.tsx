import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { SessionContext } from '../app/session-context'
import { session } from '../test/fixtures'
import { Protected } from './Protected'

describe('protected frontend states', () => {
  it('shows a permission explanation instead of administrator controls to a normal user', () => {
    render(
      <MemoryRouter>
        <SessionContext.Provider
          value={{ session, loading: false, error: null, refresh: async () => undefined }}
        >
          <Protected admin>
            <button>Privileged action</button>
          </Protected>
        </SessionContext.Provider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /for administrators/ })).toBeVisible()
    expect(screen.queryByText('Privileged action')).not.toBeInTheDocument()
  })
  it('does not show private content while account connection is unavailable', () => {
    render(
      <MemoryRouter>
        <SessionContext.Provider
          value={{
            loading: false,
            error: new Error('Connection failed'),
            refresh: async () => undefined,
          }}
        >
          <Protected>
            <div>Private settings</div>
          </Protected>
        </SessionContext.Provider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Connection failed')
    expect(screen.queryByText('Private settings')).not.toBeInTheDocument()
  })
})
