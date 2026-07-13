"""Resume a run from saved 06_verified_claims.json — re-runs Reconciler→Gap→Synthesis→Critic→render.

Cheap iteration on the post-verification stages without re-extracting/verifying hundreds of claims.
  python scripts/resume_from_verified.py outputs/demo "한화오션" "2026년 수주잔고 흐름 및 향후 사업 전망"
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_consultant.schemas import Claim, Issue
from ai_consultant.agents import reconciler, gap_finder, synthesis, critic
from ai_consultant import report, financials as finmod
from datetime import datetime, timezone

D = Path(sys.argv[1]); company = sys.argv[2]; topic = sys.argv[3]
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
L = lambda f: json.load(open(D / f))

issues = [Issue(i["issue_id"], i["question"], i["hypothesis"], i.get("sub_questions", []),
                i.get("source_plan", [])) for i in L("01_issue_tree.json")]
verified = [Claim(**c) for c in L("06_verified_claims.json")]
fin = L("03a_financials.json"); fin_md, _ = finmod.summarize(fin["rows"])
n_ver = sum(1 for c in verified if c.verification == "verified")
n_weak = sum(1 for c in verified if c.verification == "weak")
n_unsup = sum(1 for c in verified if c.verification == "unsupported")
src = L("03_sources.json")
n_dart = sum(1 for s in src if s["source_type"] == "DART")
n_news = sum(1 for s in src if s["source_type"] == "News")

print("Reconciler…")
recon = reconciler.run(company, verified, today=today)
json.dump(recon, open(D / "07_reconciliation.json", "w"), ensure_ascii=False, indent=2)
print(f"  timelines {len(recon['timelines'])} · conflicts {len(recon['conflicts'])} · notes {len(recon['cross_source_notes'])}")

print("Gap Finder…")
gaps = gap_finder.run(issues, verified)
json.dump([g.__dict__ for g in gaps], open(D / "08_gaps.json", "w"), ensure_ascii=False, indent=2)

print("Synthesis…")
synth = synthesis.run(company, topic, issues, verified, gaps, fin_md, recon)
json.dump(synth, open(D / "09_synthesis.json", "w"), ensure_ascii=False, indent=2)

stats = {"verified": n_ver, "weak": n_weak, "unsupported": n_unsup, "total": len(verified),
         "sources": len(src), "dart_sources": n_dart, "news_sources": n_news,
         "timelines": len(recon["timelines"]), "conflicts": len(recon["conflicts"])}
draft = report.render_markdown(company, topic, synth, {}, stats, fin_md, recon)
print("Critic…")
crit = critic.run(draft, n_ver, n_weak, n_unsup)
json.dump(crit, open(D / "10_critic.json", "w"), ensure_ascii=False, indent=2)

final = report.render_markdown(company, topic, synth, crit, stats, fin_md, recon)
(D / "fact_pack.md").write_text(final, encoding="utf-8")
(D / "fact_pack.html").write_text(report.markdown_to_html(final, f"{company} Fact Pack"), encoding="utf-8")
print("done →", D)
