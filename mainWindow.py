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
from mbedtls import cipher


class MainWindow(QMainWindow):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.initTime = datetime.now().timestamp()
		self.scanner = BleakScanner(detection_callback=self.deviceFound)
		self.screws = {}
		self.aes = cipher.AES.new(b'66556a586e32723566556a586e327235', cipher.MODE_ECB, iv=b'')

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
		# No connect function. PlotUpdate function will look at the selected item
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

		# Data retrieval clock function
		self.dataRetrievalTimer = QTimer()
		self.dataRetrievalTimer.setTimerType(Qt.PreciseTimer)
		self.dataRetrievalTimer.timeout.connect(self.dataRefreshingFunction)
		self.dataRetrievalTimer.setInterval(50)
		self.dataRetrievalTimer.start()

	def eventFilter(self, source, event):
		"""
		Function that rules behavior of right-click on list
		:param source:
		:param event:
		:return:
		"""
		if event.type() == QEvent.ContextMenu and source is self.list:
			menu = QMenu()
			menu.addAction(QAction('Remove', menu, checkable=True))
			menu.triggered[QAction].connect(lambda i: self.contextMenuList(i, source.itemAt(event.pos()).text()))

			if menu.exec_(event.globalPos()):
				item = source.itemAt(event.pos())
			return True
		return super().eventFilter(source, event)

	def contextMenuList(self, q, text):
		"""
		Function called as callback when selection in right-click menu from list is performed
		:param q: Option that has been clicked
		:param text: Tag of right-clicked element
		"""
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
		"""
		Add Screw button callback
		"""
		self.windowAddScrew = AddScrewWindow()
		self.windowAddScrew.messageNewClientMAC.connect(self._newScrew)

	def availableBLEOnClick(self):
		"""
		Explore BLE button callback
		"""
		self.windowAvailableBLE = AvailableBLEWindow()
		self.windowAvailableBLE.messageNewClientMAC.connect(self._newScrew)

	def startNewRecordingOnClick(self):
		"""
		Restart button callback
		"""
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

	def exportAllOnClick(self):
		"""
		Export button callback
		"""
		if len(self.screws) > 0:
			res = pd.DataFrame()
			for screw in self.screws:
				mac = self.screws[screw].mac
				dfCopy = self.screws[screw].data.copy()
				for i in dfCopy.columns:
					dfCopy.columns[i] = mac + "_" + dfCopy.columns[i]
				res = pd.concat([res, dfCopy], axis=1)

			res.to_csv('data.csv')

	def saveBLEOnClick(self):
		"""
		Save conf button callback
		"""
		listConf = []
		for screw in self.screws:
			listConf.append(screw.mac)
		json_str = json.dumps(listConf)

		with open('bleConf.json', 'w') as f:
			f.write(json_str)
			f.close()

		print("Save BLE configuration")

	def _newScrew(self, screwMAC: str):
		"""
		Private method used as callback when new screw is introduced through the explore ble and add screw signals
		:param screwMAC: MAC address to be added
		"""
		# If not already in the list, add to it
		if screwMAC not in self.screws.keys():
			newScrew = Screw(screwMAC, 'Screw' + str(self.numScrew), pd.DataFrame())
			self.screws[screwMAC] = newScrew
			self.list.addItem(newScrew.name)
			self.numScrew += 1

	def updatePlot(self):
		"""
		Function that updates the plot
		"""
		item = self.list.currentItem()
		screw = None
		if item:
			# Search for selected screw
			for screw in self.screws:
				if self.screws[screw].name == item.text():
					screw = self.screws[screw]

		# If found, refresh plot
		if screw:
			if len(screw.data) != 0:
				self.strain1.setData(screw.data['seconds'].values, screw.data['strain1'].values)
				self.strain2.setData(screw.data['seconds'].values, screw.data['strain2'].values)
				self.strain3.setData(screw.data['seconds'].values, screw.data['strain3'].values)
				self.temperature.setData(screw.data['seconds'].values, screw.data['temp'].values)

	@qasync.asyncSlot()
	async def deviceFound(self, device: BLEDevice, advertisement_data: AdvertisementData):
		"""
		Scanner callback function
		:param device:
		:param advertisement_data: formatted advertisement_data
		"""
		# If MAC of received data is inside the track ones, proceed
		if device.address in self.screws.keys():
			screw = self.screws[device.address]
			try:
				# If manufacturer_data is 0x0C3F-> periodic mode, else -> continuous
				ownData = advertisement_data.manufacturer_data[0x0C3F]
				print(f'{datetime.now().timestamp()} - > {advertisement_data} with manufacturer_data {advertisement_data.manufacturer_data}')
				screw.bleClient = None
				screw.connecting = False
				strain1, strain2, strain3, temp = self.decryptIncomingData(ownData)

				screw.data = pd.concat([screw.data, pd.DataFrame(
					{'strain1': strain1, 'strain2': strain2, 'strain3': strain3, 'temp': temp,
					 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()},
					index=[0])], ignore_index=True)

				self.updatePlot()

			except KeyError:
				# In order to avoid some unknown errors with wrong advertisements coming from the MCU, check service uuid
				if '68708bcb-6c81-413d-b35d-ca6cd122babf' in advertisement_data.service_uuids:
					print(f'{datetime.now().timestamp()} - > {advertisement_data}')
					# Continuous mode (if it's first time or client is not connected yet)
					if not screw.bleClient and not screw.connecting:
						screw.connecting = True
						await self.handle_connect(device.address, screw)
					elif screw.bleClient and screw.bleClient.device.is_connected:
						screw.connecting = False

	@qasync.asyncSlot()
	async def handle_connect(self, address: str, screw: Screw):
		"""
		Function to connect and build ble client
		:param address: MAC address
		:param screw: Screw object
		"""
		device = await BleakScanner.find_device_by_address(address)
		if isinstance(device, BLEDevice):
			client = QBleakClient(device)
			await client.build_client()
			screw.bleClient = client
			client.messageChangedData.connect(lambda data: self.digestNewData(data, screw))

	@qasync.asyncSlot()
	async def dataRefreshingFunction(self):
		"""
		Function to be called periodically to search for advertisement packets
		"""
		try:
			await self.scanner.start()
		except asyncio.CancelledError:
			pass

	def digestNewData(self, data: bytes, screw: Screw):
		"""
		Notify event callback function
		:param data: raw data (that contains measurements)
		:param screw: Screw object
		"""
		for mac in self.screws:
			i = self.screws[mac]
			if mac == screw.mac:
				strain1, strain2, strain3, temp = self.decryptIncomingData(data)
				i.data = pd.concat([i.data, pd.DataFrame(
					{'strain1': strain1, 'strain2': strain2, 'strain3': strain3, 'temp':temp,
					 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()},
					index=[0])], ignore_index=True)
				self.updatePlot()

	def decryptIncomingData(self, ownData):
		"""
		Function that tries to decrypt data encrypted as AES ECB
		:param ownData: Encrypted data
		:return: decrypted and unpacked data
		"""
		# TODO
		# NOT WORKING

		# print(f'received data {ownData.hex()}')
		# x = b''
		# for i in range(4):
		# 	x = b''.join([x, ownData[i*4:(i+1)*4][::-1]])
		# print(f'flipped data {x.hex()}')
		# decryptedData = self.aes.decrypt(x)
		# print(f'decrypted data {decryptedData.hex()}')
		strain1 = struct.unpack_from('<f', ownData, 0)
		strain2 = struct.unpack_from('<f', ownData, 4)
		strain3 = struct.unpack_from('<f', ownData, 8)
		temp = struct.unpack_from('<f', ownData, 12)
		print(f'strain1 {strain1}, strain2 {strain2}, strain3 {strain3}, temp {temp}')
		return strain1, strain2, strain3, temp


if __name__ == "__main__":
	app = QApplication(sys.argv)
	loop = qasync.QEventLoop(app)
	asyncio.set_event_loop(loop)
	ui = MainWindow()

	with loop:
		loop.run_forever()
