from dataclasses import dataclass
import pandas as pd
from BLEClient import QBleakClient


@dataclass
class Screw:
	mac: str
	name: str
	dataStrain1: pd.DataFrame
	dataStrain2: pd.DataFrame
	dataStrain3: pd.DataFrame
	dataTemp1: pd.DataFrame
	bleClient: QBleakClient = None
	connecting: bool = False
