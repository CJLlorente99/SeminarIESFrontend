from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from bleak.backends.device import BLEDevice
from bleak import BleakScanner
import qasync
from functools import cached_property


class AddScrewWindow(QMainWindow):
	messageNewClientMAC = pyqtSignal(str)

	def __init__(self):
		super().__init__()

		# Configure graphical window
		self.window = pg.GraphicsLayoutWidget(title='Add Screw', show=True)
		self.window.resize(700, 250)
		self.window.setBackground('black')

		# Buttons
		# Button to add new screw
		self.proxyAdd = QGraphicsProxyWidget()
		self.addScrewButton = QPushButton('Add Screw')
		self.addScrewButton.setStyleSheet("background-color : green")
		self.proxyAdd.setWidget(self.addScrewButton)
		self.addScrewButton.clicked.connect(self.addScrewOnClick)

		# Input
		self.proxyInput = QGraphicsProxyWidget()
		self.macInput = QLineEdit()
		self.proxyInput.setWidget(self.macInput)

		# Label
		self.proxyLabel = QGraphicsProxyWidget()
		self.labelMac = QLabel()
		self.labelMac.setFixedHeight(38)
		self.labelMac.setStyleSheet('background-color:black; color:white')
		self.labelMac.setText('Screw BLE MAC')
		self.proxyLabel.setWidget(self.labelMac)

		# Add button
		self.p1 = self.window.addLayout(row=0, col=0)
		self.p1.addItem(self.proxyAdd, row=1, col=1)

		# Add label
		self.p2 = self.window.addLayout(row=1, col=0)
		self.p2.addItem(self.proxyLabel, row=1, col=1)
		self.p2.addItem(self.proxyInput, row=1, col=2)

	@qasync.asyncSlot()
	async def addScrewOnClick(self):
		if self.macInput.text():
			self.addScrewButton.setStyleSheet("background-color : red")
			self.build_client(await BleakScanner.find_device_by_address(self.macInput.text()))

	def build_client(self, device):
		if isinstance(device, BLEDevice):
			self.messageNewClientMAC.emit(device.address)
		self.addScrewButton.setStyleSheet("background-color : green")
