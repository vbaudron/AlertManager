import calendar
import json
import os.path
import sys
from enum import Enum
import logging as log
from typing import Any, Union

import dateutil.parser
import mysql.connector
from mysql.connector import errorcode, MySQLConnection

import datetime

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
        my_str += "'{0}' : {1}    ".format(name, member.value)
    return my_str


# __________________________________________________ MY SQL ____________________________________________________________


class MySqlConnection:

    FILENAME = "mysql_config.json"

    __host: str
    __username: str
    __password: str
    __database: str

    __open_time: datetime

    __connection: MySQLConnection

    def __init__(self) -> None:
        super().__init__()
        self.__open_time = datetime.datetime.today()
        self.__update_connection_info()
        self.__connection = None

    def get_file_path(self):
        return get_path_in_data_folder_of(MySqlConnection.FILENAME)

    def update_file_if_needed(self) -> bool:
        if self.open_time.timestamp() < get_file_last_modification_time(self.get_file_path()):
            self.__update_connection_info()
            return True
        return False

    def __update_connection_info(self):
        setup = get_data_from_json_file(self.get_file_path())
        self.__host = setup["host"]
        self.__username = setup["username"]
        self.__password = setup["password"]
        self.__database = setup["database"]

    def connect(self):
        self.__connection = MySQLConnection(
            host=self.host,
            user=self.username,
            password=self.password,
            db=self.database
        )
        log.debug("connected")
        print("connected")

    def generate_cursor(self):
        if self.update_file_if_needed() or not self.__connection or not self.__connection.is_connected():
            self.connect()
        return self.__connection.cursor()

    def execute_and_close(self, query: str, params=None):
        my_cursor = self.generate_cursor()
        my_cursor.execute(operation=query, params=params)
        my_sql.commit()
        my_cursor.close()
        my_sql.close()

    def commit(self):
        my_sql.__connection.commit()

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


# -------------------------- #   MySQL Connection   # -------------------------- #

my_sql = MySqlConnection()

# -------------------------- #     Alert Table      # -------------------------- #

ALERT_TABLE_NAME = "alerts"
METER_TABLE_NAME = "BI_COMPTEURS"

CREATE_ALERT_TABLE = "CREATE TABLE IF NOT EXISTS {}".format(ALERT_TABLE_NAME)
ALERT_TABLE_COMPO = {
    "alert_id": "INT AUTO_INCREMENT PRIMARY KEY",
    "datetime": "DATETIME NOT NULL",
    "alert_definition_description": "VARCHAR(255) NOT NULL",
    "data": "DOUBLE",
    "value": "DOUBLE",
    "status": "TINYINT",
    "meter_id": "INT NOT NULL"
}

FOREIGN_KEY = "FOREIGN KEY (meter_id) REFERENCES {}(id)".format(METER_TABLE_NAME)

# -------------------------- #     Compteurs Table      # -------------------------- #


# ______________________________________________________________________________________________________________________

