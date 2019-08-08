#!/usr/bin/python3
# -*-coding:Utf-8 -*
import calendar
import datetime

from model.AlertEnum.Day import Day

import unittest

from utils.DateUtils import DateUtils


class DayTest(unittest.TestCase):

    def setUp(self):
        self.monday = datetime.datetime(2019, 7, 29)  # 29 July 2019 was a MONDAY

    def test__get_day_name(self):
        for i in range(0, 7):
            day = self.monday + datetime.timedelta(days=i)
            day_name = DateUtils.get_day_name(day)
            self.assertEqual(day_name, calendar.day_name[i])


if __name__ == '__main__':
    unittest.main()
