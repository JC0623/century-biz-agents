interface Props {
  report: string
  loading: boolean
}

export function ReportPanel({ report, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-3">
          <div className="text-3xl animate-pulse">🔍</div>
          <p className="text-sm text-gray-400">에이전트가 데이터를 수집하고 있습니다...</p>
        </div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-3">
          <p className="text-4xl">📊</p>
          <p className="text-sm text-gray-500">분석을 실행하면 리포트가 여기에 표시됩니다.</p>
        </div>
      </div>
    )
  }

  // 마크다운을 간단히 렌더링
  const lines = report.split('\n')

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="prose prose-invert prose-sm max-w-none">
        {lines.map((line, i) => {
          if (line.startsWith('# ')) return <h1 key={i} className="text-2xl font-bold text-white mt-6 mb-3">{line.slice(2)}</h1>
          if (line.startsWith('## ')) return <h2 key={i} className="text-lg font-semibold text-indigo-300 mt-5 mb-2 border-b border-gray-800 pb-1">{line.slice(3)}</h2>
          if (line.startsWith('### ')) return <h3 key={i} className="text-base font-medium text-gray-200 mt-4 mb-1">{line.slice(4)}</h3>
          if (line.startsWith('> ')) return (
            <blockquote key={i} className="border-l-2 border-indigo-500 pl-4 py-1 my-2 text-gray-300 italic text-sm">
              {line.slice(2)}
            </blockquote>
          )
          if (line.startsWith('| ')) return <TableRow key={i} line={line} />
          if (line.startsWith('---')) return <hr key={i} className="border-gray-800 my-4" />
          if (line.startsWith('- ') || line.startsWith('* ')) return (
            <li key={i} className="text-sm text-gray-300 ml-4 list-disc my-0.5">{line.slice(2)}</li>
          )
          if (line.trim() === '') return <div key={i} className="h-2" />
          return <p key={i} className="text-sm text-gray-300 leading-relaxed">{line}</p>
        })}
      </div>
    </div>
  )
}

function TableRow({ line }: { line: string }) {
  if (line.replace(/[|\s-]/g, '') === '') return <tr key={line} />
  const cells = line.split('|').slice(1, -1).map(c => c.trim())
  const isHeader = cells.some(c => c.length > 0)
  return (
    <tr className="border-b border-gray-800">
      {cells.map((c, i) => (
        isHeader
          ? <td key={i} className="px-3 py-1.5 text-xs text-gray-300">{c}</td>
          : <th key={i} className="px-3 py-1.5 text-xs text-gray-400 font-medium text-left">{c}</th>
      ))}
    </tr>
  )
}
