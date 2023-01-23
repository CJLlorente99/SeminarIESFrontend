import qasync
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from bleak import BleakScanner
from functools import cached_property
from bleak.backends.device import BLEDevice
from BLEClient import QBleakClient
import sys
import pyqtgraph as pg


class AvailableBLEWindow(QMainWindow):

	messageNewClient = pyqtSignal(QBleakClient)

	def __init__(self):
		super().__init__()

		self._client = None

		# Configure graphical window
		self.window = pg.GraphicsLayoutWidget(title='Explore BLE', show=True)
		self.window.resize(700, 500)
		self.setWindowTitle("Available BLE Window")
		self.window.setBackground('black')

		# Button for refreshing
		self.proxyRefresh = QGraphicsProxyWidget()
		self.refresh_button = QPushButton("Scan Devices")
		self.refresh_button.setStyleSheet("background-color : green")
		self.proxyRefresh.setWidget(self.refresh_button)
		self.refresh_button.clicked.connect(self.handle_scan, Qt.QueuedConnection)

		# Button for connecting
		self.proxyConnect = QGraphicsProxyWidget()
		self.connect_button = QPushButton("Connect")
		self.connect_button.setStyleSheet("background-color : green")
		self.proxyConnect.setWidget(self.connect_button)
		self.connect_button.clicked.connect(self.handle_connect)

		# Devices box
		self.proxyDevices = QGraphicsProxyWidget()
		self.devices_combobox = QComboBox()
		self.devices_combobox.currentIndexChanged.connect(self.changeSelection)
		self.proxyDevices.setWidget(self.devices_combobox)

		# Add informative labels
		self.proxyLabels = QGraphicsProxyWidget()
		self.macLabel = QLabel()
		self.proxyLabels.setWidget(self.macLabel)

		# Add all buttons to the window
		self.p1 = self.window.addLayout(row=0, col=0)
		self.p1.addItem(self.proxyRefresh, row=1, col=1)
		self.p1.addItem(self.proxyConnect, row=1, col=2)

		# Add combobox
		self.p2 = self.window.addLayout(row=1, col=0)
		self.p2.addItem(self.proxyLabels, row=1, col=1)

		# Add informative labels
		self.p3 = self.window.addLayout(row=2, col=0)
		self.p3.addItem(self.proxyDevices, row=1, col=1)

		# Intentional space
		self.p4 = self.window.addLayout(row=3, col=0)

	def changeSelection(self):
		device = self.devices_combobox.currentData()
		if device and device.address and device.rssi:
			self.macLabel.setText(f'Device BLE Address: {device.address}\n'
								  f'Device RSSI: {device.rssi}')

	@cached_property
	def devices(self):
		return list()

	@property
	def current_client(self):
		return self._client

	async def build_client(self, device):
		if self._client is not None:
			await self._client.stop()
		self._client = QBleakClient(device)
		await self._client.start()
		self.messageNewClient.emit(self._client)
		self.connect_button.setStyleSheet("background-color : green")

	@qasync.asyncSlot()
	async def handle_connect(self):
		self.connect_button.setStyleSheet("background-color : red")
		device = self.devices_combobox.currentData()
		if isinstance(device, BLEDevice):
			await self.build_client(device)

	@qasync.asyncSlot()
	async def handle_scan(self, *args, **kwargs):
		self.refresh_button.setStyleSheet("background-color : red")
		self.devices.clear()
		devices = await BleakScanner.discover()
		self.devices.extend(devices)
		self.devices_combobox.clear()
		for i, device in enumerate(self.devices):
			if device and device.name and device.address:
				self.devices_combobox.insertItem(i, device.name, device)
		self.refresh_button.setStyleSheet("background-color : green")


# if __name__ == "__main__":
# 	app = QApplication(sys.argv)
# 	loop = qasync.QEventLoop(app)
# 	asyncio.set_event_loop(loop)
# 	ui = AvailableBLEWindow()
#
# 	with loop:
# 		loop.run_forever()
