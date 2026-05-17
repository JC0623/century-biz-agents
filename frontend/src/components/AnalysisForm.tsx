import { useState } from 'react'

interface Props {
  onAnalyze: (region: string, query: string) => void
  loading: boolean
}

const PRESETS = [
  { region: '서울특별시 강남구 역삼동', query: '이 지역 소규모 식당 인수 적합성 분석' },
  { region: '서울특별시 마포구 합정동', query: '카페 창업 입지 분석 및 밸류에이션' },
  { region: '경기도 성남시 판교동', query: 'IT 스타트업 오피스 임차 적합성 분석' },
]

export function AnalysisForm({ onAnalyze, loading }: Props) {
  const [region, setRegion] = useState(PRESETS[0].region)
  const [query, setQuery] = useState(PRESETS[0].query)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!region.trim() || !query.trim()) return
    onAnalyze(region.trim(), query.trim())
  }

  const applyPreset = (p: typeof PRESETS[number]) => {
    setRegion(p.region)
    setQuery(p.query)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <h2 className="text-sm font-semibold text-white">입지 분석</h2>

      {/* 프리셋 */}
      <div className="flex flex-col gap-1">
        {PRESETS.map((p, i) => (
          <button
            key={i}
            type="button"
            onClick={() => applyPreset(p)}
            className="text-left text-xs text-gray-500 hover:text-indigo-400 truncate transition-colors cursor-pointer"
          >
            · {p.region.split(' ').slice(-1)[0]}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-gray-400">분석 지역</label>
        <input
          value={region}
          onChange={e => setRegion(e.target.value)}
          placeholder="예: 서울특별시 강남구 역삼동"
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 transition-colors"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-gray-400">분석 질문</label>
        <textarea
          value={query}
          onChange={e => setQuery(e.target.value)}
          rows={3}
          placeholder="예: 이 지역 식당 인수 적합성을 분석해줘"
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium py-2 rounded-lg transition-colors cursor-pointer"
      >
        {loading ? '분석 중...' : '분석 시작'}
      </button>
    </form>
  )
}
