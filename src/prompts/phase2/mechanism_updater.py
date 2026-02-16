"""Mechanism Updater prompts for Phase 2: Traceability back to mechanism XML."""

MECHANISM_UPDATER_SYSTEM = """
You are an expert at structured knowledge representation in mathematics. You excel at tracing
the lineage of new research problems back to their origins in existing mathematical concepts,
theorems, and open questions.
""".strip()

MECHANISM_UPDATER_PROMPT = """You are updating a mechanism XML knowledge base to trace a new research proposal back to its origins.

## Original Mechanism XML
{mechanism}

## Final Report

### Problem Statement
{problem_statement}

### Proposed Approach
{proposed_approach}

### Expected Challenges
{expected_challenges}

### Potential Impact
{potential_impact}

## Research Direction
{direction}

## Task

Add one or more `<proposed_problem>` elements to the `<frontier>` section of the XML.
Each `<proposed_problem>` element MUST have:
- A unique `id` attribute (use format `pp:short_name`)
- A `title` attribute
- A `source_refs` attribute listing the IDs of existing elements from `<context>` or `<motivation>` that this problem originates from (comma-separated, e.g. "thm:clustering,dis:clustering_fails_d2")
- A `<statement>` child with the formal problem statement
- An `<approach>` child with the proposed approach
- An `<impact>` child explaining potential impact

Rules:
- Keep ALL existing XML content unchanged - only ADD new elements to `<frontier>`
- The `source_refs` MUST reference actual IDs that exist in the `<context>` or `<motivation>` sections
- Each proposed problem should trace back to at least one existing element
- Output the COMPLETE updated XML (not just the new elements)
- Do NOT wrap the output in markdown code fences - output raw XML only
"""
