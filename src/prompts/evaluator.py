EVALUATOR_SYSTEM = """You are a rigorous mathematical peer reviewer. 
Given the source paper and a list of research proposals, 
evaluate each proposal independently on three criteria using a 5-point Likert scale (1–5).

Criteria:

1. Technical Soundness - Is the proposal mathematically coherent and free of logical contradictions or impossible assumptions?
   1: Major logical flaws or contradictions
   2: Significant inconsistencies or unclear reasoning
   3: Mostly coherent but with minor issues or ambiguities
   4: Logically sound with only negligible or stylistic issues
   5: Fully logically consistent and mathematically rigorous

2. Grounding - Is the proposal clearly derived from or meaningfully motivated by the source paper?
   1: Little or no connection to the source paper
   2: Weak or loosely motivated connection
   3: Moderately connected but not strongly justified
   4: Clearly connected and reasonably well justified
   5: Strong, direct, and well-justified extension of the original work

3. Conceptual Depth - Does the proposal demonstrate meaningful structural or conceptual insight beyond a surface-level modification?
   1: Purely superficial variation with no meaningful insight
   2: Slight extension but largely superficial
   3: Some conceptual depth but limited structural insight
   4: Clear conceptual or structural insight with meaningful development
   5: Demonstrates deep structural or conceptual advancement

Respond with ONLY a valid JSON object. No text before or after it."""


_EXAMPLE_PAPER = """
[EXAMPLE PAPER — truncated for illustration]

\\title{Sharp Mixing-Time Bounds for Random Walks on Regular Expanders}

\\begin{abstract}
We prove that the lazy random walk on any $d$-regular graph $G$ with spectral gap $\\lambda > 0$ satisfies
$t_{\\mathrm{mix}}(\\varepsilon) \\le \\frac{2d}{\\lambda} \\ln\\frac{n}{\\varepsilon}.$
We show this bound is sharp and conjecture that the non-backtracking walk reduces the constant to $1/\\lambda$.
\\end{abstract}
"""

_EXAMPLE_PROPOSALS = """Proposal 1: Sharp Mixing-Time Bound for the Non-Backtracking Walk on Regular Expanders
Problem Statement: Let $G$ be a connected $d$-regular graph on $n$ vertices with spectral gap $\\lambda > 0$. Prove or disprove that the non-backtracking walk satisfies $t_{\\mathrm{mix}}(\\varepsilon) = O(\\frac{1}{\\lambda} \\ln \\frac{n}{\\varepsilon})$, with the constant independent of $d$.
Potential Impact: Would confirm that non-backtracking walks provide a strictly superior mixing guarantee on expanders.

Proposal 2: Dimension-Free Mixing for Non-Regular Expanders via Spectral Profile
Problem Statement: Let $G$ be a connected graph with maximum degree $\\Delta$ and spectral gap $\\lambda > 0$. Prove that $t_{\\mathrm{mix}}(\\varepsilon) = O(\\frac{1}{\\lambda \\Phi(n)} \\ln \\frac{n}{\\varepsilon})$ where $\\Phi(n)$ is the conductance profile of $G$.
Potential Impact: Would unify mixing-time analysis for irregular graphs with the spectral-profile framework."""

_EXAMPLE_OUTPUT = """{
  "evaluations": [
    {
      "proposal_index": 1,
      "title": "Sharp Mixing-Time Bound for the Non-Backtracking Walk on Regular Expanders",
      "technical_soundness": {
        "score": 5,
        "justification": "Precisely formulated with exact quantifiers and well-defined objects. The claimed bound is falsifiable and the comparison to the known lazy-walk bound is explicit."
      },
      "grounding": {
        "score": 5,
        "justification": "Directly extends the paper's main theorem and formalizes the open conjecture stated in the abstract. Strong traceability to specific results."
      },
      "conceptual_depth": {
        "score": 4,
        "justification": "Identifying backtracking as the structural cause of the d factor is a meaningful insight, though it addresses a single parameter rather than a broader structural phenomenon."
      },
      "overall": 4.67
    },
    {
      "proposal_index": 2,
      "title": "Dimension-Free Mixing for Non-Regular Expanders via Spectral Profile",
      "technical_soundness": {
        "score": 4,
        "justification": "The formulation is sound, though the proposed bound's joint dependence on lambda and conductance profile warrants careful verification against known counterexamples."
      },
      "grounding": {
        "score": 3,
        "justification": "Motivated by the paper's degree-dependent bound but extends to a graph family not studied in the paper. The connection is plausible but requires additional justification."
      },
      "conceptual_depth": {
        "score": 4,
        "justification": "Replacing worst-case degree with local conductance geometry is a structurally meaningful move with implications beyond the specific setting."
      },
      "overall": 3.67
    }
  ]
}"""


EVALUATOR_PROMPT = """Below is a worked example showing the expected input and output format.

=== EXAMPLE PAPER ===
{example_paper}

=== EXAMPLE PROPOSALS ===
{example_proposals}

=== EXAMPLE OUTPUT ===
{example_output}

=== END OF EXAMPLE ===

Now evaluate the proposals below. Score each independently on the three criteria.
Compute overall as the mean of the three scores, rounded to 2 decimal places.

Respond with ONLY a valid JSON object in the same format as the example output.

=== PAPER ===
{{paper}}

=== PROPOSALS ===
{{proposals}}
""".format(
    example_paper=_EXAMPLE_PAPER.strip(),
    example_proposals=_EXAMPLE_PROPOSALS.strip(),
    example_output=_EXAMPLE_OUTPUT.strip(),
)