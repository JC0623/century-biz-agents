import { useMemo } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap,
  type Node, type Edge,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { ToolResult } from '../../types'
import { TOOL_LABELS } from '../../types'

interface Props {
  tools: Record<string, ToolResult>
  loading: boolean
}

function statusColor(status?: ToolResult['status']) {
  if (!status) return '#4b5563'
  if (status === 'ok') return '#059669'
  if (status === 'timeout') return '#d97706'
  return '#dc2626'
}

export function AgentDAG({ tools, loading }: Props) {
  const { nodes, edges } = useMemo(() => {
    const toolKeys = ['tool_market', 'tool_realestate', 'tool_industry', 'tool_valuation', 'tool_macro', 'tool_ip']
    const cols = 3
    const nodeW = 160, gapX = 200, gapY = 100

    const nodes: Node[] = [
      {
        id: 'start',
        position: { x: 340, y: 0 },
        data: { label: '🔍 쿼리 입력' },
        style: { background: '#312e81', color: '#e0e7ff', border: '1px solid #4f46e5', borderRadius: 8, fontSize: 12, padding: '8px 16px' },
      },
      {
        id: 'plan',
        position: { x: 320, y: 90 },
        data: { label: '📋 plan_tools' },
        style: { background: '#1e1b4b', color: '#c7d2fe', border: '1px solid #4338ca', borderRadius: 8, fontSize: 12, padding: '8px 16px' },
      },
    ]

    toolKeys.forEach((key, i) => {
      const r = tools[key]
      const col = i % cols
      const row = Math.floor(i / cols)
      nodes.push({
        id: key,
        position: { x: col * gapX + 60, y: 200 + row * gapY },
        data: {
          label: (
            <div className="flex flex-col gap-0.5">
              <span className="font-medium">{TOOL_LABELS[key]}</span>
              {r && <span className="text-[10px] opacity-70">신뢰도 {r.confidence.toFixed(2)}</span>}
            </div>
          ),
        },
        style: {
          background: r ? (r.status === 'ok' ? '#064e3b' : '#450a0a') : '#1f2937',
          color: r ? (r.status === 'ok' ? '#6ee7b7' : '#fca5a5') : '#9ca3af',
          border: `1px solid ${statusColor(r?.status)}`,
          borderRadius: 8,
          fontSize: 12,
          width: nodeW,
          padding: '8px 12px',
          opacity: loading && !r ? 0.5 : 1,
        },
      })
    })

    nodes.push({
      id: 'aggregate',
      position: { x: 280, y: 420 },
      data: { label: '⚖️ aggregate_results' },
      style: { background: '#1e293b', color: '#94a3b8', border: '1px solid #334155', borderRadius: 8, fontSize: 12, padding: '8px 16px' },
    })
    nodes.push({
      id: 'synthesize',
      position: { x: 285, y: 510 },
      data: { label: '✨ synthesize (Claude)' },
      style: { background: '#312e81', color: '#a5b4fc', border: '1px solid #6366f1', borderRadius: 8, fontSize: 12, padding: '8px 16px' },
    })

    const edges: Edge[] = [
      { id: 'e-start-plan', source: 'start', target: 'plan', style: { stroke: '#4f46e5' }, animated: loading },
      ...toolKeys.map(key => ({
        id: `e-plan-${key}`,
        source: 'plan',
        target: key,
        style: { stroke: statusColor(tools[key]?.status) },
        animated: loading && !tools[key],
      })),
      ...toolKeys.map(key => ({
        id: `e-${key}-agg`,
        source: key,
        target: 'aggregate',
        style: { stroke: '#334155' },
      })),
      { id: 'e-agg-syn', source: 'aggregate', target: 'synthesize', style: { stroke: '#6366f1' }, animated: loading },
    ]

    return { nodes, edges }
  }, [tools, loading])

  return (
    <div className="w-full h-[600px] rounded-xl overflow-hidden border border-gray-800">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-right"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1f2937" gap={20} />
        <Controls style={{ background: '#111827', border: '1px solid #374151' }} />
        <MiniMap
          nodeColor={n => (n.style?.background as string) ?? '#1f2937'}
          style={{ background: '#111827', border: '1px solid #374151' }}
        />
      </ReactFlow>
    </div>
  )
}
