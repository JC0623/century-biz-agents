import type { ToolResult } from '../../types'
import { TOOL_LABELS } from '../../types'

interface Props {
  tools: Record<string, ToolResult>
}

type Scenario = 'pessimistic' | 'base' | 'optimistic'

const SCENARIO_LABELS: Record<Scenario, string> = {
  pessimistic: '비관 (P10)',
  base: '기준 (P50)',
  optimistic: '낙관 (P90)',
}

const SCENARIO_MULTIPLIERS: Record<Scenario, number> = {
  pessimistic: 0.75,
  base: 1.0,
  optimistic: 1.25,
}

function confToScore(conf: number): number {
  return Math.round(conf * 100)
}

function scoreColor(score: number) {
  if (score >= 75) return 'bg-emerald-900/50 text-emerald-300 border-emerald-800'
  if (score >= 55) return 'bg-yellow-900/40 text-yellow-300 border-yellow-800'
  return 'bg-red-900/40 text-red-300 border-red-800'
}

export function ScenarioMatrix({ tools }: Props) {
  const entries = Object.entries(tools).filter(([, r]) => r.status === 'ok')

  if (entries.length === 0) {
    return (
      <div className="bg-gray-900 rounded-xl p-5 flex items-center justify-center h-64">
        <p className="text-sm text-gray-600">분석 결과가 없습니다.</p>
      </div>
    )
  }

  const scenarios: Scenario[] = ['pessimistic', 'base', 'optimistic']

  return (
    <div className="bg-gray-900 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-white mb-1">시나리오 비교 매트릭스</h3>
      <p className="text-xs text-gray-500 mb-4">에이전트 신뢰도 × 시나리오 보정 점수</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="text-left text-gray-500 font-medium pb-2 pr-3">에이전트</th>
              {scenarios.map(s => (
                <th key={s} className="text-center text-gray-400 font-medium pb-2 px-2 min-w-[80px]">
                  {SCENARIO_LABELS[s]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {entries.map(([key, r]) => {
              const base = confToScore(r.confidence)
              return (
                <tr key={key}>
                  <td className="py-2 pr-3 text-gray-300 whitespace-nowrap">{TOOL_LABELS[key] ?? key}</td>
                  {scenarios.map(s => {
                    const score = Math.min(100, Math.round(base * SCENARIO_MULTIPLIERS[s]))
                    return (
                      <td key={s} className="py-2 px-2 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded border text-xs font-mono ${scoreColor(score)}`}>
                          {score}
                        </span>
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex gap-3 text-xs text-gray-600">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-emerald-700" />75+ 양호</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-yellow-700" />55-74 보통</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-700" />~54 주의</span>
      </div>
    </div>
  )
}
