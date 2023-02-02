from threading import Thread
from queue import Queue
from mainGUI import mainGUI
from mainBLE import mainBLE

if __name__ == "__main__":

	# Create queue for transmitting data
	queueData = Queue()
	# Create queue for new screws
	queueScrewsBLEToGUI = Queue()
	queueScrewsGUIToBLE = Queue()

	# Create two threads
	threadGUI = Thread(target=mainGUI, args=(queueData, queueScrewsBLEToGUI, queueScrewsGUIToBLE))
	threadBLE = Thread(target=mainBLE, args=(queueData, queueScrewsBLEToGUI, queueScrewsGUIToBLE))

	# Start the threads
	threadGUI.start()
	threadBLE.start()

	# Wait for the threads to complete
	threadGUI.join()
	threadBLE.join()
