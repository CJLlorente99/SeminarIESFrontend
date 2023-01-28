from dataclasses import dataclass
import pandas as pd


@dataclass
class Screw:
	mac: str
	name: str
	data: pd.DataFrame
