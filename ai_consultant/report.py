"""Fact pack 렌더러 — synthesis 결과(dict)를 마크다운/HTML fact pack으로 조립."""
from __future__ import annotations
import html
from datetime import datetime, timezone


def render_markdown(company: str, topic: str, synth: dict, critic: dict,
                    stats: dict, financials_md: str, recon: dict | None = None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        f"# {company} — {topic} · 1차 Fact Pack",
        f"_generated {now} · Evidence-grounded multi-agent research assistant_",
        "",
        f"> 근거 통계: verified **{stats.get('verified',0)}** · weak {stats.get('weak',0)} · "
        f"unsupported(제외) {stats.get('unsupported',0)} · 총 claim {stats.get('total',0)} · "
        f"소스 {stats.get('sources',0)}건 (DART {stats.get('dart_sources',0)} / News {stats.get('news_sources',0)}) · "
        f"시점 timeline {stats.get('timelines',0)} · 소스충돌 {stats.get('conflicts',0)}",
        "",
        "## 1. Executive Summary",
        synth.get("executive_summary", "_(없음)_"),
        "",
        "## 2. Issue Tree",
        synth.get("issue_tree_md", "_(없음)_"),
        "",
        "## 3. 시점·소스 정합 (Timeline & Conflicts)",
        synth.get("timeline_md", "_(없음)_"),
        "",
        _recon_detail_md(recon),
        "## 4. Evidence Table",
        synth.get("evidence_table_md", "_(없음)_"),
        "",
        "## 5. 핵심 재무 (정형 · DART 주요계정)",
        financials_md or "_(없음)_",
        "",
        "## 6. Order & Backlog",
        synth.get("order_backlog_md", "_(없음)_"),
        "",
        "## 7. Strategic Outlook",
        synth.get("strategic_outlook_md", "_(없음)_"),
        "",
        "## 8. Risks & Open Questions",
        synth.get("risks_open_questions_md", "_(없음)_"),
        "",
        "## 9. Next Research Agenda",
        synth.get("next_research_agenda_md", "_(없음)_"),
        "",
        "## 10. Critic Review (self-critique)",
        _critic_md(critic),
    ]
    return "\n".join(parts)


def _recon_detail_md(recon: dict | None) -> str:
    """소스 충돌·교차노트를 표로 (synthesis의 timeline_md를 보강)."""
    if not recon:
        return ""
    out = []
    conflicts = recon.get("conflicts", [])
    if conflicts:
        out += ["**소스 간 충돌 / 시점 차이**", "", "| 종류 | 주제 | 내용 |", "|---|---|---|"]
        for c in conflicts[:12]:
            out.append(f"| {c.get('kind','')} | {c.get('topic','')} | {c.get('description','')} |")
        out.append("")
    notes = recon.get("cross_source_notes", [])
    if notes:
        out.append("**교차 소스 노트** (공시↔뉴스 상호보강/공백)")
        out += [f"- {n}" for n in notes[:6]]
        out.append("")
    return "\n".join(out)


def _critic_md(critic: dict) -> str:
    if not critic:
        return "_(없음)_"
    lines = ["| Where | Problem | Fix | Severity |", "|---|---|---|---|"]
    for it in critic.get("issues_found", []):
        lines.append(f"| {it.get('where','')} | {it.get('problem','')} | {it.get('fix','')} | {it.get('severity','')} |")
    note = critic.get("overall_note", "")
    return "\n".join(lines) + (f"\n\n**총평:** {note}" if note else "")


_HTML_SHELL = """<!doctype html><html lang=ko><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;max-width:1000px;
margin:0 auto;padding:32px 20px 80px;line-height:1.65;color:#17202a;background:#f6f7f9}}
h1{{color:#14213d}}h2{{color:#17324d;border-bottom:2px solid #d9e0ea;padding-bottom:6px;margin-top:34px}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;background:#fff}}
th,td{{border:1px solid #d9e0ea;padding:7px 9px;text-align:left;vertical-align:top}}
th{{background:#f1f5f9}}code{{background:#f0fdf4;padding:1px 5px;border-radius:4px}}
blockquote{{background:#eef5ff;border-left:4px solid #2563eb;padding:10px 14px;margin:14px 0}}
.wrap{{background:#fff;border:1px solid #d9e0ea;border-radius:10px;padding:26px 30px}}
</style></head><body><div class=wrap>{body}</div></body></html>"""


def markdown_to_html(md: str, title: str) -> str:
    """아주 가벼운 md→html (헤딩/표/blockquote/리스트/굵게). 데모용."""
    import re
    lines = md.split("\n")
    out: list[str] = []
    in_table = False
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>"); in_list = False

    def flush_table_end():
        nonlocal in_table
        if in_table:
            out.append("</table>"); in_table = False

    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("|") and "|" in ln.strip()[1:]:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            is_sep = all(set(c) <= {"-", ":", " "} and c for c in cells)
            if not in_table:
                out.append("<table>"); in_table = True
            if is_sep:
                i += 1; continue
            tag = "th" if (i + 1 < len(lines) and set(lines[i+1].strip()) <= set("|-: ")) else "td"
            row = "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells)
            out.append(f"<tr>{row}</tr>")
            i += 1; continue
        flush_table_end()
        if ln.startswith("### "):
            close_list(); out.append(f"<h3>{_inline(ln[4:])}</h3>")
        elif ln.startswith("## "):
            close_list(); out.append(f"<h2>{_inline(ln[3:])}</h2>")
        elif ln.startswith("# "):
            close_list(); out.append(f"<h1>{_inline(ln[2:])}</h1>")
        elif ln.startswith("> "):
            close_list(); out.append(f"<blockquote>{_inline(ln[2:])}</blockquote>")
        elif ln.strip().startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{_inline(ln.strip()[2:])}</li>")
        elif ln.strip() == "":
            close_list(); out.append("")
        else:
            close_list(); out.append(f"<p>{_inline(ln)}</p>")
        i += 1
    flush_table_end(); close_list()
    return _HTML_SHELL.format(title=html.escape(title), body="\n".join(out))


def _inline(s: str) -> str:
    import re
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"_(.+?)_", r"<em>\1</em>", s)
    return s
