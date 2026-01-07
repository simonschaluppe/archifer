

import yaml
import pulp as pl

def parse_yaml_config(yaml_path):
    """returns a config di
    needs to check that constraints are well formed, etc
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    targets = cfg.get("targets", {})
    weights = cfg.get("weights", {})
    constraints = cfg.get("constraints", [])
    # check ?

    return targets, weights, constraints


def create_model(targets, weights, constraints, archetype_df):
    archetypes = archetype_df.index.tolist()
    # ---------------------------------------------------
# 3) Modell und Variablen
# ---------------------------------------------------
    model = pl.LpProblem("Archetype_Inference", pl.LpMinimize)

    # Gewichte / Anzahlen der Archetypen
    w = pl.LpVariable.dicts("w", archetypes, lowBound=0, cat="Integer") # hier cat = "Continuous" für LP-Relaxation

    # Slack-Variablen sammeln (pro Constraint-Name oder Gruppen-Element)
    slack_pos = {}
    slack_neg = {}
    # ---------------------------------------------------
    # 4) Constraints aus YAML kompilieren
    # ---------------------------------------------------
    for c in constraints:
        name = c["name"]
        ctype = c["type"]
        hard = c.get("hard", False)

        # Ziel(e) auflösen
        # - für 'sum' oder 'share' mit target: einfacher Wert oder String-Referenz
        # - für 'share_group' mit targets: dict in targets
        if ctype in ["sum", "share"]:
            if isinstance(c.get("target"), str):
                target_value = targets[c["target"]]
            else:
                target_value = c["target"]
        elif ctype == "share_group":
            # targets: Name des Dicts in 'targets'
            target_group_name = c["targets"]
            target_group = targets[target_group_name]
        else:
            raise ValueError(f"Unknown constraint type: {ctype}")

        # Serie/Spalte für Aggregation
        column = c["column"]
        series = archetype_df[column].astype(float)

        if ctype == "sum":
            # Summe über alle
            expr = pl.lpSum(w[i] * series[i] for i in archetypes)
            if hard:
                model += expr == target_value, name
            else:
                s_pos = pl.LpVariable(f"s_{name}_pos", lowBound=0)
                s_neg = pl.LpVariable(f"s_{name}_neg", lowBound=0)
                slack_pos[name] = s_pos
                slack_neg[name] = s_neg
                model += expr - target_value == s_pos - s_neg, name

        elif ctype == "share":
            predicate = c["predicate"]
            sel_idx = archetype_df.query(predicate).index
            expr_num = pl.lpSum(w[i] * series[i] for i in sel_idx)
            expr_den = pl.lpSum(w[i] * series[i] for i in archetypes)
            if hard:
                model += expr_num - target_value * expr_den == 0, name
            else:
                s_pos = pl.LpVariable(f"s_{name}_pos", lowBound=0)
                s_neg = pl.LpVariable(f"s_{name}_neg", lowBound=0)
                slack_pos[name] = s_pos
                slack_neg[name] = s_neg
                model += expr_num - target_value * expr_den == s_pos - s_neg, name

        elif ctype == "share_group":
            # categories: dict {cat_name: predicate}
            categories = c["categories"]
            for cat_name, predicate in categories.items():
                sub_name = f"{name}_{cat_name}"
                target_share = target_group[cat_name]

                sel_idx = archetype_df.query(predicate).index
                expr_num = pl.lpSum(w[i] * series[i] for i in archetypes)
                expr_den = pl.lpSum(w[i] * series[i] for i in archetypes)

                if hard:
                    model += expr_num - target_share * expr_den == 0, sub_name
                else:
                    s_pos = pl.LpVariable(f"s_{sub_name}_pos", lowBound=0)
                    s_neg = pl.LpVariable(f"s_{sub_name}_neg", lowBound=0)
                    slack_pos[sub_name] = s_pos
                    slack_neg[sub_name] = s_neg
                    model += (
                        expr_num - target_share * expr_den == s_pos - s_neg
                    ), sub_name

        else:
            raise ValueError(f"Unknown constraint type: {ctype}")
        
        objective_terms = []

    for name in slack_pos:
        # einfache Zuordnung der Gewichte
        if name == "Af_total":
            alpha = weights.get("Af_total", 1.0)
        elif name == "share_residential_Af":
            alpha = weights.get("share_residential_Af", 1.0)
        elif name.startswith("share_energy_therm_"):
            alpha = weights.get("share_energy_therm", 1.0)
        else:
            alpha = 1.0

        objective_terms.append(alpha * (slack_pos[name] + slack_neg[name]))

    if objective_terms:
        model += pl.lpSum(objective_terms)
    else:
        model += 0
        
    return model


