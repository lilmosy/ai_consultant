"""중간 산출물 기록기 — 각 단계(agent)가 무엇을 냈는지, 어떤 한계가 있었는지 파일로 남긴다."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

from .schemas import to_jsonable


class RunArtifacts:
    def __init__(self, base: str | Path, run_id: str):
        self.dir = Path(base) / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.log_lines: list[str] = []
        self.stage_notes: list[dict] = []

    def write_json(self, name: str, obj) -> Path:
        p = self.dir / name
        p.write_text(json.dumps(to_jsonable(obj), ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    def write_text(self, name: str, text: str) -> Path:
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p

    def log(self, msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}"
        self.log_lines.append(line)
        print(line, flush=True)

    def stage(self, name: str, produced: str, limitations: str = "") -> None:
        """각 단계 결과/한계를 RUN_LOG용으로 축적."""
        self.stage_notes.append({"stage": name, "produced": produced, "limitations": limitations})
        self.log(f"STAGE {name} — {produced}" + (f" | 한계: {limitations}" if limitations else ""))

    def finalize_run_log(self, header: dict) -> Path:
        md = [f"# RUN LOG — {self.run_id}", ""]
        md.append("## 실행 개요")
        for k, v in header.items():
            md.append(f"- **{k}**: {v}")
        md.append("")
        md.append("## 단계별 산출물 & 한계")
        md.append("")
        md.append("| 단계 | 산출물 | 관찰된 한계 |")
        md.append("|---|---|---|")
        for s in self.stage_notes:
            lim = s["limitations"].replace("\n", " ") or "—"
            md.append(f"| {s['stage']} | {s['produced'].replace(chr(10),' ')} | {lim} |")
        md.append("")
        md.append("## 원시 로그")
        md.append("```")
        md.extend(self.log_lines)
        md.append("```")
        return self.write_text("RUN_LOG.md", "\n".join(md))
