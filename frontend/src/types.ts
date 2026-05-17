export interface ToolResult {
  tool: string
  status: 'ok' | 'timeout' | 'error' | 'skipped'
  confidence: number
  freshness_days: number | null
  summary: string
  error?: string
}

export interface AnalysisResponse {
  region_id: string
  query: string
  final_report: string
  tool_results: Record<string, ToolResult>
  warnings: string[]
  avg_confidence: number
}

export interface StreamEvent {
  event: 'status' | 'tool_result' | 'report' | 'done' | 'error'
  data: Record<string, unknown>
}

export const TOOL_LABELS: Record<string, string> = {
  tool_market: '상권 분석',
  tool_realestate: '공간 가치',
  tool_industry: '산업 클러스터',
  tool_valuation: '밸류에이션',
  tool_macro: '거시 원가',
  tool_ip: '무형자산·인증',
}
