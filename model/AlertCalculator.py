from abc import ABC, abstractmethod


class AlertCalculator(ABC):

    def __init__(self):
        self.__data__
        self.__process__
        pass

    @abstractmethod
    def is_alert_situation(self):
        pass