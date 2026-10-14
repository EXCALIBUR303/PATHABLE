import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  Bookmark,
  Check,
  Compass,
  MapPin,
  MessageSquare,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react'
import { useSession } from '../app/session-context'
import { api, ApiError } from '../services/api'
import { Badge, Button, ErrorNotice, Loading } from '../components/ui'
import { useCampusData } from '../hooks/queries'

export default function Dashboard() {
  const { session, refresh } = useSession()
  const user = session!.user!
  const queryClient = useQueryClient()
  const saved = useQuery({ queryKey: ['saved'], queryFn: ({ signal }) => api.saved(signal) })
  const data = useCampusData()
  const [name, setName] = useState(user.display_name)
  const [message, setMessage] = useState('')
  const remove = useMutation({
    mutationFn: api.removeDestination,
    onSuccess: () => {
      setMessage('Saved place removed.')
      void queryClient.invalidateQueries({ queryKey: ['saved'] })
    },
  })
  const editName = useMutation({
    mutationFn: api.editUser,
    onSuccess: async () => {
      await refresh()
      setMessage('Your name has been updated.')
    },
  })
  return (
    <section className="page-container dashboard-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">Your corner of campus</div>
          <h1>Hello, {user.display_name.split(' ')[0]}.</h1>
          <p className="muted">Your places, your preferences, and a little less starting over.</p>
        </div>
        <Button asChild>
          <Link to="/navigate">
            Explore campus <ArrowRight size={17} />
          </Link>
        </Button>
      </div>
      <div className="dashboard-grid">
        <section className="saved-panel">
          <div className="section-title">
            <h2>
              <Bookmark size={21} />
              Your saved places
            </h2>
            <Badge>{saved.data?.length ?? 0}</Badge>
          </div>
          {saved.isPending ? (
            <Loading label="Loading saved places" />
          ) : saved.error ? (
            <ErrorNotice error={saved.error} retry={() => void saved.refetch()} />
          ) : saved.data?.length ? (
            <div className="saved-list">
              {saved.data.map((item) => (
                <article key={item.id}>
                  <span className="place-icon">
                    <MapPin size={21} />
                  </span>
                  <div>
                    <h3>{item.label}</h3>
                    <p>
                      {data.locations.data?.find((location) => location.id === item.location_id)
                        ?.name ?? 'Saved campus destination'}
                    </p>
                  </div>
                  <Button asChild variant="ghost" size="small">
                    <Link
                      to={`/navigate?place=${item.location_id}`}
                      aria-label={`Explore ${item.label}`}
                    >
                      <ArrowRight size={18} />
                    </Link>
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Remove ${item.label}`}
                    disabled={remove.isPending}
                    onClick={() => remove.mutate(item.id)}
                  >
                    <Trash2 size={17} />
                  </Button>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Bookmark size={31} />
              <h3>A familiar place starts here.</h3>
              <p>Explore a building on the map, then save it for next time.</p>
              <Button asChild variant="secondary">
                <Link to="/navigate">
                  Find a place <ArrowRight size={15} />
                </Link>
              </Button>
            </div>
          )}
          {remove.error && (
            <p role="alert" className="form-error">
              {remove.error.message}
            </p>
          )}
        </section>
        <div className="dashboard-side">
          <Link className="preference-card" to="/profile">
            <SlidersHorizontal size={25} />
            <h2>Go your own way.</h2>
            <p>Your saved accessibility preferences are always within reach.</p>
            <span>
              Manage preferences <ArrowRight size={16} />
            </span>
          </Link>
          <section className="reports-preview">
            <MessageSquare size={24} />
            <h2>Your voice matters.</h2>
            <p>View your submitted concerns, private evidence and administrator review history.</p>
            <Link className="text-link" to="/reports">
              Explore reporting <ArrowRight size={15} />
            </Link>
          </section>
        </div>
      </div>
      <section className="account-settings">
        <div>
          <h2>Account details</h2>
          <p className="muted">{user.email}</p>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            editName.mutate({ display_name: name.trim(), expected_version: user.row_version })
          }}
        >
          <div className="field">
            <label htmlFor="display-name">Display name</label>
            <input
              id="display-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              maxLength={80}
            />
          </div>
          <Button type="submit" variant="secondary" busy={editName.isPending}>
            Update name
          </Button>
        </form>
      </section>
      {message && (
        <p className="success-text" role="status">
          <Check size={16} />
          {message}
        </p>
      )}
      {editName.error && (
        <p className="form-error" role="alert">
          {editName.error instanceof ApiError && editName.error.status === 409
            ? 'Your account changed in another session. Reload the latest details before updating.'
            : editName.error.message}
        </p>
      )}
      <div className="dashboard-note">
        <Compass size={17} />
        <span>
          All campus places in this demo are fictional. Your account settings are persisted.
        </span>
      </div>
    </section>
  )
}
