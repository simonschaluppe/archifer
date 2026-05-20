from dataclasses import dataclass
import pandas as pd
import pulp as pl
import numpy as np

def is_empty(value) -> bool:
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False

@dataclass
class Constraint:
    name: str
    filter: dict[str] | None # which archetypes are selected
    column: str # archetype column name with specific target  value, e.g. kWh/m²NFA
    target: float # total target, e.g. kWh, m²NFA, buildings, etc.
    weight: float   
    type: str = "absolute"  # "absolute" or "share"
    reference_filter: dict[str] | None = None

class BuildingSector:
    archetypes: pd.DataFrame
    ids: list[str]
    model: pl.LpProblem
    n: dict[pl.LpVariable]
    slack_pos: dict[pl.LpVariable]
    slack_neg: dict[pl.LpVariable]
    objective_terms: list
    constraints: list[Constraint]

    def __init__(self, archetype_df:pd.DataFrame):
        self.archetypes = archetype_df
        self.ids = archetype_df.index.tolist()
        self.constraints = []
    
    def add_constraint(self, constraint:Constraint):
        self.constraints.append(constraint)

    def solve(self, timeLimit=1):
        self.model = pl.LpProblem("Archetype_Inference", pl.LpMinimize)
        self.n = pl.LpVariable.dicts("NFA", 
                                     self.ids, 
                                     lowBound=0, 
                                     cat="Integer")
        self.slack_pos = {}
        self.slack_neg = {}
        self.objective_terms = []
        self._apply_constraints()
        self._apply_weights()
        solver = pl.PULP_CBC_CMD(timeLimit=timeLimit) # Zeitlimit in Sekunden; best-effort Lösung; wenn exakter gewünscht, Zeitlimit entfernen
        self.model.solve(solver)

        print("Status:", pl.LpStatus[self.model.status])

        buildings = pd.Series({i: self.n[i].varValue for i in self.ids})
        self.archetypes["buildings"] = buildings
        return buildings
    
    def _apply_constraints(self):
        for constraint in self.constraints:
            self._apply_constraint(constraint)

    def _apply_weights(self):
        if self.objective_terms:
            self.model += pl.lpSum(self.objective_terms)
        else:
            self.model += 0

    def _lhs_expr(self, ids, column):
        if column is None:
            return pl.lpSum(self.n[i] for i in ids)

        return pl.lpSum(self.n[i] * self.archetypes.at[i, column] for i in ids)

    def _apply_constraint(self, c:Constraint):

        filtered_ids = self._filter_indices(c.filter)
        if len(filtered_ids) == 0:
            print(f"Skipping {c.name}: no matching archetypes")
            return

        lhs = self._lhs_expr(filtered_ids, c.column)

        # elif c.type == "greater than target":
        #     s_neg = pl.LpVariable(f"s_{c.name}_shortfall", lowBound=0)
        #     self.model += (expr + s_neg >= c.target), c.name
        #     self.objective_terms.append(c.weight * s_neg)

        # elif c.type == "less than target":
        #     s_pos = pl.LpVariable(f"s_{c.name}_excess", lowBound=0)
        #     self.model += (expr - s_pos <= c.target), c.name
        #     self.objective_terms.append(c.weight * s_pos)

        if c.type == "absolute":
            rhs = c.target

        elif c.type == "share":
            reference_ids = self._filter_indices(c.reference_filter)
            reference_expr = self._lhs_expr(reference_ids, c.column)

            rhs = c.target * reference_expr

        else:
            raise ValueError(f"Unknown constraint type: {c.type}")

        s_pos = pl.LpVariable(f"s_{c.name}_pos", lowBound=0)
        s_neg = pl.LpVariable(f"s_{c.name}_neg", lowBound=0)
        self.model += (lhs + s_pos - s_neg == rhs), c.name
        self.objective_terms.append(c.weight * (s_pos + s_neg))

    def _filter_indices(self, cfilter):
        if cfilter is None:
            return self.ids

        if isinstance(cfilter, dict):
            mask = pd.Series(True, index=self.archetypes.index)

            for col, value in cfilter.items():
                mask &= self.archetypes[col].eq(value)

            return self.archetypes.index[mask].tolist()

        else:
            raise TypeError(
                f"Constraint.filter must be dict or None, got {type(cfilter)}"
            )
        
    def add_constraints_from_df(
        self,
        constraints_df: pd.DataFrame,
        filter_cols: list[str] | dict[str, str],
        target: str,
        weight: float = 1_000_000,
        name_prefix: str = "constraint",
        target_column_col: str = "target_column", # where to find the target column name
    ):
        """
        Add one Constraint per row in constraints_df.

        constraints_df must contain:
        - target: column name of numeric RHS target value
        - target_column_col: archetype column to multiply with NFA

        If target_column_col is empty:
            lhs = sum(NFA_i)

        If target_column_col is filled:
            lhs = sum(NFA_i * archetype_df.at[i, Target_Column])
        """

        if isinstance(filter_cols, dict):
            filter_pairs = list(filter_cols.items())
        else:
            filter_pairs = [(col, col) for col in filter_cols]

        for row_no, row in constraints_df.iterrows():

            rhs = row[target]

            if is_empty(rhs):
                continue

            target_column = row[target_column_col]

            if is_empty(target_column):
                target_column = None

            cfilter = {}

            for constraint_col, archetype_col in filter_pairs:
                value = row[constraint_col]

                # empty filter value => do not apply this filter
                if is_empty(value):
                    continue

                cfilter[archetype_col] = value

            self.add_constraint(
                Constraint(
                    name=f"{name_prefix}_{row_no}",
                    filter=cfilter if cfilter else None,
                    column=target_column,
                    target=float(rhs),
                    weight=weight,
                )
            )

    def result_df(self, value_col: str = "NFA") -> pd.DataFrame:
        """
        Return archetype dataframe with optimization result column.
        """
        if not hasattr(self, "n"):
            raise RuntimeError("Model has not been solved yet. Call bs.solve() first.")

        result = self.archetypes.copy()

        values = pd.Series(
            {i: pl.value(self.n[i]) or 0 for i in self.ids},
            name=value_col,
        )

        result[value_col] = values
        return result


    def plot_result(
        self,
        label_col: str = "Name",
        value_col: str = "NFA",
        min_value: float = 0,
        sort: bool = False,
        figsize=(8, 10),
        ax=None,
    ):
        """
        Horizontal bar chart of non-zero optimization results.
        """
        result = self.result_df(value_col=value_col)

        plot_df = result.loc[result[value_col] > min_value, [label_col, value_col]]

        if plot_df.empty:
            print("No values above min_value.")
            return ax

        plot_df = plot_df.set_index(label_col)

        if sort:
            plot_df = plot_df.sort_values(value_col)

        ax = plot_df[value_col].plot(
            kind="barh",
            figsize=figsize,
            ax=ax,
        )

        ax.set_xlabel(value_col)
        ax.set_ylabel("")
        ax.set_title("Optimization result")

        return ax
    
    def clear_constraints(self):
        self.constraints = []


    def remove_constraints(self, name_prefix: str):
        self.constraints = [
            c for c in self.constraints
            if not c.name.startswith(name_prefix)
        ]


    def list_constraints(self):
        return pd.DataFrame([
            {
                "name": c.name,
                "type": c.type,
                "filter": c.filter,
                "column": c.column,
                "target": c.target,
                "weight": c.weight,
            }
            for c in self.constraints
        ])
    

def make_filter_from_row(row, filter_cols):
    # Create the same filter dictionary that model.py creates from one Excel row.
    if isinstance(filter_cols, dict):
        filter_pairs = list(filter_cols.items())
    else:
        filter_pairs = [(col, col) for col in filter_cols]

    cfilter = {}
    for constraint_col, archetype_col in filter_pairs:
        value = row[constraint_col]
        if is_empty(value):
            continue
        cfilter[archetype_col] = value

    return cfilter or None


def matching_ids(archetype_df, cfilter):
    # Return archetype ids matching a filter dictionary.
    if cfilter is None:
        return archetype_df.index.tolist()

    mask = pd.Series(True, index=archetype_df.index)
    for col, value in cfilter.items():
        mask &= archetype_df[col].eq(value)

    return archetype_df.index[mask].tolist()


def validate_constraints_df(
    constraints_df,
    archetype_df,
    filter_cols,
    target_col,
    target_column_col,
):
    rows = []

    for row_no, row in constraints_df.iterrows():
        target_value = row.get(target_col, np.nan)
        target_column = row.get(target_column_col, np.nan)

        cfilter = make_filter_from_row(row, filter_cols)
        ids = matching_ids(archetype_df, cfilter)

        target_is_empty = is_empty(target_value)
        target_column_is_empty = is_empty(target_column)

        if target_column_is_empty:
            target_column_exists = True
            target_column_clean = None
        else:
            target_column_clean = target_column
            target_column_exists = target_column_clean in archetype_df.columns

        rows.append({
            "row": row_no,
            "n_matches": len(ids),
            "target_value": target_value,
            "target_value_empty": target_is_empty,
            "target_column": target_column_clean,
            "target_column_exists": target_column_exists,
            "filter": cfilter,
        })

    return pd.DataFrame(rows)
