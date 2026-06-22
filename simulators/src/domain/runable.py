from abc import abstractmethod
from threading import Thread
from time import sleep


class RunAble:

    def __init__(self, tick_interval_seconds=1):
        self._thread = Thread(target=self._run, daemon=True)
        self._running = False
        self._tick_interval_seconds = tick_interval_seconds

    def start(self):
        self._running = True
        self._thread.start()

    def stop(self):
        self._running = False

    def join(self):
        self._thread.join()

    def get_thread(self):
        return self._thread

    @abstractmethod
    def run_thread(self):
        raise NotImplemented

    def _run(self):
        while self._running:
            try:
                self.run_thread()
                sleep(self._tick_interval_seconds)
            except KeyboardInterrupt:
                self._running = False