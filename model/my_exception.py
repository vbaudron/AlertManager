from enum import Enum
from model.utility import enum_str_values


class EnumError(Exception):

    __wrong_value: str
    __except_enum: Enum

    def __init__(self, except_enum: Enum, wrong_value: object) -> object:
        self.__wrong_value = str(wrong_value)
        self.__except_enum = except_enum

        print(self.__class__.__name__ + " has been created with wrong values : " + self.wrong_value)

    def __str__(self):
        my_str = "'{}' is not a valid value. {} valid values are : {}".format(
            self.wrong_value,
            self.except_enum.__name__,
            enum_str_values(self.except_enum)
        )
        return my_str

    @property
    def wrong_value(self):
        return self.__wrong_value

    @property
    def except_enum(self):
        return self.__except_enum


class ConfigError(Exception):
    __message: str
    __obj: object

    def __init__(self, obj: object, msg: str):
        self.__message = msg
        self.__obj = obj

    def __str__(self):
        return "ConfigError from {} : {}".format(self.obj.__class__.__name__, self.message)

    @property
    def message(self):
        return self.__message

    @property
    def obj(self):
        return self.__obj
