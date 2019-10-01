#!/usr/bin/python3
# -*-coding:Utf-8 -*

import logging as log
import os
import smtplib
import ssl
from abc import ABC, abstractmethod
import array
import calendar
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Union

from mysql.connector.cursor import MySQLCursor

from model import utils
from model.my_exception import EnumError, ConfigError, NoDataFoundInDatabase, StopCheckAlertDefinition
from model.utils import get_day_name_from_datetime, get_data_from_json_file, get_str_from_file, \
    get_path_in_data_folder_of, ALERT_TABLE_NAME, ALERT_TABLE_COMPO, \
    SOURCE_PATH, iter_row, METER_TABLE_NAME, NOTIFICATION_NAME, ALERT_MANAGER_TABLE_NAME, get_path_in_source_folder_of, \
    ALERT_DEFINITION_NOTIFICATION_TIME, ALERT_DEFINITION_NOTIFICATION_TIME_COMPO, my_sql
from enum import Enum, auto, unique, Flag, IntEnum



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

# Compare
def is_sup(data: float, value: float) -> bool:
    return data > value


def is_inf(data: float, value: float) -> bool:
    return data < value


def equal(data: float, value: float) -> bool:
    return data == value


# Apply Percent to value
def new_sup_value(value: float, percent: int) -> float:
    return value * (1 + (percent / 100))


def new_inf_value(value: float, percent: int) -> float:
    return value * (1 - (percent / 100))


def new_equal_value(value: float, percent: int) -> float:
    return value


# CLASS
class MyComparator(Enum):
    SUP = "SUP", is_sup, new_sup_value
    INF = "INF", is_inf, new_inf_value
    EQUAL = "EQUAL", equal, new_equal_value

    def __new__(cls, str_name, method, method_with_percent):
        obj = object.__new__(cls)
        obj._value_ = str_name
        obj.compare = method
        obj.get_new_value = method_with_percent
        return obj


# -------------------------------------------------   PERIOD Class   ---------------------------------------------------

def go_past_with_hours(end_date: datetime, quantity: int) -> datetime:
    return end_date - timedelta(hours=quantity)

def go_past_with_days(end_date: datetime, quantity: int) -> datetime:
    return end_date - timedelta(days=quantity)


def go_past_with_weeks(end_date: datetime, quantity: int) -> datetime:
    return end_date - timedelta(weeks=quantity)


def go_past_with_months(end_date: datetime, quantity: int) -> datetime:
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


def go_past_with_years(end_date: datetime, quantity: int) -> datetime:
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
    HOUR = "HOUR", go_past_with_hours, 1
    DAY = "DAY", go_past_with_days, 24
    WEEK = "WEEK", go_past_with_weeks, 7 * 24
    MONTH = "MONTH", go_past_with_months, 30 * 24
    YEAR = "YEAR", go_past_with_years, 365 * 24

    def __new__(cls, str_name, method, nb_hour):
        obj = object.__new__(cls)
        obj._value_ = str_name
        obj.go_past = method
        obj.nb_hour = nb_hour
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

    def __str__(self):
        return "[PERIOD] from {} to {}".format(self.__start_date.isoformat(), self.__end_date.isoformat())


# ---------------------------------------------------   CALCULATOR   ------------------------------------------------------


# -------------- [ PERIOD GENERATOR ] --------------

# -- Enum
@unique
class PeriodGeneratorType(Enum):
    LAST_CHECK = auto()
    USER_BASED = auto()


# -- class
class PeriodGenerator(ABC):
    _period: Period

    def get_pertinent_period(self):
        return self._period


class LastCheckBasedPeriodGenerator(PeriodGenerator):

    def __init__(self, last_check: datetime, today: datetime) -> None:
        super().__init__()
        self._period = Period(start=last_check, end=today)


class UserBasedGoBackPeriodGenerator(PeriodGenerator):
    __period_definition: PeriodDefinition

    def __init__(self, to_date: datetime, unit, quantity: int) -> None:
        super().__init__()
        self.__generate_period_definition(unit=unit, quantity=quantity)
        self.__generate_period(to_date=to_date)

    def __generate_period_definition(self, unit, quantity: int):
        print("__generate_period_definition UNIT", unit)
        if not isinstance(unit, PeriodUnitDefinition):
            try :
                unit = PeriodUnitDefinition(unit)
            except ValueError:
                raise EnumError(except_enum=PeriodUnitDefinition, wrong_value=unit)
        self.__period_definition = PeriodDefinition(unit=unit, quantity=quantity)

    def __generate_period(self, to_date: datetime):
        start_date = self.__period_definition.get_start_date_from_end_date(end_date=to_date)
        self._period = Period(start=start_date, end=to_date)


# -------------- [ VALUE GENERATOR ] --------------

# -- Enum
@unique
class ValueGeneratorType(Enum):
    USER_BASED_VALUE = auto()
    SIMPLE_DB_BASED_VALUE = auto()
    PERIOD_BASED_VALUE = auto()


@unique
class ValuePeriodType(Enum):
    LAST_YEAR = auto()
    LAST_DATA_PERIOD = auto()


# -- class
class ValueGenerator(ABC):
    _value: float

    @abstractmethod
    def calculate_value(self, meter_id: int):
        raise NotImplementedError

    @property
    def value(self):
        return self._value


class UserBasedValueGenerator(ValueGenerator):

    def __init__(self, user_data: int) -> None:
        super().__init__()
        self._value = user_data

    def calculate_value(self, meter_id: int):
        pass


class DataBaseValueGenerator(ABC):

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def get_value_in_db(self, meter_id: int, is_index: bool):
        raise NotImplementedError

    def calculate_value(self, meter_id: int, is_index: bool):
        self._value = self.get_value_in_db(meter_id=meter_id, is_index=is_index)


class SimpleDBBasedValueGenerator(DataBaseValueGenerator, ValueGenerator):  # GOAL

    def __init__(self) -> None:
        super().__init__()

    def get_value_in_db(self, meter_id: int, is_index: bool):
        query = """SELECT o.value, o.time_unit from bi_objectifs o where o.r_compteur=%s"""
        params = [meter_id]

        print("Find Objectif :")
        print("\tquery", query)
        print("\tparams", params)

        cursor = my_sql.generate_cursor()
        cursor.execute(operation=query, params=params)
        result = cursor.fetchall()
        print("\tresult", result)
        value, time_unit = result[0]
        if time_unit:
            period_unit = PeriodUnitDefinition(time_unit)
            value = value / period_unit.nb_hour
        return value


class PeriodBasedValueGenerator(DataBaseValueGenerator, ValueGenerator):

    __period: Period
    __operator: MyOperator

    def __init__(self, operator: MyOperator, unit: str, quantity: int, end_date: datetime) -> None:
        super().__init__()
        if not unit or not quantity or quantity <= 0:
            msg = "valid 'value_period_unit' and 'value_period_quantity' NEEDED"
            msg += "(found respectively '{}' and '{}'".format(
                unit,
                quantity
            )
            raise ConfigError(obj=self, msg=msg)
        self.generate_period(quantity=quantity, unit=unit, end_date=end_date)
        self.__operator = operator

    def generate_period(self, unit: str, quantity: int, end_date: datetime):
        period_generator = UserBasedGoBackPeriodGenerator(quantity=quantity, unit=unit, to_date=end_date)
        self.__period = period_generator.get_pertinent_period()

    def get_value_in_db(self, meter_id: int, is_index: bool):
        print("find values in", self.__period)
        hdl = HandleDataFromDB(period=self.__period)
        result = hdl.get_data_from_db(meter_id=meter_id, is_index=is_index)
        if result:
            return self.__operator.calculate(result)
        else:
            raise NoDataFoundInDatabase(message="no value found for {}".format(self.__period))



class NoPeriodBasedValueGenerator(ValueGenerator):
    def calculate_value(self, meter_id: int, is_index:bool):
        pass

    def __init__(self, value: float) -> None:
        super().__init__()
        self._value = value


# ------------------  [ AlertValue Class ] ---------------------

class AlertValue:
    # value
    __value_generator_type: ValueGeneratorType
    __value_generator: ValueGenerator
    __value_number: int
    __value: float  # value to compare with

    def __init__(self, value_type: str, value_number: float):
        print(self.__class__.__name__, " in creation ...")
        try:
            self.__value_generator_type = ValueGeneratorType[value_type]
        except KeyError:
            raise EnumError(ValueGeneratorType, wrong_value=value_type, where=self.__class__.__name__)

        self.__value_number = value_number

    def set_value_generator(self, end_date: datetime, unit: str, quantity: int, operator: MyOperator):

        if self.value_generator_type is ValueGeneratorType.USER_BASED_VALUE:
            self.__value_generator = NoPeriodBasedValueGenerator(value=self.value_number)
        elif self.value_generator_type is ValueGeneratorType.PERIOD_BASED_VALUE:
            self.__value_generator = PeriodBasedValueGenerator(
                operator=operator,
                unit=unit,
                quantity=quantity,
                end_date=end_date
            )
        elif self.value_generator_type is ValueGeneratorType.SIMPLE_DB_BASED_VALUE:
            self.__value_generator = SimpleDBBasedValueGenerator()

    def calculate_value(self, meter_id: int, is_index: bool):
        print("value type :", self.value_generator_type.name)
        self.value_generator.calculate_value(meter_id=meter_id, is_index=is_index)

    @property
    def value_number(self):
        return self.__value_number

    @property
    def value_generator_type(self):
        return self.__value_generator_type

    @property
    def value_generator(self):
        return self.__value_generator

    @property
    def value(self):
        return self.value_generator.value

    @property
    def setup(self):
        return self.__setup


# ------------------  [ AlertData Class ]  ---------------------


class AlertData:
    # Filter
    __hour_end: int
    __hour_start: int

    # data
    __data_period_type: PeriodGeneratorType
    __data_period_generator: PeriodGenerator
    __data: float  # data to check - calculated from value in db

    def __init__(self,
                 data_period_type: str,
                 data_period_quantity: int,
                 data_period_unit: str,
                 hour_start: int,
                 hour_end: int,
                 last_check: datetime,
                 today: datetime):
        print(self.__class__.__name__, " in creation ...")
        self.__hour_start = hour_start
        self.__hour_end = hour_end

        try:
            self.__data_period_type = PeriodGeneratorType[data_period_type]
        except KeyError:
            raise EnumError(except_enum=PeriodGeneratorType, wrong_value=data_period_type, where=self.__class__.__name__)

        self.set_period_generator(
            last_check=last_check,
            today=today,
            data_period_quantity=data_period_quantity,
            data_period_unit=data_period_unit
        )

    def set_period_generator(self, last_check: datetime, today: datetime, data_period_quantity: int, data_period_unit: str,) -> None:
        # Set Factory
        if self.data_period_type is PeriodGeneratorType.LAST_CHECK:
            self.__data_period_generator = LastCheckBasedPeriodGenerator(
                last_check=last_check,
                today=today
            )
        elif self.data_period_type is PeriodGeneratorType.USER_BASED:
            self.__data_period_generator = UserBasedGoBackPeriodGenerator(
                quantity=data_period_quantity,
                unit=data_period_unit,
                to_date=today
            )

    def get_all_data_in_db(self, meter_id: int, is_index: bool) -> "list: all data from db":
        period = self.__data_period_generator.get_pertinent_period()
        all_data = HandleDataFromDB(period=period).get_data_from_db(
            meter_id=meter_id,
            is_index=is_index,
            hour_start=self.__hour_start,
            hour_end=self.__hour_end,
        )
        return all_data

    @property
    def data_period_type(self):
        return self.__data_period_type

    @property
    def data_period_generator(self):
        return self.__data_period_generator

    @property
    def data(self):
        return self.__data

    @property
    def setup(self):
        return self.__setup


# -----------------------------------------------    HANDLE DONNESCOMPTAGE  -------------------------------------------------


class HandleDataFromDB:
    table_name = "bi_donneescomptage"
    value_column_name = "valeur"
    meter_id_column_name = "r_compteurs"
    hour_column_name = "date_heure"

    __period: Period

    def __init__(self, period: Period):
        self.__period = period

    @staticmethod
    def generate_query(time_needed: bool) -> str:

        def get_select():
            if time_needed:
                return "{}, {}".format(
                    HandleDataFromDB.value_column_name, HandleDataFromDB.hour_column_name
                )
            return HandleDataFromDB.value_column_name

        query = "SELECT {} FROM {} WHERE {} = %s AND {} BETWEEN %s AND %s".format(
            get_select(),
            HandleDataFromDB.table_name,
            HandleDataFromDB.meter_id_column_name,
            HandleDataFromDB.hour_column_name
        )
        return query

    def __get_query_result(self, meter_id: int, time_needed: bool):
        cursor = my_sql.generate_cursor()

        query = HandleDataFromDB.generate_query(time_needed=time_needed)
        params = (
                meter_id,
                self.__period.get_start_date(),
                self.__period.get_end_date()
        )

        print("query :", query)
        print("params :", params)

        cursor.execute(operation=query, params=params)

        result = list()
        for row in iter_row(cursor, 10):
            result.append(row[0])

        print("result :", result)

        return result

    def __aggregate_result(self, result):
        agg = list()
        i = 1
        while i < len(result):
            agg.append(result[i] - result[i - 1])
            i += 1
        return agg

    def is_between_hour(self, time: datetime, hour_start: int, hour_end: int):
        hour = time.hour
        if hour_start < hour_end:
            return hour_start <= hour < hour_end
        if hour >= hour_end:
            return hour >= hour_start
        return True

    def get_data_from_db(self, meter_id: int, is_index: bool, hour_start: int = None, hour_end: int = None,):
        results = self.__get_query_result(meter_id=meter_id, time_needed=bool(hour_end and hour_start))
        if hour_start and hour_end and hour_end != hour_start:
            results = [result[0] for result in results if self.is_between_hour(result[1], hour_start=hour_start, hour_end=hour_end)]
        if is_index:
            results = self.__aggregate_result(result=results)
        return results


# ------------------   [ FACTORY Class ]   ---------------------


class AlertCalculator:

    # datetime
    __last_check: datetime
    __today: datetime

    # general
    __acceptable_diff: bool
    __operator: MyOperator
    __comparator: MyComparator

    # data
    __alert_data: AlertData
    __data: float

    # value
    __alert_value: AlertValue
    __value: float

    def __init__(self,
                 operator: str,
                 comparator: str,
                 data_period_type: str,
                 data_period_quantity: int,
                 data_period_unit: str,
                 value_type: str,
                 value_number: float,
                 value_period_type: str,
                 hour_start: int,
                 hour_end: int,
                 acceptable_diff: bool,
                 last_check: datetime,
                 today: datetime):

        print(self.__class__.__name__, " in creation ...")
        self.__last_check = last_check
        self.__today = today
        print(data_period_unit, type(data_period_unit))

        self.__acceptable_diff = acceptable_diff

        # OPERATOR
        try:
            self.__operator = MyOperator[operator]
        except KeyError:
            raise EnumError(MyOperator, wrong_value=operator)

        # COMPARATOR
        try:
            self.__comparator = MyComparator[comparator]
        except ValueError:
            raise EnumError(MyComparator, wrong_value=comparator, where=self.__class__.__name__)


        # ALERT DATA
        self.__alert_data = AlertData(
            data_period_type=data_period_type,
            data_period_quantity=data_period_quantity,
            data_period_unit=data_period_unit,
            hour_start=hour_start,
            hour_end=hour_end,
            last_check=last_check,
            today=today
        )

        # ALERT VALUE
        self.__alert_value = AlertValue(
            value_number=value_number,
            value_type=value_type
        )

        self.check_non_coherent_config(value_type=value_type, value_period_type=value_period_type)
        self.__handle_alert_value_generator(
            today=today,
            value_period_type=value_period_type,
            data_period_unit=data_period_unit,
            data_period_quantity=data_period_quantity,
            operator=self.__operator
        )



    def __handle_alert_value_generator(self,
                                       today: datetime,
                                       value_period_type: str,
                                       data_period_unit: str,
                                       data_period_quantity: int,
                                       operator: MyOperator):

        def get_value_end_date():
            period_type: ValuePeriodType = ValuePeriodType[value_period_type]
            if period_type is ValuePeriodType.LAST_YEAR:
                unit = PeriodUnitDefinition.YEAR.name
                quantity = 1
            elif period_type is ValuePeriodType.LAST_DATA_PERIOD:
                unit = data_period_unit
                quantity = data_period_quantity
                # Go back data period time
            tmp_period = UserBasedGoBackPeriodGenerator(
                to_date=today,
                unit=unit,
                quantity=quantity
            ).get_pertinent_period()
            # Get startDate which will be new end date
            return tmp_period.get_start_date()
        end_date = get_value_end_date() if value_period_type else today

        self.__alert_value.set_value_generator(
            end_date=end_date,
            unit=data_period_unit,
            quantity=data_period_quantity,
            operator=operator
        )


    def check_non_coherent_config(self, value_type, value_period_type):
        try:
            vt = ValueGeneratorType[value_type]
        except KeyError:
            raise EnumError(ValueGeneratorType, wrong_value=value_type)

        if vt is ValueGeneratorType.PERIOD_BASED_VALUE and not value_period_type:
            raise ConfigError(
                self.__alert_value,
                "Since 'value_type' is '{}' 'value_period_type' can not be null".format(
                    ValueGeneratorType.PERIOD_BASED_VALUE.name
                )
            )
        if self.acceptable_diff and vt is ValueGeneratorType.USER_BASED_VALUE:
            raise ConfigError(self, "acceptable_diff and ValueGeneratorType.USER_BASED_VALUE not compatible")

    # -- Find Value that will be Compare with Data --
    def __get_value(self, meter_id: int, is_index: bool):
        print("\n --- Calculate Value ---")
        self.__alert_value.calculate_value(meter_id=meter_id, is_index=is_index)
        if self.acceptable_diff:
            return self.comparator.get_new_value(
                value=self.alert_value.value,
                percent=self.alert_value.value_number
            )
        return self.alert_value.value

    def is_alert_situation(self, meter_id: int, is_index: bool) -> bool:
        print("\n --- Calculate Data ---")
        data_from_db = self.alert_data.get_all_data_in_db(meter_id=meter_id, is_index=is_index)
        print("data from db :", data_from_db)
        if not data_from_db:
            raise NoDataFoundInDatabase("no data found in db for meter id {}".format(meter_id))
        print("operator :", self.__operator.name)
        self.__data = self.__operator.calculate(data_from_db)
        print("____________________  DATA  :", self.__data)

        self.__value = self.__get_value(meter_id=meter_id, is_index=is_index)
        print("____________________  VALUE :", self.__value)

        print("\n --- Comparaison ---\n is data {} value ? ".format(self.comparator.name))
        return self.comparator.compare(self.data, self.value)

    # --- PROPERTIES ---
    # general
    @property
    def setup(self):
        return self.__setup

    @property
    def data(self):
        return self.__data

    @property
    def value(self):
        return self.__value

    @property
    def operator(self):
        return self.__operator

    @property
    def comparator(self):
        return self.__comparator

    @property
    def acceptable_diff(self):
        return self.__acceptable_diff

    # data
    @property
    def alert_data(self):
        return self.__alert_data

    # value
    @property
    def alert_value(self):
        return self.__alert_value

    # datetime
    @property
    def today(self):
        return self.__today

    @property
    def last_check(self):
        return self.__last_check


# -----------------------------------------------   NOTIFICATION   -------------------------------------------------

@unique
class Day(Flag):
    NONE = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 4
    THURSDAY = 8
    FRIDAY = 16
    SATURDAY = 32
    SUNDAY = 64

    @staticmethod
    def str_values():
        my_str = ""
        for name, member in Day.__members__.items():
            my_str += "_{0} : {1}_    ".format(name, member.value)
        return my_str


@unique
class NotificationPeriod(Enum):
    DAY = 1  # 1 Day per DAY
    WEEK = 7  # 7 Days per WEEK
    MONTH = 30  # 30 Days per MONTH


@unique
class Hour(Flag):
    NONE = 0
    H_0 = pow(2, 0)
    H_1 = pow(2, 1)
    H_2 = pow(2, 2)
    H_3 = pow(2, 3)
    H_4 = pow(2, 4)
    H_5 = pow(2, 5)
    H_6 = pow(2, 6)
    H_7 = pow(2, 7)
    H_8 = pow(2, 8)
    H_9 = pow(2, 9)
    H_10 = pow(2, 10)
    H_11 = pow(2, 11)
    H_12 = pow(2, 12)
    H_13 = pow(2, 13)
    H_14 = pow(2, 14)
    H_15 = pow(2, 15)
    H_16 = pow(2, 16)
    H_17 = pow(2, 17)
    H_18 = pow(2, 18)
    H_19 = pow(2, 19)
    H_20 = pow(2, 20)
    H_21 = pow(2, 21)
    H_22 = pow(2, 22)
    H_23 = pow(2, 23)

    @staticmethod
    def get_from_int(number: int):
        name = "H_" + str(number)
        return Hour[name]

  #  @property
  #  def int_hour(self) -> int:
  #      return int(self.name.split("_")[1])


class AlertNotification:
    __id: int
    __number: int
    __period: NotificationPeriod
    __email: str
    __notification_days: int
    __notification_hours: int
    __previous_notification_datetime: datetime

    def __init__(self, notification_id: int, period_unit: str, period_quantity: int, email: str, hours: int, days: int):
        self.__id = notification_id
        self.__number = period_quantity
        self.__period = NotificationPeriod[period_unit]
        self.__email = email
        self.__notification_hours = hours
        self.__notification_days = days
        self.__previous_notification_datetime = None


    def query_last_notification_time(self, alert_definition_id: int):
        query = """ SELECT notification_datetime FROM {} 
                    WHERE alert_definition_id=%s AND notification_id=%s 
                    ORDER BY notification_datetime DESC LIMIT 1""".format(ALERT_DEFINITION_NOTIFICATION_TIME)

        params = (alert_definition_id, self.__id)

        print("query", query)
        cursor = my_sql.generate_cursor()
        cursor.execute(operation=query, params=params)
        results = cursor.fetchall()
        print("results =", results)
        if not results:
            return None
        else:
            return results[0][0]

    # -- IS Notification ALLOWED --

    def is_notification_allowed(self, datetime_to_check: datetime, alert_definition_id: int):
        return self.is_notification_allowed_for_datetime(
            datetime_to_check=datetime_to_check
        ) and self._enough_time_between_notifications(
            alert_definition_id=alert_definition_id,
            datetime_to_check=datetime_to_check
        )


    # [IS_ALLOWED] Period recurrency

    def _enough_time_between_notifications(self, alert_definition_id: int, datetime_to_check: datetime):
        """
               check if we are allowed to send a new notification

               :param previous: datetime of the last notification
               :type previous: datetime
               :param datetime_to_check the date you want to check
               :type datetime_to_check: datetime

               """

        print("CHECK if is enough_time_between_notifications")

        # get last notification time
        self.__previous_notification_datetime = self.query_last_notification_time(alert_definition_id=alert_definition_id)
        if not self.previous_notification_datetime:
            return True

        # get Time between both date
        delta = datetime_to_check - self.previous_notification_datetime

        # Get day divided by nb_day in period (equivalent values)
        count = delta.days / self.period.value

        return count >= self.number

    # [IS_ALLOWED] Datetime
    def is_notification_allowed_for_datetime(self, datetime_to_check: datetime):
        print("CHECK if is_notification_allowed_for_datetime")
        return self.is_datetime_in_notification_days(
            datetime_to_check=datetime_to_check
        ) and self.is_datetime_in_notification_hours(
            datetime_to_check=datetime_to_check)


    # -- DAY --

    def is_datetime_in_notification_days(self, datetime_to_check: datetime) -> bool:
        """
        check if notifications are allowed for the day of this datetime

        :param datetime_to_check the date you want to check
        :type datetime_to_check datetime

        """
        try:
            day = get_day_name_from_datetime(my_datetime=datetime_to_check)
            result = self.has_day_in_notification_days(Day[day.upper()])
            print("IS in notification day" if result else "is NOT in notification day")
            return result
        except AttributeError as error:
            log.warning("823", error.__str__())

    def has_day_in_notification_days(self, day: Day) -> bool:
        try:
            return bool(day.value & self.notification_days)
        except AttributeError:
            error = EnumError(except_enum=Day, wrong_value=day)
            log.warning(error.__str__())
            return False

    # -- HOUR --

    def is_datetime_in_notification_hours(self, datetime_to_check: datetime):
        try:
            int_hour = datetime_to_check.hour
            hour = Hour.get_from_int(number=int_hour)
            print("int_hour = {} Hour.name = {} hour.value = {}".format(int_hour, hour.name, hour.value))
            result = self.has_hour_in_notification_hours(hour=hour)
            print("IS in notification hour" if result else "is NOT in notification hour")
            return result
        except AttributeError as error:
            log.warning(error.__str__())

    def has_hour_in_notification_hours(self, hour: Hour) -> bool:
        try:
            return bool(hour.value & self.notification_hours)
        except AttributeError:
            error = EnumError(except_enum=Hour, wrong_value=hour)
            log.warning(error.__str__())
            return False


    @property
    def id(self):
        return self.__id

    @property
    def number(self):
        return self.__number

    @property
    def period(self):
        return self.__period

    @property
    def email(self):
        return self.__email

    @property
    def notification_days(self):
        return self.__notification_days

    @property
    def notification_hours(self):
        return self.__notification_hours

    @property
    def previous_notification_datetime(self):
        return self.__previous_notification_datetime


# -----------------------------------------------   EMAIL   -------------------------------------------------

class Email:
    TEMPLATE_FOLDER_NAME = "template"
    PASSWORD = "password"

    __sender_email: str
    __receiver_email: str
    __subject: str
    __config: dict
    __message: MIMEMultipart
    __email_content: str

    def __init__(self):
        pass

    def prepare(self, filename: str):
        self.__config = get_data_from_json_file(self.email_config_path(filename))
        self.__subject = self.config["subject"]
        self.__sender_email = self.config["sender_email"]
        self.__email_content = get_str_from_file(self.get_file_path_name())

    def generate_template(self, replacements: dict):
        for key, value in replacements.items():
            self.email_content.replace("{{" + key + "}}", value)


    def send(self, receiver_email: str):
        self.__receiver_email = receiver_email
        self.__message = MIMEMultipart("alternative")
        self.__message["Subject"] = self.subject
        self.__message["From"] = self.sender_email
        self.__message["To"] = self.receiver_email

        html = MIMEText(self.email_content, "html")
        self.__message.attach(html)

        try:
            with smtplib.SMTP("localhost", port=8025) as connection:
 #               import pdb;pdb.set_trace()

                connection.send_message(from_addr=self.sender_email, to_addrs=self.receiver_email, msg=self.__message)
             #   connection.sendmail(from_addr=self.sender_email, to_addrs=self.receiver_email, msg=self.__message.as_string())
                print("mail send to", self.receiver_email)
                return True
        except Exception as error:
            log.error(error)
            return False

    def email_config_path(self, filename: str):
        config_path = get_path_in_data_folder_of(filename)
        print("config_path", config_path)
        return config_path

    def get_template_path(self):
        template_path = os.path.join(SOURCE_PATH, self.TEMPLATE_FOLDER_NAME)
        print("template_path", template_path)
        return template_path

    def get_file_path_name(self):
        file_name_path = os.path.join(self.get_template_path(), self.config["template_name"] + ".html")
        print("file_name_path : ", file_name_path)
        return file_name_path

    @property
    def config(self):
        return self.__config

    @property
    def email_content(self):
        return self.__email_content

    @property
    def message(self):
        return self.__message

    @property
    def subject(self):
        return self.__subject

    @property
    def sender_email(self):
        return self.__sender_email

    @property
    def receiver_email(self):
        return self.__receiver_email


# -----------------------------------------------------   ALERT  -------------------------------------------------------

class AlertStatus(Enum):
    ARCHIVE = 0
    CURRENT = 1


class Alert:
    __id: int
    __datetime: datetime
    __alert_definition_id: id
    __value: float
    __data: float
    __status: AlertStatus
    __meter_id: int

    def __init__(self, alert_definition_id: int, value: float, data: float, today: datetime, meter_id: int) -> None:
        self.__value = value
        self.__data = data
        self.__datetime = today
        self.__meter_id = meter_id
        self.__status = AlertStatus.CURRENT
        self.__alert_definition_id = alert_definition_id

    def save(self):
        query = self.query_construction()
        params = [
            self.__datetime,
            self.__datetime,
            self.__data,
            self.__value,
            self.__status.value,
            self.__alert_definition_id,
            self.__meter_id
         ]

        print("query", query)
        print("params", params)


        cursor = my_sql.generate_cursor()
        cursor.execute(operation=query, params=params)
        my_sql.commit()
        self.__id = cursor.lastrowid
        print("[Alert] saved with id :", self.__id)

    def query_construction(self):
        # PARAMS
        params_list = list(key for key, value in ALERT_TABLE_COMPO.items())
        params_list.pop(0)
        params_str = ", ".join([param for param in params_list])

        # Format
        format_param = ", ".join(["%s" for param in params_list])

        # QUERY
        query = "INSERT INTO {} ({}) VALUES ({})".format(ALERT_TABLE_NAME, params_str, format_param)
        print(query)
        return query

    @property
    def id(self):
        return self.__id


# -----------------------------------------------   ALERT DEFINITION   -------------------------------------------------

# FLAG
@unique
class AlertDefinitionFlag(Flag):
    NONE = 0  # Nothing
    SAVE_ALL = auto()  # Always calculate Alert even if notification not allowed & if alert exist, save it
    ANOTHER_FLAG = auto()  # Flag to Test - Do not forget to Refactor when change it

# STATUS
@unique
class AlertDefinitionStatus(Enum):
    INACTIVE = 0
    ACTIVE = 1

# LEVEL
@unique
class Level(Enum):
    LOW = 0
    HIGH = 1


# CLASS
class AlertDefinition:
    """
    This class represent how is define an Alert.
    It can be divided in 4 parts :
    - its DEFINITION - name, level, status, category...
    - its TRIGGER - calculation, values related... this part will evaluate if an Alert has to be created
    - its NOTIFICATION - template, period of watch
    - an ALERT CREATION - date, invalid data ...
    """

    ALERT_EMAIL_CONFIG_FILENAME = "alert_email_config.json"

    __name: str
    __id: int
    __description: str
    __category: str
    __meter_ids: array
    __level: Level
    __status: AlertDefinitionStatus
    __calculator: AlertCalculator
    __notification: AlertNotification

    def __init__(self, setup: dict, last_check: datetime, today: datetime = datetime.today()):
        self.__name = setup["name"]
        self.__id = setup["id"]
        self.__description = setup["description"]
        self.__category = setup["category"]
        self.__level = Level(setup["level"])
        self.__status = AlertDefinitionStatus(setup["status"])
        self.__meter_ids = setup["meter_ids"]

        # Notification
        self.__notification = AlertNotification(
            notification_id=setup["notification_id"],
            period_unit=setup["notification_period_unit"],
            period_quantity=setup["notification_period_quantity"],
            email=setup["notification_email"],
            days=setup["notification_days"],
            hours=setup["notification_hours"],
        )

        # Calculator
        self.__calculator = AlertCalculator(
            operator=setup["operator"],
            comparator=setup["comparator"],
            data_period_type=setup["data_period_type"],
            data_period_quantity=setup["data_period_quantity"],
            data_period_unit=setup["data_period_unit"],
            value_type=setup["value_type"],
            value_number=setup["value_number"],
            value_period_type=setup["value_period_type"],
            hour_start=setup["hour_start"],
            hour_end=setup["hour_end"],
            acceptable_diff=setup["acceptable_diff"],
            today=today,
            last_check=last_check
        )


    @property
    def is_active(self) -> bool:
        return self.__status is AlertDefinitionStatus.ACTIVE

    # ---- CHECK ----
    def check(self, today: datetime):
        """
        Check if we are in alert situation for each meter ids according to this Alert Definition

        :param today the date you want to check
        :type today datetime

        """
        print("\n______________________________________________________ CHECK AlertDefinition", self.__id)
        results = AlertDefinition.find_is_index(meter_ids=self.meter_ids)
        print("meters_ids to Handle :", self.__meter_ids)
        for meter_id, is_index in results:
            print("\n     ==>  for meter_id : {} is_idx = {}".format(meter_id, is_index))
            if self.calculator.is_alert_situation(meter_id=meter_id, is_index=bool(is_index)):
                print("____________________  this IS an Alert Situation")
                alert = Alert(
                    alert_definition_id=self.__id,
                    value=self.calculator.value,
                    data=self.calculator.data,
                    today=today,
                    meter_id=meter_id
                )
                alert.save()
                print("____________________  Notify ?")
                if self.notification.is_notification_allowed(datetime_to_check=today, alert_definition_id=self.__id):
                    self.notify(meter_id=meter_id, alert=alert, time=today)
            else:
                print("____________________  this IS NOT an Alert Situation")

    # ---- NOTIFY ----
    def notify(self, meter_id, alert, time: datetime):
        replacements = {
            "name": self.name,
            "message_txt": "We calculate that the value of the meter {} follows rules of the Alert Definition : {}".format(
                meter_id,
                self.__name
            ),
            "button_link": "http://dev.emanager.softee.fr/alert/{}".format(alert.id)
        }
        email = Email()
        email.prepare(filename=AlertDefinition.ALERT_EMAIL_CONFIG_FILENAME)
        email.generate_template(replacements=replacements)
        if email.send(self.notification.email):
            print("email SEND")
            self.add_notification_in_db(time=time)

    def add_notification_in_db(self, time: datetime):
        query = utils.insert_query_construction(
            name=ALERT_DEFINITION_NOTIFICATION_TIME,
            compo=ALERT_DEFINITION_NOTIFICATION_TIME_COMPO
        )
        params = [
            self.notification.id,
            self.id,
            time
        ]

        print("query", query)
        print("params", params)

        cursor = my_sql.generate_cursor()
        cursor.execute(operation=query, params=params)
        my_sql.commit()

    # ---- is_idx query ----

    @staticmethod
    def find_is_index(meter_ids):
        format_param = ", ".join(["%s" for m in meter_ids])
        query = "select id, IS_INDEX from {} where id IN ({})".format(METER_TABLE_NAME, format_param)
        print(query)
        my_cursor = my_sql.generate_cursor()
        my_cursor.execute(operation=query, params=meter_ids)
        return my_cursor.fetchall()

    @property
    def name(self):
        return self.__name

    @property
    def calculator(self):
        return self.__calculator

    @property
    def notification(self):
        return self.__notification

    @property
    def level(self):
        return self.__level

    @property
    def category_id(self):
        return self.__category

    @property
    def id(self):
        return self.__id

    @property
    def description(self):
        return self.__description

    @property
    def meter_ids(self):
        return self.__meter_ids

# ---------------------------------------------------------------------------------------------------------------------


class AlertManager:

    __alert_definition_list: list
    __today: datetime

    def __init__(self):
        print("\n\nALERT MANAGER *** INIT ***")
        self.__today = datetime.today()
        data = self.get_alert_def_in_db()
        self.__alert_definition_list = list()

        last_check = self.get_last_check_from_db()
        print("--> last_check", last_check)

        print("create AlertDefinition Instances")
        for setup in data:
            print("_____________________________________________________________________________________________")
            print("AlertDefinition to create from :")
            for key, value in setup.items():
                print('\t', key, ':', value)

            try:
                alert_definition = AlertDefinition(setup=setup, last_check=last_check, today=self.today)
                self.__alert_definition_list.append(alert_definition)
            except (KeyError, ConfigError, EnumError) as error:
                log.error("[ALERT_DEFINITION_{}] {}".format(setup["id"], error.__str__()))

    def start_check(self):
        print("\n\nALERT MANAGER *** START ***")
        for alert_definition in self.alert_definition_list:
            try:
                alert_definition.check(today=self.today)
            except StopCheckAlertDefinition as error:
                log.warning("[ALERT_DEFINITION_{}] {}".format(alert_definition.id, error.__str__()))

    def save(self):
        print("\n\nALERT MANAGER *** SAVE ***")

        query = "INSERT INTO {} (launch_datetime) VALUES (%s)".format(ALERT_MANAGER_TABLE_NAME)
        params = [self.__today]

        print("query", query)
        print("params", params)

        my_sql.execute_and_close(query=query, params=params)

    @staticmethod
    def get_last_check_from_db():
        query = """SELECT launch_datetime from {} ORDER BY launch_datetime DESC LIMIT 1""".format(ALERT_MANAGER_TABLE_NAME)
        cursor = my_sql.generate_cursor()
        cursor.execute(operation=query)
        result = cursor.fetchall()
        if not result:
            return datetime.today() - timedelta(days=1)
        return result[0][0]

    @staticmethod
    def get_alert_def_in_db():
        query = """select d.*, 
                n.period_unit "notification_period_unit", n.period_quantity "notification_period_quantity", 
                n.email "notification_email", n.days_flag "notification_days", n.hours_flag "notification_hours", 
                c.operator, c.comparator, c.data_period_type, c.data_period_quantity, c.data_period_unit, 
                c.value_type, c.value_number, c.value_period_type, c.acceptable_diff, c.hour_start, c.hour_end, 
                dm.meter_id 
                from alert_definition d 
                LEFT JOIN alert_definition_meter dm ON d.id=dm.alert_definition_id 
                LEFT JOIN alert_notification n ON d.notification_id=n.id 
                LEFT jOIN alert_calculator c ON d.calculator_id=c.id 
                WHERE d.status=%s """
        params = [AlertDefinitionStatus.ACTIVE.value]

        cursor = my_sql.generate_cursor()
        cursor.execute(operation=query, params=params)

        return AlertManager.__handle_result(cursor=cursor)

    @staticmethod
    def start():
        alert_manager = AlertManager()
        alert_manager.start_check()
        alert_manager.save()

    @staticmethod
    def __handle_result(cursor: MySQLCursor):
        column_names = cursor.column_names
        results = cursor.fetchall()

        tmp = {}

        # Merge meter id on the same AlertDefinition
        for result in results:
            i = 0
            id_def = result[0]
            if id_def not in tmp.keys():
                tmp[id_def] = {}
                tmp[id_def]["meter_ids"] = []
            while i < len(column_names):
                if column_names[i] == "meter_id":
                    tmp[id_def]["meter_ids"].append(result[i])
                else:
                    tmp[id_def][column_names[i]] = result[i]
                i += 1

        # make array
        return [tmp[key] for key in tmp.keys()]

    @property
    def alert_definition_list(self):
        return self.__alert_definition_list

    @property
    def today(self):
        return self.__today


def startAlertScript():
    AlertManager.start()


