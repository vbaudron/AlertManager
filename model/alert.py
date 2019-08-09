#!/usr/bin/python3
# -*-coding:Utf-8 -*

import logging as log
from abc import ABC, abstractmethod
import array
import calendar
from datetime import datetime, timedelta

from model.day import Day
from model.my_exception import DayTypeError
from model.tokill.my_decorator import controller_types
from model.utility import get_day_name_from_datetime
from enum import Enum, auto, unique, Flag


# ALERT DEFINITION
@unique
class AlertDefinitionStatus(Enum):  # USELESS --> Has Been moved to FLAG
    INACTIVE = 0
    ACTIVE = auto()
    ARCHIVE = auto()


@unique
class AlertDefinitionFlag(Flag):
    INACTIVE = 0           # Nothing
    ACTIVE = auto()        # Replace status
    SAVE_ALL = auto()      # Always calculate Alert even if notification not allowed & if alert exist, save it
    ANOTHER_FLAG = auto()  # Flag to Test - Do not forget to Refactor when change it


@unique
class Level(Enum):
    LOW = 0
    HIGH = auto()

# ALERT DEFINITION CLASS
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
    def check(self, today: datetime):
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
    def handle_alert_calculation(self, today: datetime):
        """
        check if we are allowed to send a new notification

        :param today the date you want to check
        :type today datetime

        :TODO write it
        """
        pass

    # NOTIFICATION
    @controller_types(datetime)
    def is_notification_allowed(self, datetime_to_check: datetime):
        """
        check if we are allowed to send a new notification

        :param datetime_to_check the date you want to check
        :type datetime_to_check datetime

        :TODO write it
        """
        pass

    # WATCHING PERIOD
    def add_day_to_watching_period(self, day: Day):
        try:
            self.__watching_period |= day.value
        except AttributeError as error:
            log.error(error)
            raise DayTypeError(day)

    def remove_day_from_watching_period(self, day: Day):
        self.__watching_period ^= day.value

    def reset_watching_period(self):
        self.__watching_period = Day.NONE.value

    def is_datetime_in_watching_period(self, datetime_to_check: datetime):
        """
        check if datetime is a period that we watch

        :param datetime_to_check the date you want to check
        :type datetime_to_check datetime

        """
        day = get_day_name_from_datetime(datetime_to_check)
        try:
            day = Day.get_day_by_str_name(day)
            result = self.has_day_in_watching_period(day)
            return result
        except DayTypeError as error:
            log.error(error.__str__())

    def set_watching_period(self, days_list: array):
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

    def has_day_in_watching_period(self, day: Day):
        try:
            return bool(day.value & self.__watching_period)
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
    def set_level(self, level : Level):
        self.__level = level

    def get_level(self):
        return self.__level

    # DEFINITION FLAG
    def has_definition_flag(self, flag: AlertDefinitionFlag):
        return bool(flag.value & self.__alert_definition_flag)

    def add_definition_flag(self, flag: AlertDefinitionFlag):
        self.__alert_definition_flag |= flag.value

    def reset_definition_flag(self):
        self.__alert_definition_flag = AlertDefinitionFlag.INACTIVE.value

    def remove_definition_flag(self, flag: AlertDefinitionFlag):
        self.__alert_definition_flag ^= flag.value

    def set_definition_flag(self, flag: AlertDefinitionFlag):
        self.reset_definition_flag()
        self.add_definition_flag(flag)

    def set_definition_flags(self, flags_list: array):
        self.reset_definition_flag()
        for flag in flags_list:
            self.add_definition_flag(flag)

    def get_definition_flag(self):
        return self.__alert_definition_flag





class AlertCalculator(ABC):

    def __init__(self, setup: dict):
        self.setup = setup
        self._data_name = setup["data_name"]
        self._operator = MyOperator(setup["operator"])
        self._comparator = MyComparator(setup["comparator"])
        self._reference_value = setup["reference_value"]
        self._data = None   # data calculated from data_name to check
        self._value = None  # value to compare with

    def __get_all_data_in_db(self, period):
        all_data = [30, 45, 60]  # TODO : Link To DB
        return all_data

    # OPERATOR
    def __get_data(self):
        """ 
        get all data 
        """
        period = self._get_data_period()
        all_data = self.__get_all_data_in_db(period)
        return self._operator.calculate(all_data)

    @abstractmethod
    def _get_data_period(self):
        pass

    @abstractmethod
    def _get_comparative_value_from_reference(self):
        pass

    def is_alert_situation(self):
        self._data = self.__get_data()
        self._value = self._get_comparative_value_from_reference()
        return self._comparator.compare(self._data, self._value)


class ValueBasedCalculator(AlertCalculator):

    def __init__(self, setup: dict):
        super.__init__(setup)

    def _get_comparative_value_from_reference(self):
        return self._reference_value

    def _get_data_period(self):
        if self._operator is MyOperator.AVERAGE:
            pass


class PercentBasedCalculator(AlertCalculator):

    def __init__(self, setup: dict):
        super.__init__(setup)
        self.__percent_period = setup["percent_period"]

    def _get_comparative_value_from_reference(self):
        if self.__percent_period is ComparativeValueCalculator.GOAL:
            return self.__get_goal_value_in_db()
        else:
            return self.__get_value_from_past_period()


    def __get_goal_value_in_db(self):
        # TODO
        pass

    def __get_values_from_past_period(self):
        pass

    def _get_data_period(self):
        pass

    def __get_comparative_period(self):
        pass


def go_past_with_days(end_date: datetime, quantity):
    return end_date - timedelta(days=quantity)


def go_past_with_weeks(end_date: datetime, quantity):
    return end_date - timedelta(weeks=quantity)


def go_past_with_months(end_date: datetime, quantity):
    new_year = end_date.year
    if quantity >= 12:
        year = quantity // 12
        new_year -= year
        quantity = quantity % 12

    new_month = end_date.month - quantity
    if new_month < 1:
        new_year -=1
        new_month += 12

    last_day_of_month = calendar.monthrange(new_year, new_month)[1]
    print(last_day_of_month)
    new_day = min(end_date.day, last_day_of_month)
    return datetime(year=new_year, month=new_month, day=new_day)


def go_past_with_years(end_date: datetime, quantity):
    new_year = end_date.year - quantity
    last_day_of_month = calendar.monthrange(new_year, end_date.month)[1]
    new_day = min(end_date.day, last_day_of_month)
    return datetime(year=new_year, month=end_date.month, day=new_day)


class PeriodUnitDefinition(Enum):
    DAY = "DAY", go_past_with_days
    WEEK = "WEEK", go_past_with_weeks
    MONTH = "MONTH", go_past_with_months
    YEAR = "YEAR", go_past_with_years

    def __new__(cls, str_name, method):
        obj = object.__new__(cls)
        obj._value_ = str_name
        obj.go_past = method
        return obj



class PeriodDefinition:
    def __init__(self, setup: dict):
        self._unit = setup["unit"]
        self._quantity = setup["quantity"]

    def get_start_date_from_end_date(self):
        pass


class Period:
    def __init__(self, start: datetime, end: datetime):
        self.__start_date = start
        self.__end_date = end

    def get_start_date(self):
        return self.__start_date

    def get_end_date(self):
        return self.__end_date



def get_last_year_period(start_datetime: datetime, period:PeriodDefinition):
    """
    :param start_datetime datetime
    :rtype: Period
    """
    end_date = start_datetime - timedelta(years=1)
    pass


def get_previous_similar_period():
    pass


class ComparativeValueCalculator(Enum):
    PREVIOUS_PERIOD = "PREVIOUS_PERIOD", get_previous_similar_period,
    GOAL = "GOAL", None



# OPERATOR
def calculate_average(data: array):
    return sum(data) / len(data)


def find_max(data: array):
    return max(data)


def find_min(data: array):
    return min(data)


class MyOperator(Enum):
    MAX = "MAX", find_max
    MIN = "MIN", find_min
    AVERAGE = "AVERAGE", calculate_average

    def __new__(cls, str_name, method):
        obj = object.__new__(cls)
        obj._value_ = str_name
        obj.calculate = method
        return obj


# COMPARATOR
def is_sup(data, value):
    return data > value


def is_inf(data, value):
    return data < value


def equal(data, value):
    return data == value


class MyComparator(Enum):
    MAX = "SUP", is_sup
    MIN = "INF", is_inf
    AVERAGE = "EQUAL", equal

    def __new__(cls, str_name, method):
        obj = object.__new__(cls)
        obj._value_ = str_name
        obj.compare = method
        return obj








