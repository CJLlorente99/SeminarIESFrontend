import queue
import time
import asyncio
import pandas as pd
from BLEClient import QBleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak import BleakScanner
from datetime import datetime
import struct
from queue import Queue
from dataclasses import dataclass
from screw import Screw


@dataclass
class BLEManager:
	queueData: Queue
	queueScrewsBLEToGUI: Queue
	queueScrewsGUIToBLE: Queue
	screws: dict

	def __post_init__(self):
		self.scanner = BleakScanner(detection_callback=self.deviceFound)
		self.initTime = datetime.now().timestamp()

	def manageIncomingQueues(self):
		try:
			newData = self.queueScrewsGUIToBLE.get(block=False)
		except queue.Empty:
			return

		for tag in newData:  # Only one-entry dict {screw: msg('add', 'remove)'}
			print(tag)
			i = newData[tag]
			if tag == 'add':
				self.screws[i.mac] = i
				print(f'{len(self.screws)} {self.screws}')
				break
			elif tag == 'remove':
				del self.screws[i.mac]
				break

	async def deviceFound(self, device: BLEDevice, advertisement_data: AdvertisementData):
		print('deviceFound')
		if device.address in self.screws.keys():
			screw = self.screws[device.address]
			try:
				print(advertisement_data)
				ownData = advertisement_data.manufacturer_data[0x0C3F]
				screw.bleClient = None
				screw.connecting = False
				sizeFloat = struct.calcsize('f')
				mode = struct.unpack_from('B', ownData, offset=sizeFloat * 4)
				strain1 = struct.unpack_from('f', ownData, offset=sizeFloat * 0)
				strain2 = struct.unpack_from('f', ownData, offset=sizeFloat * 1)
				strain3 = struct.unpack_from('f', ownData, offset=sizeFloat * 2)
				temp = struct.unpack_from('f', ownData, offset=sizeFloat * 3)

				dataStrain1 = pd.DataFrame(
					{'strain1': strain1[0], 'seconds': datetime.now().timestamp() - self.initTime,
					 'date': datetime.now()}, index=[0])

				self.queueData.put({device.address: {'strain1': dataStrain1}})

				dataStrain2 = pd.DataFrame(
					{'strain2': strain2[0], 'seconds': datetime.now().timestamp() - self.initTime,
					 'date': datetime.now()}, index=[0])

				self.queueData.put({device.address: {'strain2': dataStrain2}})

				dataStrain3 = pd.DataFrame(
					{'strain3': strain3[0], 'seconds': datetime.now().timestamp() - self.initTime,
					 'date': datetime.now()}, index=[0])

				self.queueData.put({device.address: {'strain3': dataStrain3}})

				dataTemp1 = pd.DataFrame(
					{'temp': temp[0], 'seconds': datetime.now().timestamp() - self.initTime,
					 'date': datetime.now()}, index=[0])

				self.queueData.put({device.address: {'temp': dataTemp1}})

			except KeyError:
				# In order to avoid some unknown errors with wrong advertisements coming from the MCU, check service uuid
				if '68708bcb-6c81-413d-b35d-ca6cd122babf' in advertisement_data.service_uuids:

					# Continuous mode (if it's first time or client is not connected yet)
					if not screw.bleClient and not screw.connecting:
						screw.connecting = True
						await self.handle_connect(device.address, screw)
					elif screw.bleClient and screw.bleClient.device.is_connected:
						screw.connecting = False

	async def handle_connect(self, address: str, screw: Screw):
		device = await BleakScanner.find_device_by_address(address)
		if isinstance(device, BLEDevice):
			client = QBleakClient(device)
			await client.build_client()
			screw.bleClient = client
			client.messageChangedStrain1.connect(lambda data: self.digestNewDataStrain1(data, screw))
			client.messageChangedStrain2.connect(lambda data: self.digestNewDataStrain2(data, screw))
			client.messageChangedStrain3.connect(lambda data: self.digestNewDataStrain3(data, screw))
			client.messageChangedTemp1.connect(lambda data: self.digestNewDataTemperature(data, screw))

	def digestNewDataStrain1(self, data: bytes, screw: Screw):
		value = conversionFromBytes(data)
		for mac in self.screws:
			if mac == screw.mac:
				dataStrain1 = pd.DataFrame(
					{'strain1': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()},
					index=[0])
				self.queueData.put({mac: {'strain1': dataStrain1}})

	def digestNewDataStrain2(self, data: bytes, screw: Screw):
		value = conversionFromBytes(data)
		for mac in self.screws:
			if mac == screw.mac:
				dataStrain2 = pd.DataFrame(
					{'strain2': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()},
					index=[0])
				self.queueData.put({mac: {'strain2': dataStrain2}})

	def digestNewDataStrain3(self, data: bytes, screw: Screw):
		value = conversionFromBytes(data)
		for mac in self.screws:
			if mac == screw.mac:
				dataStrain3 = pd.DataFrame(
					{'strain3': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()},
					index=[0])
				self.queueData.put({mac: {'strain3': dataStrain3}})

	def digestNewDataTemperature(self, data: bytes, screw: Screw):
		value = conversionFromBytes(data)
		for mac in self.screws:
			if mac == screw.mac:
				dataTemp1 = pd.DataFrame(
					{'temp': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()},
					index=[0])
				self.queueData.put({mac: {'temp': dataTemp1}})

	async def refreshingFunction(self):
		task = None
		while True:
			self.manageIncomingQueues()
			if task and task.done():
				task = asyncio.create_task(self.scanner.start())

def conversionFromBytes(data: bytes):
	return struct.unpack('<f', data)[0]


def mainBLE(queueData, queueScrewsBLEToGUI, queueScrewsGUIToBLE):
	bleManager = BLEManager(queueData, queueScrewsBLEToGUI, queueScrewsGUIToBLE, {})
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)
	try:
		asyncio.ensure_future(bleManager.refreshingFunction())
		loop.run_forever()
	except KeyboardInterrupt:
		pass
	finally:
		loop.stop()
