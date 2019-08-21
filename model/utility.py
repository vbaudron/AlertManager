import calendar
import json
import os.path
import sys
from typing import Any, Union

import mysql.connector

import datetime

DATA_FOLDER_NAME = "data"
SOURCE_FOLDER_NAME = "source"

def get_day_name_from_datetime(datetime):
    return calendar.day_name[datetime.weekday()]


def get_dict_from_json_file(file_path_name):
    print(file_path_name)
    with open(file_path_name, 'r') as f:
        my_dict = json.load(f)
    return my_dict


def get_str_from_file(file_path_name):
    with open(file_path_name, 'r') as f:
        my_str = f.read()
    return my_str


def get_file_last_modification_time(file_path_name: str) -> datetime:
    return os.path.getmtime(file_path_name)

def get_source_path():
    return os.path.join(os.getcwd(), SOURCE_FOLDER_NAME)


def get_data_path():
    return os.path.join(os.getcwd(), DATA_FOLDER_NAME)


class MySqlConnection():

    FILENAME = "../data/mysql_config.json"  # TODO

    __host: str
    __username: str
    __password: str
    __database: str

    __open_time: datetime

    def __init__(self) -> None:
        super().__init__()
        self.__open_time = datetime.datetime.today()
        self.__update_connection_info()

    def get_or_update_file(self):
        if self.open_time < get_file_last_modification_time(self.FILENAME):
            self.__update_connection_info()

    def __update_connection_info(self):
        setup = get_dict_from_json_file(self.FILENAME)
        self.__host = setup["host"]
        self.__username = setup["username"]
        self.__password = setup["password"],
        self.__database = setup["database"]

    def connect(self):
        return mysql.connector.connect(
            host=self.host,
            user=self.username,
            passwd=self.password
        )

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


# TODO mysql_conn = MySqlConnection().connect()

if __name__ == '__main__':
    for i in range(0, 7):
        print(calendar.day_name[i])

