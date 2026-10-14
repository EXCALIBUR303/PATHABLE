import { lazy, Suspense } from 'react'
import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'motion/react'
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  Compass,
  HeartHandshake,
  Layers,
  MapPin,
  MoveUpRight,
  SlidersHorizontal,
} from 'lucide-react'
import { useCampusData } from '../hooks/queries'
import { Badge, Button, ErrorNotice, Loading } from '../components/ui'
import { graphEdges } from '../features/navigation/map-data'

const CampusMap = lazy(() => import('../features/navigation/CampusMap'))

export default function Landing() {
  const data = useCampusData()
  const reduced = useReducedMotion()
  const edges = graphEdges(data.graph.data)
  return (
    <>
      <section className="landing-hero page-container">
        <motion.div
          className="hero-copy"
          initial={reduced ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <div className="eyebrow">
            <span className="eyebrow-line" />A little more freedom. Every day.
          </div>
          <h1>
            Every path
            <br />
            should be{' '}
            <span>
              possible
              <span className="word-underline" />.
            </span>
          </h1>
          <p className="hero-description">
            Explore your campus with your needs in mind.
            <br className="desktop-break" />
            Know the paths, choose your preferences, and move with more confidence.
          </p>
          <div className="hero-actions">
            <Button asChild>
              <Link to="/navigate">
                Explore the campus <ArrowUpRight size={18} />
              </Link>
            </Button>
            <Link className="text-link" to="/register">
              Make it yours <ArrowRight size={16} />
            </Link>
          </div>
          <div className="hero-assurance">
            <span>
              <Check size={15} />
              No map service account needed
            </span>
            <span>
              <Check size={15} />
              Your preferences, your pace
            </span>
          </div>
          <div className="hero-demo-note">
            <span className="demo-dot" />
            <span>A fictional campus. A real starting point for inclusive navigation.</span>
          </div>
        </motion.div>
        <motion.div
          className="hero-preview"
          initial={reduced ? false : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.1 }}
        >
          <div className="preview-toolbar">
            <div>
              <span className="status-dot" />
              <strong>Your campus, at a glance</strong>
            </div>
            <Badge>Live demo data</Badge>
          </div>
          {data.error ? (
            <ErrorNotice error={data.error} retry={() => void data.refresh()} />
          ) : data.loading ? (
            <Loading />
          ) : (
            data.graph.data && (
              <Suspense fallback={<Loading />}>
                <CampusMap
                  graph={data.graph.data}
                  locations={data.locations.data ?? []}
                  infrastructure={data.infrastructure.data ?? []}
                  preview
                />
              </Suspense>
            )
          )}
          <div className="preview-insight">
            <span className="insight-icon">
              <Compass size={22} />
            </span>
            <div>
              <strong>Find a path that fits you.</strong>
              <span>Explore mapped pathways and accessibility details.</span>
            </div>
            <Link to="/navigate" aria-label="Open the campus map">
              <ArrowUpRight size={19} />
            </Link>
          </div>
          <div className="floating-note">
            <HeartHandshake size={18} />
            <span>
              Built around
              <br />
              <strong>individual needs</strong>
            </span>
          </div>
        </motion.div>
      </section>
      <section className="metrics-strip">
        <div className="page-container metrics-inner">
          <div>
            <span className="metric-icon">
              <MapPin size={21} />
            </span>
            <strong>
              {data.locations.data?.length ?? '—'}
              <small>mapped destinations</small>
            </strong>
          </div>
          <div>
            <span className="metric-icon">
              <Layers size={21} />
            </span>
            <strong>
              {data.graph.data ? edges.length : '—'}
              <small>documented pathways</small>
            </strong>
          </div>
          <div>
            <span className="metric-icon">
              <SlidersHorizontal size={21} />
            </span>
            <strong>
              Your preferences<small>at the heart of the journey</small>
            </strong>
          </div>
          <p>
            Numbers come from the
            <br />
            <strong>fictional campus dataset.</strong>
          </p>
        </div>
      </section>
      <section className="page-container introduction" id="how-it-works">
        <div className="section-heading">
          <div>
            <div className="eyebrow">Thoughtful navigation starts here</div>
            <h2>
              More than getting
              <br />
              from A to B.
            </h2>
          </div>
          <p>
            A short walk shouldn’t come with unexpected barriers. PathAble brings pathway
            information and personal preferences together, in one calm workspace.
          </p>
        </div>
        <div className="feature-grid">
          <article>
            <span className="feature-icon">
              <Compass size={25} />
            </span>
            <h3>Know your surroundings</h3>
            <p>
              Explore buildings, mapped entrances, ramps and pathways. Details stay visible
              alongside the map.
            </p>
            <Link to="/navigate">
              Explore the map <ArrowRight size={16} />
            </Link>
          </article>
          <article>
            <span className="feature-icon">
              <SlidersHorizontal size={25} />
            </span>
            <h3>Make room for your needs</h3>
            <p>
              Save stair, slope, width and surface preferences. Clear controls help express what
              matters to you.
            </p>
            <Link to="/profile">
              Set your preferences <ArrowRight size={16} />
            </Link>
          </article>
          <article>
            <span className="feature-icon">
              <HeartHandshake size={25} />
            </span>
            <h3>Better paths, together</h3>
            <p>
              Community reporting and human-reviewed updates are coming next. Uncertainty is always
              made clear.
            </p>
            <Link to="/reports">
              About community reports <ArrowRight size={16} />
            </Link>
          </article>
        </div>
      </section>
      <section className="page-container steps-section">
        <div className="section-heading">
          <div>
            <div className="eyebrow">Simple by design</div>
            <h2>
              A campus that feels
              <br />a little more yours.
            </h2>
          </div>
          <a href="#journey" className="text-link">
            Start exploring <ArrowDown size={16} />
          </a>
        </div>
        <div className="steps-grid">
          {[
            {
              n: '01',
              title: 'Find your place',
              body: 'Search a building and explore its mapped entrance.',
            },
            {
              n: '02',
              title: 'Choose what matters',
              body: 'Tell PathAble about your mobility preferences.',
            },
            {
              n: '03',
              title: 'Explore with context',
              body: 'Compare calculated routes, read pathway observations, and follow directions as text.',
            },
          ].map((step) => (
            <article key={step.n}>
              <span>{step.n}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="page-container journey-section" id="journey">
        <div>
          <div className="eyebrow">Every journey belongs</div>
          <h2>
            Let’s make the campus
            <br />
            easier to explore.
          </h2>
          <p>Start with the fictional demo. No sign-in required.</p>
        </div>
        <Button asChild>
          <Link to="/navigate">
            Open the campus map <MoveUpRight size={18} />
          </Link>
        </Button>
      </section>
    </>
  )
}
