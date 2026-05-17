import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts'
import type { ToolResult } from '../../types'
import { TOOL_LABELS } from '../../types'

interface Props {
  tools: Record<string, ToolResult>
}

export function TornadoChart({ tools }: Props) {
  const entries = Object.entries(tools).filter(([, r]) => r.status === 'ok')

  if (entries.length === 0) {
    return <Empty />
  }

  // 신뢰도를 0.55 기준선 대비 편차로 표현
  const baseline = 0.55
  const data = entries
    .map(([key, r]) => ({
      name: TOOL_LABELS[key] ?? key,
      value: parseFloat((r.confidence - baseline).toFixed(3)),
      confidence: r.confidence,
    }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))

  return (
    <div className="bg-gray-900 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-white mb-1">민감도 토네이도 차트</h3>
      <p className="text-xs text-gray-500 mb-4">기준선(0.55) 대비 에이전트별 신뢰도 편차</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 40, left: 90, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
          <XAxis
            type="number"
            domain={[-0.6, 0.6]}
            tickFormatter={v => (v >= 0 ? `+${v.toFixed(2)}` : v.toFixed(2))}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            axisLine={{ stroke: '#374151' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: '#d1d5db', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={85}
          />
          <Tooltip
            cursor={{ fill: 'rgba(99,102,241,0.1)' }}
            contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
            formatter={(v, _n, props) => {
              const val = v as number
              const conf = (props as { payload?: { confidence?: number } })?.payload?.confidence ?? 0
              return [`신뢰도 ${conf.toFixed(2)} (편차 ${val >= 0 ? '+' : ''}${val.toFixed(3)})`, '신뢰도']
            }}
          />
          <ReferenceLine x={0} stroke="#6366f1" strokeDasharray="4 2" />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={24}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.value >= 0.2 ? '#10b981' : entry.value >= 0 ? '#6366f1' : '#ef4444'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function Empty() {
  return (
    <div className="bg-gray-900 rounded-xl p-5 flex items-center justify-center h-48">
      <p className="text-sm text-gray-600">분석 결과가 없습니다.</p>
    </div>
  )
}
