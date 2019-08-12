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


# -----------------------------------------------   ALERT DEFINITION   -------------------------------------------------

# STATUS
@unique
class AlertDefinitionStatus(Enum):  # USELESS --> Has Been moved to FLAG
    INACTIVE = 0
    ACTIVE = auto()
    ARCHIVE = auto()

# FLAG
@unique
class AlertDefinitionFlag(Flag):
    INACTIVE = 0           # Nothing
    ACTIVE = auto()        # Replace status
    SAVE_ALL = auto()      # Always calculate Alert even if notification not allowed & if alert exist, save it
    ANOTHER_FLAG = auto()  # Flag to Test - Do not forget to Refactor when change it

# LEVEL
@unique
class Level(Enum):
    LOW = 0
    HIGH = auto()


# CLASS
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
    def is_active(self) -> bool:
        return self.has_definition_flag(AlertDefinitionFlag.ACTIVE)

    def set_inactive(self) -> None:
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
    def is_notification_allowed(self, datetime_to_check: datetime) -> bool:
        """
        check if we are allowed to send a new notification

        :param datetime_to_check the date you want to check
        :type datetime_to_check datetime

        :TODO write it
        """
        pass

    # WATCHING PERIOD
    def add_day_to_watching_period(self, day: Day) -> None:
        try:
            self.__watching_period |= day.value
        except AttributeError as error:
            log.error(error)
            raise DayTypeError(day)

    def remove_day_from_watching_period(self, day: Day) -> None:
        self.__watching_period ^= day.value

    def reset_watching_period(self) -> None:
        self.__watching_period = Day.NONE.value

    def is_datetime_in_watching_period(self, datetime_to_check: datetime) -> bool:
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

    def set_watching_period(self, days_list: array) -> None:
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

    def has_day_in_watching_period(self, day: Day) -> bool:
        try:
            return bool(day.value & self.__watching_period)
        except AttributeError:
            raise DayTypeError

    def get_watching_period(self) -> "self.__watching_period":
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


# ---------------------------------------------------   OPERATOR   -----------------------------------------------------

def calculate_average(data: array):
    return sum(data) / len(data)


def find_max(data: array):
    return max(data)


def find_min(data: array):
    return min(data)


# CLASS
class MyOperator(Enum):
    MAX = "MAX", find_max
    MIN = "MIN", find_min
    AVERAGE = "AVERAGE", calculate_average

    def __new__(cls, str_name, method):
        obj = object.__new__(cls)
        obj._value_ = str_name
        obj.calculate = method
        return obj


# --------------------------------------------------   COMPARATOR   ----------------------------------------------------

def is_sup(data, value):
    return data > value


def is_inf(data, value):
    return data < value


def equal(data, value):
    return data == value


# CLASS
class MyComparator(Enum):
    SUP = "SUP", is_sup
    INF = "INF", is_inf
    EQUAL = "EQUAL", equal

    def __new__(cls, str_name, method):
        obj = object.__new__(cls)
        obj._value_ = str_name
        obj.compare = method
        return obj


# -------------------------------------------------   PERIOD Class   ---------------------------------------------------

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
        new_year -= 1
        new_month += 12

    last_day_of_month = calendar.monthrange(new_year, new_month)[1]
    new_day = min(end_date.day, last_day_of_month)
    return datetime(year=new_year, month=new_month, day=new_day)


def go_past_with_years(end_date: datetime, quantity):
    new_year = end_date.year - quantity
    last_day_of_month = calendar.monthrange(new_year, end_date.month)[1]
    new_day = min(end_date.day, last_day_of_month)
    return datetime(year=new_year, month=end_date.month, day=new_day)


class PeriodUnitDefinition(Enum):
    """
       Represent units of period available
       value : represent the String associated to the period - it is the KEY in json file
       go_past : it is the method associated to calculate the start date from the end_date
   """
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

    _unit: PeriodUnitDefinition
    _quantity: int

    def __init__(self, unit: PeriodUnitDefinition, quantity: int):
        self._unit = unit
        self._quantity = quantity

    def get_start_date_from_end_date(self, end_date: datetime):
        return self._unit.go_past(end_date=end_date, quantity=self._quantity)

    def get_unit(self):
        return self._unit

    def get_quantity(self):
        return self._quantity

# CLASS
class Period:
    """
        Represent a time period.
    """

    __start_date: datetime
    __end_date: datetime

    def __init__(self, start: datetime, end: datetime):
        self.__start_date = start
        self.__end_date = end

    def get_start_date(self):
        return self.__start_date

    def get_end_date(self):
        return self.__end_date


# ---------------------------------------------------   FACTORY   ------------------------------------------------------


# -------------- [ PERIOD ] --------------

class PeriodGenerator(ABC):

    _period: Period

    def get_pertinent_period(self):
        return self._period


class LastCheckBasedPeriod(PeriodGenerator):

    def __init__(self, last_check: datetime, today: datetime) -> None:
        super().__init__()
        self._period = Period(start=last_check, end=today)


class UserBasedPeriod(PeriodGenerator):

    __period_definition: PeriodDefinition

    def __init__(self, today: datetime, user_data: dict) -> None:
        super().__init__()
        self.generate_period_definition(unit=user_data["unit"], quantity=user_data["quantity"])
        self.generate_period(today=today)

    def generate_period_definition(self, unit: str, quantity: int):
        period_unit = PeriodUnitDefinition(unit)
        self.__period_definition = PeriodDefinition(period_unit=period_unit, quantity=quantity)

    def generate_period(self, today: datetime):
        start_date = self.__period_definition.get_start_date_from_end_date(end_date=today)
        self._period = Period(start=start_date, end=today)


class NoPeriodBased(PeriodGenerator):
    def __init__(self, user_data: dict) -> None:
        super().__init__()
        self._period = None


# -------------- [ PERCENT VALUE ] --------------

class ValueToCompareModifier(ABC):

    PERCENT = "PERCENT"
    VALUE = "VALUE"

    _percent: int

    def calculate_value_to_compare(self, value_base) -> "value to compare data with":
        return (self._percent / 100) * value_base


class FullValue(ValueToCompareModifier):

    def __init__(self) -> None:
        super().__init__()
        self._percent = 100


class PercentValue(ValueToCompareModifier):

    def __init__(self, percent) -> None:
        super().__init__()
        self._percent = percent


# -------------- [ VALUE GENERATOR] --------------

class ValueGenerator(ABC):

    SIMPLE_DB_BASED_VALUE = "SIMPLE_DB_BASED_VALUE"
    PERIOD_BASED_VALUE = "PERIOD_BASED_VALUE"

    _value: float

    def get_value(self):
        return self._value


class UserBaseValueGenerator(ValueGenerator):

    def __init__(self, user_data: int) -> None:
        super().__init__()
        self._value = user_data


class DataBaseValue(ABC, ValueGenerator):

    def __init__(self, conn_info: dict) -> None:
        super().__init__()
        self.connect(conn_info)

    def connect(self, conn_info: dict): # TODO
        pass

    @abstractmethod
    def get_value_in_db(self):
        raise NotImplementedError


class SimpleDBBasedValueGenerator(DataBaseValue): # GOAL

    def __init__(self, conn_info: dict) -> None:
        super().__init__(conn_info=conn_info)
        self.get_value_in_db()

    def get_value_in_db(self):
        pass #TODO


class PeriodBasedValueGenerator(DataBaseValue):

    __period: Period

    def __init__(self, conn_info: dict, user_data: dict, today: datetime) -> None:
        super().__init__(conn_info=conn_info)
        self.generate_period(user_data=user_data, today=today)
        self.get_value_in_db()

    def generate_period(self, user_data: dict, today: datetime):
        period_generator = UserBasedPeriod(user_data=user_data, today=today)
        self.__period = period_generator.get_pertinent_period()


    def get_value_in_db(self):
        pass  # TODO


# ------------------ [ FACTORY Class ] ---------------------

class AlertCalculator:

    __data_period_generator: PeriodGenerator
    __value_to_compare: ValueToCompareModifier  # TODO

    __setup: dict
    _data_name: str
    _operator: MyOperator
    _comparator: MyComparator
    _reference_value: int
    _data: float  # data to check - calculated from data_name
    _value: float  # value to compare with

    def __init__(self, setup: dict, last_check: datetime, today: datetime):
        self.__setup = setup
        self._last_check = last_check
        self._today = today

        self._data_name = setup["data_name"]
        self._reference_value = self.__setup["reference_value"]
        self._calculator_type = self.__setup["calculator_type"]

        self._operator = MyOperator(setup["operator"])
        self._comparator = MyComparator(setup["comparator"])

        self.create_value_to_compare_interface()
        self.create_data_period_generator()

        self._data = None
        self._value = None

    def create_value_to_compare_interface(self):
        if self._calculator_type == ValueToCompareModifier.VALUE:
            self.__value_to_compare = PercentValue(percent=self._reference_value)
        else:
            self.__value_to_compare = FullValue()

    def create_data_period_generator(self):
        if self._calculator_type == ValueToCompareModifier.VALUE and self._operator is not MyOperator.AVERAGE:
            self.__data_period_generator = LastCheckBasedPeriod(last_check=self._last_check, today=self._today)
        else:
            self.__data_period_generator = UserBasedPeriod(user_data=self.__setup["data_period"], today=self._today)

    def __get_all_data_in_db(self, period):
        all_data = [30, 45, 60]  # TODO : Link To DB
        return all_data

    # -- Find Data To Compare --
    def __get_data(self):
        """
        get all data
        """
        period = self._get_data_period()
        all_data = self.__get_all_data_in_db(period)
        return self._operator.calculate(all_data)

    def _get_data_period(self):
        return self.__data_period_generator.get_pertinent_period()

    # -- Find Value that will be Compare with Data --
    def _get_comparative_value_from_reference(self):
        if self._calculator_type == ValueToCompareModifier.VALUE:
            return self._reference_value

        value_type = self.__setup["value_type"]

        value_generator: ValueGenerator

        if value_type == ValueGenerator.PERIOD_BASED_VALUE:
            value_generator = PeriodBasedValueGenerator(
                conn_info={},
                user_data=self.__setup["value_period"],
                today=self._today
            )
        elif value_type == ValueGenerator.SIMPLE_DB_BASED_VALUE:
            value_generator = SimpleDBBasedValueGenerator(conn_info={})

        return value_generator.get_value()

    def is_alert_situation(self):
        self._data = self.__get_data()
        self._value = self._get_comparative_value_from_reference()
        return self._comparator.compare(self._data, self._value)


# ---------------------------------------------------------------------------------------------------------------------
