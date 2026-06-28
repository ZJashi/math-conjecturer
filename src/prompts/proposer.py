"""Few-shot prompt for the baseline single-call proposer."""

BASELINE_SYSTEM = """You are a world-class research mathematician specializing in formulating open problems.
Given the full LaTeX source of a mathematics paper, you produce exactly 2 novel, precisely stated,
genuinely open research proposals that extend or generalize the paper's results.

Each proposal must be:
- A concrete mathematical claim (a conjecture, existence result, or construction task) — not a
  research direction or vague program.
- Genuinely open: do not propose anything the paper itself already proves, disproves, or cites
  as known in the literature.
- Precisely formulated: exact objects, conditions, quantifiers, and a definite goal. A researcher
  should be able to sit down and begin working on it immediately.
- Grounded: traceable to a specific result, construction, or obstruction in the paper.

Respond with ONLY a valid JSON object. No text before or after it."""


# ---------------------------------------------------------------------------
# Few-shot example
# The example is drawn from a prototypical spectral graph theory paper that
# proves an O(d / spectral-gap) mixing-time bound for random walks on
# d-regular expander graphs and shows the d factor is necessary.
# ---------------------------------------------------------------------------

_EXAMPLE_INPUT = """
[EXAMPLE PAPER — truncated for illustration]

\\title{Sharp Mixing-Time Bounds for Random Walks on Regular Expanders}

\\begin{abstract}
We prove that the lazy random walk on any $d$-regular graph $G$ with
spectral gap $\\lambda > 0$ satisfies
$$t_{\\mathrm{mix}}(\\varepsilon) \\le \\frac{2d}{\\lambda} \\ln\\!\\frac{n}{\\varepsilon}.$$
We show this bound is sharp: for every $d \\ge 3$ and $\\lambda \\in (0,1)$
there exist $d$-regular graphs achieving $t_{\\mathrm{mix}} = \\Omega(d/\\lambda)$.
We further conjecture that replacing the lazy walk with the non-backtracking
walk reduces the constant factor to $1/\\lambda$ for all $d \\ge 3$.
\\end{abstract}

\\section{Main Results}
\\begin{theorem}[Upper bound]
  Let $G$ be a connected $d$-regular graph on $n$ vertices with spectral gap
  $\\lambda$. Then $t_{\\mathrm{mix}}(\\varepsilon) \\le (2d/\\lambda)\\ln(n/\\varepsilon)$.
\\end{theorem}
\\begin{theorem}[Sharpness]
  For every $d \\ge 3$ and $\\lambda \\in (0,1)$ there exists a $d$-regular graph
  with $n$ vertices, spectral gap $\\lambda$, and $t_{\\mathrm{mix}}(1/4) \\ge (d/4\\lambda)\\ln n$.
\\end{theorem}
\\begin{remark}
  The factor $d$ is necessary for the lazy walk: removing it would contradict
  Theorem 2.
\\end{remark}
\\section{Open Problems}
  We conjecture the non-backtracking walk achieves $t_{\\mathrm{mix}} = O((1/\\lambda)\\ln n)$,
  independent of $d$, but our proof technique breaks down for non-lazy chains.
"""

_EXAMPLE_OUTPUT = """{
  "proposals": [
    {
      "title": "Sharp Mixing-Time Bound for the Non-Backtracking Walk on Regular Expanders",
      "problem_statement": "Let $G$ be a connected $d$-regular graph on $n$ vertices with spectral gap $\\lambda > 0$. Prove or disprove that the non-backtracking (Hashimoto) random walk satisfies $t_{\\mathrm{mix}}(\\varepsilon) = O\\!\\left(\\frac{1}{\\lambda} \\ln \\frac{n}{\\varepsilon}\\right)$, with the constant independent of $d$. The upper bound $O(d/\\lambda \\cdot \\ln(n/\\varepsilon))$ from the paper holds for the lazy walk and is shown to be sharp for that chain; the conjecture asserts that removing backtracking eliminates the $d$ factor entirely.",
      "potential_impact": "A proof would confirm that non-backtracking walks provide a strictly superior mixing guarantee on expanders, with implications for expander-based constructions in coding theory and pseudorandomness. A disproof would require a new lower-bound construction and would sharpen our understanding of which walk properties are responsible for the $d$ factor."
    },
    {
      "title": "Dimension-Free Mixing for Non-Regular Expanders via Spectral Profile",
      "problem_statement": "Let $G$ be a connected graph on $n$ vertices with maximum degree $\\Delta$ and spectral gap $\\lambda > 0$. The paper's bound $t_{\\mathrm{mix}} = O(\\Delta/\\lambda \\cdot \\ln(n/\\varepsilon))$ extends to this setting by replacing $d$ with $\\Delta$, but may be loose when degrees vary widely. Prove that $t_{\\mathrm{mix}}(\\varepsilon) = O\\!\\left(\\frac{1}{\\lambda \\, \\Phi(n)} \\ln \\frac{n}{\\varepsilon}\\right)$ where $\\Phi(n)$ is the conductance profile of $G$, yielding a bound depending on local geometry rather than worst-case degree.",
      "potential_impact": "Would unify mixing-time analysis for irregular graphs with the spectral-profile framework of Goel--Montenegro--Tetali, replacing degree-dependent constants with conductance-based ones. Directly applicable to Markov chain Monte Carlo on graphs with heterogeneous degree distributions."
    }
  ]
}"""


BASELINE_PROMPT = """Below is a worked example showing the expected input and output format.

=== EXAMPLE INPUT ===
{example_input}

=== EXAMPLE OUTPUT ===
{example_output}

=== END OF EXAMPLE ===

Now generate 2 research proposals for the following paper. Apply the same standards:
concrete mathematical claims, genuinely open, precisely formulated, grounded in the paper's
specific results. Do NOT repeat or paraphrase anything from the example above.

Respond with ONLY a valid JSON object in the same format as the example output.
You may use LaTeX notation for mathematical expressions (e.g., $\\lambda$, $O(n^2)$).

=== PAPER ===
{{paper}}
""".format(example_input=_EXAMPLE_INPUT.strip(), example_output=_EXAMPLE_OUTPUT.strip())
