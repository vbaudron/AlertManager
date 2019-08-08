#!/usr/bin/python3
# -*-coding:Utf-8 -*
from datetime import datetime, timedelta

from model.AlertEnum.Level import Level
from model.AlertEnum.Day import Day
from model.AlertDefinition import AlertDefinition, AlertDefinitionFlag

import unittest

from model.AlertDefinition import AlertDefinitionStatus
from model.Exception.MyException import DayTypeError


class AlertDefinitionTest(unittest.TestCase):

    def setUp(self):
        self.monday = datetime(2019, 7, 29)  # 29 July 2019 was a MONDAY
        self.saturday = datetime(2019, 7, 27)  # 27 July 2019 was a SATURDAY

    def test__init(self):
        alert_definition = AlertDefinition()
        self.assertIsInstance(alert_definition, AlertDefinition)

    # WATCHING PERIOD
    def test__add_day_to_watching_period(self):
        alert_definition = AlertDefinition()

        # initialize with None
        self.assertEqual(alert_definition.get_watching_period(), Day.NONE.value)

        # SIMPLE : add one day
        day = Day.MONDAY
        alert_definition.add_day_to_watching_period(day)
        self.assertEqual(alert_definition.get_watching_period(), day.value)

        # SIMPLE : add another day
        second_day = Day.TUESDAY
        alert_definition.add_day_to_watching_period(second_day)
        result_expected = day.value | second_day.value
        self.assertEqual(alert_definition.get_watching_period(), result_expected)

        # ERROR : Not a Day
        with self.assertRaises(DayTypeError):
            alert_definition.add_day_to_watching_period("hello")

    def test__reset_watching_period(self):
        alert_definition = AlertDefinition()

        # add day that should be removed after reset call
        day = Day.MONDAY
        alert_definition.add_day_to_watching_period(day)
        self.assertEqual(alert_definition.get_watching_period(), day.value)

        alert_definition.reset_watching_period()
        self.assertEqual(alert_definition.get_watching_period(), Day.NONE.value)

    def test__has_day_in_watching_period(self):
        alert_definition = AlertDefinition()

        to_have_flag = Day.MONDAY
        not_to_have_flag = Day.TUESDAY

        alert_definition.add_day_to_watching_period(to_have_flag)

        self.assertTrue(alert_definition.has_day_in_watching_period(to_have_flag))
        self.assertFalse(alert_definition.has_day_in_watching_period(not_to_have_flag))

        # Test in Multiples Flags
        alert_definition.add_day_to_watching_period(Day.SATURDAY)
        self.assertTrue(alert_definition.has_day_in_watching_period(Day.SATURDAY))
        self.assertFalse(alert_definition.has_day_in_watching_period(not_to_have_flag))
        self.assertTrue(alert_definition.has_day_in_watching_period(to_have_flag))

    def test__set_watching_period(self):
        alert_definition = AlertDefinition()

        # Single Day to add
        day = [Day.MONDAY]
        alert_definition.set_watching_period(day)
        self.assertTrue(bool(alert_definition.get_watching_period() & day[0].value))

        # Method replace day, not added it to previous
        day_new = [Day.TUESDAY]
        alert_definition.set_watching_period(day_new)
        self.assertFalse(alert_definition.has_day_in_watching_period(day[0]))
        self.assertTrue(bool(alert_definition.get_watching_period() & day_new[0].value))

        # Multiple Day in Once
        days_list = [Day.MONDAY, Day.TUESDAY]
        not_to_have_day = Day.SUNDAY
        alert_definition.set_watching_period(days_list)
        self.assertTrue(alert_definition.has_day_in_watching_period(Day.MONDAY))
        self.assertTrue(alert_definition.has_day_in_watching_period(Day.TUESDAY))

        # ERROR CASE : Day not added
        not_day = "im no Day"
        alert_definition.set_watching_period(not_day)
        self.assertEqual(alert_definition.get_watching_period(), Day.NONE.value)

        # ERROR CASE - List of days with second number
        not_day_list = [Day.MONDAY, not_day]
        alert_definition.set_watching_period(not_day_list)
        self.assertEqual(alert_definition.get_watching_period(), Day.MONDAY.value)

    def test__is_watching_period(self):
        alert_definition = AlertDefinition()

        # Flags list is added with FLAG
        alert_definition.add_day_to_watching_period(Day.MONDAY)

        # Watching Period : SINGLE day
        self.assertTrue(alert_definition.is_datetime_in_watching_period(self.monday))
        self.assertFalse(alert_definition.is_datetime_in_watching_period(self.saturday))

        # Watching Period : MANY days
        alert_definition.add_day_to_watching_period(Day.TUESDAY)
        tuesday = self.monday + timedelta(days=1)
        self.assertTrue(alert_definition.is_datetime_in_watching_period(self.monday))
        self.assertTrue(alert_definition.is_datetime_in_watching_period(tuesday))
        self.assertFalse(alert_definition.is_datetime_in_watching_period(self.saturday))

        alert_definition.add_day_to_watching_period(Day.SATURDAY)
        self.assertTrue(alert_definition.is_datetime_in_watching_period(self.saturday))

    # STATUS @deprecated --> replace by a flag in AlertDefinitionFlag class
    def test__set_status(self):
        alert_definition = AlertDefinition()
        alert_definition.set_definition_status(AlertDefinitionStatus.INACTIVE)
        self.assertTrue(alert_definition.get_definition_status() == AlertDefinitionStatus.INACTIVE)
        alert_definition.set_definition_status(AlertDefinitionStatus.ACTIVE)
        self.assertTrue(alert_definition.get_definition_status() == AlertDefinitionStatus.ACTIVE)

    # IS ACTIVE
    def test__is_active(self):
        alert_definition = AlertDefinition()
        alert_definition.add_definition_flag(AlertDefinitionFlag.INACTIVE)
        self.assertFalse(alert_definition.is_active)
        alert_definition.add_definition_flag(AlertDefinitionStatus.ACTIVE)
        self.assertTrue(alert_definition.is_active)

    # SET INACTIVE
    def test__set_inactive(self):
        alert_definition = AlertDefinition()
        active_flag = AlertDefinitionFlag.ACTIVE

        # SIMPLE
        alert_definition.set_definition_flag(active_flag)
        self.assertTrue(alert_definition.has_definition_flag(active_flag))
        alert_definition.set_inactive()
        self.assertFalse(alert_definition.has_definition_flag(active_flag))

        # MULTIPLE
        flag_2 = AlertDefinitionFlag.SAVE_ALL
        alert_definition.set_definition_flags([active_flag, flag_2])

        self.assertTrue(alert_definition.has_definition_flag(active_flag))
        self.assertTrue(alert_definition.has_definition_flag(flag_2))

        alert_definition.set_inactive()

        self.assertFalse(alert_definition.has_definition_flag(active_flag))
        self.assertTrue(alert_definition.has_definition_flag(flag_2))

    # LEVEL
    def test__set_level(self):
        alert_definition = AlertDefinition()
        self.assertTrue(alert_definition.get_level() is None)
        alert_definition.set_level(Level.HIGH)
        self.assertTrue(alert_definition.get_level() == Level.HIGH)

    # DEFINITION FLAG
    def test__set_definition_flag(self):
        alert_definition = AlertDefinition()
        alert_definition.set_definition_flag(AlertDefinitionFlag.SAVE_ALL)
        self.assertTrue(alert_definition.get_definition_flag() == AlertDefinitionFlag.SAVE_ALL.value)

    def test__remove_definition_flag(self):
        alert_definition = AlertDefinition()
        flag = AlertDefinitionFlag.ACTIVE

        # SIMPLE
        alert_definition.set_definition_flag(flag)
        self.assertTrue(alert_definition.has_definition_flag(flag))
        alert_definition.remove_definition_flag(flag)
        self.assertFalse(alert_definition.has_definition_flag(flag))

        # MULTIPLE
        flag_2 = AlertDefinitionFlag.SAVE_ALL
        alert_definition.set_definition_flags([flag, flag_2])

        self.assertTrue(alert_definition.has_definition_flag(flag))
        self.assertTrue(alert_definition.has_definition_flag(flag_2))

        alert_definition.remove_definition_flag(flag)

        self.assertFalse(alert_definition.has_definition_flag(flag))
        self.assertTrue(alert_definition.has_definition_flag(flag_2))

    def test__has_definition_flag(self):
        alert_definition = AlertDefinition()
        self.assertFalse(alert_definition.has_definition_flag(AlertDefinitionFlag.SAVE_ALL))
        alert_definition.set_definition_flag(AlertDefinitionFlag.SAVE_ALL)
        self.assertTrue(alert_definition.has_definition_flag(AlertDefinitionFlag.SAVE_ALL))

    def test__set_definition_flags(self):
        alert_definition = AlertDefinition()
        flags = [AlertDefinitionFlag.SAVE_ALL, AlertDefinitionFlag.ANOTHER_FLAG]
        alert_definition.set_definition_flags(flags)
        self.assertTrue(bool(alert_definition.get_definition_flag() & AlertDefinitionFlag.SAVE_ALL.value))
        self.assertTrue(bool(alert_definition.get_definition_flag() & AlertDefinitionFlag.ANOTHER_FLAG.value))


if __name__ == '__main__':
    unittest.main()
