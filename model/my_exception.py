import logging as log
from enum import Enum

import model.alert
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
