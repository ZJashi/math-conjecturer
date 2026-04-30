# Math Conjecturer: A Multi-Agent System for Automated Mathematical Research Proposal Generation

## System Overview

Math Conjecturer is a multi-agent pipeline built on LangGraph that takes an arXiv paper identifier as input and autonomously produces novel, rigorously formulated mathematical research proposals. The system operates in two sequential phases. Phase 1 processes the raw paper into a structured knowledge representation. Phase 2 uses that representation to drive a panel of simulated field experts who survey the literature, propose open problems, subject them to peer critique, and distill the survivors into polished, scored research reports. All language model calls are routed through the OpenRouter API, defaulting to Google Gemini 2.0 Flash.

---

## Phase 1: Paper Processing

Phase 1 ingests a raw arXiv paper and produces two artifacts that serve as the shared knowledge base for all of Phase 2: a Markdown summary of the paper and a structured XML knowledge graph called the blackboard.

The Phase 1 workflow follows a linear chain: `ingest → summarize → critic → (revision loop) → mechanism`.

### Node 1.1 — Ingestion

**Role.** Downloads and preprocesses the LaTeX source of the paper from arXiv.

**Input.** An arXiv paper identifier (e.g., `2512.01868`).

**Process.** The node calls an internal ingestion pipeline that retrieves the paper's LaTeX source, cleans it, and returns it as a processable text document. This step handles all the messy realities of raw LaTeX: macro expansions, comment stripping, and normalization.

**Output.** A cleaned LaTeX document stored in the workflow state as `tex`, and written to disk at `papers/{arxiv_id}/step1_ingest/`.

---

### Node 1.2 — Summarizer

**Role.** Generates a structured Markdown summary of the paper's mathematical content.

**Input.** The cleaned LaTeX document from the ingestion node.

**Process.** The node sends the full paper text to the LLM with a prompt asking it to extract the key definitions, main theorems with their formal statements, proof ideas, technical obstructions, sharpness examples, and any explicit conjectures raised by the authors. The temperature is set low (0.1) to prioritize faithfulness over creativity. This is iteration 1 of the summary.

**Output.** A Markdown summary saved to `papers/{arxiv_id}/step2_summary/iteration_1.md` and stored in state as `summary`.

---

### Node 1.3 — Critic

**Role.** Evaluates the quality of the summary against the original paper and decides whether it needs revision.

**Input.** Both the original LaTeX document and the current summary.

**Process.** The node runs a separate LLM call with a critic prompt that compares the summary against the paper. It checks whether all key results are faithfully represented, whether technical detail is preserved, and whether any important limitations or conjectures were omitted. The response contains a structured verdict with the marker `**STATUS:** PASS` or `**STATUS:** NEEDS_REVISION`. The node parses this marker with a regular expression to extract the status. The critic runs at temperature 0.0 to produce deterministic evaluations.

**Output.** The critique text is saved to `papers/{arxiv_id}/step2_critique/iteration_N.md`. The state is updated with `critique` and `critic_status`.

**Control flow.** If `critic_status` is `NEEDS_REVISION`, the workflow routes to the revision node. If `PASS`, it proceeds to the mechanism node. This creates a feedback loop that can run for multiple iterations.

---

### Node 1.4 — Revision

**Role.** Revises the summary in response to the critic's specific feedback.

**Input.** The original LaTeX document, the previous summary, and the critic's detailed feedback.

**Process.** The node sends all three to the LLM with a revision prompt instructing it to address each point of feedback specifically rather than merely reformulating. Temperature is set to 0.4 to allow some generative flexibility. The iteration counter is incremented and the revised summary is saved as `iteration_N.md`.

**Output.** An updated `summary` in state and a new file `papers/{arxiv_id}/step2_summary/iteration_N.md`. Control returns to the critic node for re-evaluation.

---

### Node 1.5 — Mechanism Extractor

**Role.** Translates the finalized Markdown summary into a structured XML knowledge graph called the blackboard. This is the most architecturally important artifact in the entire system — it is the shared source of truth consumed by every node in Phase 2.

**Input.** The final approved Markdown summary.

**Process.** The node sends the summary to the LLM with a detailed schema prompt instructing it to decompose the paper's content into three hierarchical XML layers:

- **`<context>` — The Established Truth.** Contains `<definition>`, `<concept>`, `<theorem>`, `<lemma>`, and `<proposition>` elements. Each element has an `id`, a `title`, a `<content>` child with the formal LaTeX statement, and an `<impact>` child explaining its significance. These represent what the paper has proven.

- **`<motivation>` — The Friction.** Contains `<dissatisfaction>` elements, each representing a limitation, missing generalization, or weakened assumption relative to a result in `<context>`. Each dissatisfaction has a `source_refs` attribute pointing to the theorem IDs it is unsatisfied with. Critically, each dissatisfaction includes a `<desired_behavior>` (what should ideally be true), a `<heuristic>` (why the current proof fails to achieve it), a mandatory `<known_in_literature>` field (checked against the paper's own results, cited work, and the broader literature — writing "Open." only when genuinely uncertain), and an optional `<known_false>` field (included only when the paper explicitly disproves the desired behavior via a counterexample, lower bound, matching upper bound, or negative theorem). The prompt enforces that each independently improvable aspect of a theorem gets its own separate dissatisfaction node — for instance, "reduce the constant" and "remove the logarithmic dimension factor" are two distinct nodes, not one bundled node.

- **`<frontier>` — The Open Questions.** Contains `<raised_conjecture>` elements for open problems explicitly raised by the paper's authors. Each carries `<content>`, `<heuristic>`, `<impact>`, and a mandatory `<known_in_literature>` field applying the same literature check as dissatisfactions.

The `<known_false>` and non-"Open." `<known_in_literature>` fields are the primary mechanism by which Phase 2 is prevented from re-proposing things the paper already resolved. Every Phase 2 node is required to scan these fields before generating any proposal.

**Output.** The complete XML blackboard saved to `papers/{arxiv_id}/step3_mechanism/mechanism.xml` and stored in state as `mechanism`. Temperature is 0.0 for determinism.

---

## Phase 2: Expert-Driven Open Problem Formulation

Phase 2 takes the summary and mechanism XML from Phase 1 and runs a multi-stage expert simulation to generate and refine research proposals. It is structured as two sub-workflows run sequentially: the **Agenda Workflow** (proposal generation and vetting) and the **Finalization Workflow** (polishing and scoring, run once per selected proposal).

The overall agenda workflow follows this graph:

```
agenda_creator
    → [4x field_expert_r1 in parallel]
    → r2_sync
    → [4x field_expert_r2 in parallel]
    → r2_proposals_sync
    → [4x expert_r2_critic in parallel]
    → r2_critic_aggregate
    → [loop back to r2 or proceed]
    → expert_acceptance
    → problem_ranker
```

---

### Node 2.1 — Agenda Creator

**Role.** Strategic planning node. Identifies the most promising research directions emerging from the paper and assigns each of four expert agents to a distinct mathematical subfield.

**Input.** The paper summary and mechanism XML.

**Process.** The node sends both inputs to the LLM with a prompt framing it as a world-class research strategist. The prompt instructs the model to identify 3–5 high-level research directions that are grounded in the paper, specific enough to guide concrete problem formulation, genuinely open (not pointing at anything already proved, disproved, or known — cross-checked against `<known_false>` tags and `<known_in_literature>` fields in the mechanism XML), and mutually distinct. Simultaneously, it selects exactly 4 mathematical subfields — specific subdisciplines (e.g., "spectral theory of random matrices", "free probability theory") rather than topic keywords — to assign to the four parallel expert agents. Temperature is 0.8 to allow creative strategic thinking.

The response is parsed into an `AgendaResult` structured output with fields `research_directions` (a list of 3–5 strings), `subfields` (a list of exactly 4 strings), and `rationale`.

**Output.** `agenda` (the research directions) and `subfields` (the four expert subfield assignments) are written into state and saved as `step4_open_problems/4a_agenda/agenda.md` and `agenda.json`.

**Downstream effect.** All four expert agents fan out in parallel immediately after this node, each receiving `subfields[i]` as their identity and domain of expertise.

---

### Node 2.2 — Field Expert Round 1 (four parallel agents)

**Role.** Four parallel literature survey agents. Each expert conducts a deep, encyclopedic survey of the paper from the perspective of their assigned mathematical subfield. No proposals are made in this round — the sole output is a rich contextual map.

**Input.** The paper summary, mechanism XML, the research agenda, and the expert's assigned subfield.

**Process.** Each expert is given a system prompt that frames it as a world-class mathematician with encyclopedic knowledge of the literature in their subfield. The human prompt instructs it to produce six structured sections:

1. **Paper connections.** Which specific named results and techniques from the paper are directly relevant to the subfield, and what specialists would recognize as significant.

2. **State of the art.** Where the frontier in the subfield currently sits, naming major open conjectures (e.g., the Connes embedding conjecture, the Anderson paving problem) and what has been tried and failed.

3. **Landmark results.** A list of named theorems, conjectures, and results from the broader literature, each with author attribution and an explanation of relevance.

4. **Settled claims — the FORBIDDEN LIST.** The expert is instructed to scan the mechanism XML first: every `<dissatisfaction>` with a `<known_false>` child is added as `FALSE`, every `<dissatisfaction>` or `<raised_conjecture>` with a non-"Open." `<known_in_literature>` is added as `KNOWN` or `TRUE`. Then the expert adds what the paper proves directly (including lower and upper bounds that show a particular improvement is impossible), what the paper mentions as already known or refuted, and what the expert knows from the broader literature. This list is populated aggressively: over-inclusion is explicitly preferred over under-inclusion. Any claim on this list is forbidden as a downstream proposal.

5. **Available techniques.** Key methods from the subfield likely to be applicable, each named precisely (not "functional analysis" but "the Haagerup approximation property"), with provenance (author, paper, era) and an assessment of where the technique may break down.

6. **Cross-field bridges.** Specific connections between the subfield and other areas illuminated by this paper, naming theorems and authors on both sides.

The response is parsed into an `ExpertSurveyResult` structured output. Temperature is 0.8.

**Output.** Each expert appends one survey dictionary to the shared `expert_surveys_r1` list in state (accumulated via LangGraph's `operator.add` fan-in pattern). The survey is saved to `step4_open_problems/4b_experts/expert_{i}_r1_survey.json`. All four run concurrently; the `r2_sync` barrier node waits for all to complete before Round 2 begins.

---

### Node 2.3 — R2 Sync

**Role.** Barrier synchronization node. Does no computation — simply waits until all four R1 surveys are present in state before allowing Round 2 to begin.

**Output.** Empty dictionary (state unchanged). Prints a count of received surveys for diagnostic purposes.

---

### Node 2.4 — Field Expert Round 2 (four parallel agents)

**Role.** Four parallel proposal-writing agents. Each expert now has access to all four R1 surveys and writes exactly two precise, novel research proposals.

**Input.** The paper summary, mechanism XML, the research agenda, the expert's own R1 survey, and all other experts' R1 surveys.

**Process — first-time proposal writing.** The expert is given a detailed prompt that walks it through four mandatory steps before writing anything:

- **Step 0a — Mechanism XML scan.** Scan every `<dissatisfaction>` with `<known_false>` and every non-"Open." `<known_in_literature>` field in the mechanism XML. These are absolute bans on proposing anything equivalent to those desired behaviors. This check is independent of what the expert wrote in its R1 survey.

- **Step 0b — Settled claims check.** Read every `settled_claims` entry from its own R1 survey and all other experts' surveys. A proposal is forbidden if it asks to prove something TRUE, prove something FALSE, or is a direct logical consequence of a FALSE claim.

- **Step 1 — Novelty check.** Verify the problem is not already resolved by a result in `landmark_results` and that `open_territory` indicates genuine openness.

- **Step 2 — Precision check.** The problem statement must be a concrete mathematical claim — exact conditions, quantifiers, and a definite goal. Directional language such as "study the behavior of X" or "investigate whether Y" is explicitly disqualified.

- **Step 3 — Distinctness check.** The two proposals must be genuinely distinct from each other and from what other experts appear likely to propose based on their R1 surveys. Cross-field proposals are encouraged since diversity across all four experts is the primary goal.

- **Step 4 — Cross-field check.** Experts are encouraged to use insights from other experts' surveys to strengthen or enrich their proposals.

The output is parsed into an `ExpertProposalResult` structured output containing exactly two `SingleProposal` objects, each with a `title`, `problem_statement`, and `potential_impact`. Temperature is 0.7.

**Process — revision pass.** If the expert's previous R2 proposals were critiqued and at least one was rejected, the node uses a different revision prompt that presents the previous proposals alongside the critic's detailed feedback. Approved proposals must be reproduced verbatim. Rejected proposals must be substantively fixed — not merely rephrased — addressing each blocking issue. If the expert's proposals were already fully approved, it re-emits them unchanged without calling the LLM.

**Output.** Each expert appends one proposal dictionary to `expert_proposals_r2` (via `operator.add`). The state helper `get_latest_r2_proposals` always retrieves the most recent submission per expert, so the accumulated list serves as a revision history. Results saved to `step4_open_problems/4b_experts/expert_{i}_r2_proposal.json`.

---

### Node 2.5 — R2 Proposals Sync

**Role.** Second barrier synchronization node. Waits until all four Round 2 proposal sets are present in state before launching the critic pass.

**Output.** Empty dictionary. Prints a diagnostic count.

---

### Node 2.6 — Expert R2 Critic (four parallel agents)

**Role.** Four parallel peer-review agents. Each critic evaluates the two proposals written by its corresponding expert (critic 0 reviews expert 0's proposals, etc.) against that expert's own R1 survey as the authoritative benchmark.

**Input.** The paper summary, mechanism XML, the expert's R1 survey, and the expert's two R2 proposals.

**Process.** The critic applies five criteria in strict order. A single failure on any criterion is sufficient to reject a proposal:

- **Criterion 0 — Settled claims (automatic rejection).** Performed in two independent steps. Step 0a scans the mechanism XML directly — independently of the R1 survey — for `<known_false>` and non-"Open." `<known_in_literature>` tags. Any proposal equivalent to a forbidden desired behavior is rejected immediately, citing the XML element ID. Step 0b checks the expert's `settled_claims` list, and additionally applies the critic's own mathematical background knowledge as an independent check.

- **Criterion 1 — Novelty.** The critic checks whether the problem is resolved by any result in `landmark_results`, whether `open_territory` supports genuine openness, and applies its own knowledge of the field as a further check. Rejection requires naming the specific result that closes the problem — "this may be known" is not a valid blocking issue.

- **Criterion 2 — Precision (hard blocker).** The problem statement must be a concrete mathematical claim. Vague language ("investigate whether", "study the behavior of", "characterize the class of") is an unconditional blocking issue. The critic is explicitly instructed that "close but needs sharpening" does not pass; it must state exactly which object is undefined, which quantifier is absent, or what the precise goal should be.

- **Criterion 3 — Feasibility.** Does the proposal connect to specific techniques from `available_techniques` and acknowledge known obstructions from `open_territory`? This criterion rarely causes rejection alone but contributes to the suggestions list.

- **Criterion 4 — Grounding in the paper.** Does the proposal build on specific results from the paper rather than being merely loosely inspired by the topic area? Checked against the mechanism XML. If the connection to the paper's actual contributions is absent, this is flagged as a blocking issue.

Temperature is 0.3 for consistent and stringent evaluation. If R1 survey or R2 proposals are missing for a given expert, the critic auto-rejects both proposals.

**Output.** Each critic appends one critique result to `expert_r2_critiques` (via `operator.add`). Each critique contains two per-proposal verdicts, each with `approved`, `blocking_issues`, and `suggestions`, plus an `overall_approved` flag (true only if both proposals pass) and a summary sentence. Saved to `step4_open_problems/4b_experts/expert_{i}_r2_critique.json`.

---

### Node 2.7 — R2 Critic Aggregate

**Role.** Aggregation and loop-control node. Collects all four critic verdicts and decides whether the Round 2 cycle is complete or whether failing experts must revise their proposals.

**Input.** All accumulated Round 2 critiques, resolved to the most recent submission per expert.

**Process.** Checks whether all four experts received `overall_approved = True`. If not, increments the iteration counter. If the current iteration has reached `expert_r2_max_iterations` (default: 2), approval is forced regardless of remaining issues — this prevents infinite loops while still allowing one full revision cycle.

**Output.** `expert_r2_approved` (boolean) and `expert_r2_iteration` (integer) written to state. A conditional edge reads `expert_r2_approved` and routes to either `expert_acceptance` (if approved) or `expert_r2_revision_dispatch` (if more revision is needed).

---

### Node 2.8 — R2 Revision Dispatch

**Role.** Routing helper node. Identifies which experts need to revise their proposals and logs them diagnostically. Does no computation beyond this.

**Output.** Empty dictionary. All four Round 2 expert nodes are re-triggered; the revision logic within each expert node itself skips already-approved experts by re-emitting their proposals unchanged without an LLM call.

---

### Node 2.9 — Expert Acceptance

**Role.** Filtering node. Collects the final proposals from all experts after the Round 2 loop completes and applies per-proposal verdict filtering to produce a clean list of accepted proposals.

**Input.** The final `expert_proposals_r2` list and `expert_r2_critiques` list.

**Process.** For each expert's proposal set, the node retrieves the final critique and checks the per-proposal `approved` flag from each verdict. Proposals with `approved = True` (or those missing a verdict, treated as accepted by default) are admitted; proposals with `approved = False` are logged as rejected with their blocking issues. If no proposals at all pass — all eight were rejected — a fallback accepts everything to prevent an empty output.

**Output.** `accepted_proposals` — a flat list of individual proposal dictionaries, each carrying `expert_index`, `subfield`, `proposal_index`, `title`, `problem_statement`, and `potential_impact`. An acceptance report is saved to `step4_open_problems/4b_experts/acceptance_report.json`.

---

### Node 2.10 — Problem Ranker

**Role.** Global ranking node. Orders all accepted proposals so that the top three selected for finalization are maximally diverse and individually strong.

**Input.** The full `accepted_proposals` list, the paper summary, and the mechanism XML.

**Process.** If there is only one proposal (or zero), the node skips ranking. Otherwise, it sends all proposals — formatted as index, subfield, title, and a truncated problem statement excerpt — to the LLM with a ranking prompt that enforces diversity as the first-priority criterion: the top three slots must address genuinely different mathematical problems. Two proposals that ask the same core question under different framings, or that would be solved by the same proof strategy, must not both appear in the top three regardless of their individual quality. Secondary criteria are precision, grounding in the paper, feasibility, novelty depth, and potential impact. Temperature is 0.2 for consistent, reproducible ranking decisions.

The response contains `ranked_indices` (all 0-based indices of accepted proposals in ranked order) and a `ranking_rationale`. The node validates that the returned indices form a complete permutation; if not, it keeps the original order as a fallback.

**Output.** `accepted_proposals` is replaced with the reordered list. The ranking is saved to `step4_open_problems/4b_experts/proposal_ranking.json`. The finalization workflow then takes the top three proposals.

---

## Finalization Workflow

After the agenda workflow completes, the top three ranked proposals are finalized one at a time by running each through a three-node sequential sub-workflow: `report_generator → final_judge → mechanism_updater`. This sub-workflow is instantiated fresh for each proposal.

---

### Node 2.11 — Report Generator

**Role.** Polishes a raw proposal into a publication-quality research report with two precisely structured sections.

**Input.** The current proposal (formatted as Markdown), the paper summary, and the mechanism XML.

**Process.** The node sends all three to the LLM with a prompt framing it as a distinguished mathematical writer. The prompt instructs it to produce exactly two sections:

1. **Problem Statement.** A formal, rigorous, self-contained mathematical formulation. All objects must be defined, all conditions and quantifiers must be explicit, and the goal (prove X, construct Y, compute Z) must be stated with sufficient precision that a researcher could begin working immediately. Vague directional language is forbidden.

2. **Potential Impact.** Addresses novelty (citing specific related work or known open problems), field advancement (what a successful solution would unlock specifically), and publication potential (naming strong venues where a solution would be publishable).

Temperature is 0.4. The result is parsed into a `ReportResult` structured output.

**Output.** A formatted Markdown report stored in state as `final_report` and saved to `step4_open_problems/proposal_{N}/final_report.md`.

---

### Node 2.12 — Final Judge

**Role.** Impartial quality assessment node. Scores the finalized report across seven independent criteria using a 1–5 rubric.

**Input.** The final report, the paper summary, and the mechanism XML.

**Process.** The judge is framed as an experienced mathematical reviewer with decades of journal reviewing experience. It evaluates the report across two sections:

**Problem Statement (4 criteria):**
- `ps_coherence` — Mathematical coherence and logical consistency (1: major contradictions; 5: fully rigorous and consistent).
- `ps_motivation` — How clearly the problem is derived from or motivated by the original paper (1: no connection; 5: strong direct well-justified extension).
- `ps_derivation` — Precision and completeness of formulation (1: poorly scoped or undefined; 5: precisely and completely formulated).
- `ps_depth` — Conceptual and structural depth beyond surface-level modification (1: purely superficial variation; 5: deep structural or conceptual advancement).

**Potential Impact (3 criteria):**
- `pi_novelty` — Genuineness of novelty (1: clearly known or already resolved; 5: appears genuinely new and original).
- `pi_advancement` — Degree of field advancement if solved (1: minor extension with limited impact; 5: significant theoretical advancement with broad lasting impact).
- `pi_publication` — Publication potential in strong venues (1: unlikely to meet reputable journal standards; 5: high-impact suitable for a top journal).

The prompt explicitly instructs the judge to use the full 1–5 range and not to default to middle values, and to evaluate each criterion independently on the substance of the specific proposal. Temperature is 0.5.

**Score computation.** Two aggregate section scores are computed: `ps_score = mean(ps_coherence, ps_motivation, ps_derivation, ps_depth)` and `pi_score = mean(pi_novelty, pi_advancement, pi_publication)`, both rounded to two decimal places.

**Output.** `quality_assessment`, `ps_score`, and `pi_score` written to state. Detailed results saved as `step4_open_problems/proposal_{N}/quality_assessment.md`, `quality_assessment.json`, and `summary.md`/`summary.json`.

---

### Node 2.13 — Mechanism Updater

**Role.** Traceability node. Writes the finalized proposal back into the mechanism XML knowledge base, linking it to the specific theorems, dissatisfactions, and conjectures that motivated it.

**Input.** The original mechanism XML, the problem statement and potential impact from the final report, and a direction label (the expert's subfield and proposal title).

**Process.** The node parses the final report into sections by heading and sends the mechanism XML together with the problem statement, potential impact, and direction label to the LLM. The prompt instructs it to add one or more `<proposed_problem>` elements to the `<frontier>` section of the XML. Each `<proposed_problem>` must carry:

- A unique `id` in the format `pp:short_name`.
- A `title` attribute.
- A `source_refs` attribute listing the IDs of existing `<context>` or `<motivation>` elements that the proposal traces back to (at least one reference is required).
- A `<statement>` child with the formal problem statement.
- An `<impact>` child explaining potential impact.

All existing XML content must be preserved unchanged — only new elements are added. The response is stripped of any Markdown code fences and stored as raw XML. Temperature is 0.3.

**Output.** `updated_mechanism` written to state and saved to `step4_open_problems/proposal_{N}/mechanism_updated.xml`. This creates a living knowledge graph that records not just what the paper proved, but what open problems it motivated and exactly which results they trace back to.

---

## End-to-End Data Flow

```
arXiv ID
    │
    ▼
[Phase 1]
ingestion → summarizer → critic → (revision loop) → mechanism extractor
                                                              │
                           summary ───────────────────────── ┤
                           mechanism XML ─────────────────── ┘
                                                              │
                                                              ▼
[Phase 2 — Agenda Workflow]
agenda_creator
    │ subfields[0..3], agenda
    ├──► field_expert_0_r1 ──┐
    ├──► field_expert_1_r1 ──┤  (parallel)
    ├──► field_expert_2_r1 ──┤
    └──► field_expert_3_r1 ──┘
                              │
                           r2_sync (barrier)
                              │
    ┌─────────────────────────┘
    ├──► field_expert_0_r2 ──┐
    ├──► field_expert_1_r2 ──┤  (parallel, each sees all 4 R1 surveys)
    ├──► field_expert_2_r2 ──┤
    └──► field_expert_3_r2 ──┘
                              │
                     r2_proposals_sync (barrier)
                              │
    ┌─────────────────────────┘
    ├──► expert_r2_critic_0 ──┐
    ├──► expert_r2_critic_1 ──┤  (parallel)
    ├──► expert_r2_critic_2 ──┤
    └──► expert_r2_critic_3 ──┘
                              │
                    r2_critic_aggregate
                         │          │
                   approved?        no ──► expert_r2_revision_dispatch
                         │                       └──► (back to R2 nodes)
                        yes
                         │
                expert_acceptance → problem_ranker
                                          │
                              top 3 proposals (ranked by diversity + quality)
                                          │
[Phase 2 — Finalization Workflow, run once per proposal]
    report_generator → final_judge → mechanism_updater
```

---

## Key Design Principles

### Multi-Layered Novelty Enforcement

The system uses three independent mechanisms to prevent rediscovering known results. First, the `<known_false>` and `<known_in_literature>` fields in the mechanism XML are checked by every Round 2 expert node and every critic node independently of each other. Second, the `settled_claims` lists built by each expert's R1 survey provide a subfield-specific FORBIDDEN list derived from the expert's own literature knowledge. Third, the critics apply their own mathematical background as a further independent check beyond what any survey explicitly lists. The redundancy is intentional: a single novelty filter is easily circumvented by paraphrase or subtle reformulation.

### Separation of Survey and Proposal

Round 1 and Round 2 are deliberately decoupled. Experts are forbidden from proposing anything in Round 1, which forces a dedicated context-building pass before any proposals are written. This prevents premature commitment to a proposal framing before the full cross-field picture is assembled.

### Cross-Pollination Across Subfields

In Round 2, each expert reads all other experts' Round 1 surveys before writing its proposals. This cross-exposure is the primary mechanism by which the system generates proposals that span multiple subfields, rather than producing four independent and potentially redundant single-subfield proposals.

### Diversity as the First Ranking Criterion

The problem ranker places diversity above individual quality when selecting the top three proposals for finalization. A set of three distinct good proposals is explicitly considered preferable to three near-identical excellent ones. Two proposals that would be solved by the same proof strategy must not both appear in the top three, regardless of their individual scores.

### Traceability Back to Source

The mechanism updater closes the loop by writing every finalized proposal back into the XML knowledge graph with explicit `source_refs` linking it to the specific theorems and dissatisfactions that motivated it. This creates an auditable lineage from paper results to open problem formulation, making the provenance of each proposal fully transparent.
