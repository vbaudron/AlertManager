#!/usr/bin/python3
# -*-coding:Utf-8 -*
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from model.alert import AlertDefinition, AlertDefinitionFlag, Level, MyOperator, MyComparator, PeriodUnitDefinition, \
    PeriodDefinition, AlertCalculator, LastCheckBasedPeriodGenerator, PeriodGenerator, Period, UserBasedPeriodGenerator, \
    UserBasedValueGenerator, ValueGenerator, PeriodBasedValueGenerator, DataBaseValueGenerator, PeriodGeneratorType, \
    ValueGeneratorType, NoPeriodBasedValueGenerator, SimpleDBBasedValueGenerator, AlertData, AlertValue, \
    AlertNotification, NotificationPeriod, Day, Hour, AlertManager

from model.alert import AlertDefinitionStatus
from model.my_exception import EnumError


class NotificationTest(unittest.TestCase):

    setup: dict
    previous_notification_datetime: datetime

    def setUp(self) -> None:

        self.monday = datetime(2019, 7, 29)  # 29 July 2019 was a MONDAY
        self.saturday = datetime(2019, 7, 27)  # 27 July 2019 was a SATURDAY

        self.number = 1
        self.period = NotificationPeriod.DAY
        self.email = "test@test.com"
        self.notification_days = [
            Day.MONDAY, Day.TUESDAY
        ]
        self.notification_hours = [
            Hour.H_1, Hour.H_2
        ]
        self.previous_notification_datetime = None

    def generate_setup(self):
        self.setup = {
            "number": self.number,
            "period": self.period.name,
            "email": self.email,
            "notification_days": [day.name for day in self.notification_days],
            "notification_hours": [hour.int_hour for hour in self.notification_hours],
            "previous_notification_datetime": self.previous_notification_datetime.isoformat() if self.previous_notification_datetime else None
        }

    def update_and_generate_alert_notification(self) -> AlertNotification:
        self.generate_setup()
        return self.get_alert_notification()

    def get_alert_notification(self) -> AlertNotification:
        return AlertNotification(self.setup)

    # INIT
    def test__init(self):
        notification = self.update_and_generate_alert_notification()
        self.assertIsInstance(notification, AlertNotification)
        self.assertEqual(notification.number, self.number)
        self.assertEqual(notification.email, self.email)
        self.assertIsInstance(notification.period, NotificationPeriod)
        self.assertEqual(notification.period, self.period)


    def test__previous_datetime(self):
        # today
        dt = datetime.today()
        self.previous_notification_datetime = dt

        notification = self.update_and_generate_alert_notification()
        self.assertEqual(dt, notification.previous_notification_datetime)

        # None
        dt = None
        self.previous_notification_datetime = dt

        notification = self.update_and_generate_alert_notification()
        self.assertEqual(dt, notification.previous_notification_datetime)


    # --  DAY --

    def test__has_day_in_notification_days(self):
        to_have_day = Day.MONDAY
        not_to_have_day = Day.TUESDAY

        self.notification_days = [to_have_day]
        alert_notification = self.update_and_generate_alert_notification()

        self.assertTrue(alert_notification.has_day_in_notification_days(to_have_day))
        self.assertFalse(alert_notification.has_day_in_notification_days(not_to_have_day))

        # Test in Multiples Flags
        another_day_to_have = Day.SATURDAY
        self.notification_days = [to_have_day, another_day_to_have]
        alert_notification = self.update_and_generate_alert_notification()
        self.assertTrue(alert_notification.has_day_in_notification_days(day=to_have_day))
        self.assertFalse(alert_notification.has_day_in_notification_days(day=not_to_have_day))
        self.assertTrue(alert_notification.has_day_in_notification_days(day=another_day_to_have))

        # ERROR : Not a Day
        wrong_day = "iam no day"
        error = EnumError(except_enum=Day, wrong_value=wrong_day)

        with patch("logging.error") as mock:
            self.assertFalse(alert_notification.has_day_in_notification_days(day=wrong_day))
            mock.assert_called_with(error.__str__())

    def test__add_day_to_notification_days(self):
        self.notification_days = []
        alert_notification = self.update_and_generate_alert_notification()

        # initialize with None
        self.assertEqual(alert_notification.notification_days, Day.NONE.value)

        # SIMPLE : add one day
        day = Day.MONDAY
        alert_notification.add_day_to_notification_days(day)
        self.assertEqual(alert_notification.notification_days, day.value)

        # SIMPLE : add another day
        second_day = Day.TUESDAY
        alert_notification.add_day_to_notification_days(second_day)
        result_expected = day.value | second_day.value
        self.assertEqual(alert_notification.notification_days, result_expected)

        # ERROR : Not a Day
        self.notification_days = [Day.MONDAY]
        alert_notification = self.update_and_generate_alert_notification()

        wrong_day = "iam no day"
        error = EnumError(except_enum=Day, wrong_value=wrong_day)

        with patch("logging.error") as mock:
            alert_notification.add_day_to_notification_days(wrong_day)
            mock.assert_called_with(error.__str__())
            self.assertTrue(alert_notification.has_day_in_notification_days(Day.MONDAY))

    def test__remove_day_from_notification_days(self):
        # SIMPLE
        self.notification_days = [Day.MONDAY, Day.TUESDAY]
        alert_notification = self.update_and_generate_alert_notification()

        self.assertTrue(alert_notification.has_day_in_notification_days(Day.MONDAY))
        self.assertTrue(alert_notification.has_day_in_notification_days(Day.TUESDAY))

        alert_notification.remove_day_from_notification_days(Day.MONDAY)

        self.assertFalse(alert_notification.has_day_in_notification_days(Day.MONDAY))
        self.assertTrue(alert_notification.has_day_in_notification_days(Day.TUESDAY))

        # ERROR
        self.notification_days = [Day.MONDAY, Day.TUESDAY]
        alert_notification = self.update_and_generate_alert_notification()

        not_valid_day = "still not a day"
        error = EnumError(except_enum=Day, wrong_value=not_valid_day)

        self.assertTrue(alert_notification.has_day_in_notification_days(Day.MONDAY))
        self.assertTrue(alert_notification.has_day_in_notification_days(Day.TUESDAY))

        with patch("logging.error") as mock:
            alert_notification.remove_day_from_notification_days(not_valid_day)
            mock.assert_called_with(error.__str__())

        self.assertTrue(alert_notification.has_day_in_notification_days(Day.MONDAY))
        self.assertTrue(alert_notification.has_day_in_notification_days(Day.TUESDAY))

    def test__reset_notification_days(self):
        # - Only One -
        day = Day.MONDAY
        # add day that should be removed after reset call
        self.notification_days = [day]
        alert_notification = self.update_and_generate_alert_notification()
        self.assertEqual(alert_notification.notification_days, day.value)
        self.assertNotEqual(alert_notification.notification_days, Day.NONE.value)

        alert_notification.reset_notification_days()

        self.assertEqual(alert_notification.notification_days, Day.NONE.value)

        # - Many -
        self.notification_days = [Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY]
        alert_notification = self.update_and_generate_alert_notification()
        self.assertNotEqual(alert_notification.notification_days, Day.NONE.value)

        alert_notification.reset_notification_days()

        self.assertEqual(alert_notification.notification_days, Day.NONE.value)

    def test__set_notification_days(self):
        self.notification_days = []
        alert_definition = self.update_and_generate_alert_notification()

        # Single Day to add
        day = Day.MONDAY
        day_str = [day.name]
        alert_definition.set_notification_days(day_str)
        self.assertTrue(bool(alert_definition.notification_days & day.value))

        # Method replace day, not added it to previous
        day_new = Day.TUESDAY
        day_new_str = [day_new.name]
        alert_definition.set_notification_days(day_new_str)
        self.assertFalse(alert_definition.has_day_in_notification_days(day))
        self.assertTrue(bool(alert_definition.notification_days & day_new.value))

        # Multiple Day in Once
        days_list = [Day.MONDAY.name, Day.TUESDAY.name]
        not_to_have_day = Day.SUNDAY
        alert_definition.set_notification_days(days_list)
        self.assertTrue(alert_definition.has_day_in_notification_days(Day.MONDAY))
        self.assertTrue(alert_definition.has_day_in_notification_days(Day.TUESDAY))
        self.assertFalse(alert_definition.has_day_in_notification_days(not_to_have_day))

        # ERROR CASE : Day not added
        not_day = ["im no Day"]
        alert_definition.set_notification_days(not_day)
        self.assertEqual(alert_definition.notification_days, Day.NONE.value)

        # ERROR CASE - List of days with second number
        not_day_list = [Day.MONDAY.name, "im no Day_again"]
        alert_definition.set_notification_days(not_day_list)
        self.assertEqual(alert_definition.notification_days, Day.MONDAY.value)

    def test__is_datetime_in_notification_days(self):
        # Watching Period : SINGLE day
        self.notification_days = [Day.MONDAY]
        alert_notification = self.update_and_generate_alert_notification()

        self.assertTrue(alert_notification.is_datetime_in_notification_days(self.monday))
        self.assertFalse(alert_notification.is_datetime_in_notification_days(self.saturday))

        # Watching Period : MANY days
        self.notification_days = [Day.MONDAY, Day.TUESDAY]
        alert_notification = self.update_and_generate_alert_notification()

        tuesday = self.monday + timedelta(days=1)

        self.assertTrue(alert_notification.is_datetime_in_notification_days(self.monday))
        self.assertTrue(alert_notification.is_datetime_in_notification_days(tuesday))
        self.assertFalse(alert_notification.is_datetime_in_notification_days(self.saturday))

        # ERROR
        wrong_days = "iam no datetime"

        with patch("logging.error") as mock:
            alert_notification.is_datetime_in_notification_days(wrong_days)
            mock.assert_called()

    # --  HOURS --

    def test__has_hour_in_notification_hours(self):
        to_have_hour = Hour.H_1
        not_to_have_hour = Hour.H_2

        self.notification_hours = [to_have_hour]
        alert_notification = self.update_and_generate_alert_notification()

        self.assertTrue(alert_notification.has_hour_in_notification_hours(to_have_hour))
        self.assertFalse(alert_notification.has_hour_in_notification_hours(not_to_have_hour))

        # Test in Multiples Flags
        another_day_to_have = Hour.H_3
        self.notification_hours = [to_have_hour, another_day_to_have]
        alert_notification = self.update_and_generate_alert_notification()
        self.assertTrue(alert_notification.has_hour_in_notification_hours(hour=to_have_hour))
        self.assertFalse(alert_notification.has_hour_in_notification_hours(hour=not_to_have_hour))
        self.assertTrue(alert_notification.has_hour_in_notification_hours(hour=another_day_to_have))

        # ERROR : Not a Hour
        wrong_hour = "iam no hour"
        error = EnumError(except_enum=Hour, wrong_value=wrong_hour)

        with patch("logging.error") as mock:
            self.assertFalse(alert_notification.has_hour_in_notification_hours(hour=wrong_hour))
            mock.assert_called_with(error.__str__())

    def test__add_notification_hour(self):
        self.notification_hours = []
        alert_notification = self.update_and_generate_alert_notification()

        # initialize with None
        self.assertEqual(alert_notification.notification_hours, Hour.NONE.value)

        # SIMPLE : add one hour
        hour = Hour.H_1
        alert_notification.add_notification_hour(hour)
        self.assertEqual(alert_notification.notification_hours, hour.value)

        # SIMPLE : add another hour
        second_hour = Hour.H_2
        alert_notification.add_notification_hour(second_hour)
        result_expected = hour.value | second_hour.value
        self.assertEqual(alert_notification.notification_hours, result_expected)

        # ERROR : Not a hour - str
        self.notification_hours = [hour]
        alert_notification = self.update_and_generate_alert_notification()

        wrong_hour = "iam no hour"
        error = EnumError(except_enum=Hour, wrong_value=wrong_hour)

        with patch("logging.error") as mock:
            alert_notification.add_notification_hour(wrong_hour)
            mock.assert_called_with(error.__str__())
            self.assertTrue(alert_notification.has_hour_in_notification_hours(hour))

    def test__remove_hour_from_notification_hours(self):
        # SIMPLE
        self.notification_hours = [Hour.H_3, Hour.H_1]
        alert_notification = self.update_and_generate_alert_notification()

        self.assertTrue(alert_notification.has_hour_in_notification_hours(Hour.H_1))
        self.assertTrue(alert_notification.has_hour_in_notification_hours(Hour.H_3))

        alert_notification.remove_hour_from_notification_hours(Hour.H_3)

        self.assertFalse(alert_notification.has_hour_in_notification_hours(Hour.H_3))
        self.assertTrue(alert_notification.has_hour_in_notification_hours(Hour.H_1))

        # ERROR
        self.notification_hours = [Hour.H_3, Hour.H_1]
        alert_notification = self.update_and_generate_alert_notification()

        not_valid_hour = "still not an hour"
        error = EnumError(except_enum=Hour, wrong_value=not_valid_hour)

        self.assertTrue(alert_notification.has_hour_in_notification_hours(Hour.H_1))
        self.assertTrue(alert_notification.has_hour_in_notification_hours(Hour.H_3))

        with patch("logging.error") as mock:
            alert_notification.remove_hour_from_notification_hours(not_valid_hour)
            mock.assert_called_with(error.__str__())

        self.assertTrue(alert_notification.has_hour_in_notification_hours(Hour.H_1))
        self.assertTrue(alert_notification.has_hour_in_notification_hours(Hour.H_3))

    def test__reset_notification_days(self):
        # - Only One -
        hour = Hour.H_1
        # add day that should be removed after reset call
        self.notification_hours = [hour]
        alert_notification = self.update_and_generate_alert_notification()
        self.assertEqual(alert_notification.notification_hours, hour.value)
        self.assertNotEqual(alert_notification.notification_hours, Hour.NONE.value)

        alert_notification.reset_notification_hours()

        self.assertEqual(alert_notification.notification_hours, Hour.NONE.value)

        # - Many -
        self.notification_hours = [Hour.H_1, Hour.H_3, Hour.H_5]
        alert_notification = self.update_and_generate_alert_notification()
        self.assertNotEqual(alert_notification.notification_hours, Hour.NONE.value)

        alert_notification.reset_notification_hours()

        self.assertEqual(alert_notification.notification_hours, Hour.NONE.value)

    def test__set_notification_days(self):
        self.notification_hours = []
        alert_definition = self.update_and_generate_alert_notification()

        # Single Day to add
        hour: Hour = Hour.H_5
        alert_definition.set_notification_hours([hour.int_hour])
        self.assertTrue(bool(alert_definition.notification_hours & hour.value))

        # Method replace day, not added it to previous
        hour_new = Hour.H_10
        alert_definition.set_notification_hours([hour_new.int_hour])
        self.assertFalse(alert_definition.has_hour_in_notification_hours(hour))
        self.assertTrue(bool(alert_definition.notification_hours & hour_new.value))


        # Multiple hours in Once
        self.notification_hours = []
        alert_definition = self.update_and_generate_alert_notification()

        hours_list = [Hour.H_0.int_hour, Hour.H_1.int_hour]
        not_to_have_hour = Hour.H_23

        alert_definition.set_notification_hours(hours_list)
        self.assertTrue(alert_definition.has_hour_in_notification_hours(Hour.H_0))
        self.assertTrue(alert_definition.has_hour_in_notification_hours(Hour.H_1))
        self.assertFalse(alert_definition.has_hour_in_notification_hours(not_to_have_hour))

        # ERROR CASE : hour not added
        not_hour = ["im no hour"]
        alert_definition.set_notification_hours(not_hour)
        self.assertEqual(alert_definition.notification_hours, Hour.NONE.value)

        # ERROR CASE : hour not added
        not_hour = [54]
        alert_definition.set_notification_hours(not_hour)
        self.assertEqual(alert_definition.notification_hours, Hour.NONE.value)

        # ERROR CASE - List of days with second number
        not_day_list = [Hour.H_1.int_hour, "im no hour_again"]
        alert_definition.set_notification_hours(not_day_list)
        self.assertEqual(alert_definition.notification_hours, Hour.H_1.value)

    def test__is_datetime_in_notification_hours(self):
        # Hour : SINGLE Hour
        self.notification_hours = [Hour.H_1]
        alert_notification = self.update_and_generate_alert_notification()

        hour_one = datetime(year=2019, month=8, day=26, hour=1, minute=20)
        hour_two = datetime(year=2019, month=8, day=26, hour=2, minute=20)

        self.assertTrue(alert_notification.is_datetime_in_notification_hours(hour_one))
        self.assertFalse(alert_notification.is_datetime_in_notification_hours(hour_two))

        # Watching Period : MANY hours
        self.notification_hours = [Hour.H_1, Hour.H_2]
        alert_notification = self.update_and_generate_alert_notification()

        hour_zero = hour_one - timedelta(hours=1)

        self.assertTrue(alert_notification.is_datetime_in_notification_hours(hour_one))
        self.assertTrue(alert_notification.is_datetime_in_notification_hours(hour_two))
        self.assertFalse(alert_notification.is_datetime_in_notification_hours(hour_zero))

        # ERROR
        wrong_hour = "iam no datetime"

        with patch("logging.error") as mock:
            alert_notification.is_datetime_in_notification_hours(wrong_hour)
            mock.assert_called()


    # -- PERIOD --
    def test___enough_time_between_notifications(self):
        today = datetime(2019, 7, 29)
        yesterday = datetime(2019, 7, 28)
        twenty_days_ago = datetime(2019, 7, 9)
        fourty_days_ago = today - timedelta(days=40)


        # -- 2 DAY --

        self.number = 2
        self.period = NotificationPeriod.DAY
        # False
        self.previous_notification_datetime = yesterday
        notification = self.update_and_generate_alert_notification()
        self.assertFalse(notification._enough_time_between_notifications(today))

        # True
        self.previous_notification_datetime = twenty_days_ago
        notification = self.update_and_generate_alert_notification()
        self.assertTrue(notification._enough_time_between_notifications(today))

        # -- 1 MONTH --

        self.number = 1
        self.period = NotificationPeriod.MONTH

        # False
        self.previous_notification_datetime = yesterday
        notification = self.update_and_generate_alert_notification()
        self.assertFalse(notification._enough_time_between_notifications(today))
        # False
        self.previous_notification_datetime = twenty_days_ago
        notification = self.update_and_generate_alert_notification()
        self.assertFalse(notification._enough_time_between_notifications(today))
        # True
        self.previous_notification_datetime = fourty_days_ago
        notification = self.update_and_generate_alert_notification()
        self.assertTrue(notification._enough_time_between_notifications(today))

    # -- DATETIME --
    def test__is_notification_allowed_for_datetime(self):
        alert_notification = self.update_and_generate_alert_notification()
        today = datetime(year=2019, month=8, day=26, hour=1, minute=20)

        # DAY = True
        with patch("model.alert.AlertNotification.is_datetime_in_notification_days", return_value=True) as day_mock:
            # HOUR = True
            with patch("model.alert.AlertNotification.is_datetime_in_notification_hours", return_value=True) as hour_mock:
                self.assertTrue(alert_notification.is_notification_allowed_for_datetime(datetime_to_check=today))
                day_mock.assert_called_with(datetime_to_check=today)
                hour_mock.assert_called_with(datetime_to_check=today)
            # HOUR = False
            with patch("model.alert.AlertNotification.is_datetime_in_notification_hours", return_value=False) as hour_mock:
                self.assertFalse(alert_notification.is_notification_allowed_for_datetime(datetime_to_check=today))
                day_mock.assert_called_with(datetime_to_check=today)
                hour_mock.assert_called_with(datetime_to_check=today)

        # DAY = False
        with patch("model.alert.AlertNotification.is_datetime_in_notification_days", return_value=False) as day_mock:
            # HOUR = True
            with patch("model.alert.AlertNotification.is_datetime_in_notification_hours", return_value=True) as hour_mock:
                self.assertFalse(alert_notification.is_notification_allowed_for_datetime(datetime_to_check=today))
                day_mock.assert_called_with(datetime_to_check=today)
                hour_mock.assert_not_called()
            # HOUR = False
            with patch("model.alert.AlertNotification.is_datetime_in_notification_hours", return_value=False) as hour_mock:
                self.assertFalse(alert_notification.is_notification_allowed_for_datetime(datetime_to_check=today))
                day_mock.assert_called_with(datetime_to_check=today)
                hour_mock.assert_not_called()

    # -- Notification Allowed - GENERAL --
    def test__is_notification_allowed(self):
        alert_notification = self.update_and_generate_alert_notification()
        today = datetime(year=2019, month=8, day=26, hour=1, minute=20)

        # PERIOD = True
        with patch("model.alert.AlertNotification._enough_time_between_notifications", return_value=True) as period_mock:
            # DATETIME = True
            with patch("model.alert.AlertNotification.is_datetime_in_notification_hours", return_value=True) as datetime_mock:
                self.assertTrue(alert_notification.is_notification_allowed(datetime_to_check=today))
                period_mock.assert_called_with(datetime_to_check=today)
                datetime_mock.assert_called_with(datetime_to_check=today)
            # DATETIME = False
            with patch("model.alert.AlertNotification.is_datetime_in_notification_hours", return_value=False) as datetime_mock:
                self.assertFalse(alert_notification.is_notification_allowed(datetime_to_check=today))
                period_mock.assert_called_with(datetime_to_check=today)
                datetime_mock.assert_called_with(datetime_to_check=today)

        # PERIOD = False
        with patch("model.alert.AlertNotification._enough_time_between_notifications", return_value=False) as period_mock:
            # DATETIME = True
            with patch("model.alert.AlertNotification.is_datetime_in_notification_hours", return_value=True) as datetime_mock:
                self.assertFalse(alert_notification.is_notification_allowed(datetime_to_check=today))
                period_mock.assert_called_with(datetime_to_check=today)
                datetime_mock.assert_not_called()
            # DATETIME = False
            with patch("model.alert.AlertNotification.is_datetime_in_notification_hours", return_value=False) as datetime_mock:
                self.assertFalse(alert_notification.is_notification_allowed(datetime_to_check=today))
                period_mock.assert_called_with(datetime_to_check=today)
                datetime_mock.assert_not_called()


class AlertDefinitionTest(unittest.TestCase):

    def setUp(self) -> None:
        self.today = datetime.today()

        self.name = "i am the name"
        self.alert_definition_id = "id"
        self.description = "i am supposed to describe the Alert definition"
        self.category = "category"
        self.level = Level.HIGH
        self.definition_flags = [
            AlertDefinitionFlag.INACTIVE
        ]
        self.previous_notification = None
        self.sensor_ids = ["sensor_id_1"]
        self.last_check = self.today - timedelta(days=2)



    def generate_setup(self):
        self.setup = {
            "name": self.name,
            "id": self.alert_definition_id,
            "description": self.description,
            "category_id": self.category,
            "level": self.level.name,
            "sensor_ids": self.sensor_ids,
            "last_check": self.last_check.isoformat(),
            "flags": [
                flags.name for flags in self.definition_flags
            ],
            "notification": {},
            "calculator": {}
        }

    def get_alert_definition(self):
        return AlertDefinition(self.setup, self.today)

    def update_setup_and_get_alert_definition(self):
        self.generate_setup()
        return self.get_alert_definition()

    def test__init(self):
        self.definition_flags = [AlertDefinitionFlag.ACTIVE]
        with patch("model.alert.AlertCalculator") as calculator_mock:
            with patch("model.alert.AlertNotification") as notification_mock:
                with patch("model.alert.AlertDefinition.set_definition_flags_from_str_flags") as flag_mock:
                    alert_definition = self.update_setup_and_get_alert_definition()
                    self.assertEqual(self.name, alert_definition.name)
                    self.assertEqual(self.alert_definition_id, alert_definition.id)
                    self.assertEqual(self.category, alert_definition.category_id)
                    self.assertEqual(self.description, alert_definition.description)
                    self.assertEqual(self.sensor_ids, alert_definition.sensor_ids)
                    calculator_mock.assert_called_with(setup=self.setup["calculator"], today=self.today, last_check=self.last_check)
                    notification_mock.assert_called_with(setup=self.setup["notification"])
                    flag_mock.assert_called_with(flags_list=self.setup["flags"])


    # IS ACTIVE
    def test__is_active(self):
        self.definition_flags = [
            AlertDefinitionFlag.INACTIVE
        ]
        with patch("model.alert.AlertCalculator"):
            with patch("model.alert.AlertNotification"):
                alert_definition = self.update_setup_and_get_alert_definition()
        alert_definition.add_definition_flag(AlertDefinitionFlag.INACTIVE)
        self.assertFalse(alert_definition.is_active)
        alert_definition.add_definition_flag(AlertDefinitionStatus.ACTIVE)
        self.assertTrue(alert_definition.is_active)

    # LEVEL
    def test__level(self):
        self.level = Level.LOW
        with patch("model.alert.AlertCalculator"):
            with patch("model.alert.AlertNotification"):
                alert_definition = self.update_setup_and_get_alert_definition()
        self.assertTrue(alert_definition.level == Level.LOW)

    # DEFINITION FLAG
    def test__remove_definition_flag(self):
        with patch("model.alert.AlertCalculator"):
            with patch("model.alert.AlertNotification"):
                alert_definition = self.update_setup_and_get_alert_definition()

        flag = AlertDefinitionFlag.ACTIVE

        # SIMPLE
        alert_definition.set_definition_flags_from_str_flags([flag.name])
        self.assertTrue(alert_definition.has_definition_flag(flag))
        alert_definition.remove_definition_flag(flag)
        self.assertFalse(alert_definition.has_definition_flag(flag))

        # MULTIPLE
        flag_2 = AlertDefinitionFlag.SAVE_ALL
        alert_definition.set_definition_flags_from_str_flags([flag.name, flag_2.name])

        self.assertTrue(alert_definition.has_definition_flag(flag))
        self.assertTrue(alert_definition.has_definition_flag(flag_2))

        alert_definition.remove_definition_flag(flag)

        self.assertFalse(alert_definition.has_definition_flag(flag))
        self.assertTrue(alert_definition.has_definition_flag(flag_2))

    def test__has_definition_flag(self):
        with patch("model.alert.AlertCalculator"):
            with patch("model.alert.AlertNotification"):
                alert_definition = self.update_setup_and_get_alert_definition()
                self.assertFalse(alert_definition.has_definition_flag(AlertDefinitionFlag.SAVE_ALL))
                alert_definition.set_definition_flags_from_str_flags([AlertDefinitionFlag.SAVE_ALL.name])
                self.assertTrue(alert_definition.has_definition_flag(AlertDefinitionFlag.SAVE_ALL))

    def test__set_definition_flags_from_str_flags(self):
        with patch("model.alert.AlertCalculator"):
            with patch("model.alert.AlertNotification"):
                alert_definition = self.update_setup_and_get_alert_definition()
        flags = [AlertDefinitionFlag.SAVE_ALL.name, AlertDefinitionFlag.ANOTHER_FLAG.name]
        alert_definition.set_definition_flags_from_str_flags(flags)
        self.assertTrue(bool(alert_definition.definition_flag & AlertDefinitionFlag.SAVE_ALL.value))
        self.assertTrue(bool(alert_definition.definition_flag & AlertDefinitionFlag.ANOTHER_FLAG.value))


class MyOperatorTest(unittest.TestCase):

    def setUp(self):
        self.arr = [3, 5, 10, 25, 36, 174]

    def test__max(self):
        import pdb;pdb.set_trace()
        my_str = "MAX"
        elem = MyOperator[my_str]

        self.assertIsInstance(elem, MyOperator)
        result_expected = max(self.arr)
        result = elem.calculate(self.arr)
        self.assertEqual(result_expected, result)

        # ERROR
        with self.assertRaises(TypeError):
            elem.calculate(2)

    def test__min(self):
        my_str = "MIN"
        elem = MyOperator(my_str)

        self.assertIsInstance(elem, MyOperator)
        result_expected = min(self.arr)
        result = elem.calculate(self.arr)
        self.assertEqual(result_expected, result)

        # ERROR
        with self.assertRaises(TypeError):
            elem.calculate(2)

    def test__average(self):
        my_str = "AVERAGE"
        elem = MyOperator(my_str)

        self.assertIsInstance(elem, MyOperator)
        result_expected = sum(self.arr) / len(self.arr)
        result = elem.calculate(self.arr)
        self.assertEqual(result_expected, result)

        # ERROR
        with self.assertRaises(TypeError):
            elem.calculate(2)


class MyOperatorTest(unittest.TestCase):

    def setUp(self):
        self.data = 5
        self.value = 10

    def test__sup(self):
        my_str = "SUP"
        elem = MyComparator(my_str)
        self.assertIsInstance(elem, MyComparator)

        result_expected = self.data > self.value
        result = elem.compare(self.data, self.value)

        self.assertEqual(result_expected, result)

    def test__inf(self):
        my_str = "INF"
        elem = MyComparator(my_str)
        self.assertIsInstance(elem, MyComparator)

        result_expected = self.data < self.value
        result = elem.compare(self.data, self.value)

        self.assertEqual(result_expected, result)

    def test__equal(self):
        my_str = "EQUAL"
        elem = MyComparator(my_str)
        self.assertIsInstance(elem, MyComparator)

        result_expected = self.data == self.value
        result = elem.compare(self.data, self.value)

        self.assertEqual(result_expected, result)


class PeriodUnitDefinitionTest(unittest.TestCase):

    def setUp(self):
        self.end_date = datetime(year=2012, month=2, day=29)
        self.mock_return_value = datetime(year=2000, month=12, day=12)
        self.period_quantity = 8

    def test__day(self):
        my_str = "DAY"
        elem = PeriodUnitDefinition(my_str)
        self.assertIsInstance(elem, PeriodUnitDefinition)

        # SINGLE
        base_datetime = datetime(year=2010, month=3, day=3)
        result_expected = datetime(year=2010, month=3, day=2)
        result = elem.go_past(base_datetime, 1)
        self.assertEqual(result, result_expected)

        # MULTIPLE
        result_expected = datetime(year=2010, month=2, day=28)
        result = elem.go_past(base_datetime, 3)
        self.assertEqual(result, result_expected)


    def test__month(self):
        my_str = "MONTH"
        elem = PeriodUnitDefinition(my_str)
        self.assertIsInstance(elem, PeriodUnitDefinition)

        # SIMPLE
        base_datetime = datetime(year=2010, month=3, day=15)
        result_expected = datetime(year=2010, month=2, day=15)
        result = elem.go_past(base_datetime, 1)
        self.assertEqual(result, result_expected)

        # MULTIPLE
        base_datetime = datetime(year=2010, month=6, day=15)
        result_expected = datetime(year=2010, month=2, day=15)
        result = elem.go_past(base_datetime, 4)
        self.assertEqual(result, result_expected)

        # 30 vs 31 DAYS per MONTH
        base_datetime = datetime(year=2010, month=7, day=31)
        result_expected = datetime(year=2010, month=6, day=30)
        result = elem.go_past(base_datetime, 1)
        self.assertEqual(result, result_expected)

        # FEBRUARY CASE
        base_datetime = datetime(year=2011, month=3, day=30)
        result_expected = datetime(year=2011, month=2, day=28)
        result = elem.go_past(base_datetime, 1)
        self.assertEqual(result, result_expected)

        # BISEXTILE YEAR
        base_datetime = datetime(year=2012, month=3, day=30)
        result_expected = datetime(year=2012, month=2, day=29)
        result = elem.go_past(base_datetime, 1)
        self.assertEqual(result, result_expected)

        # MORE THAN 12 MONTH
        base_datetime = datetime(year=2011, month=3, day=30)
        result_expected = datetime(year=2010, month=2, day=28)
        result = elem.go_past(base_datetime, 13)
        self.assertEqual(result, result_expected)

    def test__year(self):
        my_str = "YEAR"
        elem = PeriodUnitDefinition(my_str)
        self.assertIsInstance(elem, PeriodUnitDefinition)

        # SINGLE
        base_datetime = datetime(year=2010, month=3, day=3)
        result_expected = datetime(year=2009, month=3, day=3)
        result = elem.go_past(base_datetime, 1)
        self.assertEqual(result, result_expected)

        # MULTIPLE & BISEXTILE
        base_datetime = datetime(year=2012, month=2, day=29)
        result_expected = datetime(year=2009, month=2, day=28)
        result = elem.go_past(base_datetime, 3)
        self.assertEqual(result, result_expected)


class PeriodDefinitionTest(unittest.TestCase):

    def setUp(self):
        self.end_date = datetime(year=2012, month=2, day=29)
        self.mock_return_value = datetime(year=2000, month=12, day=12)
        self.period_quantity = 8

    def test__init(self):
        period_unit = PeriodUnitDefinition.DAY

        period_definition = PeriodDefinition(unit=period_unit, quantity=self.period_quantity)

        self.assertIsInstance(period_definition, PeriodDefinition)
        self.assertEqual(period_definition.get_unit(), period_unit)
        self.assertEqual(period_definition.get_quantity(), self.period_quantity)

    def test__get_start_date_from_end_date(self):
        # GENERAL
        period_unit = PeriodUnitDefinition.DAY
        period_definition = PeriodDefinition(unit=period_unit, quantity=self.period_quantity)

        with patch("model.alert.PeriodDefinition.get_start_date_from_end_date", return_value=self.mock_return_value) as mock:
            result = period_definition.get_start_date_from_end_date(end_date=self.end_date)
            mock.assert_called_with(end_date=self.end_date)
            self.assertEqual(result, self.mock_return_value)

    def test__get_start_date_from_end_date_go_past_association(self):
        # -- DAY --
        period_unit = PeriodUnitDefinition.DAY
        period_definition = PeriodDefinition(unit=period_unit, quantity=self.period_quantity)

        with patch("model.alert.PeriodUnitDefinition.DAY.go_past", return_value=self.mock_return_value) as mock:
            result = period_definition.get_start_date_from_end_date(end_date=self.end_date)
            mock.assert_called_with(end_date=self.end_date, quantity=self.period_quantity)
            self.assertEqual(result, self.mock_return_value)

        # -- WEEK --
        period_unit = PeriodUnitDefinition.WEEK
        period_definition = PeriodDefinition(unit=period_unit, quantity=self.period_quantity)

        with patch("model.alert.PeriodUnitDefinition.WEEK.go_past", return_value=self.mock_return_value) as mock:
            result = period_definition.get_start_date_from_end_date(end_date=self.end_date)
            mock.assert_called_with(end_date=self.end_date, quantity=self.period_quantity)
            self.assertEqual(result, self.mock_return_value)

        # -- MONTH --
        period_unit = PeriodUnitDefinition.MONTH
        period_definition = PeriodDefinition(unit=period_unit, quantity=self.period_quantity)

        with patch("model.alert.PeriodUnitDefinition.MONTH.go_past", return_value=self.mock_return_value) as mock:
            result = period_definition.get_start_date_from_end_date(end_date=self.end_date)
            mock.assert_called_with(end_date=self.end_date, quantity=self.period_quantity)
            self.assertEqual(result, self.mock_return_value)

        # -- YEAR --
        period_unit = PeriodUnitDefinition.YEAR
        period_definition = PeriodDefinition(unit=period_unit, quantity=self.period_quantity)

        with patch("model.alert.PeriodUnitDefinition.YEAR.go_past", return_value=self.mock_return_value) as mock:
            result = period_definition.get_start_date_from_end_date(end_date=self.end_date)
            mock.assert_called_with(end_date=self.end_date, quantity=self.period_quantity)
            self.assertEqual(result, self.mock_return_value)


class PeriodGeneratorTest(unittest.TestCase):

    def setUp(self) -> None:
        self.today = datetime(year=2019, month=8, day=13)

    def test__last_check_based_period_generator(self):
        last_check = datetime(year=2019, month=8, day=8)
        last_check_based_period_generator = LastCheckBasedPeriodGenerator(last_check=last_check, today=self.today)
        expected_period = Period(start=last_check, end=self.today)

        self.assertIsInstance(last_check_based_period_generator, LastCheckBasedPeriodGenerator)
        self.assertIsInstance(last_check_based_period_generator, PeriodGenerator)

        result_period = last_check_based_period_generator.get_pertinent_period()

        self.assertIsInstance(result_period, Period)
        self.assertEqual(expected_period.get_start_date(), result_period.get_start_date())
        self.assertEqual(expected_period.get_end_date(), result_period.get_end_date())

    def test__user_based_period_generator(self):
        user_data = {
            "quantity": 5,
            "unit": PeriodUnitDefinition.DAY.value
        }
        expected_start = datetime(year=2019, month=8, day=8)
        user_based_period_generator = UserBasedPeriodGenerator(user_data=user_data, today=self.today)

        self.assertIsInstance(user_based_period_generator, UserBasedPeriodGenerator)
        self.assertIsInstance(user_based_period_generator, PeriodGenerator)

        result_period = user_based_period_generator.get_pertinent_period()

        self.assertIsInstance(result_period, Period)
        self.assertEqual(expected_start, result_period.get_start_date())
        self.assertEqual(self.today, result_period.get_end_date())


class ValueGeneratorTest(unittest.TestCase):

    def test__user_based_value_generator(self):
        user_data = 5

        user_based_value_generator = UserBasedValueGenerator(user_data=user_data)

        self.assertIsInstance(user_based_value_generator, UserBasedValueGenerator)
        self.assertIsInstance(user_based_value_generator, ValueGenerator)

        self.assertEqual(user_based_value_generator.value, user_data)

    def test__period_based_value_generator(self):
        conn_info = {}
        user_data = {
            "quantity": 5,
            "unit": PeriodUnitDefinition.DAY.value
        }
        today = datetime(year=2019, month=8, day=13)

        period_based_value_generator = PeriodBasedValueGenerator(conn_info=conn_info, user_data=user_data, today=today)

        self.assertIsInstance(period_based_value_generator, PeriodBasedValueGenerator)
        self.assertIsInstance(period_based_value_generator, DataBaseValueGenerator)
        self.assertIsInstance(period_based_value_generator, ValueGenerator)

        # -- GENERATE PERIOD --
        with patch("model.alert.PeriodBasedValueGenerator.generate_period") as mock:
            period_based_value_generator = PeriodBasedValueGenerator(
                conn_info=conn_info,
                user_data=user_data,
                today=today)
            mock.assert_called_with(user_data=user_data, today=today)

        # Period Generator
        with patch("model.alert.UserBasedPeriodGenerator") as mock:
            period_based_value_generator = PeriodBasedValueGenerator(
                conn_info=conn_info,
                user_data=user_data,
                today=today)
            mock.assert_called_with(user_data=user_data, today=today)

        # Period
        with patch("model.alert.PeriodGenerator.get_pertinent_period") as mock:
            period_based_value_generator = PeriodBasedValueGenerator(
                conn_info=conn_info,
                user_data=user_data,
                today=today)
            mock.assert_called()


class AlertDatatest(unittest.TestCase):

    def setUp(self) -> None:

        # data
        self.data_period_type = PeriodGeneratorType.USER_BASED

        # Period
        self.period_unit = PeriodUnitDefinition.DAY
        self.period_quantity = 1

        # datetime
        self.today = datetime(year=2019, month=8, day=13)
        self.last_check = datetime(year=2019, month=8, day=8)

    def generate_setup(self):
        # -- Data --
        self.setup = {
            "data_period_type": self.data_period_type.name
        }

        if self.data_period_type is PeriodGeneratorType.USER_BASED:
            self.setup["data_period"] = {
                "quantity": self.period_quantity,
                "unit": self.period_unit.value
            }

    def update_and_get_new_alert_data(self):
        self.generate_setup()
        return self.generate_alert_data()

    def generate_alert_data(self):
        return AlertData(setup=self.setup, last_check=self.last_check, today=self.today)

    def test__init(self):
        alert_data: AlertData = self.update_and_get_new_alert_data()

        self.assertIsInstance(alert_data, AlertData)

        self.assertEqual(self.data_period_type, alert_data.data_period_type)

    def test__data_period_generator(self):
        # -- LAST CHECK --
        # Instance created
        self.data_period_type = PeriodGeneratorType.LAST_CHECK

        alert_data: AlertData = self.update_and_get_new_alert_data()
        self.assertIsInstance(alert_data.data_period_generator, LastCheckBasedPeriodGenerator)

        # Pertinent parameters
        with patch("model.alert.LastCheckBasedPeriodGenerator") as mock:
            self.generate_alert_data()
            mock.assert_called_with(last_check=self.last_check, today=self.today)

        # -- USER BASED --
        # Instance created
        self.data_period_type = PeriodGeneratorType.USER_BASED

        alert_data = self.update_and_get_new_alert_data()
        self.assertIsInstance(alert_data.data_period_generator, UserBasedPeriodGenerator)

        # Pertinent parameters
        with patch("model.alert.UserBasedPeriodGenerator") as mock:
            self.generate_alert_data()
            mock.assert_called_with(user_data=self.setup["data_period"], today=self.today)

        # -- ERROR -- TODO


class AlertValueTest(unittest.TestCase):

    def setUp(self) -> None:

        # value
        self.value_number = 15
        self.value_generator_type = ValueGeneratorType.PERIOD_BASED_VALUE

        # Period
        self.period_unit = PeriodUnitDefinition.DAY
        self.period_quantity = 1

        # datetime
        self.today = datetime(year=2019, month=8, day=13)

    def generate_setup(self):
        # -- Value --
        self.setup = {
            "value_number": self.value_number,
            "value_type": self.value_generator_type.name
        }

        if self.value_generator_type is ValueGeneratorType.PERIOD_BASED_VALUE:
            self.setup["value_period"] = {
                "quantity": self.period_quantity,
                "unit": self.period_unit.value
            }

    def update_and_get_new_alert_value(self):
        self.generate_setup()
        return self.generate_alert_value()

    def generate_alert_value(self):
        return AlertValue(setup=self.setup, today=self.today)

    def test__init(self):
        alert_value: AlertValue = self.update_and_get_new_alert_value()

        self.assertIsInstance(alert_value, AlertValue)

        self.assertEqual(self.value_number, alert_value.value_number)
        self.assertEqual(self.value_generator_type, alert_value.value_generator_type)

    def test__value_generator(self):
        # -- SIMPLE DB --
        # Instance created
        self.value_generator_type = ValueGeneratorType.SIMPLE_DB_BASED_VALUE

        alert_value: AlertValue = self.update_and_get_new_alert_value()
        self.assertIsInstance(alert_value.value_generator, SimpleDBBasedValueGenerator)

        # Pertinent parameters
        with patch("model.alert.SimpleDBBasedValueGenerator") as mock:
            self.generate_alert_value()
            mock.assert_called_with(conn_info={})

        # -- PERIOD BASED VALUE --
        # Instance created
        self.value_generator_type = ValueGeneratorType.PERIOD_BASED_VALUE

        alert_value = self.update_and_get_new_alert_value()
        self.assertIsInstance(alert_value.value_generator, PeriodBasedValueGenerator)

        # Pertinent parameters
        with patch("model.alert.PeriodBasedValueGenerator") as mock:
            self.generate_alert_value()
            mock.assert_called_with(conn_info={}, user_data=self.setup["value_period"], today=self.today)

        # -- USER BASED VALUE --
        # Instance created
        self.value_generator_type = ValueGeneratorType.USER_BASED_VALUE

        alert_value = self.update_and_get_new_alert_value()
        self.assertIsInstance(alert_value.value_generator, NoPeriodBasedValueGenerator)

        # Pertinent parameters
        with patch("model.alert.NoPeriodBasedValueGenerator") as mock:
            self.generate_alert_value()
            mock.assert_called_with(value=self.value_number)

        # -- ERROR -- TODO


class AlertCalculatorTest(unittest.TestCase):

    def setUp(self):
        # -- Setup Info --

        # general
        self.operator = MyOperator.MAX
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # data
        self.data_period_type = PeriodGeneratorType.USER_BASED

        # value
        self.value_number = 15
        self.value_generator_type = ValueGeneratorType.PERIOD_BASED_VALUE

        # Period
        self.period_unit = PeriodUnitDefinition.DAY
        self.period_quantity = 1

        # -- Generate setup --
        self.generate_setup()

        # -- RESULT --
        self.data = None
        self.value = None

        # -- Datetime --
        self.today = datetime(year=2019, month=8, day=13)
        self.last_check = datetime(year=2019, month=8, day=8)

    def generate_setup(self):
        # -- Data --
        self.data_setup = {
            "data_period_type": self.data_period_type.name
        }

        if self.data_period_type is PeriodGeneratorType.USER_BASED:
            self.data_setup["data_period"] = {
                "quantity": self.period_quantity,
                "unit": self.period_unit.value
            }

        # -- Value --
        self.value_setup = {
            "value_number": self.value_number,
            "value_type": self.value_generator_type.name
        }

        if self.value_generator_type is ValueGeneratorType.PERIOD_BASED_VALUE:
            self.value_setup["value_period"] = {
                "quantity": self.period_quantity,
                "unit": self.period_unit.value
            }

        # -- SETUP --
        self.setup = {
            "data": self.data_setup,
            "value": self.value_setup,
            "operator": self.operator.value,
            "acceptable_diff": self.acceptable_diff,
            "comparator": self.comparator.value
        }

    def get_alert_calculator(self) -> AlertCalculator:
        return AlertCalculator(
            setup=self.setup,
            last_check=self.last_check,
            today=self.today
        )

    def update_and_get_new_alert_calculator(self) -> AlertCalculator:
        self.generate_setup()
        return self.get_alert_calculator()

    def test__init(self):
        alert_calculator = self.update_and_get_new_alert_calculator()

        self.assertIsInstance(alert_calculator, AlertCalculator)

        # assert Attributes
        self.assertEqual(self.setup, alert_calculator.setup)
        self.assertEqual(self.operator, alert_calculator.operator)
        self.assertEqual(self.comparator, alert_calculator.comparator)
        self.assertEqual(self.acceptable_diff, alert_calculator.acceptable_diff)
        # datetime
        self.assertEqual(self.today, alert_calculator.today)
        self.assertEqual(self.last_check, alert_calculator.last_check)
        # data
        self.assertIsInstance(alert_calculator.alert_data, AlertData)
        # value
        self.assertIsInstance(alert_calculator.alert_value, AlertValue)

        # -- Pertinent parameters --

        # data
        with patch("model.alert.AlertData") as mock:
            self.get_alert_calculator()
            mock.assert_called_with(setup=self.setup["data"], last_check=self.last_check, today=self.today)

        # value
        with patch("model.alert.AlertValue") as mock:
            self.get_alert_calculator()
            mock.assert_called_with(setup=self.setup["value"], today=self.today)

        # -- ERROR -- TODO


class AlertManager(unittest.TestCase):

    alert_manager: AlertManager

    def test__init(self):
        self.alert_manager = AlertManager()
        self.assertEqual(1, len(self.alert_manager.alert_definition_list))



if __name__ == '__main__':
    unittest.main()
