import { useQuery } from '@tanstack/react-query'
import { SlidersHorizontal, ShieldCheck } from 'lucide-react'
import { api } from '../services/api'
import { ProfileEditor } from '../features/profile/ProfileEditor'
import { Badge, ErrorNotice, Loading } from '../components/ui'

export default function Profile() {
  const profile = useQuery({ queryKey: ['profile'], queryFn: ({ signal }) => api.profile(signal) })
  return (
    <section className="page-container settings-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">Your needs belong here</div>
          <h1>Made for your pace.</h1>
          <p className="muted">Save preferences that describe the paths you want to take.</p>
        </div>
        <Badge tone="good">
          <SlidersHorizontal size={14} />
          Personal preferences
        </Badge>
      </div>
      <div className="settings-layout">
        <div>
          {profile.isPending ? (
            <Loading label="Loading your preferences" />
          ) : profile.error ? (
            <ErrorNotice error={profile.error} retry={() => void profile.refetch()} />
          ) : (
            profile.data && <ProfileEditor key={profile.data.id} profile={profile.data} />
          )}
        </div>
        <aside className="settings-aside">
          <span className="context-icon">
            <ShieldCheck size={26} />
          </span>
          <h2>
            Personal, without
            <br />
            the personal questions.
          </h2>
          <p>
            There’s no need to share a diagnosis. Just choose the pathway conditions that work for
            you.
          </p>
          <div className="aside-divider" />
          <h3>What happens next?</h3>
          <p>
            Your preferences are saved to your account. Route planning is coming next; it will use
            these settings when it becomes available.
          </p>
          <p className="helper">You can change them whenever your needs change.</p>
        </aside>
      </div>
    </section>
  )
}
