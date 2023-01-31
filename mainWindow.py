import math
from PyQt5.QtCore import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from addScrewWindow import AddScrewWindow
from availableBLEWindow import AvailableBLEWindow
import sys
import qasync
import asyncio
from screw import Screw
import pandas as pd
import json
import struct
from datetime import datetime
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak import BleakScanner
from BLEClient import QBleakClient


class MainWindow(QMainWindow):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.initTime = datetime.now().timestamp()
		self.scanner = BleakScanner(detection_callback=self.deviceFound)
		self.screws = {}

		# Configure graphical window
		self.window = pg.GraphicsLayoutWidget(title='M20 Screws Dashboard', show=True)
		self.window.resize(1920, 1080)
		self.window.setBackground('black')

		# Graph
		self.graphWidget = self.window.addPlot(title='Strain and Temperature')
		self.graphWidget.enableAutoRange('xy', True)
		self.graphWidget.addLegend(labelTextColor='white')
		self.strain1 = self.graphWidget.plot(pen=pg.mkPen('red', width=3), name='Strain1')
		self.strain2 = self.graphWidget.plot(pen=pg.mkPen('orange', width=3), name='Strain2')
		self.strain3 = self.graphWidget.plot(pen=pg.mkPen('yellow', width=3), name='Strain3')
		self.temperature = self.graphWidget.plot(pen=pg.mkPen('white', width=3), name='Temperature')
		self.graphWidget.showGrid(x=True, y=True)

		# Buttons
		# Create button to add a new screw
		self.proxyAdd = QGraphicsProxyWidget()
		self.addScrewButton = QPushButton('Add Screw')
		self.addScrewButton.setToolTip('Add Screw manually')
		self.proxyAdd.setWidget(self.addScrewButton)
		self.addScrewButton.clicked.connect(self.addScrewOnClick)

		# Create button to see available BLE devices
		self.proxyAvailable = QGraphicsProxyWidget()
		self.availableBLEButton = QPushButton('Explore BLE')
		self.availableBLEButton.setToolTip('Scann for BLE devices')
		self.proxyAvailable.setWidget(self.availableBLEButton)
		self.availableBLEButton.clicked.connect(self.availableBLEOnClick)

		# Create button to start new record
		self.proxyNewRecord = QGraphicsProxyWidget()
		self.startNewRecordingButton = QPushButton('Restart')
		self.proxyNewRecord.setWidget(self.startNewRecordingButton)
		self.startNewRecordingButton.clicked.connect(self.startNewRecordingOnClick)

		# Create button to export data to csv
		self.proxyExport = QGraphicsProxyWidget()
		self.exportAllButton = QPushButton('Export Data')
		self.proxyExport.setWidget(self.exportAllButton)
		self.exportAllButton.clicked.connect(self.exportAllOnClick)

		# Create button to export data to csv
		self.proxySave = QGraphicsProxyWidget()
		self.saveBLEButton = QPushButton('Save BLE config')
		self.proxySave.setWidget(self.saveBLEButton)
		self.saveBLEButton.clicked.connect(self.saveBLEOnClick)

		# List view for showing the screws
		self.proxyList = QGraphicsProxyWidget()
		self.list = QListWidget()
		self.list.installEventFilter(self)
		self.list.itemSelectionChanged.connect(self.listItemClicked)
		self.proxyList.setWidget(self.list)

		# Add all buttons to the window
		self.p1 = self.window.addLayout(row=0, col=0)
		self.p1.addItem(self.proxyAdd, row=1, col=1)
		self.p1.addItem(self.proxyAvailable, row=1, col=2)
		self.p1.addItem(self.proxyNewRecord, row=1, col=3)
		self.p1.addItem(self.proxyExport, row=1, col=4)
		self.p1.addItem(self.proxySave, row=1, col=5)

		# Add plot
		self.p2 = self.window.addLayout(row=1, col=1)
		self.p2.addItem(self.graphWidget, row=1, col=1)

		# Add list of sensors
		self.p3 = self.window.addLayout(row=1, col=0)
		self.p3.addItem(self.proxyList, row=1, col=1)

		self.qGraphicsGridLayout = self.window.ci.layout
		self.qGraphicsGridLayout.setColumnStretchFactor(0, 1)
		self.qGraphicsGridLayout.setColumnStretchFactor(1, 3)
		#
		# self.qapp = QApplication([])
		# self.qapp.processEvents()

		# List of screws
		self.numScrew = 0

		# Refreshing function
		self.timer = QTimer()
		self.timer.setTimerType(Qt.PreciseTimer)
		self.timer.timeout.connect(self.refreshingFunction)
		self.timer.setInterval(10)
		self.timer.start()

	def eventFilter(self, source, event):
		if event.type() == QEvent.ContextMenu and source is self.list:
			menu = QMenu()
			menu.addAction(QAction('Remove', menu, checkable=True))
			menu.triggered[QAction].connect(lambda i: self.contextMenuList(i, source.itemAt(event.pos()).text()))

			if menu.exec_(event.globalPos()):
				item = source.itemAt(event.pos())
			return True
		return super().eventFilter(source, event)

	def contextMenuList(self, q, text):
		if q.text() == 'Remove':
			self.list.clear()
			delEntry = None
			for i in self.screws:
				if text == self.screws[i].name:
					delEntry = text
					self.numScrew -= 1
				else:
					self.list.addItem(self.screws[i].name)
			del self.screws[delEntry]

	def addScrewOnClick(self):
		self.windowAddScrew = AddScrewWindow()
		self.windowAddScrew.messageNewClientMAC.connect(self._newScrew)

	def availableBLEOnClick(self):
		self.windowAvailableBLE = AvailableBLEWindow()
		self.windowAvailableBLE.messageNewClientMAC.connect(self._newScrew)

	def startNewRecordingOnClick(self):
		if len(self.screws) > 0:
			res = pd.DataFrame()
			for screw in self.screws:
				mac = self.screws[screw].mac
				dfCopy = self.screws[screw].data.copy()
				for i in dfCopy.columns:
					dfCopy.columns[i] = mac + "_" + dfCopy.columns[i]
				res = pd.concat([res, dfCopy], axis=1)
				self.screws[screw].data = pd.DataFrame()

			res.to_csv('data.csv')

			item = self.list.currentItem()
			if item:
				for screw in self.screws:
					if self.screws[screw].name == item.text():
						self.updatePlot(self.screws[screw])

	def exportAllOnClick(self):
		if len(self.screws) > 0:
			res = pd.DataFrame()
			for screw in self.screws:
				mac = self.screws[screw].mac
				dfCopy = self.screws[screw].data.copy()
				for i in dfCopy.columns:
					dfCopy.columns[i] = mac + "_" + dfCopy.columns[i]
				res = pd.concat([res, dfCopy], axis=1)

			res.to_csv('data.csv')
			item = self.list.currentItem()
			if item:
				for screw in self.screws:
					if self.screws[screw].name == item.text():
						self.updatePlot(self.screws[screw])

	def saveBLEOnClick(self):
		listConf = []
		for screw in self.screws:
			listConf.append(screw.mac)
		json_str = json.dumps(listConf)

		with open('bleConf.json', 'w') as f:
			f.write(json_str)
			f.close()

		print("Save BLE configuration")

	def listItemClicked(self):
		item = self.list.currentItem()
		for screw in self.screws:
			if self.screws[screw].name == item.text():
				self.updatePlot(self.screws[screw])

	def _newScrew(self, screwMAC: str):
		if screwMAC not in self.screws.keys():
			newScrew = Screw(screwMAC, 'Screw' + str(self.numScrew), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
			self.screws[screwMAC] = newScrew
			self.list.addItem(newScrew.name)
			self.numScrew += 1

	def updatePlot(self, screw: Screw):
		if len(screw.dataStrain1) != 0:
			self.strain1.setData(screw.dataStrain1['seconds'].values, screw.dataStrain1['strain1'].values)
		if len(screw.dataStrain2) != 0:
			self.strain2.setData(screw.dataStrain2['seconds'].values, screw.dataStrain2['strain2'].values)
		if len(screw.dataStrain3) != 0:
			self.strain3.setData(screw.dataStrain3['seconds'].values, screw.dataStrain3['strain3'].values)
		if len(screw.dataTemp1) != 0:
			self.temperature.setData(screw.dataTemp1['seconds'].values, screw.dataTemp1['temp'].values)

	@qasync.asyncSlot()
	async def deviceFound(self, device: BLEDevice, advertisement_data: AdvertisementData):
		if device.address in self.screws.keys():
			screw = self.screws[device.address]
			try:
				ownData = advertisement_data.manufacturer_data[0x0C3F]
				print(f'{advertisement_data}')
				screw.bleClient = None
				screw.connecting = False
				sizeFloat = struct.calcsize('f')
				mode = struct.unpack_from('B', ownData, offset=sizeFloat * 4)
				strain1 = struct.unpack_from('f', ownData, offset=sizeFloat * 0)
				strain2 = struct.unpack_from('f', ownData, offset=sizeFloat * 1)
				strain3 = struct.unpack_from('f', ownData, offset=sizeFloat * 2)
				temp = struct.unpack_from('f', ownData, offset=sizeFloat * 3)

				screw.dataStrain1 = pd.concat([screw.dataStrain1, pd.DataFrame(
					{'strain1': strain1[0], 'seconds': datetime.now().timestamp() - self.initTime,
					 'date': datetime.now()}, index=[0])], ignore_index=True)

				screw.dataStrain2 = pd.concat([screw.dataStrain1, pd.DataFrame(
					{'strain2': strain2[0], 'seconds': datetime.now().timestamp() - self.initTime,
					 'date': datetime.now()}, index=[0])], ignore_index=True)

				screw.dataStrain3 = pd.concat([screw.dataStrain1, pd.DataFrame(
					{'strain3': strain3[0], 'seconds': datetime.now().timestamp() - self.initTime,
					 'date': datetime.now()}, index=[0])], ignore_index=True)

				screw.dataTemp1 = pd.concat([screw.dataStrain1, pd.DataFrame(
					{'temp': temp[0], 'seconds': datetime.now().timestamp() - self.initTime,
					 'date': datetime.now()}, index=[0])], ignore_index=True)

				item = self.list.currentItem()
				if item:
					for screw in self.screws:
						if self.screws[screw].name == item.text():
							self.updatePlot(self.screws[screw])

			except KeyError:
				# In order to avoid some unknown errors with wrong advertisements coming from the MCU, check service uuid
				if '68708bcb-6c81-413d-b35d-ca6cd122babf' in advertisement_data.service_uuids:
					print(f'{advertisement_data}')
					print(f'{not screw.bleClient} {screw.connecting}')
					# Continuous mode (if it's first time or client is not connected yet)
					if not screw.bleClient and not screw.connecting:
						screw.connecting = True
						await self.handle_connect(device.address, screw)
					elif screw.bleClient and screw.bleClient.device.is_connected:
						screw.connecting = False

	@qasync.asyncSlot()
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

	@qasync.asyncSlot()
	async def refreshingFunction(self):
		await self.scanner.start()

	def digestNewDataStrain1(self, data: bytes, screw: Screw):
		print('Strain1')
		value = conversionFromBytes(data)
		for mac in self.screws:
			i = self.screws[mac]
			if mac == screw.mac:
				i.dataStrain1 = pd.concat([i.dataStrain1, pd.DataFrame(
					{'strain1': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()},
					index=[0])], ignore_index=True)
			if self.list.currentItem() and i.name == self.list.currentItem().text():
				self.updatePlot(i)

	def digestNewDataStrain2(self, data: bytes, screw: Screw):
		print('Strain2')
		value = conversionFromBytes(data)
		for mac in self.screws:
			i = self.screws[mac]
			if mac == screw.mac:
				i.dataStrain2 = pd.concat([i.dataStrain2, pd.DataFrame(
					{'strain2': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()},
					index=[0])], ignore_index=True)
			if self.list.currentItem() and i.name == self.list.currentItem().text():
				self.updatePlot(i)

	def digestNewDataStrain3(self, data: bytes, screw: Screw):
		print('Strain3')
		value = conversionFromBytes(data)
		for mac in self.screws:
			i = self.screws[mac]
			if mac == screw.mac:
				i.dataStrain3 = pd.concat([i.dataStrain3, pd.DataFrame(
					{'strain3': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()},
					index=[0])], ignore_index=True)
			if self.list.currentItem() and i.name == self.list.currentItem().text():
				self.updatePlot(i)

	def digestNewDataTemperature(self, data: bytes, screw: Screw):
		print('Temp')
		value = conversionFromBytes(data)
		for mac in self.screws:
			i = self.screws[mac]
			if mac == screw.mac:
				i.dataTemp1 = pd.concat([i.dataTemp1, pd.DataFrame(
					{'temp': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()},
					index=[0])], ignore_index=True)
			if self.list.currentItem() and i.name == self.list.currentItem().text():
				self.updatePlot(i)


def conversionFromBytes(data: bytes):
	return struct.unpack('<f', data)[0]


if __name__ == "__main__":
	app = QApplication(sys.argv)
	loop = qasync.QEventLoop(app)
	asyncio.set_event_loop(loop)
	ui = MainWindow()

	with loop:
		loop.run_forever()
