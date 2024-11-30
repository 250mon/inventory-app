import asyncio
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, Slot, QEvent
from common.d_logger import Logs
from db.db_utils import DbUtil

logger = Logs().get_logger("main")

class AsyncHelper(QObject):
    _instance = None
    _loop = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AsyncHelper, cls).__new__(cls)
        return cls._instance

    class ReenterQtObject(QObject):
        """ This is a QObject to which an event will be posted, allowing
            asyncio to resume when the event is handled. event.fn() is
            the next entry point of the asyncio event loop. """
        def event(self, event: QEvent):
            if event.type() == QEvent.Type.User + 1:
                event.fn()
                return True
            return False

    class ReenterQtEvent(QEvent):
        """ This is the QEvent that will be handled by the ReenterQtObject.
            self.fn is the next entry point of the asyncio event loop. """
        def __init__(self, fn):
            super().__init__(QEvent.Type(QEvent.Type.User + 1))
            self.fn = fn

    def __init__(self):
        # Only initialize once
        if not hasattr(self, 'reenter_qt'):
            super().__init__()
            self.reenter_qt = self.ReenterQtObject()
            
            # Create and store the loop if not already created
            if AsyncHelper._loop is None:
                logger.debug("Creating new event loop in AsyncHelper")
                AsyncHelper._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(AsyncHelper._loop)
                logger.debug(f"AsyncHelper loop id: {id(AsyncHelper._loop)}")
                DbUtil.set_loop(AsyncHelper._loop)
            else:
                logger.debug(f"Using existing AsyncHelper loop id: {id(AsyncHelper._loop)}")
            
            self.loop = AsyncHelper._loop
            self.workers = {}
            self.done = {}

    def set_worker_entry(self, worker, entry):
        """Register a worker and its entry point
        
        Args:
            worker: Object with start_signal and done_signal
            entry: Async entry point function for this worker
        """
        worker_id = id(worker)  # Use object id as unique identifier
        
        # Disconnect existing signals if this worker was previously registered
        if worker_id in self.workers:
            old_worker = self.workers[worker_id]['worker']
            if hasattr(old_worker, "start_signal") and isinstance(old_worker.start_signal, Signal):
                old_worker.start_signal.disconnect(self.on_worker_started)
            if hasattr(old_worker, "done_signal") and isinstance(old_worker.done_signal, Signal):
                old_worker.done_signal.disconnect(self.on_worker_done)

        # Store worker and entry point
        self.workers[worker_id] = {
            'worker': worker,
            'entry': entry
        }

        # Connect signals
        if hasattr(worker, "start_signal") and isinstance(worker.start_signal, Signal):
            worker.start_signal.connect(lambda action, params=None, w=worker: 
                self.on_worker_started(action, params, w))
        if hasattr(worker, "done_signal") and isinstance(worker.done_signal, Signal):
            worker.done_signal.connect(lambda action, w=worker: 
                self.on_worker_done(action, w))

    @Slot(str, list, QObject)
    def on_worker_started(self, action: str, params: list = None, worker: QObject = None):
        """Handle worker start signal with worker identification"""
        logger.debug(f"on_worker_started... {action}")
        worker_id = id(worker)
        if worker_id not in self.workers:
            raise Exception("Worker not registered with AsyncHelper")
            
        entry = self.workers[worker_id]['entry']
        current_loop = asyncio.get_event_loop()
        logger.debug(f"Current loop id before set: {id(current_loop)}")
        logger.debug(f"Setting loop id: {id(self.loop)}")
        
        # Create a new task with explicit loop
        async def run_task():
            # Ensure the loop is set in this context
            asyncio.set_event_loop(self.loop)
            try:
                if params:
                    await entry(action, *params)
                else:
                    await entry(action)
            except Exception as e:
                logger.error(f"Task error: {e}")
                raise
        
        # Create and start the task
        task = self.loop.create_task(run_task())
        logger.debug(f"Created task with loop id: {id(task.get_loop())}")
        
        # Schedule the next iteration
        self.loop.call_soon(lambda: self.next_guest_run_schedule(action))
        self.done[action] = False
        self.loop.run_forever()

    @Slot(str, QObject)
    def on_worker_done(self, action: str, worker: QObject = None):
        """Handle worker done signal with worker identification"""
        self.done[action] = True

    def remove_worker(self, worker):
        """Unregister a worker"""
        worker_id = id(worker)
        if worker_id in self.workers:
            del self.workers[worker_id]

    def continue_loop(self, action: str):
        """Continue the asyncio event loop"""
        if not self.done[action]:
            # Ensure we're using the correct loop
            asyncio.set_event_loop(self.loop)
            self.loop.call_soon(lambda: self.next_guest_run_schedule(action))
            if not self.loop.is_running():
                self.loop.run_forever()

    def next_guest_run_schedule(self, action: str):
        """ This function serves to pause and re-schedule the guest
            (asyncio) event loop inside the host (Qt) event loop. It is
            registered in asyncio as a callback to be called at the next
            iteration of the event loop. When this function runs, it
            first stops the asyncio event loop, then by posting an event
            on the Qt event loop, it both relinquishes to Qt's event
            loop and also schedules the asyncio event loop to run again.
            Upon handling this event, a function will be called that
            resumes the asyncio event loop.
            
            The `next_guest_run_schedule` method is part of a system that allows
            asyncio and Qt event loops to coexist, where asyncio runs as a 'guest'
            inside Qt's 'host' event loop. This is necessary because both Qt and
            asyncio have their own event loops, and they need to cooperate
            without blocking each other.
            """
        # Stop the asyncio event loop
        self.loop.stop()

        # Post an event to the Qt event loop to continue the asyncio event loop
        # This event will be handled by the ReenterQtObject, which will call the
        # continue_loop method to resume the asyncio event loop.

        # self.reenter_qt is the QObject that will handle the event
        # self.ReenterQtEvent is the QEvent that will be posted to the Qt event loop
        # lambda: self.continue_loop(action) is the function that will be called
        # when the event is handled
        QApplication.postEvent(self.reenter_qt,
                               self.ReenterQtEvent(lambda: self.continue_loop(action)))
