import type { Edge, Graph, Infrastructure } from '../../services/api'

export const graphEdges = (graph?: Graph): Edge[] =>
  graph?.features.flatMap((feature) =>
    'source_node_id' in feature.properties ? [feature.properties] : [],
  ) ?? []

export function edgeAvailability(edge: Edge, infrastructure: Infrastructure[]) {
  const dependencies = infrastructure.filter((item) => item.edge_ids.includes(edge.id))
  if (
    edge.effective_availability === 'closed' ||
    edge.availability === 'closed' ||
    dependencies.some((item) => item.availability === 'closed')
  )
    return 'closed'
  if (
    edge.effective_availability === 'temporarily_blocked' ||
    edge.availability === 'temporarily_blocked' ||
    dependencies.some((item) => item.availability === 'temporarily_blocked')
  )
    return 'temporarily_blocked'
  return 'open'
}
