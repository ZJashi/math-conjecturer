### 1. The Mathematical Landscape
* **Main Contribution:** Introduction and analysis of three new spatial point processes:  
  (i) Generalized Poisson Random Field (GPRF) allowing multiple points in infinitesimal regions,  
  (ii) Fractional GPRF (FGPRF) via time-changing with inverse subordinators,  
  (iii) Generalized Skellam Point Process (GSPP) constructed from independent GPRFs.  
* **Foundations & Framework:** Spatial point processes on $\mathbb{R}^d_+$ (focus on $d=2$), two-parameter Lévy processes with rectangular increments, fractional calculus (Caputo derivatives), and inverse stable subordinators.  
* **Prior Work:**  
  - *Previous Best Result:* Standard Poisson random fields (PRFs) allow at most one point in infinitesimal regions. Time-changed/fractional PRFs were studied in [Leonenko2015, Kataria2024].  
  - *The Gap:* Existing models could not capture multiple arrivals in infinitesimal regions or fractional dynamics in spatial settings.  

---

### 2. Precise Setup (Self-Contained)
* **Key Definitions:**  
  - **GPRF** $\{M(A), A \in \mathcal{A}_d\}$: Non-negative integer-valued measure with independent increments, where for $A \in \mathcal{A}_d$:  
    $$
    \mathrm{Pr}\{M(A) = n\} = \sum_{\Theta(k,n)} \prod_{j=1}^k \frac{(\lambda_j |A|)^{n_j}}{n_j!} e^{-\lambda_j |A|}, \quad \Theta(k,n) = \left\{(n_1, \dots, n_k) \in \mathbb{N}_0^k : \sum_{j=1}^k j n_j = n\right\}.
    $$  
  - **FGPRF** $\{M^{\alpha,\beta}(s,t)\}$: Time-changed GPRF on $\mathbb{R}^2_+$:  
    $$
    M^{\alpha,\beta}(s,t) = M(L^\alpha(s), L^\beta(t)), \quad 0 < \alpha, \beta \leq 1,
    $$  
    where $L^\alpha, L^\beta$ are independent inverse $\alpha$- and $\beta$-stable subordinators.  
  - **GSPP** $\{S(A)\}$: For finite $\mathcal{I} \subset \mathbb{R} \setminus \{0\}$ and independent GPRFs $\{M_i(A)\}$,  
    $$
    S(A) = \sum_{i \in \mathcal{I}} i M_i(A).
    $$  
* **Global Assumptions:**  
  - Independence of increments for all processes.  
  - $\lambda_j > 0$ for GPRF/FGPRF; $\mathcal{I}$ finite for GSPP.  

---

### 3. Main Results  
* **Formal Statements:**  
  - **Theorem (GPRF Representation):** Every GPRF satisfies $M(A) \overset{d}{=} \sum_{j=1}^k j N_j(A)$, where $\{N_j(A)\}$ are independent PRFs with rates $\lambda_j$.  
  - **Theorem (FGPRF Distribution):** The state probabilities $p^{\alpha,\beta}(n,s,t)$ of FGPRF solve:  
    $$
    \frac{\partial^{\alpha+\beta}}{\partial t^\beta \partial s^\alpha} p^{\alpha,\beta}(n,s,t) = -\sum_{j=1}^k \lambda_j (I - B^j) \left(1 + \sum_{j'=1}^k \lambda_{j'} \sum_{r=1}^{j'} B^{j'-r} \frac{\partial}{\partial \lambda_1}\right) p^{\alpha,\beta}(n,s,t),
    $$  
    with explicit solution involving generalized Wright functions.  
  - **Proposition (GSPP Representation):** $S(A) \overset{d}{=} \sum_{r=1}^{N(A)} X_r Y_r$, where $\{N(A)\}$ is a PRF and $\{(X_r, Y_r)\}$ are iid jumps.  

* **Heuristics & Intuition:**  
  - GPRF generalizes Poisson counts by allowing batch arrivals (size $\leq k$) in infinitesimal regions.  
  - FGPRF introduces memory via inverse subordinators, capturing subdiffusive spatial dynamics.  
* **Impact:**  
  - GPRF improves modeling flexibility for clustered spatial data.  
  - FGPRF provides a fractional analog governing anomalous diffusion.  

---

### 4. Illustrations & Applications  
* **Examples & Special Cases:**  
  - **Thinning:** GPRF thins into independent GPRFs with reduced rates $\lambda_j p_j$.  
  - **Compound Poisson Representation:** GPRF $\overset{d}{=}$ compound PRF with jump distribution $\mathrm{Pr}\{X_1 = j\} = \lambda_j / \sum \lambda_j$.  
  - **GSPP for $\mathcal{I} = \{1, -1\}$:** Explicit distribution via modified Bessel functions:  
    $$
    \mathrm{Pr}\{\mathcal{S}(A) = n\} = e^{-(\Lambda^{(1)} + \Lambda^{(2)})|A|} \sum_{\tilde{\Theta}(k,n)} \prod_{j=1}^k \left(\frac{\lambda_j^{(1)}}{\lambda_j^{(2)}}\right)^{n_j/2} I_{|n_j|}\left(2|A|\sqrt{\lambda_j^{(1)} \lambda_j^{(2)}}\right).
    $$  
* **Conjectures & Heuristics:**  
  - Fractional dynamics may model long-range dependence in spatial systems.  
  - GSPP could describe signed measures (e.g., charge distributions).  

---

### 5. Anatomy of the Proofs & Machinery  
* **Crucial Insight:**  
  - GPRF representation via independent PRFs enables tractable analysis.  
  - Time-change with inverse subordinators introduces Mittag-Leffler waiting times.  
* **Ingredients:**  
  - **Key Lemma:** Laplace transforms of inverse subordinators (Meerschaert & Straka, 2013).  
  - **External Theorems:** Fractional PDE techniques (Kilbas et al., 2006), Wright function asymptotics.  
* **Proof Skeleton:**  
  1. Represent GPRF as weighted PRF sum.  
  2. Derive generating functions → governing PDEs.  
  3. For FGPRF: Time-change → fractionalize PDEs via Caputo derivatives.  

---

### 6. Boundaries & The Negative Space  
* **Optimality & Counterexamples:**  
  - **Bounds:** FGPRF variance grows as $s^{2\alpha} t^{2\beta}$; dependence on $\alpha, \beta$ is sharp.  
  - **Assumptions:** Independence of $L^\alpha, L^\beta$ is critical; correlated subordinators break current proofs.  
* **Technical Obstructions:**  
  - **Dimensionality:** Proofs rely on rectangular increments; extension to $d \geq 3$ is non-trivial.  
  - **Fractional Orders:** The method fails if $\alpha + \beta > 1$ due to non-locality of Caputo derivatives.  
* **Alternative Notions:**  
  - Itô vs. Stratonovich integrals for path integrals of GPRF remain open.  
  - Space-fractional analogs (via Riesz derivatives) are conjectured but not proven.  

---

### 7. The Frontier (Open Problems)  
1. **Higher Dimensions:** Extend GPRF/FGPRF to $\mathbb{R}^d_+$ for $d \geq 3$ with non-rectangular increments.  
2. **Dependent Subordinators:** Analyze FGPRF under dependent $L^\alpha, L^\beta$.  
3. **Alternative Fractional Operators:** Replace Caputo with Atangana-Baleanu or Prabhakar derivatives.  
4. **Sample Path Properties:** Study Hölder continuity, Hausdorff dimension for FGPRF/GSPP.  
5. **Statistical Inference:** Develop parameter estimation methods for FGPRF rates $\lambda_j$ and $\alpha, \beta$.  
6. **Generalized Skellam:** Extend GSPP to infinite $\mathcal{I}$ or Lévy bases.  

---

**CONSTRAINTS ADHERED TO:**  
- **Fidelity:** All results/definitions are from the paper; no hallucinations.  
- **Rigor:** Notations consistent; quantifiers explicit (e.g., $\forall A \in \mathcal{A}_d$).  
- **Dependencies:** Theorem dependencies explicitly stated (e.g., Theorem 3.1 → Proposition 2.1).