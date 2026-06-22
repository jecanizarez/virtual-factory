from abc import abstractmethod

from src.domain.industrial import Industrial
from src.domain.runable import RunAble


class Process(RunAble, Industrial):

    def __init__(self, params: dict):
        tick_interval = params.get("tick_interval_seconds", 1)
        RunAble.__init__(self, tick_interval_seconds=tick_interval)
        Industrial.__init__(self, params)

    def run_thread(self):
        self.internal_run()

    @abstractmethod
    def internal_run(self):
        pass
