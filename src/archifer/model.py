from dataclasses import dataclass
import pandas as pd
import pulp as pl

@dataclass
class Constraint:
    name: str
    type: str
    column: str
    filter: str | list[str] | None
    target: float
    weight: float

class BuildingSector:
    archetypes: pd.DataFrame
    ids: list[str]
    model: pl.LpProblem
    n: dict[pl.LpVariable]
    slack_pos: dict[pl.LpVariable]
    slack_neg: dict[pl.LpVariable]
    objective_terms: list
    constraints: list[Constraint]

    def __init__(self, df:pd.DataFrame):
        self.archetypes = df
        self.ids = df.index.tolist()
        self.constraints = []

    def add_yaml_constraint(self, name, properties):
        constraint = Constraint(name=name,
                                type=properties["type"],
                                column=properties["column"],
                                target=properties["target"],
                                filter=properties.get("filter", None),
                                weight=properties.get("weight", 1),
                                )
        self.add_constraint(constraint)
    
    def add_constraint(self, constraint:Constraint):
        self.constraints.append(constraint)

    def solve(self, timeLimit=1):
        self.model = pl.LpProblem("Archetype_Inference", pl.LpMinimize)
        self.n = pl.LpVariable.dicts("n", 
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

    def _apply_constraint(self, c:Constraint):
        filtered_ids = self._filter_indices(c.filter)

        if c.column == "Building count":
            expr = pl.lpSum(self.n[i] for i in filtered_ids)
        else:
            expr = pl.lpSum(self.n[i] * self.archetypes.at[i, c.column] for i in filtered_ids)

        # Soft constraints: add appropriate slack(s)
        if c.type == "equals":
            s_pos = pl.LpVariable(f"s_{c.name}_pos", lowBound=0)
            s_neg = pl.LpVariable(f"s_{c.name}_neg", lowBound=0)
            self.model += (expr + s_pos - s_neg == c.target), c.name
            self.objective_terms.append(c.weight * (s_pos + s_neg))

        elif c.type == "greater than target":
            s_neg = pl.LpVariable(f"s_{c.name}_shortfall", lowBound=0)
            self.model += (expr + s_neg >= c.target), c.name
            self.objective_terms.append(c.weight * s_neg)

        elif c.type == "less than target":
            s_pos = pl.LpVariable(f"s_{c.name}_excess", lowBound=0)
            self.model += (expr - s_pos <= c.target), c.name
            self.objective_terms.append(c.weight * s_pos)
        else:
            raise ValueError(f"Unknown type: {c.type}")

    def _filter_indices(self, cfilter):
        if not cfilter:
            return self.ids
        elif isinstance(cfilter, str):
            return self.archetypes.query(cfilter).index
        elif isinstance(cfilter, list):
            return self.archetypes.query(" and ".join(cfilter)).index
        else:
            raise TypeError(f"c.filter must be str or list, got {type(cfilter)}")
        
