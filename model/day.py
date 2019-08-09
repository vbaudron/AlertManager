#!/usr/bin/python3
# -*-coding:Utf-8 -*

from enum import Flag, auto, unique

from model.my_exception import DayTypeError


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
    def get_day_by_str_name(name):
        name = name.upper()
        for d_name, member in Day.__members__.items():
            if d_name == name:
                return member
        raise DayTypeError(name)

    @staticmethod
    def str_values():
        my_str = ""
        for name, member in Day.__members__.items():
            my_str += "_{0} : {1}_    ".format(name, member.value)
        return my_str


if __name__ == "__main__":
    print("str_values() :")
    print(Day.str_values())
    print("Weekend definition...")
    weekend = Day.SATURDAY | Day.SUNDAY
    print("... weekend is about ", weekend, " : ", weekend.value)
    print("is Monday a day from Weekend ? ")
    print(bool(weekend & Day.MONDAY))
    print("is Saturday a day from Weekend ? ")
    print(bool(weekend & Day.SATURDAY))
