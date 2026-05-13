from agents.state import OSIMASState


FALLBACK_CHAIN = [
    "공식 공공 API (소상공인시장진흥공단, 국토교통부)",
    "지자체 포털 (지역 통계 자료)",
    "지적·용도지역·건물대장 (토지이음)",
    "상업 POI / 이동통신 유동인구 데이터",
    "뉴스 / 사업자등록 / 웹 검색",
    "사용자 업로드 문서",
    "사용자 직접 확인 요청",
]


async def fallback_search(state: OSIMASState) -> dict:
    results = state.get("tool_results", {})
    low_conf = [
        f"{name} (신뢰도: {r['confidence']:.2f})"
        for name, r in results.items()
        if r["status"] == "ok" and r["confidence"] < 0.55
    ]
    missing = [
        name for name, r in results.items()
        if r["status"] in ("timeout", "error", "skipped")
    ]

    chain_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(FALLBACK_CHAIN))

    warning = (
        f"데이터 품질 미달로 Fallback 탐색 권고.\n"
        f"  신뢰도 낮은 소스: {', '.join(low_conf) or '없음'}\n"
        f"  실패한 도구: {', '.join(missing) or '없음'}\n"
        f"  권장 보조 데이터 탐색 순서:\n{chain_text}"
    )

    return {"warnings": [warning]}
