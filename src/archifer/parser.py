
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


