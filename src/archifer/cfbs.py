
from matplotlib import pyplot as plt
import pandas as pd



class BuildingSector:
    def __init__(self, df = None, year = None):
        self._df = df
        self.year = year or 2025
        self.name = f"Gebäudesektor {self.year}"


    def plot(self, variables: list[str]=None, categorization: list[str]=None):
        """Plots y subplots for each categorization C and variable y"""
        variables = variables or ["NGF"]
        categorization = categorization or ["Nutzung"]
        for y in variables:
            self._df.pivot("Nutzung")[y].sum().plot(kind="bar",stacked=True)
            plt.legend()

    def copy(self):
        return BuildingSector(df=self._df, year=self.year)
    
    def NFA(self):
        return self._df["NGF"].sum()
    
    def __repr__(self):
        return f"Building Sector ({self.year}): {self.NFA()/1e6:.1f} mio m²"
    
    @classmethod
    def from_excel(cls, path = "data/gebaeudesektor_at.xlsx"):
        df = pd.read_excel(path)
        df.rename(columns={"Nettogrundfläche in Quadratmetern": "NGF"}, inplace=True)
        return cls(df)

def distribute(parameter, distribution):
    pass


def reduce(sector_model: pd.DataFrame, *args):
    """takes a sector model pandas dataframe"""
    print("reduce not implemented!")
    reduced_sector_model = sector_model
    return reduced_sector_model

def split(sector_model: pd.DataFrame, building_type, *rules):
    pass

def fit(sector_model, goal):
    pass


if __name__ == "__main__":
    s = BuildingSector.from_excel()
    df = s._df
    s.plot()