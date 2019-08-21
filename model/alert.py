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

from model.day import Day
from model.my_exception import DayTypeError
from model.tokill.my_decorator import controller_types
from model.utility import get_day_name_from_datetime, get_dict_from_json_file, get_str_from_file, \
    get_source_path, get_data_path
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
    return value * (1 + (percent/100))


def new_inf_value(value: float, percent: int) -> float:
    return value * (1 - (percent/100))


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
    LAST_CHECK = "LAST_CHECK"
    USER_BASED = "USER_BASED"


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
    USER_BASED_VALUE = "USER_BASED_VALUE"
    SIMPLE_DB_BASED_VALUE = "SIMPLE_DB_BASED_VALUE"
    PERIOD_BASED_VALUE = "PERIOD_BASED_VALUE"


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

    def connect(self, conn_info: dict): # TODO
        pass

    @abstractmethod
    def get_value_in_db(self):
        raise NotImplementedError


class SimpleDBBasedValueGenerator(DataBaseValueGenerator, ValueGenerator):  # GOAL

    def __init__(self, conn_info: dict) -> None:
        super().__init__(conn_info=conn_info)
        self.get_value_in_db()

    def get_value_in_db(self):
        pass #TODO


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


# ------------------ [ AlertValue Class ] ---------------------

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
        self.__value_generator_type = ValueGeneratorType(self.setup["value_type"])
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
        return self.__value

    @property
    def setup(self):
        return self.__setup

# ------------------ [ AlertData Class ] ---------------------


class AlertData:
    # setup
    __setup: dict

    # data
    __data_name: str
    __data_period_type: PeriodGeneratorType
    __data_period_generator: PeriodGenerator
    __data: float  # data to check - calculated from data_name

    def __init__(self, setup: dict, last_check: datetime, today: datetime):
        self.__setup = setup
        self.__data_name = setup["data_name"]
        self.__data_period_type = PeriodGeneratorType(setup["data_period_type"])

        self.set_period_generator(last_check=last_check, today=today)

    def set_period_generator(self, last_check: datetime, today: datetime) -> None:
        # Set Factory
        if self.data_period_type is PeriodGeneratorType.LAST_CHECK:
            self.__data_period_generator = LastCheckBasedPeriodGenerator(last_check=last_check,
                                                                         today=today)
        elif self.data_period_type is PeriodGeneratorType.USER_BASED:
            self.__data_period_generator = UserBasedPeriodGenerator(user_data=self.setup["data_period"],
                                                                    today=today)

    def get_all_data_in_db(self) -> "list: all data from db":
        period = self.__data_period_generator.get_pertinent_period()
        start_date = period.get_start_date()
        all_data = [30, 45, 60]  # TODO : Link To DB
        return all_data

    # property
    @property
    def data_name(self):
        return self.__data_name

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



# ------------------ [ FACTORY Class ] ---------------------

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

    # -- Find Value that will be Compare with Data --
    def __get_value(self):
        if self.acceptable_diff:
            self.__value = self.comparator.get_new_value(value=self.alert_value.value, percent=self.alert_value.value_number)
        return self.value_generator.value

    def is_alert_situation(self):
        self.__data = self.__operator.calculate(self.alert_data.get_all_data_in_db())
        self.__value = self.__get_value()
        return self.comparator.compare(self.data, self.value)

    # --- PROPERTIES ---
    # general
    @property
    def setup(self):
        return self.__setup

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
class NotificationPeriod(Enum):
    DAY = "DAY",  1     # 1 Day per DAY
    WEEK = "WEEK", 7    # 7 Days per WEEK
    MONTH = "MONTH", 30  # 30 Days per MONTH

    def __new__(cls, value, nb_day: int):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.nb_day_in_period = nb_day
        return obj


class AlertNotification:
    __number: int
    __period: NotificationPeriod
    __email: str

    def __init__(self, setup: dict):
        self.__number = setup["number"]
        self.__period = NotificationPeriod(setup["period"])
        self.__email = setup["email"]

    def is_notification_allowed(self, previous: datetime, datetime_to_check: datetime):
        """
        check if we are allowed to send a new notification

        :param previous: datetime of the last notification
        :type previous: datetime
        :param datetime_to_check the date you want to check
        :type datetime_to_check: datetime

        """
        # get Time between both date
        delta = datetime_to_check - previous

        # Get day divided by nb_day in period (equivalent values)
        count = delta.days / self.period.nb_day_in_period

        return count >= self.number

    @property
    def number(self):
        return self.__number

    @property
    def period(self):
        return self.__period

    @property
    def email(self):
        return self.__email


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
        self.__config = get_dict_from_json_file(self.email_config_path(filename))
        self.__subject = self.config["subject"]
        self.__sender_email = self.config["sender_email"]
        self.__email_content = get_str_from_file(self.get_file_path_name())

    def generate_template(self, data_name: str, text_message: str):
        self.__subject += data_name
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

        # Log in to server using secure context and send email
        context = ssl.create_default_context()
        with smtplib.SMTP("localhost") as server:
            server.send_message(from_addr=self.sender_email, to_addrs=self.receiver_email, msg=html.as_string())

    def email_config_path(self, filename: str):
        config_path = os.path.join(get_data_path(), filename)
        print("config_path", config_path)
        return config_path

    def get_template_path(self):
        template_path = os.path.join(get_source_path(), self.TEMPLATE_FOLDER_NAME)
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

class Alert:
    __id: str
    __data_name: str
    __date: datetime
    __alert_calculator: AlertCalculator

    def __init__(self, alert_calculator: AlertCalculator, today:datetime, data_name: str) -> None:
        self.__alert_calculator = alert_calculator
        self.__data_name = data_name
        self.__date = today
        # TODO generate ID




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
    - its NOTIFICATION - template, period of watch
    - an ALERT CREATION - date, invalid data ...
    """

    __alert_calculator: AlertCalculator
    __notification: AlertNotification

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


# ---------------------------------------------------------------------------------------------------------------------
