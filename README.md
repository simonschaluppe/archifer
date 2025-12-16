# ArchIfer — Archetype Inference for Building Stock Modelling

ArchIfer is a Python library that infers a **weighted distribution of simulation-ready building archetypes**
from **aggregate constraints** (e.g., total floor area by age class, shares of heating energy carriers, typology counts).

It is designed to separate concerns cleanly:

- **ArchIfer**: generates/filters candidate archetypes and **fits their weights** to match constraints.
- **External simulators** (e.g., City Energy Analyst) or internal tools (e.g., [Excel-based PED Declaration Tool](https://github.com/simonschaluppe/peexcel)): **simulate energy** for each archetype and aggregate results using ArchIfer weights.

## Motivation

Building stock studies often have partial statistics:
- national sector constraints (Austria current/future scenarios),
- municipality-level totals and shares,
- incomplete cross-tabulations.

ArchIfer provides a transparent, reproducible way to construct an archetype mix that is consistent with those statistics.

## What this library does

### Inputs
1. A **candidate archetype space**
   - a catalog of archetypes (predefined or generated),
   - each archetype has features (e.g., floor area, construction era, typology, heating system, energy carrier).

2. A set of **constraints**
   - hard constraints (must be satisfied if feasible),
   - soft constraints (fit as closely as possible with penalties).

Examples:
- Total residential floor area = 12.3e6 m²
- Share of heating energy carriers: gas 35%, district heat 22%, heat pump 18%, …
- Counts by building type: SFH / MFH / non-residential
- Optional: scenario constraints for future years (retrofit rates, carrier transitions)

### Outputs
- A **solution**: weights or counts per archetype
- Diagnostics:
  - feasibility status and conflicting constraints,
  - constraint residuals,
  - reproducible solver configuration and provenance.

## Non-goals
- Physics simulation and energy demand calculation (delegated to external tools).
- Geospatial modeling (unless supplied as input by another pipeline).

## Quick start (conceptual)

```python
from archifer import Catalog, ConstraintSet, solve

catalog = Catalog.from_dataframe(archetypes_df)  # features per archetype

constraints = ConstraintSet([
    # totals / marginals / shares (hard or soft)
])

solution = solve(catalog, constraints, solver="milp")  # or "lp"
solution.weights  # archetype -> weight
solution.report() # residuals, diagnostics
