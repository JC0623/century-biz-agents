import type { ToolResult } from '../types'
import { TOOL_LABELS } from '../types'

interface Props {
  tools: Record<string, ToolResult>
  loading: boolean
}

function ConfBadge({ value }: { value: number }) {
  const color = value >= 0.75 ? 'bg-emerald-900 text-emerald-300'
    : value >= 0.55 ? 'bg-yellow-900 text-yellow-300'
    : 'bg-red-900 text-red-300'
  return (
    <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${color}`}>
      {value.toFixed(2)}
    </span>
  )
}

function StatusDot({ status }: { status: ToolResult['status'] }) {
  const color = status === 'ok' ? 'bg-emerald-400'
    : status === 'timeout' ? 'bg-yellow-400'
    : status === 'error' ? 'bg-red-400'
    : 'bg-gray-500'
  return <span className={`w-2 h-2 rounded-full shrink-0 ${color}`} />
}

export function ChatPanel({ tools, loading }: Props) {
  const entries = Object.entries(tools)

  if (!loading && entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-center px-6 py-12">
        <p className="text-2xl">🤖</p>
        <p className="text-sm text-gray-500">분석을 시작하면 에이전트별 결과가 여기에 표시됩니다.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-0 p-3">
      {loading && entries.length === 0 && (
        <div className="flex items-center gap-2 p-3 text-xs text-gray-500">
          <span className="animate-spin">⟳</span> 에이전트 실행 중...
        </div>
      )}

      {entries.map(([key, r]) => (
        <div key={key} className="flex flex-col gap-1 p-3 rounded-lg hover:bg-gray-900 transition-colors">
          <div className="flex items-center gap-2">
            <StatusDot status={r.status} />
            <span className="text-xs font-medium text-gray-300">{TOOL_LABELS[key] ?? key}</span>
            {r.status === 'ok' && <ConfBadge value={r.confidence} />}
            {r.status !== 'ok' && (
              <span className="text-xs text-red-400">{r.status}</span>
            )}
          </div>
          {r.summary && (
            <p className="text-xs text-gray-500 leading-relaxed pl-4 line-clamp-3">{r.summary}</p>
          )}
          {r.error && (
            <p className="text-xs text-red-500 pl-4 line-clamp-2">{r.error}</p>
          )}
        </div>
      ))}

      {loading && entries.length > 0 && (
        <div className="flex items-center gap-2 p-3 text-xs text-gray-500">
          <span className="animate-spin inline-block">⟳</span> 리포트 합성 중...
        </div>
      )}
    </div>
  )
}
