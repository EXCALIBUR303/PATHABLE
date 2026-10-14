import { lazy, Suspense } from 'react'
import { createBrowserRouter, Link, RouterProvider } from 'react-router-dom'
import { Shell } from '../components/Shell'
import { Protected } from '../components/Protected'
import { Button, Loading } from '../components/ui'

const Landing = lazy(() => import('../pages/Landing'))
const Navigate = lazy(() => import('../pages/Navigation'))
const Auth = lazy(() => import('../pages/Auth'))
const Profile = lazy(() => import('../pages/Profile'))
const Dashboard = lazy(() => import('../pages/Dashboard'))
const Reports = lazy(() => import('../pages/Reports'))
const Admin = lazy(() => import('../pages/Admin'))
const load = (element: React.ReactNode) => (
  <Suspense fallback={<Loading label="Opening page" />}>{element}</Suspense>
)

const router = createBrowserRouter([
  {
    element: <Shell />,
    errorElement: (
      <section className="access-state" role="alert">
        <h1>Something interrupted this page.</h1>
        <p>Reload PathAble to try again. Unsaved changes may be lost.</p>
        <button className="button button-primary" onClick={() => window.location.reload()}>
          Reload page
        </button>
      </section>
    ),
    children: [
      { path: '/', element: load(<Landing />) },
      { path: '/navigate', element: load(<Navigate />) },
      { path: '/login', element: load(<Auth key="login" mode="login" />) },
      { path: '/register', element: load(<Auth key="register" mode="register" />) },
      {
        path: '/profile',
        element: load(
          <Protected>
            <Profile />
          </Protected>,
        ),
      },
      {
        path: '/dashboard',
        element: load(
          <Protected>
            <Dashboard />
          </Protected>,
        ),
      },
      { path: '/reports', element: load(<Reports />) },
      { path: '/reports/new', element: load(<Reports />) },
      {
        path: '/admin',
        element: load(
          <Protected admin>
            <Admin />
          </Protected>,
        ),
      },
      {
        path: '*',
        element: (
          <section className="page-container access-state">
            <h1>This path doesn’t lead anywhere.</h1>
            <p>The page you’re looking for could not be found.</p>
            <Button asChild>
              <Link to="/">Back to PathAble</Link>
            </Button>
          </section>
        ),
      },
    ],
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
