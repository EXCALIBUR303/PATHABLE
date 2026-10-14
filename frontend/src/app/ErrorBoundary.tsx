import { Component } from 'react'
import type { ReactNode } from 'react'

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    if (this.state.failed)
      return (
        <main className="access-state">
          <h1>Something interrupted this page.</h1>
          <p>Please reload PathAble to try again. Unsaved form changes may be lost.</p>
          <button className="button button-primary" onClick={() => window.location.reload()}>
            Reload page
          </button>
        </main>
      )
    return this.props.children
  }
}
