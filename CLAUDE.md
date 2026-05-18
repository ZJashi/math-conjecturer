# Math Conjecturer

Multi-agent LangGraph system that generates mathematical research proposals from arXiv papers.

## Quick Start

```bash
cd src
uv run python run_workflow.py <arxiv_id>

# Example
uv run python run_workflow.py 2512.01868

# Skip to Phase 2 (if Phase 1 already completed)
uv run python run_workflow.py 2512.01868 --phase2-only
```

## Architecture

```
src/
├── run_workflow.py     # CLI entry point
├── workflow/           # LangGraph workflow definitions
│   ├── phase1.py       # Paper processing workflow
│   └── phase2.py       # Open problem formulation workflow
├── nodes/              # LangGraph node implementations
│   ├── phase1/         # ingest, summarize, critic, revision, mechanism
│   └── phase2/         # brainstorm, critics, feedback, report, judge
├── schema/             # TypedDict state definitions
├── prompts/            # LLM prompts (organized by phase)
└── utils/              # openrouter.py (LLM client), ingest/ (paper processing)

papers/                 # Output directory (results per arxiv_id)
```

## Two-Phase Workflow

### Phase 1: Paper Processing
`ingest → summarize → critic → (revision loop) → mechanism`

- Downloads paper from arXiv, cleans LaTeX
- Generates summary with interactive critic feedback loop
- Extracts key research mechanisms (XML)

### Phase 2: Open Problem Formulation
`context → agenda → brainstormer → [4 parallel critics] → feedback → report → judge`

- Creates research agenda with 3-5 directions
- Brainstorms novel proposals with iterative refinement
- 4 parallel critics: sanity, example, reverse, obstruction
- Final report with quality score (0-100)

## Configuration

Create `src/.env`:
```
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=google/gemini-2.0-flash-001  # optional, defaults to free model
```

## Prompt Writing Rules

When editing any prompt in `src/prompts/`:

- **No journal names or publication venues** — never instruct the model to name specific journals (e.g., Inventiones, Annals of Probability) or speculate about where a result would be published. This is unprofessional and irrelevant to mathematical content.

## Output Structure

Results saved to `papers/{arxiv_id}/`:
- `step1_ingest/` - Processed LaTeX
- `step2_summary/` - Markdown summaries (iteration_N.md)
- `step2_critique/` - Critic feedback
- `step3_mechanism/` - Extracted mechanisms (XML)
- `step4_open_problems/` - Phase 2 outputs (agenda, proposals, report, assessment)
