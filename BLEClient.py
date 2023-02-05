from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from functools import cached_property
import asyncio
import qasync
import inspect

STRAIN1_UUID = "b884f421-e57a-4fd0-a9f7-6decd29fcfcb"
STRAIN2_UUID = "8383cf83-bdec-4419-8297-df3db9d385c9"
STRAIN3_UUID = "29cb87f0-3070-4bf9-9805-8e3aec5d91fb"
TEMP1_UUID = "40d2b763-b3c3-472c-b82d-896bd2cff94d"


@dataclass
class QBleakClient(QObject):
	device: BLEDevice
	bleakClient: BleakClient = None

	messageChangedStrain1 = pyqtSignal(bytes)
	messageChangedStrain2 = pyqtSignal(bytes)
	messageChangedStrain3 = pyqtSignal(bytes)
	messageChangedTemp1 = pyqtSignal(bytes)

	def __post_init__(self):
		super().__init__()

	@cached_property
	def client(self) -> BleakClient:
		self.bleakClient = BleakClient(self.device, disconnected_callback=self._handle_disconnect)
		return self.bleakClient

	@qasync.asyncSlot()
	async def start(self):
		try:
			await self.client.connect(protection_level=2)
			await self.client.start_notify(STRAIN1_UUID, self._handle_read_strain1)
			await self.client.start_notify(STRAIN2_UUID, self._handle_read_strain2)
			await self.client.start_notify(STRAIN3_UUID, self._handle_read_strain3)
			await self.client.start_notify(TEMP1_UUID, self._handle_read_temp1)

			strain1 = await self.client.read_gatt_char(STRAIN1_UUID)
			self.messageChangedStrain1.emit(bytes(strain1))
			strain2 = await self.client.read_gatt_char(STRAIN2_UUID)
			self.messageChangedStrain2.emit(bytes(strain2))
			strain3 = await self.client.read_gatt_char(STRAIN3_UUID)
			self.messageChangedStrain3.emit(bytes(strain3))
			temp = await self.client.read_gatt_char(TEMP1_UUID)
			self.messageChangedTemp1.emit(bytes(temp))
		except asyncio.exceptions.CancelledError:
			pass

	@qasync.asyncSlot()
	async def stop(self):
		await self.client.disconnect()
		print("Device was disconnected, goodbye.")

	async def build_client(self):
		await self.start()

	@qasync.asyncSlot()
	async def _handle_disconnect(self, client: BleakClient) -> None:
		await client.disconnect()
		print("Device was disconnected, goodbye.")

	def _handle_read_strain1(self, _: int, data: bytearray) -> None:
		# print("received:", data)
		self.messageChangedStrain1.emit(bytes(data))

	def _handle_read_strain2(self, _: int, data: bytearray) -> None:
		# print("received:", data)
		self.messageChangedStrain2.emit(bytes(data))

	def _handle_read_strain3(self, _: int, data: bytearray) -> None:
		# print("received:", data)
		self.messageChangedStrain3.emit(bytes(data))

	def _handle_read_temp1(self, _: int, data: bytearray) -> None:
		# print("received:", data)
		self.messageChangedTemp1.emit(bytes(data))