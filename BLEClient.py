from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from functools import cached_property
import asyncio
import qasync
import inspect

DATA_UUID = "b884f421-e57a-4fd0-a9f7-6decd29fcfcb"


@dataclass
class QBleakClient(QObject):
	device: BLEDevice
	bleakClient: BleakClient = None
	messageChangedData = pyqtSignal(bytes)

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
			await self.client.start_notify(DATA_UUID, self._handle_read_data)

			data = await self.client.read_gatt_char(DATA_UUID)
			self.messageChangedData.emit(bytes(data))
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

	def _handle_read_data(self, _: int, data: bytearray) -> None:
		# print("received:", data)
		self.messageChangedData.emit(bytes(data))
