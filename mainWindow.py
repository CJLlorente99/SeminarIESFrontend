import math
from PyQt5.QtCore import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from addScrewWindow import AddScrewWindow
from availableBLEWindow import AvailableBLEWindow
import sys
from BLEClient import QBleakClient
import qasync
import asyncio
from screw import Screw
import pandas as pd
import json
import struct
from datetime import datetime

screws = []


class MainWindow(QMainWindow):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.initTime = datetime.now().timestamp()

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

	def eventFilter(self, source, event):
		if event.type() == QEvent.ContextMenu and source is self.list:
			menu = QMenu()
			menu.addAction(QAction('Reconnect', menu, checkable=True))
			menu.addAction(QAction('Disconnect', menu, checkable=True))
			menu.addAction(QAction('AlwaysConnectedMode', menu, checkable=True))
			menu.addAction(QAction('Remove', menu, checkable=True))
			menu.triggered[QAction].connect(lambda i: self.contextMenuList(i, source.itemAt(event.pos()).text()))

			if menu.exec_(event.globalPos()):
				item = source.itemAt(event.pos())
			return True
		return super().eventFilter(source, event)

	def contextMenuList(self, q, text):
		if q.text() == 'Reconnect':
			for i in screws:
				if text == i.name:
					i.qBleakClient.reconnect()
			print(q.text())
		elif q.text() == 'Disconnect':
			for i in screws:
				if text == i.name:
					i.qBleakClient.stop()
			print(q.text())
		elif q.text() == 'AlwaysConnectedMode':
			for i in screws:
				if text == i.name:
					i.qBleakClient.alwaysConnected = not i.qBleakClient.alwaysConnected
			print(q.text())
		elif q.text() == 'Remove':
			self.list.clear()
			for i in screws:
				if text == i.name:
					i.qBleakClient.stop()
					screws.remove(i)
					self.numScrew -= 1
				else:
					self.list.addItem(i.name)

	def addScrewOnClick(self):
		self.windowAddScrew = AddScrewWindow()
		self.windowAddScrew.messageNewClient.connect(self._newScrew)

	def availableBLEOnClick(self):
		self.windowAvailableBLE = AvailableBLEWindow()
		self.windowAvailableBLE.messageNewClient.connect(self._newScrew)

	def startNewRecordingOnClick(self):
		res = pd.DataFrame()
		item = self.list.currentItem()

		if len(screws) > 0:
			for screw in screws:
				name = screw.name
				res = pd.concat([res, screw.dataStrain1], axis=1)
				res.rename({'data': name + '_strain1', 'seconds': name + '_strain1_seconds', 'date': name + '_strain1_date'}, axis=1, inplace=True)
				res = pd.concat([res, screw.dataStrain2], axis=1)
				res.rename({'data': name + '_strain2', 'seconds': name + '_strain2_seconds', 'date': name + '_strain2_date'}, axis=1, inplace=True)
				res = pd.concat([res, screw.dataStrain3], axis=1)
				res.rename({'data': name + '_strain3', 'seconds': name + '_strain3_seconds', 'date': name + '_strain3_date'}, axis=1, inplace=True)
				res = pd.concat([res, screw.dataTemperature], axis=1)
				res.rename({'data': name + '_temperature', 'seconds': name + '_temperature_seconds', 'date': name + '_temperature_date'}, axis=1, inplace=True)
				screw.dataStrain1 = pd.DataFrame()
				screw.dataStrain2 = pd.DataFrame()
				screw.dataStrain3 = pd.DataFrame()
				screw.dataTemperature = pd.DataFrame()

				self.strain1.setData([0], [0])
				self.strain2.setData([0], [0])
				self.strain3.setData([0], [0])
				self.temperature.setData([0], [0])
		res.to_csv('data.csv')

	def exportAllOnClick(self):
		res = pd.DataFrame()
		for screw in screws:
			name = screw.name
			res = pd.concat([res, screw.dataStrain1], axis=1)
			res.rename(
				{'data': name + '_strain1', 'seconds': name + '_strain1_seconds', 'date': name + '_strain1_date'},
				axis=1, inplace=True)
			res = pd.concat([res, screw.dataStrain2], axis=1)
			res.rename(
				{'data': name + '_strain2', 'seconds': name + '_strain2_seconds', 'date': name + '_strain2_date'},
				axis=1, inplace=True)
			res = pd.concat([res, screw.dataStrain3], axis=1)
			res.rename(
				{'data': name + '_strain3', 'seconds': name + '_strain3_seconds', 'date': name + '_strain3_date'},
				axis=1, inplace=True)
			res = pd.concat([res, screw.dataTemperature], axis=1)
			res.rename({'data': name + '_temperature', 'seconds': name + '_temperature_seconds',
						'date': name + '_temperature_date'}, axis=1, inplace=True)
		res.to_csv('data.csv')
		item = self.list.currentItem()
		for i in screws:
			if i.name == item.text():
				self.updatePlot(i)

	def saveBLEOnClick(self):
		listConf = []
		for screw in screws:
			listConf.append(screw.qBleakClient)
		json_str = json.dumps(listConf)

		with open('bleConf.json', 'w') as f:
			f.write(json_str)
			f.close()

		print("Save BLE configuration")

	def listItemClicked(self):
		item = self.list.currentItem()
		for screw in screws:
			if screw.name == item.text():
				self.updatePlot(screw)

	def _newScrew(self, screw: QBleakClient):
		newScrew = Screw(screw, 'Screw' + str(self.numScrew), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
		screws.append(newScrew)
		screw.messageChangedStrain1.connect(lambda i: self.digestNewDataStrain1(i, newScrew))
		screw.messageChangedStrain2.connect(lambda i: self.digestNewDataStrain2(i, newScrew))
		screw.messageChangedStrain3.connect(lambda i: self.digestNewDataStrain3(i, newScrew))
		screw.messageChangedTemp1.connect(lambda i: self.digestNewDataTemperature(i, newScrew))
		self.list.addItem(newScrew.name)
		self.numScrew += 1

	def updatePlot(self, screw: Screw):
		if len(screw.dataStrain1) != 0 and len(screw.dataStrain2) != 0 and len(screw.dataStrain3) != 0\
				and len(screw.dataTemperature) != 0:
			self.strain1.setData(screw.dataStrain1['seconds'].values, screw.dataStrain1['data'].values)
			self.strain2.setData(screw.dataStrain2['seconds'].values, screw.dataStrain2['data'].values)
			self.strain3.setData(screw.dataStrain3['seconds'].values, screw.dataStrain3['data'].values)
			self.temperature.setData(screw.dataTemperature['seconds'].values, screw.dataTemperature['data'].values)

	def digestNewDataStrain1(self, data: bytes, screw: Screw):
		print('Strain1')
		value = conversionFromBytes(data)
		for i in screws:
			if i.name == screw.name:
				i.dataStrain1 = pd.concat([i.dataStrain1, pd.DataFrame({'data': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()}, index=[0])], ignore_index=True)
			if self.list.currentItem() and i.name == self.list.currentItem().text():
				self.updatePlot(i)

	def digestNewDataStrain2(self, data: bytes, screw: Screw):
		print('Strain2')
		value = conversionFromBytes(data)
		for i in screws:
			if i.name == screw.name:
				i.dataStrain2 = pd.concat([i.dataStrain2, pd.DataFrame({'data': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()}, index=[0])], ignore_index=True)
			if self.list.currentItem() and i.name == self.list.currentItem().text():
				self.updatePlot(i)

	def digestNewDataStrain3(self, data: bytes, screw: Screw):
		print('Strain3')
		value = conversionFromBytes(data)
		for i in screws:
			if i.name == screw.name:
				i.dataStrain3 = pd.concat([i.dataStrain3, pd.DataFrame({'data': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()}, index=[0])], ignore_index=True)
			if self.list.currentItem() and i.name == self.list.currentItem().text():
				self.updatePlot(i)

	def digestNewDataTemperature(self, data: bytes, screw: Screw):
		print('Temp')
		value = conversionFromBytes(data)
		for i in screws:
			if i.name == screw.name:
				i.dataTemperature = pd.concat([i.dataTemperature, pd.DataFrame({'data': value, 'seconds': datetime.now().timestamp() - self.initTime, 'date': datetime.now()}, index=[0])], ignore_index=True)
			if self.list.currentItem() and i.name == self.list.currentItem().text():
				self.updatePlot(i)


def conversionFromBytes(data: bytes):
	return struct.unpack('>f', data)[0]


if __name__ == "__main__":
	app = QApplication(sys.argv)
	loop = qasync.QEventLoop(app)
	asyncio.set_event_loop(loop)
	ui = MainWindow()

	with loop:
		loop.run_forever()
