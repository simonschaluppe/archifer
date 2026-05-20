
import pandas as pd
import yaml
import pulp as pl

from .model import BuildingSector

def parse_yaml_config(yaml_path):
    """returns a config di
    needs to check that constraints are well formed, etc
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        constraints = yaml.safe_load(f)

    return constraints

def apply_constraints(matches, constraints_df,  
                          archetype_df, 
                          pl_problem:pl.LpProblem, 
                          pl_var_dict):
    """
    matches: [(constraints_df.column, archetype_column)]
    """
    
    for c in constraints_df.itertuples():
        geb_eig = c[3]
        size_class = c[4]
        age_class = c[5]
        nfa_target = c[7]
        selection = archetype_df[
            (archetype_df["Gebäudeigenschaft (überwiegende Nutzung) (Ebene +2)"] == geb_eig)&
            (archetype_df["Nettogrundfläche in Quadratmetern (in Klassen) (Ebene +1)"] == size_class)&
            (archetype_df["Bauperiode (Ebene +2)"] == age_class)
        ]
        print(geb_eig, size_class, age_class, nfa_target, selection.index)
        if len(selection) > 0:
            pl_problem += (
                pl.lpSum(pl_var_dict[i+1] for i in selection.index) == nfa_target
            )

def apply_constraint(selection, lhs_func, rhs_func, pl_problem):
    pl_problem += pl.lpSum(lhs_func(selection)) 