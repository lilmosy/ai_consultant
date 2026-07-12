"""
오프라인 데모/테스트용 합성 픽스처.

API 없이 정합 엔진(matcher + reconciler)을 검증할 수 있도록, 부문 재편이
일어난 회사를 모사한다. 실제 숫자가 아니라 이합 보존 구조를 재현한 예시다.

시나리오 (네이버형): 2021년까지 '비즈니스플랫폼'+'쇼핑' 으로 보고하다가,
2022년 보고서부터 두 부문을 '커머스' 로 통합하고 2021년을 신구조로 재작성.
'서치플랫폼'은 이름만 '검색플랫폼'으로 개명. '핀테크/콘텐츠/클라우드'는 유지.
"""
from ai_consultant.schemas.segment import SegmentRow


def naver_like_rows() -> list[SegmentRow]:
    c = "NAVER형(합성)"

    def row(fy, ry, seg, rev, restated=False):
        return SegmentRow(
            company=c, fiscal_year=fy, report_year=ry, structure_id=ry,
            segment_name=seg, revenue=rev, source_name=f"{c} {ry} 사업보고서",
            source_span="II.사업의 내용 > 부문별 매출", is_restated=restated,
        )

    rows: list[SegmentRow] = []

    # 2021 보고서 (구 구조): 2020, 2021 회계연도
    for fy in ("2020", "2021"):
        base = 1.0 if fy == "2021" else 0.85
        rows += [
            row(fy, "2021", "서치플랫폼",       round(30000 * base)),
            row(fy, "2021", "비즈니스플랫폼",   round(28000 * base)),
            row(fy, "2021", "쇼핑",             round(19000 * base)),
            row(fy, "2021", "핀테크",           round(9000 * base)),
            row(fy, "2021", "콘텐츠",           round(6000 * base)),
            row(fy, "2021", "클라우드",         round(4000 * base)),
        ]

    # 2022 보고서 (신 구조): 2021(재작성), 2022 회계연도
    #   커머스 = 비즈니스플랫폼 + 쇼핑,  검색플랫폼 = 서치플랫폼(개명)
    for fy, g in (("2021", 1.0), ("2022", 1.15)):
        restated = fy == "2021"
        rows += [
            row(fy, "2022", "검색플랫폼",  round(30000 * g), restated),
            row(fy, "2022", "커머스",      round((28000 + 19000) * g), restated),
            row(fy, "2022", "핀테크",      round(9000 * g), restated),
            row(fy, "2022", "콘텐츠",      round(6000 * g), restated),
            row(fy, "2022", "클라우드",    round(4000 * g), restated),
        ]

    return rows


# 이 픽스처가 기대하는 정답 매핑 (eval 용 gold).
NAVER_GOLD_EDGES = [
    ({"서치플랫폼"}, {"검색플랫폼"}, "rename"),
    ({"비즈니스플랫폼", "쇼핑"}, {"커머스"}, "merge"),
    ({"핀테크"}, {"핀테크"}, "identity"),
    ({"콘텐츠"}, {"콘텐츠"}, "identity"),
    ({"클라우드"}, {"클라우드"}, "identity"),
]
