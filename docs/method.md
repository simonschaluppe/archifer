# Methods — Archetype inference from aggregate building-stock statistics

This document describes a practical workflow for turning **aggregate statistical information** about a set of buildings into a **weighted (or counted) set of simulation-ready archetypes**, using optimization-based inference (LP/MILP) as the baseline method. The intent is to be readable for energy/HVAC engineers with limited background in statistics and mathematical programming.

## 1. Conceptual workflow

ArcheInfer separates the pipeline into two concerns:

1) **Archetype inference (this library)**
- defines the *candidate archetype space*
- expresses *constraints* from statistics
- finds *weights / counts* for archetypes that fit constraints
- reports feasibility and residuals

2) **Building simulation (external)**
- City Energy Analyst (CEA), or an internal Excel tool, simulates each archetype
- results are aggregated using inferred weights/counts

This is a common structure in synthetic building stock energy modelling (SBSEM / UBEM), where archetypes are used to represent a large stock with incomplete data. :contentReference[oaicite:0]{index=0}

---

## 2. Data model: archetypes, features, and simulation outputs

### 2.1 Archetype space: categorical inputs + numeric attributes

Define a finite set of candidate archetypes indexed by `i = 1..N`.

Each archetype has a **feature vector**:
- categorical features (examples):
  - `usage ∈ {residential, office, school, ...}`
  - `typology ∈ {SFH, MFH, ...}`
  - `construction_period ∈ {<1945, 1945-1980, ...}`
  - `heating_system ∈ {boiler, heat_pump, district_heat_substation, ...}`
  - `energy_carrier ∈ {gas, electricity, biomass, district_heat, ...}`
- numeric features (examples):
  - `reference_floor_area_m2`
  - `u_value_wall`, `air_change_rate`, etc. (if needed)
  - any numeric “tags” relevant to constraints or simulation mapping

#### Not all combinations exist
You should not assume the full Cartesian product of categories. Many combinations are:
- physically impossible,
- inconsistent with regulations/eras,
- absent in the source catalog.

So the archetype space is typically defined by:
- a **source catalog** (CEA archetypes, internal archetype definitions, etc.), and/or
- a **generator + filter ruleset** (generate combinations, then prune invalid ones).

### 2.2 Simulation outputs are separate from inference

Let each archetype have a simulation output vector (from external tools):
- `y_i = [annual_heat_kWh, annual_elec_kWh, peak_load_kW, ...]`

ArcheInfer does **not** compute `y_i`. It only ensures we have:
- stable archetype identifiers,
- a mapping from archetype features to simulator inputs,
- weights/counts so outputs can be aggregated:

If `w_i` is a weight (e.g., number of buildings or share of floor area represented by archetype `i`), then a stock-level KPI is:

- **by-building weighting**: $Y_{total} = Σ_i w_i * y_i$
- **by-floor-area weighting**: $Y_{total} = Σ_i w_i * A_i * y_{i_{intensity}}$ (if simulation outputs are per m²)

This choice matters and should be explicit in the model contract.

---

## 3. The inference variable: what is being solved for?

Two standard choices:

### A) Continuous weights (LP)
- Decision variable: `w_i ≥ 0` (real)
- Interpretation: “fractional” representation of a stock (often acceptable for sector studies)

### B) Integer counts (MILP)
- Decision variable: `n_i ∈ ℤ_{≥0}`
- Interpretation: actual number of buildings of each archetype (useful for small municipalities)

Both can coexist; LP is simpler and is a strong baseline.

---

## 4. Constraints: formal description

A constraint is a statement about an **aggregate property** of the stock.

### 4.1 General form

Define an **aggregation function** `g_k(i)` that maps an archetype `i` to a number relevant for constraint `k`.

Then the stock-level aggregate under weights `w` is:

`G_k(w) = Σ_i w_i * g_k(i)`

A constraint can be:
- **hard equality**: `G_k(w) = b_k`
- **hard inequality**: `G_k(w) ≤ b_k` or `≥`
- **soft constraint**: allow violation with penalty (described below)

Examples of `g_k(i)`:
- `g(i)=1` for counting buildings
- `g(i)=A_i` for floor area totals
- `g(i)=A_i * 1[energy_carrier(i)=gas]` for floor area served by gas
- `g(i)=1[construction_period(i)=1945-1980]` for counts in a vintage bin

This “feature-to-aggregate” view is the key to mapping statistics to archetypes.

### 4.2 Common constraint types

#### (1) Total (sum) constraints
Example: “Total residential floor area is 12.3 million m².”

Let `A_i` be reference floor area per archetype and `res(i)` be indicator of residential usage.

`Σ_i w_i * A_i * 1[res(i)] = 12.3e6`

#### (2) Share constraints
Example: “22% of heating is district heat (by floor area).”

Let `DH(i)` be indicator `energy_carrier = district_heat`, and define total heated floor area `T = Σ_i w_i*A_i`.

`Σ_i w_i*A_i*1[DH(i)] = 0.22 * T`

This is linear if `T` is also linear in `w` (it is), but you typically rewrite it as:

`Σ_i w_i*A_i*1[DH(i)] - 0.22 * Σ_i w_i*A_i = 0`

#### (3) Marginal distribution constraints (histograms)
Example: “Counts by construction period follow a given distribution.”

For each bin `p`:

`Σ_i w_i*1[period(i)=p] = target_count_p`

#### (4) Cross-tab constraints (if available)
Example: “Heating carrier share differs by typology (SFH vs MFH).”

For each pair `(typology=t, carrier=c)`:

`Σ_i w_i*A_i*1[typology(i)=t ∧ carrier(i)=c] = target_area_{t,c}`

---

## 5. From statistics to constraints: the mapping problem

The hardest practical issue is that **statistics and archetype features rarely align perfectly**. The solution is to treat mapping as a first-class part of the method.

### 5.1 Define a “crosswalk” layer (ontology alignment)

Create explicit mappings between:
- **statistical categories** (what the municipality/national statistics provide)
and
- **model categories** (archetype features)

This is usually a many-to-many relationship.

Examples:
- Stats: `heating_type = "central"` might map to multiple model types: `{boiler, district_heat_substation, heat_pump_central}`
- Stats: `building_age = "pre-1945"` might map to model bins that differ (e.g. `<1919`, `1919-1945`)

**Rule:** never silently “guess” mappings. Store them in a crosswalk table.

Recommended crosswalk representation:
- a table of `(stats_dimension, stats_category) -> set of model predicates`
- optionally with weights (if you need probabilistic splitting)

### 5.2 Use predicates to build indicator vectors on the archetype space

A “predicate” is a condition on archetype features, e.g.:

- `usage == residential`
- `construction_period in {1919-1945, <1919}`
- `energy_carrier == district_heat`

When you compile a constraint, you convert predicates into a vector over archetypes:
- `m_i = 1` if archetype `i` matches predicate, else `0`

Then the constraint becomes linear sums over `w_i` (or `n_i`).

### 5.3 When categories do not match: three standard strategies

#### Strategy A — Aggregate the model to the stats level (preferred)
If stats are coarse, make constraints coarse.
- If stats say only `{old, new}`, constrain `{old, new}` by grouping multiple archetype periods.

This is robust and avoids inventing information.

#### Strategy B — Split stats into model bins using assumptions (documented)
If you must map coarse stats into finer model bins, do it explicitly with assumptions:
- fixed split ratios,
- scenario rules,
- auxiliary datasets.

These splits should be treated as **soft constraints** or as preprocessing with clear provenance.

#### Strategy C — Introduce latent categories (advanced)
Sometimes you keep stats categories and treat parts of the archetype features as latent, fitting them indirectly. This is usually overkill early on; start with A and B.

### 5.4 “Soft constraints” for uncertain statistics

Real-world statistics can conflict, be outdated, or refer to different denominators.

Represent uncertain information as soft constraints by adding slack variables:

Hard equality: `Σ_i w_i*g_k(i) = b_k`

Soft equality (L1 penalty):
- `Σ_i w_i*g_k(i) - b_k = s_k^+ - s_k^-`
- `s_k^+, s_k^- ≥ 0`
- minimize `α_k*(s_k^+ + s_k^-)`

This provides:
- a feasible optimization even with conflicting inputs,
- interpretable residuals (“how much did we miss and where?”).

---

## 6. Solving: LP and MILP baselines

### 6.1 LP (continuous weights)
Use when:
- sector-level modelling,
- you want speed and convexity,
- integer building counts are not required.

Typical objective:
- minimize weighted sum of residuals (L1) across soft constraints
- optionally add regularization (e.g., discourage too many archetypes)

### 6.2 MILP (integer counts)
Use when:
- municipality-scale modelling with small counts,
- constraints are inherently integer (e.g., “18 buildings of type X”),
- you want discrete stock synthesis.

MILP is slower but gives interpretable outputs for stakeholders.

### 6.3 Relation to IPF / maximum entropy
If your constraints are mostly **categorical marginals** over a contingency table, iterative proportional fitting (IPF) is a classical method that finds the **maximum-entropy** distribution matching those marginals. :contentReference[oaicite:1]{index=1}

Practical interpretation:
- IPF is a strong option when you are fitting *probabilities over category combinations*.
- LP/MILP is more general when you have:
  - numeric attributes (floor area),
  - mixed denominators (counts vs area),
  - inequalities,
  - discrete feasibility rules.

Many synthetic population pipelines in other domains rely on IPF-like methods; the analogy is direct. :contentReference[oaicite:2]{index=2}

---

## 7. Diagnostics and “what went wrong?”

A production-quality inference library must answer:
- Is the constraint set feasible?
- If not, which constraints conflict most?
- Which constraints are being violated in the best-fit solution?

Recommended diagnostics:
- per-constraint residuals (absolute and relative)
- feasibility status by constraint group
- largest “contributors” to each constraint (which archetypes carry the mass)
- sensitivity: what changes if we relax a specific constraint?

This is essential for stakeholder trust and iterative model building.

---

## 8. Worked mapping examples (conceptual)

### Example 1 — Stats: “share of heating carriers by dwelling count”
Stats provide shares by *dwellings*, but archetypes are by *buildings*.

Options:
- add a numeric feature `dwellings_per_building` to each archetype
- use `g(i) = dwellings_i * 1[carrier(i)=c]`
- constrain shares using dwellings-weighted totals

If dwellings per building is uncertain, treat those constraints as soft.

### Example 2 — Stats: “construction periods differ”
Stats bins: `{<1945, 1945-1980, 1980-2000, >2000}`  
Model bins: `{<1919, 1919-1945, 1945-1970, 1970-1990, 1990-2010, >2010}`

Use Strategy A:
- create a mapping that aggregates model bins into stats bins:
  - `<1945` := `{<1919, 1919-1945}`
  - `1945-1980` := `{1945-1970, 1970-1990 (partial)}`
If partial overlaps exist, you either:
- redefine model bins to align, or
- split one model bin with an assumption and document it.

---

## 9. Relation to building-stock literature (context)

Archetype-based building stock modelling is widely used to represent large building sets under incomplete data; segmentation choices (which features define archetypes) strongly influence accuracy and computational cost. :contentReference[oaicite:3]{index=3}

Work on synthetic building stocks and case studies (including Austria) highlights the practicality of generating representative stocks from aggregate data and validating them against known distributions. :contentReference[oaicite:4]{index=4}

Austria-specific bottom-up building stock modelling (e.g., Invert/EE-Lab related work) demonstrates the importance of detailed stock representations and careful statistical augmentation of engineering models. :contentReference[oaicite:5]{index=5}

---

## 10. Practical guidance for implementation (what the library should expose)

To make mapping explicit and auditable, the library should separate:

1) `Catalog` (archetypes + features)
2) `Crosswalk` (stats categories -> model predicates / groupings)
3) `ConstraintSet` (compiled constraints)
4) `Solver` (LP/MILP backend)
5) `Solution` (weights/counts + diagnostics + provenance)

The critical abstraction is:
> A constraint is a target on $Σ_i w_i * g(i)$ where $g(i)$ is derived from a predicate and an optional numeric scaling.

This keeps the “stats-to-archetype mapping” as explicit code/data, not hidden logic.

---

## References (starting points)

- Nägeli et al. (2022). *Methodologies for Synthetic Spatial Building Stock Modelling* (includes Austrian case context). :contentReference[oaicite:6]{index=6}  
- Le Hong et al. (2023). *Archetype segmentation in urban building energy modelling* (segmentation guidance). :contentReference[oaicite:7]{index=7}  
- Review: *A review of approaches and applications in building stock modelling* (broad taxonomy of methods). :contentReference[oaicite:8]{index=8}  
- Loukas & Chung (2022). *Categorical Distributions of Maximum Entropy under Marginal Constraints* (IPF + max entropy framing). :contentReference[oaicite:9]{index=9}  
- Frick (2003). *Generating synthetic populations using iterative proportional fitting* (classic IPF explanation). :contentReference[oaicite:10]{index=10}  
- Müller (2014). *Energy Demand Assessment… / Invert/EE-Lab* (Austria-oriented stock modelling context). :contentReference[oaicite:11]{index=11}  
- JRC (2022). *Multipurpose synthetic population for policy applications* (general synthetic population methods and constraints). :contentReference[oaicite:12]{index=12}  
