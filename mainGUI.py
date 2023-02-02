import queue

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
from queue import Queue

screws = {}


class MainWindow(QMainWindow):

	def __init__(self, queueData: Queue, queueScrewsBLEToGUI: Queue, queueScrewsGUIToBLE: Queue, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.queueData = queueData
		self.queueScrewsBLEToGUI = queueScrewsBLEToGUI
		self.queueScrewsGUIToBLE = queueScrewsGUIToBLE

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

		# List of screws
		self.numScrew = 0

		# Refreshing function
		self.timer = QTimer()
		self.timer.timeout.connect(self.refreshingFunction)
		self.timer.setInterval(100)
		self.timer.start()

	def manageQueues(self):
		actualSize = self.queueData.qsize()
		for i in range(actualSize):
			try:
				macData = self.queueData.get(block=False)  # {mac: {sensor: df}}
			except queue.Empty:
				return

			for mac in macData:
				if mac in screws:
					screw = screws[mac]
					for tag in macData[mac]:
						df = macData[mac][tag]
						if tag == 'strain1':
							screw.dataStrain1 = pd.concat([screw.dataStrain1, df], ignore_index=True)
							return
						if tag == 'strain2':
							screw.dataStrain2 = pd.concat([screw.dataStrain2, df], ignore_index=True)
							return
						if tag == 'strain3':
							screw.dataStrain3 = pd.concat([screw.dataStrain3, df], ignore_index=True)
							return
						if tag == 'temp':
							screw.dataTemp1 = pd.concat([screw.dataTemp1, df], ignore_index=True)
							return

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
			for i in screws:
				if text == screws[i].name:
					delEntry = text
					self.queueScrewsBLEToGUI.put({'remove': screws[i]})
					self.numScrew -= 1
				else:
					self.list.addItem(screws[i].name)
			del screws[delEntry]

	def addScrewOnClick(self):
		self.windowAddScrew = AddScrewWindow()
		self.windowAddScrew.messageNewClientMAC.connect(self._newScrew)

	def availableBLEOnClick(self):
		self.windowAvailableBLE = AvailableBLEWindow()
		self.windowAvailableBLE.messageNewClientMAC.connect(self._newScrew)

	def startNewRecordingOnClick(self):
		if len(screws) > 0:
			res = pd.DataFrame()
			for screw in screws:
				mac = screws[screw].mac
				dfCopy = screws[screw].data.copy()
				for i in dfCopy.columns:
					dfCopy.columns[i] = mac + "_" + dfCopy.columns[i]
				res = pd.concat([res, dfCopy], axis=1)
				screws[screw].data = pd.DataFrame()

			res.to_csv('data.csv')

			item = self.list.currentItem()
			if item:
				for screw in screws:
					if screws[screw].name == item.text():
						self.updatePlot(screws[screw])

	def exportAllOnClick(self):
		if len(screws) > 0:
			res = pd.DataFrame()
			for screw in screws:
				mac = screws[screw].mac
				dfCopy = screws[screw].data.copy()
				for i in dfCopy.columns:
					dfCopy.columns[i] = mac + "_" + dfCopy.columns[i]
				res = pd.concat([res, dfCopy], axis=1)

			res.to_csv('data.csv')
			item = self.list.currentItem()
			if item:
				for screw in screws:
					if screws[screw].name == item.text():
						self.updatePlot(screws[screw])

	def saveBLEOnClick(self):
		listConf = []
		for screw in screws:
			listConf.append(screw.mac)
		json_str = json.dumps(listConf)

		with open('bleConf.json', 'w') as f:
			f.write(json_str)
			f.close()

		print("Save BLE configuration")

	def listItemClicked(self):
		item = self.list.currentItem()
		for screw in screws:
			if screws[screw].name == item.text():
				self.updatePlot(screws[screw])

	def _newScrew(self, screwMAC: str):
		if screwMAC not in screws.keys():
			newScrew = Screw(screwMAC, 'Screw' + str(self.numScrew), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
			screws[screwMAC] = newScrew
			self.queueScrewsGUIToBLE.put({'add': newScrew})
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

	def refreshingFunction(self):
		# Receive from queues
		self.manageQueues()

		# Refresh the plot
		item = self.list.currentItem()
		if item:
			for screw in screws:
				if screws[screw].name == item.text():
					self.updatePlot(screws[screw])


def mainGUI(queueData, queueScrewsBLEToGUI, queueScrewsGUIToBLE):
	app = QApplication(sys.argv)
	loop = qasync.QEventLoop(app)
	asyncio.set_event_loop(loop)
	ui = MainWindow(queueData, queueScrewsBLEToGUI, queueScrewsGUIToBLE)

	with loop:
		loop.run_forever()
