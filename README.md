
# ArchIfer — Archetype Inference for Building Stock Modelling

ArchIfer is a small Python modelling tool for inferring a **net-floor-area weighted mix of building archetypes** from aggregate statistics.

It fits archetype weights to constraints such as:

- total net floor area by region, use, size class, or construction period
- energy carrier totals and shares
- weighted totals such as final energy, useful energy, or CO₂ emissions
- scenario-specific building stock assumptions

The current model is centered around a `BuildingSector` object. Each archetype receives one decision variable:

```python
NFA_i = occurring net floor area of archetype i
````

All other archetype columns can then be interpreted as specific values, for example:

```text
kWh/m²NFA
kgCO₂eq/m²NFA
buildings/m²NFA
```

This makes constraints transparent and easy to formulate in Excel.

## Motivation

Building stock studies often rely on incomplete aggregate data:

* national or regional floor-area statistics
* marginal distributions by age, use, size class, or energy carrier
* energy demand and emissions indicators
* current or future scenario assumptions

ArchIfer provides a reproducible way to construct a simulation-ready archetype mix that is consistent with these statistics.

## What the model does

### Inputs

1. **Archetype table**

A dataframe with one row per candidate archetype.

Typical columns include:

* name
* region
* building use
* construction period
* size class
* heating system
* energy carrier
* specific energy demand
* specific emissions

2. **Constraint tables**

Constraints are usually defined in Excel. Each row describes one target.

Typical columns:

```text
target_value
target_column
filter columns...
```

Example:

| BuildingUse | ConstructionPeriod | target_column         | target_value |
| ----------- | ------------------ | --------------------- | -----------: |
| Residential | 1945–1980          |                       |      1200000 |
| Residential | 1945–1980          | FinalEnergy_kWh_m2NFA |     95000000 |

An empty `target_column` means:

```python
sum(NFA_i) == target_value
```

A filled `target_column` means:

```python
sum(NFA_i * archetype_value_i) == target_value
```

For example:

```python
sum(NFA_i * FinalEnergy_i) == total_final_energy
```

## Constraint types

ArchIfer currently supports two main constraint types.

### Absolute constraints

Absolute constraints match a total value.

Example:

```python
sum(NFA_i for selected archetypes) == target_value
```

or:

```python
sum(NFA_i * specific_value_i for selected archetypes) == target_value
```

### Share constraints

Share constraints match a fraction of a reference group.

Example:

```python
gas_NFA == 0.30 * total_NFA
```

or:

```python
residential_gas_NFA == 0.30 * residential_total_NFA
```

Share constraints use:

* `filter_cols` for the numerator
* `reference_cols` for the denominator

## Quick start

```python
import pandas as pd
from model import BuildingSector
```

Load archetypes:

```python
archetypes = pd.read_excel("data/building_stock_archetypes.xlsx")
```

Create a model:

```python
bs = BuildingSector(archetypes)
```

Load constraints from Excel:

```python
constraints_ngf = pd.read_excel(
    "data/constraints_sector_model.xlsx",
    sheet_name="NGF",
)
```

Define which Excel columns are used as filters:

```python
filter_cols_ngf = [
    "Region – Gebietsstand 2023 (Ebene +2)",
    "Gebäudeigenschaft (überwiegende Nutzung) (Ebene +2)",
    "Nettogrundfläche in Quadratmetern (in Klassen) (Ebene +1)",
    "Bauperiode (Ebene +2)",
]
```

Add absolute constraints:

```python
bs.add_constraints_from_df(
    constraints_df=constraints_ngf,
    filter_cols=filter_cols_ngf,
    target="target_value",
    type="absolute",
    target_column_col="target_column",
    weight=1_000_000,
    name_prefix="NGF",
)
```

Solve:

```python
bs.solve(timeLimit=10)
```

Get results:

```python
result = bs.result_df()
result.head()
```

Plot selected archetypes:

```python
bs.plot_result(label_col="Name", value_col="NFA", sort=True)
```

## Adding energy constraints

Energy constraints work the same way as floor-area constraints. The difference is that `target_column` usually contains the name of a specific archetype column.

Example Excel row:

| EnergySupply | target_column        | target_value |
| ------------ | -------------------- | -----------: |
| gas          | Endenergie_kWh_m2NFA |    250000000 |

This creates:

```python
sum(NFA_i * Endenergie_i for EnergySupply == "gas") == 250000000
```

Python:

```python
constraints_ee = pd.read_excel(
    "data/constraints_sector_model.xlsx",
    sheet_name="EE",
)

bs.add_constraints_from_df(
    constraints_df=constraints_ee,
    filter_cols=["EnergySupply"],
    target="target_value",
    type="absolute",
    target_column_col="target_column",
    weight=1_000_000,
    name_prefix="EE",
)
```

## Adding share constraints

Example: gas should represent 30% of total NFA.

Excel:

| EnergySupply | target_column | target_value |
| ------------ | ------------- | -----------: |
| gas          |               |         0.30 |

Python:

```python
bs.add_constraints_from_df(
    constraints_df=constraints_share,
    filter_cols=["EnergySupply"],
    reference_cols=None,
    target="target_value",
    type="share",
    target_column_col="target_column",
    weight=1_000_000,
    name_prefix="Share_EnergySupply",
)
```

This creates:

```python
sum(NFA_i for EnergySupply == "gas")
==
0.30 * sum(NFA_i for all archetypes)
```

Example: gas should represent 30% of residential NFA.

Excel:

| Use         | EnergySupply | ref_Use     | target_column | target_value |
| ----------- | ------------ | ----------- | ------------- | -----------: |
| Residential | gas          | Residential |               |         0.30 |

Python:

```python
bs.add_constraints_from_df(
    constraints_df=constraints_share,
    filter_cols={
        "Use": "Use",
        "EnergySupply": "EnergySupply",
    },
    reference_cols={
        "ref_Use": "Use",
    },
    target="target_value",
    type="share",
    target_column_col="target_column",
    weight=1_000_000,
    name_prefix="Share_Gas_Residential",
)
```

## Inspecting constraints

List all currently stored constraints:

```python
bs.list_constraints()
```

Remove a group of constraints by name prefix:

```python
bs.remove_constraints("NGF")
```

This is useful after editing the Excel file:

```python
bs.remove_constraints("NGF")

constraints_ngf = pd.read_excel(
    "data/constraints_sector_model.xlsx",
    sheet_name="NGF",
)

bs.add_constraints_from_df(
    constraints_df=constraints_ngf,
    filter_cols=filter_cols_ngf,
    target="target_value",
    type="absolute",
    target_column_col="target_column",
    weight=1_000_000,
    name_prefix="NGF",
)

bs.solve(timeLimit=10)
```

The PuLP model is rebuilt every time `solve()` is called. Constraint definitions are persistent; the optimization model is temporary.

## Diagnostics

All constraints are implemented as soft constraints with positive and negative slack variables.

Inspect all slacks:

```python
bs.slack_df()
```

Show only violated constraints:

```python
bs.violated_constraints()
```

Large slack values indicate that the model could not satisfy a constraint exactly, usually because constraints are inconsistent or because the archetype space does not contain matching candidates.

## Outputs

The main output is a result dataframe:

```python
result = bs.result_df()
```

It contains the original archetype table plus the optimized `NFA` value.

Typical downstream analyses:

```python
result.groupby("EnergySupply")["NFA"].sum()
result.groupby("Bauperiode (Ebene +2)")["NFA"].sum()
result.groupby("Gebäudeigenschaft (überwiegende Nutzung) (Ebene +2)")["NFA"].sum()
```

Weighted indicators can be calculated as:

```python
total_energy = (result["NFA"] * result["Endenergie_kWh_m2NFA"]).sum()
total_co2 = (result["NFA"] * result["CO2_kg_m2NFA"]).sum()
```

## Non-goals

ArchIfer does not perform physics-based building simulation.

Energy demand, emissions factors, renovation variants, or technology assumptions should be generated by external tools or preprocessing workflows and then supplied as archetype columns.

## Current status

ArchIfer is an early teaching and research prototype. The current implementation focuses on:

* transparent Excel-based constraints
* soft-constrained MILP fitting with PuLP
* simple model inspection
* reproducible scenario analysis
* plotting and aggregation of inferred building stock properties

This reflects the current `BuildingSector` implementation with NFA decision variables, soft slack constraints, `absolute`/`share` constraint types, dataframe-based constraint import, result extraction, plotting, and slack diagnostics. 


## Further resources

- [Tutorial notebook: Building Sector Model](notebooks/building_sector_model_tutorial.ipynb)  
  Step-by-step introduction to loading archetypes, adding NGF and EE constraints, solving the model, inspecting slacks, and plotting results.

- [Example constraints workbook](data/constraints_sector_model.xlsx)  
  Example Excel structure for defining NGF, energy, and share constraints.

- [Model implementation](model.py)  
  Core implementation of `BuildingSector`, `Constraint`, constraint import, solving, result extraction, and diagnostics.


