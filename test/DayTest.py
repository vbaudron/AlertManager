#!/usr/bin/python3
# -*-coding:Utf-8 -*
from datetime import datetime

from model.AlertEnum.Day import Day

import unittest

from model.Exception.MyException import DayTypeError
from utils.DateUtils import DateUtils


class DayTest(unittest.TestCase):

    def setUp(self):
        self.monday = datetime(2019, 7, 29)  # 29 July 2019 was a MONDAY
        self.saturday = datetime(2019, 7, 27)  # 27 July 2019 was a SATURDAY

    def test__get_day_str_name(self):
        # VALID
        name = DateUtils.get_day_name(self.monday)
        day = Day.get_day_by_str_name(name)
        self.assertTrue(day, Day.MONDAY)
        self.assertTrue(isinstance(day, Day))

        # ERROR
        with self.assertRaises(DayTypeError):
            Day.get_day_by_str_name("Hello")


if __name__ == '__main__':
    unittest.main()
