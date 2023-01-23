from dataclasses import dataclass
from BLEClient import QBleakClient
import pandas as pd


@dataclass
class Screw:
	qBleakClient: QBleakClient
	name: str
	dataStrain1: pd.DataFrame
	dataStrain2: pd.DataFrame
	dataStrain3: pd.DataFrame
	dataTemperature: pd.DataFrame
