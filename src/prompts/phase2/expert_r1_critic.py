"""Expert R1 Critic prompts — reviews field expert Round 1 outputs for quality."""

from pydantic import BaseModel, Field
from typing import List


EXPERT_R1_CRITIC_SYSTEM = """You are a rigorous senior mathematician reviewing the outputs of junior
field experts. Your job is to ensure each expert has produced precise, novel, grounded open problems —
not vague research directions, not already-established results, not generic observations.
You are demanding but fair. A problem is only acceptable if it passes all quality bars."""


EXPERT_R1_CRITIC_PROMPT = """You are reviewing the Round 1 outputs of {n_experts} field experts
analyzing a mathematical paper. For each expert, judge whether their output meets the quality bar
for a genuinely useful research problem.

## Paper Summary
{paper_summary}

## Key Mechanisms and Theories (XML Knowledge Base)
Use this to check whether any proposed problem is already proved in the paper itself.
Pay special attention to the `<context>` layers — a problem may be established there under
an equivalent formulation even if the phrasing looks different.
{mechanisms}

## Expert R1 Outputs to Review

{r1_contributions}

---

## Quality Criteria

For each expert, evaluate their output against ALL of the following:

### 1. Precision (most common failure)
Problems must be stated as precise mathematical claims — not "study X", "investigate the behavior of Y",
or "explore connections between A and B". Acceptable: "Prove that X holds under conditions Y and Z",
"Determine whether the constant C in Theorem 3 can be improved to C'", "Construct an example showing...".
If problems are vague directions rather than concrete mathematical statements, flag for revision.

### 2. Novelty (literature depth)
- Is the problem already proved in the paper itself? (Check mechanisms XML `<context>` layer.)
- Is it established by any work cited in the paper?
- Is it a known result in the broader mathematical literature — including:
  - Classical results (textbook-level)
  - Results from the last 10-20 years that may not be cited in this paper
  - Easy corollaries of well-known theorems
  - The same result under different notation or phrasing in an adjacent subfield

A weak novelty check is the most common failure mode. If the expert simply says "this seems open"
without citing the state of the art, that is NOT sufficient evidence of novelty — flag for revision
and ask them to name the closest solved results and explain why this problem is not subsumed by them.

### 3. Grounding
Problems must connect specifically to the paper's content and mechanisms — not just be generic open
problems in the subfield. The paper's specific results, techniques, and objects should appear.

### 4. Literature depth
The `relevant_context` field must demonstrate genuine field knowledge — it should name specific
theorems by result, landmark papers, major open conjectures or programs the paper connects to,
and what has already been tried in these directions. "Standard tools from spectral theory may apply"
is not acceptable. A literature-blind observer could write that. An expert cannot.

The `techniques` field must name specific methods with provenance (where they were developed, in
what context they have been applied, why they are promising here and where they might break down).
Generic names ("perturbation theory", "concentration inequalities") without specifics → flag for revision.

---

For each expert, produce a verdict. Be strict: if any criterion fails, set approved=false and give
specific, actionable feedback. Do not give passing grades to vague problems.

**OUTPUT FORMAT**
You MUST respond with a valid JSON object. No other text before or after the JSON.

```json
{{
  "verdicts": [
    {{
      "expert_index": 0,
      "subfield": "name of the subfield",
      "approved": true,
      "issues": [],
      "suggestions": []
    }},
    {{
      "expert_index": 1,
      "subfield": "name of the subfield",
      "approved": false,
      "issues": [
        "Problem 1 is vague: 'study the spectral behavior' is not a precise mathematical claim. Specify: what quantity? what regime? what is being proved?",
        "Problem 2 appears to be Theorem 4 of [cited paper] restated."
      ],
      "suggestions": [
        "Restate Problem 1 as a precise conjecture: e.g., 'Prove that the largest eigenvalue satisfies X <= Y under condition Z'",
        "Replace Problem 2 with a genuine open extension: e.g., what happens when [condition] is relaxed?"
      ]
    }}
  ],
  "overall_approved": false,
  "summary": "2-3 sentences: which experts passed, which need revision, and the most critical issues"
}}
```

IMPORTANT:
- Your response must be ONLY the JSON object, no other text.
- `approved` should be true ONLY if all 4 criteria are met. Be strict.
- `issues` and `suggestions` must be specific and actionable — not generic complaints.
- `overall_approved` is true only if ALL experts are approved.
- Use plain text, avoid special characters or LaTeX notation.
"""


class ExpertR1Verdict(BaseModel):
    expert_index: int = Field(description="Index of the expert (0-3)")
    subfield: str = Field(description="The expert's subfield")
    approved: bool = Field(description="Whether this expert's output meets quality bar")
    issues: List[str] = Field(description="Specific issues found (empty if approved)")
    suggestions: List[str] = Field(description="Actionable suggestions for improvement")


class ExpertR1CritiqueResult(BaseModel):
    verdicts: List[ExpertR1Verdict] = Field(description="Per-expert verdict")
    overall_approved: bool = Field(description="True only if all experts passed")
    summary: str = Field(description="Brief summary of the review")
