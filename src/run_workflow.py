#!/usr/bin/env python
"""
Run the Math Conjecturer workflow from the command line.

Usage:
  python run_workflow.py <arxiv_id> [arxiv_id ...]  [--auto] [--phase2-only]

Examples:
  python run_workflow.py 2512.01868
  python run_workflow.py 2512.01868 2501.00123 --auto
  python run_workflow.py 2512.01868 --phase2-only
  python run_workflow.py 2512.01868 2501.00123 --auto --phase2-only
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Disable LangSmith tracing to avoid noisy errors
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from workflow.phase1 import build_phase1_workflow
from workflow.phase2 import run_phase2_workflow
from nodes.phase1 import critic_node, revision_node, mechanism_node
from utils.paths import PAPERS_DIR


def run_phase1(arxiv_id: str, max_revisions: int = 10, auto: bool = False):
    """Run Phase 1 workflow and return final state.

    auto=True: silently runs revisions up to max_revisions without prompting,
               accepts the result automatically.
    """
    print(f"\n{'='*60}")
    print(f"PHASE 1: Processing arXiv paper {arxiv_id}")
    if auto:
        print("  [auto mode — no interactive prompts]")
    print(f"{'='*60}\n")

    phase1_app = build_phase1_workflow()
    initial_state = {
        "arxiv_id": arxiv_id,
        "tex": "",
        "summary": "",
        "iteration": 1,
    }
    print("Running initial pipeline: ingest → summarize → critic → mechanism...")
    state = phase1_app.invoke(initial_state)

    if auto:
        # Run revisions automatically until PASS or max_revisions exhausted
        for rev in range(max_revisions):
            if state.get("critic_status") == "PASS":
                print(f"\n  Summary approved by critic after {rev} revision(s).")
                break
            print(f"\n--- Auto-revision {rev + 1}/{max_revisions} ---")
            state = revision_node(state)
            state = critic_node(state)
        else:
            print(f"\n  Reached max revisions ({max_revisions}). Accepting current summary.")
    else:
        # Interactive critic loop
        iteration = 1
        while iteration <= max_revisions:
            print(f"\n{'='*60}")
            print(f"ITERATION {iteration}")
            print(f"{'='*60}")

            print(f"\n--- SUMMARY ---")
            print(state.get("summary", "No summary"))

            print(f"\n--- CRITIC EVALUATION ---")
            print(f"Status: {state.get('critic_status', 'UNKNOWN')}")
            print(state.get("critique", "No critique"))

            if state.get("critic_status") == "PASS":
                print("\n✅ Summary APPROVED by critic!")
                break

            print(f"\n--- DECISION ---")
            print("The critic found issues. What would you like to do?")
            print("  [c] Continue refinement")
            print("  [a] Accept current summary")
            print("  [q] Quit")

            choice = input("\nYour choice (c/a/q): ").strip().lower()

            if choice == 'q':
                print("Quitting...")
                sys.exit(0)
            elif choice == 'a':
                print("Accepting current summary.")
                break
            elif choice == 'c':
                iteration += 1
                print(f"\n--- Running Revision {iteration} ---")
                state = revision_node(state)
                state = critic_node(state)
            else:
                print("Invalid choice, please enter c, a, or q")

    # Re-run mechanism if revised
    if state.get("iteration", 1) > 1:
        print("\n--- Re-extracting mechanism from revised summary ---")
        state = mechanism_node(state)

    print(f"\n{'='*60}")
    print("PHASE 1 COMPLETE")
    print(f"{'='*60}")
    print(f"Final iteration: {state.get('iteration', 1)}")
    print(f"Critic status: {state.get('critic_status', 'UNKNOWN')}")

    return state


def run_phase2(phase1_state: dict, num_proposals: int = 2):
    """Run Phase 2 workflow, generating 2 proposals."""
    print(f"\n{'='*60}")
    print("PHASE 2: Open Problem Formulation (2 Proposals)")
    print(f"{'='*60}\n")

    result = run_phase2_workflow(
        summary=phase1_state["summary"],
        mechanism=phase1_state["mechanism"],
        arxiv_id=phase1_state.get("arxiv_id"),
        num_proposals=num_proposals,
    )

    print(f"\n{'='*60}")
    print("PHASE 2 COMPLETE")
    print(f"{'='*60}")
    proposals = result.get("proposals", [])
    for p in proposals:
        print(
            f"  Proposal {p['proposal_num']}: "
            f"PS={p.get('ps_score', 0)}/5 | PI={p.get('pi_score', 0)}/5"
        )

    return result


def load_phase1_outputs(arxiv_id: str) -> dict:
    """Load existing Phase 1 outputs from papers directory."""
    papers_dir = PAPERS_DIR / arxiv_id

    # Try to load summary
    summary_dir = papers_dir / "step2_summary"
    summary = ""
    if summary_dir.exists():
        # Get the latest iteration
        summary_files = sorted(summary_dir.glob("iteration_*.md"), reverse=True)
        if summary_files:
            summary = summary_files[0].read_text(encoding="utf-8")
            print(f"Loaded summary from {summary_files[0]}")

    # Try to load mechanism
    mechanism_file = papers_dir / "step3_mechanism" / "mechanism.xml"
    mechanism = ""
    if mechanism_file.exists():
        mechanism = mechanism_file.read_text(encoding="utf-8")
        print(f"Loaded mechanism from {mechanism_file}")

    if not summary or not mechanism:
        raise FileNotFoundError(
            f"Phase 1 outputs not found in {papers_dir}. "
            "Run without --phase2-only first."
        )

    return {
        "arxiv_id": arxiv_id,
        "summary": summary,
        "mechanism": mechanism,
    }


def _wrap_loose_math(content: str) -> str:
    """
    Wrap LaTeX math tokens that appear outside $...$ or $$...$$ delimiters.
    Uses a single combined regex (ordered most-specific first) so each token
    position is matched exactly once — no double-wrapping.
    """
    # One level of nested braces: {stuff} or {\cmd{inner}}
    _ARG = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'

    GREEK  = (r'alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|'
              r'iota|kappa|lambda|mu|nu|xi|pi|varpi|rho|varrho|sigma|varsigma|tau|'
              r'upsilon|phi|varphi|chi|psi|omega|'
              r'Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega')
    MATHOP = (r'le|ge|leq|geq|neq|approx|sim|simeq|cong|equiv|'
              r'to|rightarrow|leftarrow|leftrightarrow|Rightarrow|Leftarrow|'
              r'Leftrightarrow|mapsto|'
              r'in|notin|ni|subset|subseteq|supset|supseteq|cup|cap|setminus|emptyset|'
              r'infty|partial|nabla|forall|exists|'
              r'cdot|times|otimes|oplus|wedge|vee|neg|pm|mp|div|'
              r'perp|mid|parallel|ell|ldots|cdots|vdots|ddots')
    MATHFN = (r'sum|prod|int|iint|iiint|oint|lim|limsup|liminf|'
              r'max|min|sup|inf|det|tr|dim|ker|gcd|Pr|arg|deg|'
              r'log|ln|exp|sin|cos|tan|cot|sec|csc|arcsin|arccos|arctan|'
              r'Lip|diam')
    MATHFONT = r'mathrm|mathbb|mathcal|mathbf|mathit|boldsymbol'
    ACCENT   = r'vec|tilde|hat|bar|dot|ddot|overline|underline|widehat|widetilde|overrightarrow'

    # Combined pattern — ordered from MOST specific to LEAST specific
    COMBINED = re.compile(
        r'(?<!\$)'   # not already preceded by $
        r'('
        # 1. \frac{a}{b} and \binom{a}{b}
        r'\\(?:frac|tfrac|dfrac|binom)' + _ARG + _ARG +
        r'|'
        # 2. \sqrt{a}, \mathXX{a}, \accent{a}  — commands that take one {arg}
        r'\\(?:sqrt|' + MATHFONT + r'|' + ACCENT + r')' + _ARG +
        r'(?:' + _ARG + r')?'       # optional second arg (e.g. \sqrt[n]{x})
        r'|'
        # 3. letter with subscript/superscript, potentially nested: t_{\mathrm{ls}}
        r'[a-zA-Z](?:_' + _ARG + r'|_[a-zA-Z0-9]|\^' + _ARG + r'|\^[*+\-a-zA-Z0-9])+'
        r'|'
        # 4. Standalone \command  (Greek, operators, functions — no braces)
        r'\\(?:' + GREEK + r'|' + MATHOP + r'|' + MATHFN + r')(?![a-zA-Z{])'
        r')'
        r'(?!\$)'    # not already followed by $
    )

    def fix_segment(seg: str) -> str:
        return COMBINED.sub(r'$\1$', seg)

    result_lines = []
    in_display_block = False

    for line in content.split('\n'):
        stripped = line.strip()
        if stripped == '$$':
            in_display_block = not in_display_block
            result_lines.append(line)
            continue
        if in_display_block:
            result_lines.append(line)
            continue
        if not stripped or stripped.startswith('#') or stripped.startswith('|') or stripped == '---':
            result_lines.append(line)
            continue

        # Split by existing $...$ regions; fix only the non-math segments
        parts = re.split(r'(\$[^$\n]*?\$)', line)
        result_lines.append(''.join(
            part if k % 2 == 1 else fix_segment(part)
            for k, part in enumerate(parts)
        ))

    return '\n'.join(result_lines)


def generate_full_report(arxiv_id: str, phase2_proposals: list) -> Path:
    """Assemble all outputs into a single labelled full_report.md."""
    papers_dir = PAPERS_DIR / arxiv_id
    out_path = papers_dir / "full_report.md"

    lines = []
    lines += [
        f"# Math Conjecturer — Full Report",
        f"",
        f"**arXiv ID:** {arxiv_id}  ",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        "---",
        "",
    ]

    # --- Paper Summary ---
    summary_files = sorted((papers_dir / "step2_summary").glob("iteration_*.md"), reverse=True)
    if summary_files:
        lines += ["## Paper Summary", ""]
        lines.append(summary_files[0].read_text(encoding="utf-8").strip())
        lines += ["", "---", ""]

    # --- Research Agenda ---
    agenda_path = papers_dir / "step4_open_problems" / "4a_agenda" / "agenda.md"
    if agenda_path.exists():
        lines += ["## Research Agenda", ""]
        lines.append(agenda_path.read_text(encoding="utf-8").strip())
        lines += ["", "---", ""]

    # --- Expert R1 Surveys ---
    experts_dir = papers_dir / "step4_open_problems" / "4b_experts"
    r1_files = sorted(experts_dir.glob("expert_*_r1_survey.json")) if experts_dir.exists() else []
    if r1_files:
        lines += ["## Expert Literature Surveys (Round 1)", ""]
        for f in r1_files:
            survey = json.loads(f.read_text(encoding="utf-8"))
            subfield = survey.get("subfield", f.stem)
            lines += [f"### Expert — {subfield}", ""]
            for key, label in [
                ("paper_connections", "Paper Connections"),
                ("state_of_the_art",  "State of the Art"),
                ("open_territory",    "Open Territory"),
                ("cross_field_bridges", "Cross-Field Bridges"),
            ]:
                val = survey.get(key, "")
                if val:
                    lines += [f"**{label}:** {val}", ""]
            landmarks = survey.get("landmark_results", [])
            if landmarks:
                lines += ["**Landmark Results:**", ""]
                lines += [f"- {r}" for r in landmarks]
                lines.append("")
            settled = survey.get("settled_claims", [])
            if settled:
                lines += ["**Settled Claims (Forbidden List):**", ""]
                lines += [f"- {s}" for s in settled]
                lines.append("")
            techniques = survey.get("available_techniques", [])
            if techniques:
                lines += ["**Available Techniques:**", ""]
                lines += [f"- {t}" for t in techniques]
                lines.append("")
        lines += ["---", ""]

    # --- Expert R2 Proposals ---
    r2_files = sorted(experts_dir.glob("expert_*_r2_proposal.json")) if experts_dir.exists() else []
    r2_critique_files = {
        f.stem.replace("_r2_critique", ""): f
        for f in experts_dir.glob("expert_*_r2_critique.json")
    } if experts_dir.exists() else {}

    if r2_files:
        lines += ["## Expert Proposals (Round 2)", ""]
        for f in r2_files:
            entry = json.loads(f.read_text(encoding="utf-8"))
            subfield = entry.get("subfield", f.stem)
            proposals_list = entry.get("proposals", [])
            expert_idx = entry.get("expert_index")
            lines += [f"### Expert — {subfield}", ""]

            # Fetch matching critique
            critique_key = f"expert_{expert_idx}"
            critique_path = r2_critique_files.get(critique_key)
            critique = json.loads(critique_path.read_text(encoding="utf-8")) if critique_path else {}
            verdicts = {v["proposal_index"]: v for v in critique.get("verdicts", [])}

            for i, p in enumerate(proposals_list):
                verdict = verdicts.get(i, {})
                approved = verdict.get("approved", True)
                status = "APPROVED" if approved else "REJECTED"
                lines += [
                    f"#### Proposal {i+1}: {p.get('title', 'Untitled')}  _{status}_",
                    "",
                    f"**Problem Statement:** {p.get('problem_statement', '')}",
                    "",
                    f"**Potential Impact:** {p.get('potential_impact', '')}",
                    "",
                ]
                blocking = verdict.get("blocking_issues", [])
                suggestions = verdict.get("suggestions", [])
                if blocking:
                    lines += ["**Blocking Issues:**"] + [f"- {b}" for b in blocking] + [""]
                if suggestions:
                    lines += ["**Suggestions:**"] + [f"- {s}" for s in suggestions] + [""]

            summary = critique.get("summary", "")
            if summary:
                lines += [f"**Critic Summary:** {summary}", ""]

        lines += ["---", ""]

    # --- Proposal Ranking ---
    ranking_path = experts_dir / "proposal_ranking.json" if experts_dir.exists() else None
    if ranking_path and ranking_path.exists():
        ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
        lines += ["## Proposal Ranking", ""]
        for rank, title in enumerate(ranking.get("ranked_titles", []), 1):
            lines.append(f"{rank}. {title}")
        lines += ["", f"**Rationale:** {ranking.get('ranking_rationale', '')}", "", "---", ""]

    # --- Finalized Proposals ---
    lines += ["## Finalized Proposals", ""]
    for p in phase2_proposals:
        num = p.get("proposal_num", "?")
        subfield = p.get("subfield", "?")
        title = p.get("title", "Untitled")
        ps = p.get("ps_score", 0)
        pi = p.get("pi_score", 0)

        lines += [
            f"### Proposal {num}: {title}",
            "",
            f"**Subfield:** {subfield}  ",
            f"**Scores:** Problem Statement = {ps}/5 | Potential Impact = {pi}/5",
            "",
        ]

        # Final report
        report_path = papers_dir / "step4_open_problems" / f"proposal_{num}" / "final_report.md"
        if report_path.exists():
            lines.append(report_path.read_text(encoding="utf-8").strip())
            lines.append("")

        # Quality assessment detail
        qa_path = papers_dir / "step4_open_problems" / f"proposal_{num}" / "quality_assessment.json"
        if qa_path.exists():
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            ps_block = qa.get("problem_statement", {})
            pi_block = qa.get("potential_impact", {})
            lines += [
                "#### Quality Assessment",
                "",
                "| Criterion | Score |",
                "|-----------|-------|",
                f"| Coherence | {ps_block.get('ps_coherence', '?')}/5 |",
                f"| Motivation from paper | {ps_block.get('ps_motivation', '?')}/5 |",
                f"| Clarity of formulation | {ps_block.get('ps_derivation', '?')}/5 |",
                f"| Conceptual depth | {ps_block.get('ps_depth', '?')}/5 |",
                f"| Novelty | {pi_block.get('pi_novelty', '?')}/5 |",
                f"| Field advancement | {pi_block.get('pi_advancement', '?')}/5 |",
                f"| Publication potential | {pi_block.get('pi_publication', '?')}/5 |",
                "",
            ]
            justification = qa.get("justification", "")
            if justification:
                lines += [f"**Justification:** {justification}", ""]
            strengths = qa.get("strengths", [])
            if strengths:
                lines += ["**Strengths:**", ""] + [f"- {s}" for s in strengths] + [""]
            weaknesses = qa.get("weaknesses", [])
            if weaknesses:
                lines += ["**Weaknesses:**", ""] + [f"- {w}" for w in weaknesses] + [""]

        lines += ["---", ""]

    content = "\n".join(lines)

    # Step 1: normalise delimiter styles → $...$ and $$...$$
    # Trim spaces immediately inside \(...\) so pandoc sees $x$ not $ x $
    content = re.sub(r'\\\[\s*', '$$\n', content)
    content = re.sub(r'\s*\\\]', '\n$$', content)
    content = re.sub(r'\\\(\s*', '$', content)
    content = re.sub(r'\s*\\\)', '$', content)

    # Convert raw LaTeX display environments to $$...$$ blocks
    # Leading \n ensures $$ always ends up on its own line (so _wrap_loose_math detects it)
    for env in ('equation', 'equation*', 'align', 'align*', 'gather', 'gather*'):
        content = re.sub(
            r'\\begin\{' + re.escape(env) + r'\}([\s\S]*?)\\end\{' + re.escape(env) + r'\}',
            lambda m: '\n$$\n' + m.group(1).strip() + '\n$$\n',
            content,
        )

    # Strip $...$ delimiters from inside $$...$$ blocks (already in display math)
    def _clean_display_block(m: re.Match) -> str:
        inner = re.sub(r'\$([^$]*)\$', r'\1', m.group(1))
        return '$$\n' + inner.strip() + '\n$$'
    content = re.sub(r'\$\$([\s\S]*?)\$\$', _clean_display_block, content)

    # Step 2: wrap any bare LaTeX math tokens that are still outside $...$
    content = _wrap_loose_math(content)

    out_path.write_text(content, encoding="utf-8")
    print(f"\n  > Full report saved to papers/{arxiv_id}/full_report.md")

    # Generate LaTeX via pandoc
    tex_path = out_path.with_suffix(".tex")
    pdf_path = out_path.with_suffix(".pdf")
    try:
        subprocess.run(
            [
                "pandoc", str(out_path),
                "--from", "markdown+tex_math_dollars",
                "--to", "latex",
                "--standalone",
                "--output", str(tex_path),
                "--variable", "geometry:margin=2.5cm",
                "--variable", "fontsize=11pt",
                "--variable", "documentclass=article",
                "--variable", "colorlinks=true",
            ],
            check=True,
            capture_output=True,
        )
        print(f"  > LaTeX report saved to papers/{arxiv_id}/full_report.tex")
    except subprocess.CalledProcessError as e:
        print(f"  WARNING: pandoc failed — {e.stderr.decode().strip()}")
        return out_path
    except FileNotFoundError:
        print("  WARNING: pandoc not found — skipping .tex/.pdf generation")
        return out_path

    # Compile to PDF via pdflatex (run twice for correct cross-references)
    try:
        compile_args = [
            "pdflatex",
            "-interaction=nonstopmode",
            f"-output-directory={papers_dir}",
            str(tex_path),
        ]
        subprocess.run(compile_args, check=True, capture_output=True, cwd=papers_dir)
        subprocess.run(compile_args, check=True, capture_output=True, cwd=papers_dir)
        print(f"  > PDF report saved to papers/{arxiv_id}/full_report.pdf")
    except subprocess.CalledProcessError as e:
        print(f"  WARNING: pdflatex failed — check full_report.tex for errors")
    except FileNotFoundError:
        print("  WARNING: pdflatex not found — skipping PDF generation")
    finally:
        # Clean up pdflatex auxiliary files
        for ext in (".aux", ".log", ".out", ".toc"):
            p = pdf_path.with_suffix(ext)
            if p.exists():
                p.unlink()

    return out_path


def _print_proposals(proposals: list) -> None:
    for p in proposals:
        print("\n" + "="*60)
        print(f"PROPOSAL {p['proposal_num']} OUTPUT")
        print("="*60)
        print(f"\n--- Title ---")
        print(f"[{p.get('subfield', '?')}] {p.get('title', 'N/A')}")
        print(f"\n--- Report ---")
        print(p.get("final_report", "No report"))
        print(f"\n--- Quality Assessment ---")
        assessment = p.get("quality_assessment", {})
        print(f"Problem Statement:  coherence={assessment.get('ps_coherence','N/A')} "
              f"motivation={assessment.get('ps_motivation','N/A')} "
              f"derivation={assessment.get('ps_derivation','N/A')} "
              f"depth={assessment.get('ps_depth','N/A')}")
        print(f"Potential Impact:   novelty={assessment.get('pi_novelty','N/A')} "
              f"advancement={assessment.get('pi_advancement','N/A')} "
              f"publication={assessment.get('pi_publication','N/A')}")
        print(f"Section scores: PS={p.get('ps_score',0)}/5 | PI={p.get('pi_score',0)}/5")


def run_single_paper(arxiv_id: str, auto: bool, phase2_only: bool) -> dict:
    """Run the full pipeline for one arXiv ID. Returns a result summary dict."""
    if phase2_only:
        print(f"\n{'='*60}")
        print(f"Loading Phase 1 outputs for {arxiv_id}")
        print(f"{'='*60}\n")
        phase1_state = load_phase1_outputs(arxiv_id)
    else:
        phase1_state = run_phase1(arxiv_id, auto=auto)

        if not auto:
            print("\n" + "="*60)
            print("PHASE 1 OUTPUTS")
            print("="*60)
            print("\n--- FINAL SUMMARY ---")
            print(phase1_state.get("summary", "No summary"))
            print("\n--- MECHANISM (XML) ---")
            print(phase1_state.get("mechanism", "No mechanism"))

            print(f"\n{'='*60}")
            print("PHASE 2: Open Problem Formulation")
            print(f"{'='*60}")
            print("\nWould you like to proceed to Phase 2?")
            print("  [y] Yes, run Phase 2")
            print("  [n] No, exit")
            choice = input("\nYour choice (y/n): ").strip().lower()
            if choice != 'y':
                print(f"Exiting. Files saved to papers/{arxiv_id}/")
                return {"arxiv_id": arxiv_id, "skipped": True}

    phase2_result = run_phase2(phase1_state)
    proposals = phase2_result.get("proposals", [])

    _print_proposals(proposals)

    print("\n" + "="*60)
    print(f"SUMMARY — {arxiv_id}")
    print("="*60)
    for p in proposals:
        print(f"  Proposal {p['proposal_num']}: "
              f"PS={p.get('ps_score',0)}/5 | PI={p.get('pi_score',0)}/5")
    print(f"\nFiles saved to papers/{arxiv_id}/")

    generate_full_report(arxiv_id, proposals)

    return {
        "arxiv_id": arxiv_id,
        "proposals": [
            {
                "num": p["proposal_num"],
                "title": p.get("title", ""),
                "ps_score": p.get("ps_score", 0),
                "pi_score": p.get("pi_score", 0),
            }
            for p in proposals
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Math Conjecturer — generate research proposals from arXiv papers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python run_workflow.py 2512.01868\n"
            "  uv run python run_workflow.py 2512.01868 2501.00123 --auto\n"
            "  uv run python run_workflow.py 2512.01868 --phase2-only\n"
            "  uv run python run_workflow.py 2512.01868 2501.00123 --auto --phase2-only"
        ),
    )
    parser.add_argument(
        "arxiv_ids",
        nargs="+",
        metavar="arxiv_id",
        help="One or more arXiv IDs to process.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Non-interactive mode: run revisions automatically and proceed to Phase 2 without prompting.",
    )
    parser.add_argument(
        "--phase2-only",
        action="store_true",
        help="Skip Phase 1 and load existing outputs from papers/<arxiv_id>/.",
    )
    args = parser.parse_args()

    batch = len(args.arxiv_ids) > 1
    results = []

    for arxiv_id in args.arxiv_ids:
        if batch:
            print(f"\n{'#'*60}")
            print(f"# PAPER: {arxiv_id}")
            print(f"{'#'*60}")
        try:
            result = run_single_paper(arxiv_id, auto=args.auto, phase2_only=args.phase2_only)
            results.append(result)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            sys.exit(1)
        except Exception as e:
            print(f"\nERROR processing {arxiv_id}: {e}")
            results.append({"arxiv_id": arxiv_id, "error": str(e)})
            if not batch:
                sys.exit(1)
            # In batch mode, continue with the remaining papers

    if batch:
        print(f"\n{'='*60}")
        print("BATCH COMPLETE")
        print(f"{'='*60}")
        for r in results:
            aid = r["arxiv_id"]
            if "error" in r:
                print(f"  {aid}  FAILED — {r['error']}")
            elif r.get("skipped"):
                print(f"  {aid}  skipped (user declined Phase 2)")
            else:
                for p in r.get("proposals", []):
                    print(f"  {aid}  Proposal {p['num']}: "
                          f"PS={p['ps_score']}/5 | PI={p['pi_score']}/5  {p['title'][:60]}")


if __name__ == "__main__":
    main()
