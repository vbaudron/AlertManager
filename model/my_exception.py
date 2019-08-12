import logging as log

from model import day


class DayTypeError(Exception):
    def __init__(self, wrong_value: object) -> object:
        print(self.__class__.__name__ + " has been created with wrong values : " + wrong_value)
        log.debug(self.__class__.__name__ + " has been created with wrong values : " + wrong_value)
        self.wrong_value = str(wrong_value)

    def __str__(self):
        my_str = "{0} is not a valid value. Day valid values are : {1}".format(self.wrong_value, day.Day.str_values())
        return my_str
