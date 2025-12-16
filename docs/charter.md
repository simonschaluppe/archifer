# Project Charter — ArchIfer

## 1. Purpose

ArchIfer is a scientific Python library for **inferring a consistent distribution of building archetypes** from aggregate statistical constraints.

The library addresses a common problem in building stock and energy system modelling:  
available data are typically *aggregate, incomplete, and heterogeneous*, while simulation tools require *explicit, simulation-ready building representations*.

ArcheInfer provides a transparent, reproducible, and methodologically sound way to bridge this gap.

---

## 2. Core Problem Statement

Given:
- a (possibly large) **space of candidate building archetypes**, and
- a set of **constraints** describing a building stock (e.g. totals, shares, marginals, scenarios),

derive:
- a **weighted or counted set of archetypes** whose aggregate properties best match those constraints.

This is a **constraint satisfaction / optimization problem**, not a building physics problem.

---

## 3. Scope

### 3.1 In Scope

ArchIfer is responsible for:

#### A. Archetype inference
- Managing candidate archetype catalogs (predefined or generated).
- Representing archetype features (categorical and numeric).
- Fitting archetype weights or counts to constraints.

#### B. Constraint handling
- Representation of hard and soft constraints.
- Support for:
  - totals (e.g. total floor area),
  - shares/fractions (e.g. energy carrier mix),
  - marginal distributions (e.g. by building age class),
  - optional cross-tabulated constraints (if available).
- Feasibility checks and diagnostics.
- Quantification and reporting of constraint residuals.

#### C. Solving
- Optimization-based inference (LP / MILP as baseline).
- Optional future support for logic-heavy solvers (SAT / SMT).
- Deterministic, reproducible solver execution.

#### D. Outputs
- A solution consisting of:
  - archetype identifiers,
  - weights or integer counts,
  - diagnostics and metadata.
- Export of simulation-ready archetype sets via adapters.

#### E. Interfaces
- Clearly defined interfaces to:
  - City Energy Analyst (CEA),
  - internal Excel-based simulation tools,
  - other external building simulation frameworks.

---

### 3.2 Explicitly Out of Scope

ArcheInfer does **not**:

- Perform building energy or physics simulations.
- Model thermal systems, HVAC behavior, or occupant dynamics.
- Perform geospatial processing or urban morphology generation.
- Replace domain-specific simulation tools.
- Provide a graphical user interface (beyond minimal CLI utilities).

These concerns are intentionally delegated to specialized tools to ensure clean separation of responsibilities.

---

## 4. Intended Use Cases

### 4.1 National / Sector-Level Modelling
- Current and future scenarios of the Austrian building sector.
- Scenario assumptions such as:
  - retrofit rates,
  - fuel switching,
  - technology adoption constraints.
- Generation of archetype mixes for downstream simulation and aggregation.

### 4.2 Municipal and Local Modelling
- Small municipalities with limited published statistics.
- Partial constraints (e.g. total floor area, building counts, heating shares).
- Generation of consistent archetype distributions from sparse data.

### 4.3 Research and Method Development
- Comparison of inference methods (LP vs MILP vs SMT).
- Sensitivity and feasibility analysis of constraint sets.
- Uncertainty-aware stock representation (future extensions).

---

## 5. Conceptual Model

### 5.1 Archetypes
An archetype is an abstract building representation defined by:
- categorical attributes (e.g. typology, construction period, energy carrier),
- numeric attributes (e.g. reference floor area, occupants).

Archetypes are **simulation-ready**, but simulation is external.

### 5.2 Constraints
Constraints express aggregate knowledge about a building stock:
- hard constraints: must be satisfied if feasible,
- soft constraints: may be violated with quantified penalties.

Constraints operate on **aggregates over archetypes**, not on individual buildings.

### 5.3 Solution
A solution assigns:
- a non-negative weight or integer count to each archetype,
such that the resulting aggregate properties fit the constraint set.

---

## 6. Inputs and Outputs (Contract)

### 6.1 Inputs

1. **Archetype Catalog**
   - Table or object collection describing candidate archetypes and features.

2. **Constraint Set**
   - Structured constraints with metadata:
     - type,
     - target value,
     - hardness (hard/soft),
     - penalty weights (for soft constraints).

3. **Solver Configuration**
   - Solver backend,
   - tolerances,
   - objective formulation.

---

### 6.2 Outputs

A canonical **solution package** consisting of:

- `archetypes`: archetype definitions used in the solution.
- `weights` or `counts`: inferred distribution.
- `diagnostics`:
  - constraint residuals,
  - feasibility status,
  - solver metadata.
- `provenance`:
  - hashes or identifiers of inputs,
  - versioning information.

This package is the only object consumed by simulation adapters.

---

## 7. Architectural Principles

1. **Separation of Concerns**  
   Inference, simulation, and aggregation are distinct steps handled by different libraries.

2. **Transparency**  
   All assumptions, constraints, and solver choices are explicit and inspectable.

3. **Reproducibility**  
   Given the same inputs and configuration, ArcheInfer must produce identical results.

4. **Extensibility**  
   New constraint types, solvers, and adapters can be added without breaking the core API.

5. **Scientific Rigor**  
   Methods are documented, testable, and suitable for peer-reviewed research.

---

## 8. Methodological Baseline

- **Primary approach:** optimization-based inference (LP / MILP).
- **Objective:** minimize weighted constraint violations subject to feasibility.
- **Future extensions:** SAT/SMT solvers for logic-heavy or regulatory constraints, probabilistic formulations for uncertainty.

The baseline must remain simple, interpretable, and well-documented.

---

## 9. Success Criteria

The project is successful if:

- Users can express realistic building stock constraints clearly and concisely.
- ArchIfer produces interpretable archetype distributions with clear diagnostics.
- Outputs integrate cleanly with external simulation tools.
- The scope remains narrow enough to ensure maintainability and scientific clarity.

---

## 10. Non-Goals (Reinforced)

ArchIfer is **not**:
- a building simulation engine,
- a GIS platform,
- a monolithic urban energy model.

It is a **focused inference library** designed to play well with others.