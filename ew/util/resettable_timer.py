import threading

class ResettableTimer:
    """A resettable timer may be started, stopped and restarted again.  It may be "reset" which
    will cause it start over, optionally for a different amount of time."""
    def __init__(self, time, action):
        self._time = time
        self._action = action
        self._started = False
        self._timer = None
        self._instance_lock = threading.RLock()

    def _make_timer(self):
        self._timer = threading.Timer(self._time, self._action)
        self._started = False

    def _cancel_timer(self):
        if self._timer:
            self._timer.cancel()
            self._started = False
            del self._timer
            self._timer = None

    def start(self):
        with self._instance_lock:
            if not self._started:
                self._make_timer()
                self._timer.start()
                self._started = True

    def reset(self, new_time = None):
        with self._instance_lock:
            if new_time: 
                self._time = new_time
            self.stop()
            self.start()

    def stop(self):
        with self._instance_lock:
            self._cancel_timer()

