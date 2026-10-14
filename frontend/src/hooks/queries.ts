import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import { useSession } from '../app/session-context'
import { useCampusEvents } from '../features/events/useCampusEvents'

export function useCampusData() {
  const campuses = useQuery({
    queryKey: ['campuses'],
    queryFn: ({ signal }) => api.campuses(signal),
  })
  const campus =
    campuses.data?.find((value) => value.data_origin === 'synthetic_demo') ?? campuses.data?.[0]
  const { session } = useSession()
  const live = useCampusEvents(campus?.id, session?.user?.id)
  const locations = useQuery({
    queryKey: ['locations', campus?.id],
    queryFn: ({ signal }) => api.locations(campus!.id, signal),
    enabled: !!campus,
  })
  const graph = useQuery({
    queryKey: ['graph', campus?.id],
    queryFn: ({ signal }) => api.graph(campus!.id, signal),
    enabled: !!campus,
  })
  const infrastructure = useQuery({
    queryKey: ['infrastructure', campus?.id],
    queryFn: ({ signal }) => api.infrastructure(campus!.id, signal),
    enabled: !!campus,
  })
  const refresh = async () => {
    await campuses.refetch()
    if (campus) await Promise.all([locations.refetch(), graph.refetch(), infrastructure.refetch()])
  }
  return {
    campus,
    live,
    campuses,
    locations,
    graph,
    infrastructure,
    refresh,
    loading:
      campuses.isPending ||
      (!!campus && (locations.isPending || graph.isPending || infrastructure.isPending)),
    error: campuses.error ?? locations.error ?? graph.error ?? infrastructure.error,
  }
}
