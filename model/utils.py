import calendar
import datetime
import json
import logging as log
import os.path
from enum import Enum

import dateutil.parser
from mysql.connector import MySQLConnection

from definition import ROOT_DIR



# _______________________________________________ PATH _________________________________________________________________

# Folder Name
DATA_FOLDER_NAME = "data"
SOURCE_FOLDER_NAME = "source"

# Path Name
DATA_PATH = os.path.join(ROOT_DIR, DATA_FOLDER_NAME)
SOURCE_PATH = os.path.join(ROOT_DIR, SOURCE_FOLDER_NAME)


# Function to get full pat DATA
def get_path_in_data_folder_of(filename: str):
    return os.path.join(DATA_PATH, filename)


# Function to get full path from SOURCE
def get_path_in_source_folder_of(filename: str):
    return os.path.join(SOURCE_FOLDER_NAME, filename)


# _________________________________________________ DATETIME ___________________________________________________________


def get_datetime_from_iso_str(s: str) -> datetime:
    d = None
    if s:
        d = dateutil.parser.parse(s)
    return d


def get_day_name_from_datetime(my_datetime: datetime) -> "day Name":
    try:
        return calendar.day_name[my_datetime.weekday()]
    except KeyError as error:
        log.error(error.__str__())


def get_data_from_json_file(file_path_name):
    print(file_path_name)
    with open(file_path_name, 'r') as f:
        my_data = json.load(f)
    return my_data


# ___________________________________________________ FILE ____________________________________________________________


def get_str_from_file(file_path_name):
    with open(file_path_name, 'r') as f:
        my_str = f.read()
    return my_str


def get_file_last_modification_time(file_path_name: str) -> datetime:
    return os.path.getmtime(file_path_name)


def enum_str_values(enum: Enum) -> "Str of each member of the enum":
    my_str = ""
    for name, member in enum.__members__.items():
        my_str += "'{0}' : {1}    ".format(name, str(member.value))
    return my_str



# __________________________________________________ MY SQL ____________________________________________________________


class MySqlConnection:
    TEST_MODE = False
    FILENAME = "mysql_config.json"
    FILENAME_TEST = "mysql_config_test.json"

    __host: str
    __username: str
    __password: str
    __database: str
    __port: str

    __open_time: datetime

    __connection: MySQLConnection

    def __init__(self) -> None:
        super().__init__()
        self.__open_time = None
        self.__connection = None

        # CONFIG
    def update_open_time(self):
        self.__open_time = datetime.datetime.today()

    @staticmethod
    def get_file_path():
        if not MySqlConnection.TEST_MODE:
            return get_path_in_data_folder_of(MySqlConnection.FILENAME)
        else:
            return get_path_in_data_folder_of(MySqlConnection.FILENAME_TEST)

    def update_file_if_needed(self) -> bool:
        if not self.open_time or self.open_time.timestamp() < get_file_last_modification_time(self.get_file_path()):
            self.__update_connection_info()
            return True
        return False

    def __update_connection_info(self):
        setup = get_data_from_json_file(self.get_file_path())
        self.update_open_time()
        self.__host = setup["host"]
        self.__username = setup["username"]
        self.__password = setup["password"]
        self.__database = setup["database"]
        self.__port = setup["port"]

    def connect_without_database(self):
        self.update_file_if_needed()
        self.__connection = MySQLConnection(
            host=self.host,
            user=self.username,
            password=self.password,
            port=self.__port
        )
        print("connected without database")


    # CONNECTION
    def __connect(self):
        self.__connection = MySQLConnection(
            host=self.host,
            user=self.username,
            password=self.password,
            db=self.database,
            port=self.__port
        )
        log.debug("connected")
        print("connected")


    def generate_cursor(self):
        if self.update_file_if_needed() or not self.__connection or not self.__connection.is_connected():
            self.__connect()
        return self.__connection.cursor()

    def execute_and_close(self, query: str, params=None, return_id=False):
        my_cursor = self.generate_cursor()
        my_cursor.execute(operation=query, params=params)
        my_sql.commit()
        if return_id:
            my_id = my_cursor.lastrowid
            my_cursor.close()
            return my_id
        else:
            my_cursor.close()

    def commit(self):
        self.__connection.commit()

    def close(self):
        self.__connection.cursor().close()
        self.__connection.close()

    @property
    def open_time(self):
        return self.__open_time

    @property
    def host(self):
        return self.__host

    @property
    def username(self):
        return self.__username

    @property
    def password(self):
        return self.__password

    @property
    def database(self):
        return self.__database


def iter_row(cursor, size=10):
    while True:
        rows = cursor.fetchmany(size=size)
        if not rows:
            break
        for row in rows:
            yield row

# -------------------------- #   MySQL Connection   # -------------------------- #
my_sql = MySqlConnection()
# -------------------------- #     ABSTRACT Table Creation     # -------------------------- #

class TableToGenerate:

    __table_name: str
    __compo: dict
    __foreign_key: list

    def __init__(self, table_name: str, compo: dict, foreign_keys: list=None):
        self.__table_name = table_name
        self.__compo = compo
        self.__foreign_key = foreign_keys

    @staticmethod
    def __generate_one_compo(key: str, value: str):
        return key + " " + value

    def __generate_table_creation_param_from_compo(self) -> tuple:
        my_params = tuple(TableToGenerate.__generate_one_compo(key, value) for key, value in self.__compo.items())
        return my_params

    def __generate_alert_table_creation_query(self):
        # BASE
        my_format = "CREATE TABLE IF NOT EXISTS {} (".format(self.__table_name)

        # COMPO
        params = self.__generate_table_creation_param_from_compo()
        i = 0
        size = len(self.__compo)
        while i < size:
            my_format += params[i]
            i += 1
            if i < size:
                my_format += ", "

       # FOREIGN KEYS
        if self.__foreign_key:
            for key in self.__foreign_key:
                my_format += ", "
                my_format += key
        my_format += ")"
        return my_format

    def request_table_creation(self):
        query = self.__generate_alert_table_creation_query()
        print(query)
        my_sql.execute_and_close(query=query)
        return TableToGenerate.check_if_table_created(table_name=self.__table_name)


    def __str__(self):
        return self.__table_name + " table"


    @property
    def name(self):
        return self.__table_name

    # CHECK
    @staticmethod
    def show_tables_request():
        request = "SHOW TABLES"
        cursor = my_sql.generate_cursor()
        cursor.execute(request)
        result = list()
        for x in cursor.fetchall():
            for y in x:
                result.append(y)
        cursor.close()
        return result

    @staticmethod
    def check_if_table_created(table_name: str):
        # check
        result = TableToGenerate.show_tables_request()
        if table_name in result:
            log.debug("{} table exists".format(table_name))
            return True
        else:
            log.error("{} table does NOT exist".format(table_name))
            return False

    @staticmethod
    def drop_table(table_name: str):
        query = "DROP TABLES {}".format(table_name)
        my_sql.execute_and_close(query=query)



# _______________________________________________ Table Creation _______________________________________________________

METER_TABLE_NAME = "bi_compteurs"


# ---- #     Notification DEFINITION    # ---- #

NOTIFICATION_NAME = "alert_notification"
NOTIFICATION_COMPO = {
    "id": "INT AUTO_INCREMENT PRIMARY KEY",
    "period_unit": "VARCHAR(8) NOT NULL",
    "period_quantity": "INT NOT NULL",
    "email": "VARCHAR(255) NOT NULL",
    "days_flag": "INT NOT NULL DEFAULT 0",
    "hours_flag": "INT NOT NULL DEFAULT 0"
}

# ---- #     CALCULATOR DEFINITION    # ---- #

CALCULATOR_NAME = "alert_calculator"
CALCULATOR_COMPO = {
    "id": "INT AUTO_INCREMENT PRIMARY KEY",
    "operator": "VARCHAR(8) NOT NULL",
    "comparator": "VARCHAR(8) NOT NULL",
    "data_period_type": "VARCHAR(16) NOT NULL",
    "data_period_quantity": "INT",
    "data_period_unit": "VARCHAR(8)",
    "value_type": "VARCHAR(32) NOT NULL",
    "value_number": "DOUBLE NOT NULL",
    "value_period_type": "VARCHAR(16) DEFAULT NULL",
    "hour_start": "TINYINT SIGNED DEFAULT NULL",
    "hour_end": "TINYINT SIGNED DEFAULT NULL",
    "acceptable_diff": "BOOLEAN DEFAULT 0"
}

# ---- #     DEFINITION ALERTS   # ---- #

DEFINITION_TABLE_NAME = "alert_definition"
DEFINITION_COMPO = {
    "id": "INT AUTO_INCREMENT PRIMARY KEY",
    "name": "VARCHAR(255) DEFAULT NULL",
    "category": "VARCHAR(255) DEFAULT NULL",
    "description": "VARCHAR(255) DEFAULT NULL",
    "level": "INT NOT NULL",
    "status": "TINYINT NOT NULL",
    "notification_id": "INT NOT NULL",
    "calculator_id": "INT NOT NULL"
}
DEFINITON_ALERT_FOREIGN_KEY = [
    "FOREIGN KEY (notification_id) REFERENCES {}(id)".format(NOTIFICATION_NAME),
    "FOREIGN KEY (calculator_id) REFERENCES {}(id)".format(CALCULATOR_NAME)
]

# ---- #     BI_METERS_DEFINITIONS_ALERTS     # ---- #

METER_DEFINITIONS_ALERT_TABLE_NAME = "alert_definition_meter"

METER_DEFINITION_COMPO = {
    "meter_id": "INT NOT NULL",
    "alert_definition_id": "INT NOT NULL"
}
METER_DEFINITION_ALERT_FOREIGN_KEY = [
    "FOREIGN KEY (meter_id) REFERENCES {}(id)".format(METER_TABLE_NAME),
    "FOREIGN KEY (alert_definition_id) REFERENCES {}(id)".format(DEFINITION_TABLE_NAME)
]

# ---- #     Alert      # ---- #

ALERT_TABLE_NAME = "alert_alert"

ALERT_TABLE_COMPO = {
    "id": "INT AUTO_INCREMENT PRIMARY KEY",
    "creation_date": "DATETIME NOT NULL",
    "modification_date": "DATETIME NOT NULL",
    "data": "DOUBLE NOT NULL",
    "value": "DOUBLE NOT NULL",
    "status": "TINYINT NOT NULL",
    "alert_definition_id": "INT NOT NULL",
    "meter_id": "INT NOT NULL"
}

ALERT_FOREIGN_KEY = [
    "FOREIGN KEY (meter_id) REFERENCES {}(id)".format(METER_TABLE_NAME),
    "FOREIGN KEY (alert_definition_id) REFERENCES {}(id)".format(DEFINITION_TABLE_NAME)
]

# ---- #     Alert Definition Notification      # ---- #
ALERT_DEFINITION_NOTIFICATION_TIME = "alert_definition_notification_time"

ALERT_DEFINITION_NOTIFICATION_TIME_COMPO = {
    "id": "INT AUTO_INCREMENT PRIMARY KEY",
    "notification_id": "INT NOT NULL",
    "alert_definition_id": "INT NOT NULL",
    "notification_datetime": "DATETIME NOT NULL"
}

ALERT_DEFINITION_NOTIFICATION_TIME_FOREIGN_KEY = [
    "FOREIGN KEY (notification_id) REFERENCES {}(id)".format(NOTIFICATION_NAME),
    "FOREIGN KEY (alert_definition_id) REFERENCES {}(id)".format(DEFINITION_TABLE_NAME)
]


# ---- #     Alert Manager      # ---- #

ALERT_MANAGER_TABLE_NAME = "alert_manager"

ALERT_MANAGER_TABLE_COMPO = {
    "id": "INT AUTO_INCREMENT PRIMARY KEY",
    "launch_datetime": "DATETIME NOT NULL"
}

# ______________________________________________________________________________________________________________________


def insert_query_construction(compo, name):
    # PARAMS
    params_list = list(key for key in compo.keys())
    params_list.pop(0)
    params_str = ", ".join([param for param in params_list])

    # Format
    format_param = ", ".join(["%s" for param in params_list])

    # QUERY
    query = "INSERT INTO {} ({}) VALUES ({})".format(name, params_str, format_param)
    print(query)
    return query


def generate_hours_flag(notification_hours: list):
    hours = 0
    for hour in notification_hours:
        hours |= hour.value
    return hours


def generate_days_flag(notification_days: list):
    days = 0
    for day in notification_days:
        days |= day.value
    return days