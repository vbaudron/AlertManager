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

from mysql.connector.cursor import MySQLCursor

from model import utils
from model.my_exception import EnumError, ConfigError
from model.utils import get_day_name_from_datetime, get_data_from_json_file, get_str_from_file, \
    get_path_in_data_folder_of, my_sql, ALERT_TABLE_NAME, ALERT_TABLE_COMPO, \
    SOURCE_PATH, iter_row, METER_TABLE_NAME
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


class UserBasedPeriodGenerator(PeriodGenerator):
    __period_definition: PeriodDefinition

    def __init__(self, today: datetime, user_data: dict) -> None:
        super().__init__()
        self.generate_period_definition(unit=user_data["unit"], quantity=user_data["quantity"])
        self.generate_period(today=today)

    def generate_period_definition(self, unit: str, quantity: int):
        period_unit = PeriodUnitDefinition(unit)
        self.__period_definition = PeriodDefinition(unit=period_unit, quantity=quantity)

    def generate_period(self, today: datetime):
        start_date = self.__period_definition.get_start_date_from_end_date(end_date=today)
        self._period = Period(start=start_date, end=today)


# -------------- [ VALUE GENERATOR ] --------------

# -- Enum
@unique
class ValueGeneratorType(Enum):
    USER_BASED_VALUE = auto()
    SIMPLE_DB_BASED_VALUE = auto()
    PERIOD_BASED_VALUE = auto()


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

    def get_value_in_db(self, meter_id: int):
        return 0  # TODO


class PeriodBasedValueGenerator(DataBaseValueGenerator, ValueGenerator):

    __period: Period
    __operator: MyOperator

    def __init__(self, operator: MyOperator, user_data: dict, today: datetime) -> None:
        super().__init__()
        self.generate_period(user_data=user_data, today=today)
        self.__operator = operator

    def generate_period(self, user_data: dict, today: datetime):
        period_generator = UserBasedPeriodGenerator(user_data=user_data, today=today)
        self.__period = period_generator.get_pertinent_period()

    def get_value_in_db(self, meter_id: int, is_index: bool):
        hdl = HandleDataFromDB(period=self.__period)
        result = hdl.get_data_from_db(meter_id=meter_id, is_index=is_index)
        return self.__operator.calculate(result)


class NoPeriodBasedValueGenerator(ValueGenerator):
    def calculate_value(self, meter_id: int):
        pass

    def __init__(self, value: int) -> None:
        super().__init__()
        self._value = value


# ------------------  [ AlertValue Class ] ---------------------

class AlertValue:
    # setup
    __setup: dict
    # value
    __value_generator_type: ValueGeneratorType
    __value_generator: ValueGenerator
    __value_number: int
    __value: float  # value to compare with

    def __init__(self, setup: dict, today: datetime, operator: MyOperator):
        self.__setup = setup
        self.__value_generator_type = ValueGeneratorType[self.setup["value_type"]]
        self.__value_number = self.setup["value_number"]

        # Set Factory
        self.set_value_generator(today=today, operator=operator)

    def set_value_generator(self, today: datetime, operator: MyOperator):

        if self.value_generator_type is ValueGeneratorType.USER_BASED_VALUE:
            self.__value_generator = NoPeriodBasedValueGenerator(value=self.value_number)
        elif self.value_generator_type is ValueGeneratorType.PERIOD_BASED_VALUE:
            self.__value_generator = PeriodBasedValueGenerator(
                operator=operator,
                user_data=self.setup["value_period"],
                today=today
            )
        elif self.value_generator_type is ValueGeneratorType.SIMPLE_DB_BASED_VALUE:
            self.__value_generator = SimpleDBBasedValueGenerator()

    def calculate_value(self, meter_id: int, is_index: bool):
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
    # setup
    __setup: dict

    # data
    __data_period_type: PeriodGeneratorType
    __data_period_generator: PeriodGenerator
    __data: float  # data to check - calculated from value in db

    def __init__(self, setup: dict, last_check: datetime, today: datetime):
        self.__setup = setup
        self.__data_period_type = PeriodGeneratorType[setup["data_period_type"]]

        self.set_period_generator(last_check=last_check, today=today)

    def set_period_generator(self, last_check: datetime, today: datetime) -> None:
        # Set Factory
        if self.data_period_type is PeriodGeneratorType.LAST_CHECK:
            self.__data_period_generator = LastCheckBasedPeriodGenerator(last_check=last_check,
                                                                         today=today)
        elif self.data_period_type is PeriodGeneratorType.USER_BASED:
            self.__data_period_generator = UserBasedPeriodGenerator(user_data=self.setup["data_period"],
                                                                    today=today)

    def get_all_data_in_db(self, meter_id: int, is_index: bool) -> "list: all data from db":
        period = self.__data_period_generator.get_pertinent_period()
        all_data = HandleDataFromDB(period=period).get_data_from_db(meter_id=meter_id, is_index=is_index)
        print("all data ", all_data)
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
    def generate_query() -> str:
        query = "SELECT {} FROM {} WHERE {} = %s AND {} BETWEEN %s AND %s".format(
            HandleDataFromDB.value_column_name,
            HandleDataFromDB.table_name,
            HandleDataFromDB.meter_id_column_name,
            HandleDataFromDB.hour_column_name
        )
        print(query)
        return query

    def __get_query_result(self, meter_id: int):
        my_cursor = my_sql.generate_cursor()
        my_cursor.execute(
            operation=HandleDataFromDB.generate_query(),
            params=(
                meter_id,
                self.__period.get_start_date(),
                self.__period.get_end_date()
            )
        )

        result = list()
        for row in iter_row(my_cursor, 10):
            result.append(row[0])

        return result

    def __aggregate_result(self, result):
        agg = list()
        i = 1
        while i < len(result):
            agg.append(result[i] - result[i - 1])
            i += 1
        return agg

    def get_data_from_db(self, meter_id: int, is_index: bool):
        result = self.__get_query_result(meter_id=meter_id)
        if is_index:
            result = self.__aggregate_result(result=result)
        return result


# ------------------   [ FACTORY Class ]   ---------------------


class AlertCalculator:
    __setup: dict

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

    def __init__(self, setup: dict, last_check: datetime, today: datetime):
        self.__setup = setup

        self.__last_check = last_check
        self.__today = today

        self.__acceptable_diff = setup["acceptable_diff"]
        self.__operator = MyOperator(setup["operator"])
        self.__comparator = MyComparator(setup["comparator"])

        self.__alert_data = AlertData(setup=setup["data"], last_check=last_check, today=today)
        self.__alert_value = AlertValue(setup=setup["value"], today=today, operator=self.operator)

    def check_non_coherent_config(self):
        if self.acceptable_diff and self.alert_value.value_generator_type is ValueGeneratorType.USER_BASED_VALUE:
            raise ConfigError(self, "acceptable_diff and ValueGeneratorType.USER_BASED_VALUE not compatible")

    # -- Find Value that will be Compare with Data --
    def __get_value(self, meter_id: int, is_index: bool):
        self.__alert_value.calculate_value(meter_id=meter_id, is_index=is_index)
        if self.acceptable_diff:
            return self.comparator.get_new_value(
                value=self.alert_value.value,
                percent=self.alert_value.value_number
            )
        return self.alert_value.value

    def is_alert_situation(self, meter_id: int, is_index: bool) -> bool:
        data_from_db = self.alert_data.get_all_data_in_db(meter_id=meter_id, is_index=is_index)
        if not data_from_db:
            log.warning("no data found in db for meter id {}".format(meter_id))
            return False
        self.__data = self.__operator.calculate(data_from_db)
        self.__value = self.__get_value(meter_id=meter_id, is_index=is_index)
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

    @property
    def int_hour(self) -> int:
        return int(self.name.split("_")[1])


class AlertNotification:
    __number: int
    __period: NotificationPeriod
    __email: str
    __notification_days: int
    __notification_hours: int
    __previous_notification_datetime: datetime

    def __init__(self, setup: dict):
        self.__number = setup["number"]
        self.__period = NotificationPeriod[setup["period"]]
        self.__email = setup["email"]
        self.set_notification_days(setup["notification_days"])
        self.set_notification_hours(setup["notification_hours"])
        self.__previous_notification_datetime = utils.get_datetime_from_iso_str(setup["previous_notification_datetime"])

    # -- IS Notification ALLOWED --

    def is_notification_allowed(self, datetime_to_check: datetime):
        return self._enough_time_between_notifications(datetime_to_check=datetime_to_check) \
               and self.is_notification_allowed_for_datetime(datetime_to_check=datetime_to_check)

    # PERIOD
    def _enough_time_between_notifications(self, datetime_to_check: datetime):
        """
               check if we are allowed to send a new notification

               :param previous: datetime of the last notification
               :type previous: datetime
               :param datetime_to_check the date you want to check
               :type datetime_to_check: datetime

               """
        # get Time between both date
        delta = datetime_to_check - self.previous_notification_datetime

        # Get day divided by nb_day in period (equivalent values)
        count = delta.days / self.period.value

        return count >= self.number

    # DATETIME
    def is_notification_allowed_for_datetime(self, datetime_to_check: datetime):
        return self.is_datetime_in_notification_days(
            datetime_to_check=datetime_to_check
        ) and self.is_datetime_in_notification_hours(
            datetime_to_check=datetime_to_check)

    def is_datetime_in_notification_days(self, datetime_to_check: datetime) -> bool:
        """
        check if notifications are allowed for the day of this datetime

        :param datetime_to_check the date you want to check
        :type datetime_to_check datetime

        """
        try:
            day = get_day_name_from_datetime(my_datetime=datetime_to_check)
            result = self.has_day_in_notification_days(Day[day.upper()])
            return result
        except AttributeError as error:
            log.warning(error)

    def is_datetime_in_notification_hours(self, datetime_to_check: datetime):
        try:
            int_hour = datetime_to_check.hour
            hour = Hour.get_from_int(number=int_hour)
            return self.has_hour_in_notification_hours(hour=hour)
        except AttributeError as error:
            log.warning(error)

    # -- SET DATA FROM JSON --

    def set_notification_days(self, days_list: array) -> None:
        """
        Replace the current Notification Days by the one in Param

        :param days_list: Days that we have to watch
        :type days_list: List of str Element representing Day

        """
        self.reset_notification_days()
        try:
            if days_list:
                for day in days_list:
                    enum_day = Day[day]
                    self.add_day_to_notification_days(enum_day)
        except KeyError:
            error = EnumError(except_enum=Day, wrong_value=day)
            log.warning(error.__str__())

    def set_notification_hours(self, list_hours: array):
        self.reset_notification_hours()
        try:
            if list_hours:
                for int_hour in list_hours:
                    hour = Hour.get_from_int(int_hour)
                    self.add_notification_hour(hour)
        except KeyError:
            error = EnumError(except_enum=Hour, wrong_value=int_hour)
            log.warning(error.__str__())

    # -- UTILS --
    # days

    def add_day_to_notification_days(self, day: Day) -> None:
        try:
            self.__notification_days |= day.value
        except AttributeError:
            error = EnumError(except_enum=Day, wrong_value=day)
            log.warning(error.__str__())

    def remove_day_from_notification_days(self, day: Day) -> None:
        try:
            self.__notification_days ^= day.value
        except AttributeError:
            error = EnumError(except_enum=Day, wrong_value=day)
            log.warning(error.__str__())

    def reset_notification_days(self) -> None:
        self.__notification_days = Day.NONE.value

    def has_day_in_notification_days(self, day: Day) -> bool:
        try:
            return bool(day.value & self.notification_days)
        except AttributeError:
            error = EnumError(except_enum=Day, wrong_value=day)
            log.warning(error.__str__())
            return False

    # Hours

    def reset_notification_hours(self):
        self.__notification_hours = Hour.NONE.value

    def add_notification_hour(self, hour: Hour):
        try:
            self.__notification_hours |= hour.value
        except AttributeError:
            error = EnumError(except_enum=Hour, wrong_value=hour)
            log.warning(error.__str__())

    def has_hour_in_notification_hours(self, hour: Hour) -> bool:
        try:
            return bool(hour.value & self.notification_hours)
        except AttributeError:
            error = EnumError(except_enum=Hour, wrong_value=hour)
            log.warning(error.__str__())
            return False

    def remove_hour_from_notification_hours(self, hour: Hour) -> None:
        try:
            self.__notification_hours ^= hour.value
        except AttributeError:
            error = EnumError(except_enum=Hour, wrong_value=hour)
            log.warning(error.__str__())

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

    def generate_template(self, text_message: str):
        self.email_content.replace(self.config["template_name"], text_message)
        replacements = self.config["replacement"]
        for r in replacements:
            self.email_content.replace(r["key"], r["text"])

    def send(self, receiver_email: str):
        self.__receiver_email = receiver_email
        self.__message = MIMEMultipart("alternative")
        self.message["Subject"] = self.subject
        self.message["From"] = self.sender_email
        self.message["To"] = self.receiver_email

        html = MIMEText(self.email_content, "html")
        self.message.attach(html)

        with smtplib.SMTP("localhost") as server:
            server.send_message(from_addr=self.sender_email, to_addrs=self.receiver_email, msg=html.as_string())

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
    CURRENT = 1
    ARCHIVE = 0


class Alert:
    __id: int
    __datetime: datetime
    __alert_definition_description: str
    __value: float
    __data: float
    __status: AlertStatus
    __meter_id: int

    def __init__(self, alert_definition_description: str, value: float, data: float, today: datetime, meter_id: int) -> None:
        self.__value = value
        self.__data = data
        self.__datetime = today
        self.__meter_id = meter_id
        self.__status = AlertStatus.CURRENT
        self.__alert_definition_description = alert_definition_description

    def save(self):
        query = self.query_construction()
        data = self.generate_data()
        my_sql.execute_and_close(query=query, params=data)

    def generate_data(self):
        data = [
            self.__datetime,
            self.__alert_definition_description,
            self.__data,
            self.__value,
            self.__status.value,
            self.__meter_id
         ]
        return data

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

    __name: str
    __id: int
    __description: str
    __category_id: str
    __meter_ids: array
    __level: Level
    __flag: int
    __status: AlertDefinitionStatus
    __last_check: datetime
    __calculator: AlertCalculator
    __notification: AlertNotification

    def __init__(self, setup: dict, today: datetime = datetime.today()):
        self.__name = setup["name"]
        self.__id = setup["id"]
        self.__description = setup["description"]
        self.__category_id = setup["category_id"]
        self.__level = Level[setup["level"]]
        self.__status = AlertDefinitionStatus[setup["status"]]
        self.__meter_ids = setup["meter_ids"]
        self.set_definition_flags_from_str_flags(flags_list=setup["flags"])
        self.__last_check = utils.get_datetime_from_iso_str(setup["last_check"])
        self.__notification = AlertNotification(setup=setup["notification"])
        self.__calculator = AlertCalculator(setup=setup["calculator"], today=today, last_check=self.last_check)

    @property
    def is_active(self) -> bool:
        return self.__status is AlertDefinitionStatus.ACTIVE

    # CHECK
    def check(self, today: datetime):
        """
        Check if we are in alert situation for each meter ids according to this Alert Definition

        :param today the date you want to check
        :type today datetime

        """
        results = self.find_is_index(meter_ids=self.meter_ids)
        for meter_id, is_index in results:
            print("id = {} is_idx = {}".format(id, is_index))
            if self.calculator.is_alert_situation(meter_id=meter_id, is_index=bool(is_index)):
                alert = Alert(
                    alert_definition_description=self.description,
                    value=self.calculator.value,
                    data=self.calculator.data,
                    today=today,
                    meter_id=meter_id
                )
                alert.save()
                if self.notification.is_notification_allowed(datetime_to_check=today):
                    pass  # TODO NOTIFY

    def find_is_index(self, meter_ids):
        format_param = ", ".join(["%s" for m in meter_ids])
        print(format_param)
        query = "select id, IS_INDEX from {} where id IN ({})".format(METER_TABLE_NAME, format_param)
        print(query)
        my_cursor = my_sql.generate_cursor()
        my_cursor.execute(operation=query, params=meter_ids)
        return my_cursor.fetchall()


    # DEFINITION FLAG
    def has_definition_flag(self, flag: AlertDefinitionFlag):
        return bool(flag.value & self.__flag)

    def add_definition_flag(self, flag: AlertDefinitionFlag):
        self.__flag |= flag.value

    def reset_definition_flag(self):
        self.__flag = AlertDefinitionFlag.NONE.value

    def remove_definition_flag(self, flag: AlertDefinitionFlag):
        self.__flag ^= flag.value

    def set_definition_flags_from_str_flags(self, flags_list: array):
        self.reset_definition_flag()
        for str_flag in flags_list:
            flag = AlertDefinitionFlag[str_flag]
            self.add_definition_flag(flag)

    @property
    def definition_flag(self):
        return self.__flag

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
        return self.__category_id

    @property
    def id(self):
        return self.__id

    @property
    def description(self):
        return self.__description

    @property
    def meter_ids(self):
        return self.__meter_ids

    @property
    def last_check(self):
        return self.__last_check


# ---------------------------------------------------------------------------------------------------------------------


class AlertManager:

    __alert_definition_list: list
    __today: datetime

    def __init__(self):
        self.__today = datetime.today()
        data = self.get_alert_def_in_db()
        self.__alert_definition_list = list()

        for setup in data:
            try:
                alert_definition = AlertDefinition(setup=setup, today=self.today)
                self.__alert_definition_list.append(alert_definition)
            except (KeyError, ConfigError) as error:
                log.warning(error.__str__())

    def start(self):
        for alert_definition in self.alert_definition_list:
            if alert_definition.is_active:
                alert_definition.check(today=self.today)

    @staticmethod
    def get_alert_def_in_db():
        query = """select d.*, 
                n.period_unit "notification_period_unit", n.period_quantity "notification_period_quantity", 
                n.email "notification_email", n.days_flag "notification_days", n.hours_flag "notification_hours", 
                c.operator, c.comparator, c.data_period_type, c.data_period_quantity, c.data_period_unit, 
                c.value_type, c.value_number, c.value_period_quantity, c.value_period_unit, dm.meter_id 
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



def start():
    alert_manager = AlertManager()
    alert_manager.start()
    alert_manager.save()
