from dataclasses import dataclass
import pandas as pd
from BLEClient import QBleakClient


@dataclass
class Screw:
	mac: str
	name: str
	data: pd.DataFrame
	bleClient: QBleakClient = None
	connecting: bool = False
