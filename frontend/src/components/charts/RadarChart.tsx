import {
  Radar, RadarChart as RechartsRadar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip,
} from 'recharts'
import type { ToolResult } from '../../types'
import { TOOL_LABELS } from '../../types'

interface Props {
  tools: Record<string, ToolResult>
}

export function RadarChart({ tools }: Props) {
  const entries = Object.entries(tools)

  if (entries.length === 0) {
    return <Empty />
  }

  const data = entries.map(([key, r]) => ({
    subject: TOOL_LABELS[key] ?? key,
    신뢰도: r.status === 'ok' ? parseFloat((r.confidence * 100).toFixed(1)) : 0,
    fullMark: 100,
  }))

  return (
    <div className="bg-gray-900 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-white mb-1">경쟁력 레이더 차트</h3>
      <p className="text-xs text-gray-500 mb-3">에이전트별 데이터 신뢰도 (0~100)</p>
      <ResponsiveContainer width="100%" height={260}>
        <RechartsRadar data={data} outerRadius="75%">
          <PolarGrid stroke="#1f2937" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: '#6b7280', fontSize: 10 }}
            tickCount={4}
          />
          <Radar
            name="신뢰도"
            dataKey="신뢰도"
            stroke="#6366f1"
            fill="#6366f1"
            fillOpacity={0.25}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
            formatter={(v) => [`${(v as number).toFixed(1)}%`, '신뢰도']}
          />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  )
}

function Empty() {
  return (
    <div className="bg-gray-900 rounded-xl p-5 flex items-center justify-center h-64">
      <p className="text-sm text-gray-600">분석 결과가 없습니다.</p>
    </div>
  )
}
