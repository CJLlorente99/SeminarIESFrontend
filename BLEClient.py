from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from functools import cached_property
import asyncio
import qasync
import inspect

STRAIN1_UUID = "15f13721-3fe0-452d-820c-fc4e4c386bdb"
STRAIN2_UUID = "581944de-3e11-4add-9fa8-58d0390efa92"
STRAIN3_UUID = "57f1e4bc-ef1b-44ce-b0b9-6adca88595ad"
TEMP1_UUID = "0ab27c32-2a05-4af8-9716-67d05c639649"


@dataclass
class QBleakClient(QObject):
	device: BLEDevice
	alwaysConnected: int = 0
	bleakClient: BleakClient = None

	messageChangedStrain1 = pyqtSignal(bytes)
	messageChangedStrain2 = pyqtSignal(bytes)
	messageChangedStrain3 = pyqtSignal(bytes)
	messageChangedTemp1 = pyqtSignal(bytes)

	def __post_init__(self):
		super().__init__()

	@cached_property
	def client(self) -> BleakClient:
		aux = BleakClient(self.device, disconnected_callback=self._handle_disconnect)
		self.bleakClient = aux
		return aux

	@qasync.asyncSlot()
	async def start(self):
		await self.client.connect()
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

	@qasync.asyncSlot()
	async def stop(self):
		await self.client.disconnect()
		print("Device was disconnected, goodbye.")

	async def build_client(self, device):
		self.device = device
		await self.start()

	@qasync.asyncSlot()
	async def reconnect(self):
		await self.bleakClient.disconnect()
		found = await BleakScanner.find_device_by_address(self.device.address, timeout=1)
		await self.build_client(found)
		print("Device was reconnected.")

	@qasync.asyncSlot()
	async def _handle_disconnect(self, client: BleakClient) -> None:
		await client.disconnect()
		print("Device was disconnected, goodbye.")
		if self.alwaysConnected == 0:
			# cancelling all tasks effectively ends the program
			for task in asyncio.all_tasks():
				task.cancel()
		else:
			found = False
			searching = False
			while not found:
				# print(f'found {found}, searching {searching}')
				if not searching and not found:
					found = await BleakScanner.find_device_by_address(self.device.address, timeout=1)
				searching = inspect.iscoroutine(found)
			await self.build_client(found)
			print("Device was reconnected.")



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
