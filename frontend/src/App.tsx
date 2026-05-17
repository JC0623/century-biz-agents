import { useState } from 'react'
import { AnalysisForm } from './components/AnalysisForm'
import { ChatPanel } from './components/ChatPanel'
import { ReportPanel } from './components/ReportPanel'
import { TornadoChart } from './components/charts/TornadoChart'
import { RadarChart } from './components/charts/RadarChart'
import { ScenarioMatrix } from './components/charts/ScenarioMatrix'
import { AgentDAG } from './components/charts/AgentDAG'
import type { AnalysisResponse, ToolResult } from './types'

type Tab = 'report' | 'charts' | 'dag'

export default function App() {
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [streaming, setStreaming] = useState(false)
  const [streamedTools, setStreamedTools] = useState<Record<string, ToolResult>>({})
  const [streamedReport, setStreamedReport] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('report')

  const handleAnalyze = async (region: string, query: string) => {
    setResult(null)
    setStreamedTools({})
    setStreamedReport('')
    setStreaming(true)
    setActiveTab('report')
    try {
      const res = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region_id: region, query }),
      })
      const data: AnalysisResponse = await res.json()
      setResult(data)
      setStreamedTools(data.tool_results)
      setStreamedReport(data.final_report)
    } finally {
      setStreaming(false)
    }
  }

  const toolResults = result?.tool_results ?? streamedTools
  const report = result?.final_report ?? streamedReport
  const avgConf = result?.avg_confidence ?? (() => {
    const scores = Object.values(streamedTools)
      .filter(r => r.status === 'ok').map(r => r.confidence)
    return scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0
  })()

  const confColor = avgConf >= 0.75 ? 'text-emerald-400' : avgConf >= 0.55 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-3 flex items-center gap-3 shrink-0">
        <div className="w-7 h-7 rounded-md bg-indigo-600 flex items-center justify-center text-xs font-bold text-white">O</div>
        <span className="text-sm font-semibold text-white">OSI-MAS</span>
        <span className="text-xs text-gray-600">Open Spatial Intelligence · Multi-Agent System</span>
        <div className="ml-auto flex items-center gap-1.5 text-xs text-gray-500">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          API 연결됨
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <aside className="w-80 shrink-0 border-r border-gray-800 flex flex-col bg-gray-950">
          <div className="p-4 border-b border-gray-800">
            <AnalysisForm onAnalyze={handleAnalyze} loading={streaming} />
          </div>
          <div className="flex-1 overflow-y-auto">
            <ChatPanel tools={toolResults} loading={streaming} />
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Tab bar */}
          <div className="border-b border-gray-800 flex items-center shrink-0">
            {(['report', 'charts', 'dag'] as Tab[]).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
                  activeTab === tab
                    ? 'border-indigo-500 text-indigo-400'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}
              >
                {tab === 'report' ? '📄 리포트' : tab === 'charts' ? '📊 차트 분석' : '🔗 에이전트 DAG'}
              </button>
            ))}
            {avgConf > 0 && (
              <div className="ml-auto flex items-center pr-5 gap-2 text-xs">
                <span className="text-gray-500">종합 신뢰도</span>
                <span className={`font-mono font-bold text-sm ${confColor}`}>{avgConf.toFixed(2)}</span>
              </div>
            )}
          </div>

          <div className="flex-1 overflow-y-auto">
            {activeTab === 'report' && (
              <ReportPanel report={report} loading={streaming && !report} />
            )}
            {activeTab === 'charts' && (
              <div className="p-6 grid grid-cols-2 gap-6">
                <div className="col-span-2">
                  <TornadoChart tools={toolResults} />
                </div>
                <ScenarioMatrix tools={toolResults} />
                <RadarChart tools={toolResults} />
              </div>
            )}
            {activeTab === 'dag' && (
              <AgentDAG tools={toolResults} loading={streaming} />
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
