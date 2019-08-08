#!/usr/bin/python3
# -*-coding:Utf-8 -*

import logging as log
from abc import ABC, abstractmethod
from datetime import datetime

from pip._internal.utils.deprecation import deprecated

from model.AlertEnum.Day import Day
from model.AlertEnum.AlertDefinitionStatus import AlertDefinitionStatus
from model.Exception.MyException import DayTypeError
from model.decorator.MyDecorator import controller_types
from utils.DateUtils import DateUtils
from enum import Enum, auto, unique, Flag


# ALERT DEFINITION
class AlertDefinition:
    """
    This class represent how is define an Alert.
    It can be divided in 4 parts :
    - its DEFINITION - name, level, status, category...
    - its TRIGGER - calculation, values related... this part will evaluate if an Alert has to be created
    - its NOTIFICATION - email, period of watch
    - an ALERT CREATION - date, invalid data ...
    """

    def __init__(self):
        self.__watching_period = Day.NONE.value
        self.name = ""
        self.description = ""
        self.category = ""
        self.__level = None
        self.__alert_definition_status = None
        self.sending_date = None
        self.__alert_definition_flag = AlertDefinitionFlag.INACTIVE.value

    @property
    def is_active(self):
        return self.has_definition_flag(AlertDefinitionFlag.ACTIVE)

    def set_inactive(self):
        self.remove_definition_flag(AlertDefinitionFlag.ACTIVE)

    # CHECK
    def check(self, today):
        """
        Check if we have to notify this Alert
        Step 1 : Are we in watchingPeriod
        Step 2 : Are we able to Notify
        Step 3 : is there an alert situation to Send

        :param today the date you want to check
        :type today datetime

        :TODO check the order of these steps
        """
        if self.is_datetime_in_watching_period(today) and \
                (self.has_definition_flag(AlertDefinitionFlag.SAVE_ALL) or self.is_notification_allowed(today)):
            self.handle_alert_calculation(today)

    # CALCULATION
    def handle_alert_calculation(self, today):
        """
        check if we are allowed to send a new notification

        :param today the date you want to check
        :type today datetime

        :TODO write it
        """
        pass

    # NOTIFICATION
    @controller_types(datetime)
    def is_notification_allowed(self, datetime_to_check):
        """
        check if we are allowed to send a new notification

        :param datetime_to_check the date you want to check
        :type datetime_to_check datetime

        :TODO write it
        """
        pass

    # WATCHING PERIOD
    def add_day_to_watching_period(self, day):
        try:
            self.__watching_period |= day.value
        except AttributeError as error:
            log.error(error)
            raise DayTypeError(day)

    def remove_day_from_watching_period(self, day):
        self.__watching_period ^= day.value

    def reset_watching_period(self):
        self.__watching_period = Day.NONE.value

    def is_datetime_in_watching_period(self, datetime_to_check):
        """
        check if datetime is a period that we watch

        :param datetime_to_check the date you want to check
        :type datetime_to_check datetime

        """
        day = DateUtils.get_day_name(datetime_to_check)
        try:
            day = Day.get_day_by_str_name(day)
            result = self.has_day_in_watching_period(day)
            return result
        except DayTypeError as error:
            log.error(error.__str__())

    def set_watching_period(self, days_list):
        """
        Replace the current watching Period by the one in Param

        :param days_list: Period that we have to watch
        :type days_list: List of Day Element

        """
        self.reset_watching_period()
        try:
            for day in days_list:
                self.add_day_to_watching_period(day)
        except DayTypeError as error:
            log.error(error.__str__())

    def has_day_in_watching_period(self, flag):
        try:
            return bool(flag.value & self.__watching_period)
        except AttributeError:
            raise DayTypeError

    def get_watching_period(self):
        return self.__watching_period

    # DEFINITION STATUS @deprecated --> replace by a flag in AlertDefinitionFlag class
    def set_definition_status(self, status):
        self.__alert_definition_status = status

    def get_definition_status(self):
        return self.__alert_definition_status

    # LEVEL
    def set_level(self, level):
        self.__level = level

    def get_level(self):
        return self.__level

    # DEFINITION FLAG
    def has_definition_flag(self, flag):
        return bool(flag.value & self.__alert_definition_flag)

    def add_definition_flag(self, flag):
        self.__alert_definition_flag |= flag.value

    def reset_definition_flag(self):
        self.__alert_definition_flag = AlertDefinitionFlag.INACTIVE.value

    def remove_definition_flag(self, flag):
        self.__alert_definition_flag ^= flag.value

    def set_definition_flag(self, flag):
        self.reset_definition_flag()
        self.add_definition_flag(flag)

    def set_definition_flags(self, flags_list):
        self.reset_definition_flag()
        for flag in flags_list:
            self.add_definition_flag(flag)

    def get_definition_flag(self):
        return self.__alert_definition_flag


@unique
class AlertDefinitionStatus(Enum):  # USELESS --> Has Been moved to FLAG
    INACTIVE = 0
    ACTIVE = auto()
    ARCHIVE = auto()


@unique
class AlertDefinitionFlag(Flag):
    INACTIVE = 0            # Nothing
    ACTIVE = auto()        # Replace status
    SAVE_ALL = auto()      # Always calculate Alert even if notification not allowed & if alert exist, save it
    ANOTHER_FLAG = auto()  # Flag to Test - Do not forget to Refactor when change it


class AlertCalculator(ABC):

    def __init__(self):
        self.__data__
        self.__process__
        pass

    @abstractmethod
    def is_alert_situation(self):
        pass
