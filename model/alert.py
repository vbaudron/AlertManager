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

from model import utility
from model.my_exception import EnumError, ConfigError
from model.utility import get_day_name_from_datetime, get_data_from_json_file, get_str_from_file, \
    get_path_in_data_folder_of, my_sql, ALERT_TABLE_NAME, ALERT_TABLE_COMPO, \
    SOURCE_PATH
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

    @property
    def value(self):
        return self._value


class UserBasedValueGenerator(ValueGenerator):

    def __init__(self, user_data: int) -> None:
        super().__init__()
        self._value = user_data


class DataBaseValueGenerator(ABC):

    def __init__(self, conn_info: dict) -> None:
        super().__init__()
        self.connect(conn_info)

    def connect(self, conn_info: dict):  # TODO
        pass

    @abstractmethod
    def get_value_in_db(self):
        raise NotImplementedError


class SimpleDBBasedValueGenerator(DataBaseValueGenerator, ValueGenerator):  # GOAL

    def __init__(self, conn_info: dict) -> None:
        super().__init__(conn_info=conn_info)
        self.get_value_in_db()

    def get_value_in_db(self):
        pass  # TODO


class PeriodBasedValueGenerator(DataBaseValueGenerator, ValueGenerator):
    __period: Period

    def __init__(self, conn_info: dict, user_data: dict, today: datetime) -> None:
        super().__init__(conn_info=conn_info)
        self.generate_period(user_data=user_data, today=today)
        self.get_value_in_db()

    def generate_period(self, user_data: dict, today: datetime):
        period_generator = UserBasedPeriodGenerator(user_data=user_data, today=today)
        self.__period = period_generator.get_pertinent_period()

    def get_value_in_db(self):
        self._value = 3  # TODO


class NoPeriodBasedValueGenerator(ValueGenerator):
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

    def __init__(self, setup: dict, today: datetime):
        self.__setup = setup
        self.__value_generator_type = ValueGeneratorType[self.setup["value_type"]]
        self.__value_number = self.setup["value_number"]

        # Set Factory
        self.set_value_generator(today=today)

    def set_value_generator(self, today: datetime):

        if self.value_generator_type is ValueGeneratorType.USER_BASED_VALUE:
            self.__value_generator = NoPeriodBasedValueGenerator(value=self.value_number)
        elif self.value_generator_type is ValueGeneratorType.PERIOD_BASED_VALUE:
            self.__value_generator = PeriodBasedValueGenerator(
                conn_info={},
                user_data=self.setup["value_period"],
                today=today
            )
        elif self.value_generator_type is ValueGeneratorType.SIMPLE_DB_BASED_VALUE:
            self.__value_generator = SimpleDBBasedValueGenerator(conn_info={})

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

    def get_all_data_in_db(self, meter_id: str) -> "list: all data from db":
        period = self.__data_period_generator.get_pertinent_period()
        start_date = period.get_start_date()
        all_data = [30, 45, 60]  # TODO : Link To DB
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
        self.__alert_value = AlertValue(setup=setup["value"], today=today)

    def check_non_coherent_config(self):
        if self.acceptable_diff and self.alert_value.value_generator_type is ValueGeneratorType.USER_BASED_VALUE:
            raise ConfigError(self, "acceptable_diff and ValueGeneratorType.USER_BASED_VALUE not compatible")

    # -- Find Value that will be Compare with Data --
    def __get_value(self):
        if self.acceptable_diff:
            return self.comparator.get_new_value(
                value=self.alert_value.value,
                percent=self.alert_value.value_number
            )
        return self.alert_value.value

    def is_alert_situation(self, meter_id: str) -> bool:
        self.__data = self.__operator.calculate(self.alert_data.get_all_data_in_db(meter_id=meter_id))
        self.__value = self.__get_value()
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
    MONDAY = auto()
    TUESDAY = auto()
    WEDNESDAY = auto()
    THURSDAY = auto()
    FRIDAY = auto()
    SATURDAY = auto()
    SUNDAY = auto()

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
    H_0 = auto()
    H_1 = auto()
    H_2 = auto()
    H_3 = auto()
    H_4 = auto()
    H_5 = auto()
    H_6 = auto()
    H_7 = auto()
    H_8 = auto()
    H_9 = auto()
    H_10 = auto()
    H_11 = auto()
    H_12 = auto()
    H_13 = auto()
    H_14 = auto()
    H_15 = auto()
    H_16 = auto()
    H_17 = auto()
    H_18 = auto()
    H_19 = auto()
    H_20 = auto()
    H_21 = auto()
    H_22 = auto()
    H_23 = auto()

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
        self.__previous_notification_datetime = utility.get_datetime_from_iso_str(setup["previous_notification_datetime"])

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

# STATUS
@unique
class AlertDefinitionStatus(Enum):  # USELESS --> Has Been moved to FLAG
    INACTIVE = 0
    ACTIVE = auto()
    ARCHIVE = auto()


# FLAG
@unique
class AlertDefinitionFlag(Flag):
    INACTIVE = 0  # Nothing
    ACTIVE = auto()  # Replace status
    SAVE_ALL = auto()  # Always calculate Alert even if notification not allowed & if alert exist, save it
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
    - its NOTIFICATION - template, period of watch
    - an ALERT CREATION - date, invalid data ...
    """

    __name: str
    __id: int
    __description: str
    __category_id: str
    __meter_ids: array
    __level: Level
    __alert_definition_flag: int
    __last_check: datetime
    __calculator: AlertCalculator
    __notification: AlertNotification

    def __init__(self, setup: dict, today: datetime = datetime.today()):
        self.__name = setup["name"]
        self.__id = setup["id"]
        self.__description = setup["description"]
        self.__category_id = setup["category_id"]
        self.__level = Level[setup["level"]]
        self.__meter_ids = setup["meter_ids"]
        self.set_definition_flags_from_str_flags(flags_list=setup["flags"])
        self.__last_check = utility.get_datetime_from_iso_str(setup["last_check"])
        self.__notification = AlertNotification(setup=setup["notification"])
        self.__calculator = AlertCalculator(setup=setup["calculator"], today=today, last_check=self.last_check)


    @property
    def is_active(self) -> bool:
        return self.has_definition_flag(AlertDefinitionFlag.ACTIVE)

    # CHECK
    def check(self, today: datetime):
        """
        Check if we are in alert situation for each meter ids according to this Alert Definition

        :param today the date you want to check
        :type today datetime

        """
        for meter_id in self.meter_ids:
            if self.calculator.is_alert_situation(meter_id=meter_id):
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

    # DEFINITION FLAG
    def has_definition_flag(self, flag: AlertDefinitionFlag):
        return bool(flag.value & self.__alert_definition_flag)

    def add_definition_flag(self, flag: AlertDefinitionFlag):
        self.__alert_definition_flag |= flag.value

    def reset_definition_flag(self):
        self.__alert_definition_flag = AlertDefinitionFlag.INACTIVE.value

    def remove_definition_flag(self, flag: AlertDefinitionFlag):
        self.__alert_definition_flag ^= flag.value

    def set_definition_flags_from_str_flags(self, flags_list: array):
        self.reset_definition_flag()
        for str_flag in flags_list:
            flag = AlertDefinitionFlag[str_flag]
            self.add_definition_flag(flag)

    @property
    def definition_flag(self):
        return self.__alert_definition_flag

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

    FILENAME = "alert_definitions.json"

    __alert_definition_list: list
    __today: datetime

    def __init__(self):
        self.__today = datetime.today()
        data = get_data_from_json_file(get_path_in_data_folder_of(AlertManager.FILENAME))
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

    def save(self):
        pass  # TODO

    @staticmethod
    def start_manager():
        alert_manager = AlertManager()
        alert_manager.start()
        alert_manager.save()

    @property
    def alert_definition_list(self):
        return self.__alert_definition_list

    @property
    def today(self):
        return self.__today


if __name__ == '__main__':
    AlertManager.start_manager()
