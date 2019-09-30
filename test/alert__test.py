#!/usr/bin/python3
# -*-coding:Utf-8 -*
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from model.alert import AlertDefinition, AlertDefinitionFlag, Level, MyOperator, MyComparator, PeriodUnitDefinition, \
    PeriodDefinition, AlertCalculator, LastCheckBasedPeriodGenerator, PeriodGenerator, Period, \
    UserBasedGoBackPeriodGenerator, \
    UserBasedValueGenerator, ValueGenerator, PeriodBasedValueGenerator, DataBaseValueGenerator, PeriodGeneratorType, \
    ValueGeneratorType, NoPeriodBasedValueGenerator, SimpleDBBasedValueGenerator, AlertData, AlertValue, \
    AlertNotification, NotificationPeriod, Day, Hour, AlertManager, ValuePeriodType

from model.alert import AlertDefinitionStatus
from model.my_exception import EnumError, ConfigError


def generate_hours_flag(notification_hours: list):
    hours = 0
    for hour in notification_hours:
        hours |= hour.value
    return hours


def generate_days_flag(notification_days: list):
    days = 0
    for day in notification_days:
        days |= day.value
    return days


class NotificationTest(unittest.TestCase):

    setup: dict
    previous_notification_datetime: datetime

    def setUp(self) -> None:

        self.monday = datetime(2019, 7, 29)  # 29 July 2019 was a MONDAY
        self.saturday = datetime(2019, 7, 27)  # 27 July 2019 was a SATURDAY

        self.notification_id = 1
        self.notification_period_quantity = 1
        self.notification_period_unit = NotificationPeriod.DAY
        self.email = "test@test.com"
        self.notification_days = [
            Day.MONDAY, Day.TUESDAY
        ]
        self.notification_hours = [
            Hour.H_1, Hour.H_2
        ]

    def get_alert_notification(self) -> AlertNotification:
        return AlertNotification(
            notification_id=self.notification_id,
            period_unit=self.notification_period_unit.name,
            period_quantity=self.notification_period_quantity,
            email=self.email,
            days=generate_days_flag(notification_days=self.notification_days),
            hours=generate_hours_flag(notification_hours=self.notification_hours)
        )

    # INIT

    def test__init(self):
        notification = self.get_alert_notification()
        self.assertIsInstance(notification, AlertNotification)
        self.assertEqual(notification.number, self.notification_period_quantity)
        self.assertEqual(notification.email, self.email)
        self.assertIsInstance(notification.period, NotificationPeriod)
        self.assertEqual(notification.period, self.notification_period_unit)

    # --  DAY --

    def test__has_day_in_notification_days(self):
        to_have_day = Day.MONDAY
        not_to_have_day = Day.TUESDAY

        self.notification_days = [to_have_day]
        alert_notification = self.get_alert_notification()

        self.assertTrue(alert_notification.has_day_in_notification_days(to_have_day))
        self.assertFalse(alert_notification.has_day_in_notification_days(not_to_have_day))

        # Test in Multiples Flags
        another_day_to_have = Day.SATURDAY
        self.notification_days = [to_have_day, another_day_to_have]
        alert_notification = self.get_alert_notification()
        self.assertTrue(alert_notification.has_day_in_notification_days(day=to_have_day))
        self.assertFalse(alert_notification.has_day_in_notification_days(day=not_to_have_day))
        self.assertTrue(alert_notification.has_day_in_notification_days(day=another_day_to_have))

        # ERROR : Not a Day
        wrong_day = "iam no day"
        error = EnumError(except_enum=Day, wrong_value=wrong_day)

        with patch("logging.warning") as mock:
            self.assertFalse(alert_notification.has_day_in_notification_days(day=wrong_day))
            mock.assert_called_with(error.__str__())

    def test__is_datetime_in_notification_days(self):
        # Watching Period : SINGLE day
        self.notification_days = [Day.MONDAY]
        alert_notification = self.get_alert_notification()

        self.assertTrue(alert_notification.is_datetime_in_notification_days(self.monday))
        self.assertFalse(alert_notification.is_datetime_in_notification_days(self.saturday))

        # Watching Period : MANY days
        self.notification_days = [Day.MONDAY, Day.TUESDAY]
        alert_notification = self.get_alert_notification()

        tuesday = self.monday + timedelta(days=1)

        self.assertTrue(alert_notification.is_datetime_in_notification_days(self.monday))
        self.assertTrue(alert_notification.is_datetime_in_notification_days(tuesday))
        self.assertFalse(alert_notification.is_datetime_in_notification_days(self.saturday))

        # ERROR
        wrong_days = "iam no datetime"

        with patch("logging.warning") as mock:
            alert_notification.is_datetime_in_notification_days(wrong_days)
            mock.assert_called()

    # --  HOURS --

    def test__has_hour_in_notification_hours(self):
        to_have_hour = Hour.H_1
        not_to_have_hour = Hour.H_2

        self.notification_hours = [to_have_hour]
        alert_notification = self.get_alert_notification()

        self.assertTrue(alert_notification.has_hour_in_notification_hours(to_have_hour))
        self.assertFalse(alert_notification.has_hour_in_notification_hours(not_to_have_hour))

        # Test in Multiples Flags
        another_hour_to_have = Hour.H_3
        self.notification_hours = [to_have_hour, another_hour_to_have]
        alert_notification = self.get_alert_notification()
        self.assertTrue(alert_notification.has_hour_in_notification_hours(hour=to_have_hour))
        self.assertFalse(alert_notification.has_hour_in_notification_hours(hour=not_to_have_hour))
        self.assertTrue(alert_notification.has_hour_in_notification_hours(hour=another_hour_to_have))

        # ERROR : Not a Hour
        wrong_hour = "iam no hour"
        error = EnumError(except_enum=Hour, wrong_value=wrong_hour)

        with patch("logging.warning") as mock:
            self.assertFalse(alert_notification.has_hour_in_notification_hours(hour=wrong_hour))
            mock.assert_called_with(error.__str__())

    def test__is_datetime_in_notification_hours(self):
        # Hour : SINGLE Hour
        self.notification_hours = [Hour.H_1]
        alert_notification = self.get_alert_notification()

        hour_one = datetime(year=2019, month=8, day=26, hour=1, minute=20)
        hour_two = datetime(year=2019, month=8, day=26, hour=2, minute=20)

        self.assertTrue(alert_notification.is_datetime_in_notification_hours(hour_one))
        self.assertFalse(alert_notification.is_datetime_in_notification_hours(hour_two))

        # Watching Period : MANY hours
        self.notification_hours = [Hour.H_1, Hour.H_2]
        alert_notification = self.get_alert_notification()

        hour_zero = hour_one - timedelta(hours=1)

        self.assertTrue(alert_notification.is_datetime_in_notification_hours(hour_one))
        self.assertTrue(alert_notification.is_datetime_in_notification_hours(hour_two))
        self.assertFalse(alert_notification.is_datetime_in_notification_hours(hour_zero))

        # ERROR
        wrong_hour = "iam no datetime"

        with patch("logging.warning") as mock:
            alert_notification.is_datetime_in_notification_hours(wrong_hour)
            mock.assert_called()

    # -- PERIOD --

    def test__query_last_notification_time(self):
        alert_notification = self.get_alert_notification()
        alert_definition_id = 1

        query_response = [(self.monday)]
        # TODO
        method_mock = MagicMock(return_value=query_response)
        # with patch('mysql.connector.cursor.CursorBase.fetchall', return_value=query_response):
        #     self.assertEqual(
        #         self.monday,
        #         alert_notification.query_last_notification_time(alert_definition_id=alert_definition_id)
        #     )

    def test___enough_time_between_notifications(self):
        today = datetime(2019, 7, 29)
        yesterday = datetime(2019, 7, 28)
        twenty_days_ago = datetime(2019, 7, 9)
        fourty_days_ago = today - timedelta(days=40)


        # -- 2 DAY --

        self.notification_period_quantity = 2
        self.notification_period_unit = NotificationPeriod.DAY
        notification = self.get_alert_notification()

        alert_definition_id = 1

        # False
        with patch('model.alert.AlertNotification.query_last_notification_time', return_value=yesterday) as mock:
            self.assertFalse(notification._enough_time_between_notifications(
                alert_definition_id=alert_definition_id,
                datetime_to_check=today
            ))
            mock.assert_called_with(alert_definition_id=alert_definition_id)

        # True
        with patch('model.alert.AlertNotification.query_last_notification_time', return_value=twenty_days_ago) as mock:
            self.assertTrue(notification._enough_time_between_notifications(
                alert_definition_id=alert_definition_id,
                datetime_to_check=today
            ))
            mock.assert_called_with(alert_definition_id=alert_definition_id)

        # -- 1 MONTH --

        self.notification_period_quantity = 1
        self.notification_period_unit = NotificationPeriod.MONTH
        notification = self.get_alert_notification()

        # False
        with patch('model.alert.AlertNotification.query_last_notification_time', return_value=yesterday) as mock:
            self.assertFalse(notification._enough_time_between_notifications(
                alert_definition_id=alert_definition_id,
                datetime_to_check=today
            ))
            mock.assert_called_with(alert_definition_id=alert_definition_id)

        # False
        with patch('model.alert.AlertNotification.query_last_notification_time', return_value=twenty_days_ago) as mock:
            self.assertFalse(notification._enough_time_between_notifications(
                alert_definition_id=alert_definition_id,
                datetime_to_check=today
            ))
            mock.assert_called_with(alert_definition_id=alert_definition_id)

        # True
        with patch('model.alert.AlertNotification.query_last_notification_time', return_value=fourty_days_ago) as mock:
            self.assertTrue(notification._enough_time_between_notifications(
                alert_definition_id=alert_definition_id,
                datetime_to_check=today
            ))
            mock.assert_called_with(alert_definition_id=alert_definition_id)

    #

    # -- DATETIME --

    def test__is_notification_allowed_for_datetime(self):
        alert_notification = self.get_alert_notification()
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
        alert_notification = self.get_alert_notification()
        today = datetime(year=2019, month=8, day=26, hour=1, minute=20)
        alert_definition_id = 1

        # DATETIME = True
        with patch("model.alert.AlertNotification.is_notification_allowed_for_datetime", return_value=True) as dt_mock:
            # PERIOD BETWEEN = True
            with patch("model.alert.AlertNotification._enough_time_between_notifications", return_value=True) as between_mock:
                self.assertTrue(alert_notification.is_notification_allowed(
                    alert_definition_id=alert_definition_id,
                    datetime_to_check=today
                ))
                dt_mock.assert_called_with(datetime_to_check=today)
                between_mock.assert_called_with(
                    alert_definition_id=alert_definition_id,
                    datetime_to_check=today)
            # PERIOD BETWEEN = False
            with patch("model.alert.AlertNotification._enough_time_between_notifications", return_value=False) as between_mock:
                self.assertFalse(alert_notification.is_notification_allowed(
                    alert_definition_id=alert_definition_id,
                    datetime_to_check=today))
                dt_mock.assert_called_with(datetime_to_check=today)
                between_mock.assert_called_with(
                    alert_definition_id=alert_definition_id,
                    datetime_to_check=today)

        # DATETIME = False
        with patch("model.alert.AlertNotification.is_notification_allowed_for_datetime", return_value=False) as dt_mock:
            # PERIOD BETWEEN = True
            with patch("model.alert.AlertNotification._enough_time_between_notifications", return_value=True) as between_mock:
                self.assertFalse(alert_notification.is_notification_allowed(
                    alert_definition_id=alert_definition_id,
                    datetime_to_check=today))
                dt_mock.assert_called_with(datetime_to_check=today)
                between_mock.assert_not_called()
            # PERIOD BETWEEN = False
            with patch("model.alert.AlertNotification._enough_time_between_notifications", return_value=False) as between_mock:
                self.assertFalse(alert_notification.is_notification_allowed(
                    alert_definition_id=alert_definition_id,
                    datetime_to_check=today))
                dt_mock.assert_called_with(datetime_to_check=today)
                between_mock.assert_not_called()


class MyOperatorTest(unittest.TestCase):

    def setUp(self):
        self.arr = [3, 5, 10, 25, 36, 174]

    def test__max(self):
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

        quantity = 5
        unit = PeriodUnitDefinition.DAY.name

        expected_start = self.today - timedelta(days=quantity)

        user_based_period_generator = UserBasedGoBackPeriodGenerator(
            to_date=self.today,
            unit=unit,
            quantity=quantity
        )

        self.assertIsInstance(user_based_period_generator, UserBasedGoBackPeriodGenerator)
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

    def create_period_based_value_generator_instance(self):
        return PeriodBasedValueGenerator(
            operator=self.operator,
            unit=self.unit,
            quantity=self.quantity,
            end_date=self.today
        )


    def test__period_based_value_generator(self):
        self.quantity = 5
        self.unit = PeriodUnitDefinition.DAY.name
        self.operator = MyOperator.MAX

        self.today = datetime(year=2019, month=8, day=13)

        # -- INIT --

        period_based_value_generator = self.create_period_based_value_generator_instance()

        self.assertIsInstance(period_based_value_generator, PeriodBasedValueGenerator)
        self.assertIsInstance(period_based_value_generator, DataBaseValueGenerator)
        self.assertIsInstance(period_based_value_generator, ValueGenerator)

        # -- GENERATE PERIOD --

        with patch("model.alert.PeriodBasedValueGenerator.generate_period") as mock:
            self.create_period_based_value_generator_instance()
            mock.assert_called_with(
                unit=self.unit,
                quantity=self.quantity,
                end_date=self.today
            )

        # Period Generator
        with patch("model.alert.UserBasedGoBackPeriodGenerator") as mock:
            self.create_period_based_value_generator_instance()
            mock.assert_called_with(
                unit=self.unit,
                quantity=self.quantity,
                to_date=self.today
            )

        # Period
        with patch("model.alert.PeriodGenerator.get_pertinent_period") as mock:
            self.create_period_based_value_generator_instance()
            mock.assert_called()

        # -- ERROR Cases --

        # Error - unit empty
        self.unit = None
        with self.assertRaises(ConfigError):
            self.create_period_based_value_generator_instance()

        # Error - unit empty
        self.unit = "Hello"
        with self.assertRaises(EnumError):
            self.create_period_based_value_generator_instance()

        # Error - quantity None
        self.quantity = None
        self.unit = PeriodUnitDefinition.DAY.name
        with self.assertRaises(ConfigError):
            self.create_period_based_value_generator_instance()

        # Error - quantity Negative
        self.quantity = -5
        self.unit = PeriodUnitDefinition.DAY.name
        with self.assertRaises(ConfigError):
            self.create_period_based_value_generator_instance()




class AlertDataTest(unittest.TestCase):

    def setUp(self) -> None:

        # data
        self.data_period_type = PeriodGeneratorType.USER_BASED

        # Period
        self.period_unit = PeriodUnitDefinition.DAY
        self.period_quantity = 1

        # Hours
        self.hour_start = None
        self.hour_end = None

        # datetime
        self.today = datetime(year=2019, month=8, day=13)
        self.last_check = datetime(year=2019, month=8, day=8)

    def get_alert_data(self):
        quantity = self.period_quantity if self.data_period_type is PeriodGeneratorType.USER_BASED else None
        unit = self.period_unit if self.data_period_type is PeriodGeneratorType.USER_BASED else None
        data_period_type = self.data_period_type.name if isinstance(self.data_period_type, PeriodGeneratorType) else self.data_period_type

        return AlertData(
            data_period_type=data_period_type,
            data_period_quantity=quantity,
            data_period_unit=unit,
            last_check=self.last_check,
            hour_start=self.hour_start,
            hour_end=self.hour_end,
            today=self.today
        )

    def test__init(self):
        alert_data: AlertData = self.get_alert_data()

        self.assertIsInstance(alert_data, AlertData)

        self.assertEqual(self.data_period_type, alert_data.data_period_type)

        # Error
        self.data_period_type = "IM_NOT_A_VALID_PERIOD_TYPE"
        with self.assertRaises(EnumError):
            self.get_alert_data()


    def test__data_period_generator(self):
        # -- LAST CHECK --
        # Instance created
        self.data_period_type = PeriodGeneratorType.LAST_CHECK

        alert_data: AlertData = self.get_alert_data()
        self.assertIsInstance(alert_data.data_period_generator, LastCheckBasedPeriodGenerator)

        # Pertinent parameters
        with patch("model.alert.LastCheckBasedPeriodGenerator") as mock:
            self.get_alert_data()
            mock.assert_called_with(last_check=self.last_check, today=self.today)

        # -- USER BASED --
        # Instance created
        self.data_period_type = PeriodGeneratorType.USER_BASED

        alert_data = self.get_alert_data()
        self.assertIsInstance(alert_data.data_period_generator, UserBasedGoBackPeriodGenerator)

        # Pertinent parameters
        with patch("model.alert.UserBasedGoBackPeriodGenerator") as mock:
            self.get_alert_data()
            mock.assert_called_with(
                quantity=self.period_quantity,
                unit=self.period_unit,
                to_date=self.today
            )

        # -- ERROR -- TODO


class AlertValueTest(unittest.TestCase):

    def setUp(self) -> None:

        # value
        self.value_number = 15
        self.value_generator_type = ValueGeneratorType.PERIOD_BASED_VALUE

        # Period
        self.value_period_type = None

        # datetime
        self.today = datetime(year=2019, month=8, day=13)

    def get_alert_value(self):
        return AlertValue(
            value_type=self.value_generator_type.name,
            value_number=self.value_number
        )

    def test__init(self):
        alert_value: AlertValue = self.get_alert_value()

        self.assertIsInstance(alert_value, AlertValue)

        self.assertEqual(self.value_number, alert_value.value_number)
        self.assertEqual(self.value_generator_type, alert_value.value_generator_type)

    def get_alert_data_and_set_value_generator(self):
        alert_value: AlertValue = self.get_alert_value()
        alert_value.set_value_generator(
            end_date=self.end_date,
            unit=self.unit.name,
            quantity=self.quantity,
            operator=self.operator
        )
        return alert_value

    def test__value_generator(self):
        # -- SIMPLE DB --
        # Instance created
        self.end_date = datetime.today()
        self.unit = PeriodUnitDefinition.DAY
        self.quantity = 2
        self.operator = MyOperator.MAX

        self.value_generator_type = ValueGeneratorType.SIMPLE_DB_BASED_VALUE

        alert_value: AlertValue = self.get_alert_data_and_set_value_generator()
        self.assertIsInstance(alert_value.value_generator, SimpleDBBasedValueGenerator)

        # Pertinent parameters
        with patch("model.alert.SimpleDBBasedValueGenerator") as mock:
            self.get_alert_data_and_set_value_generator()
            mock.assert_called_with()

        # -- PERIOD BASED VALUE --
        # Instance created
        self.value_generator_type = ValueGeneratorType.PERIOD_BASED_VALUE

        alert_value = self.get_alert_data_and_set_value_generator()
        self.assertIsInstance(alert_value.value_generator, PeriodBasedValueGenerator)

        # Pertinent parameters
        with patch("model.alert.PeriodBasedValueGenerator") as mock:
            self.get_alert_data_and_set_value_generator()
            mock.assert_called_with(
                operator=self.operator,
                unit=self.unit.name,
                quantity=self.quantity,
                end_date=self.end_date
            )

        # -- USER BASED VALUE --
        # Instance created
        self.value_generator_type = ValueGeneratorType.USER_BASED_VALUE

        alert_value = self.get_alert_data_and_set_value_generator()
        self.assertIsInstance(alert_value.value_generator, NoPeriodBasedValueGenerator)

        # Pertinent parameters
        with patch("model.alert.NoPeriodBasedValueGenerator") as mock:
            self.get_alert_data_and_set_value_generator()
            mock.assert_called_with(value=self.value_number)

        # -- ERROR -- TODO

    def test__value_period_type(self):
        pass  # TODO


class AlertCalculatorTest(unittest.TestCase):

    def setUp(self):
        # -- Setup Info --

        # general
        self.operator = MyOperator.MAX
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # -- DATA --
        self.data_period_type = PeriodGeneratorType.USER_BASED
        # Period
        self.data_period_unit = PeriodUnitDefinition.DAY
        self.data_period_quantity = 1
        # Hours
        self.hour_start = None
        self.hour_end = None

        # -- VALUE --
        self.value_number = 15
        self.value_generator_type = ValueGeneratorType.PERIOD_BASED_VALUE
        # Period
        self.value_period_type = ValuePeriodType.LAST_DATA_PERIOD

        # -- RESULT --
        self.data = None
        self.value = None

        # -- Datetime --
        self.today = datetime(year=2019, month=8, day=13)
        self.last_check = datetime(year=2019, month=8, day=8)


    def get_alert_calculator(self) -> AlertCalculator:
        return AlertCalculator(
            operator=self.operator.name,
            comparator=self.comparator.name,
            data_period_type=self.data_period_type.name,
            data_period_quantity=self.data_period_quantity,
            data_period_unit=self.data_period_unit.name,
            value_type=self.value_generator_type.name,
            value_number=self.value_number,
            value_period_type=self.value_period_type if not isinstance(self.value_period_type, ValuePeriodType) else self.value_period_type.name,
            hour_start=self.hour_start,
            hour_end=self.hour_end,
            acceptable_diff=self.acceptable_diff,
            last_check=self.last_check,
            today=self.today
        )

    def test__init(self):

        print("______________________ MOCKED TEST")

        with patch("model.alert.AlertData") as data_mock:
            with patch("model.alert.AlertValue") as value_mock:
                alert_calculator = self.get_alert_calculator()
                self.assertIsInstance(alert_calculator, AlertCalculator)
                self.assertEqual(self.operator, alert_calculator.operator)
                self.assertEqual(self.comparator, alert_calculator.comparator)
                self.assertEqual(self.acceptable_diff, alert_calculator.acceptable_diff)
                self.assertEqual(self.today, alert_calculator.today)
                self.assertEqual(self.last_check, alert_calculator.last_check)
                self.get_alert_calculator()
                data_mock.assert_called_with(
                    data_period_type=self.data_period_type.name,
                    data_period_quantity=self.data_period_quantity,
                    data_period_unit=self.data_period_unit.name,
                    last_check=self.last_check,
                    hour_start=self.hour_start,
                    hour_end=self.hour_end,
                    today=self.today
                )
                value_mock.assert_called_with(
                    value_type=self.value_generator_type.name,
                    value_number=self.value_number
                )

        # -- ERROR -- TODO



class AlertDefinitionTest(unittest.TestCase):

    def setUp(self) -> None:
        self.today = datetime.today()

        self.name = "i am the name"
        self.alert_definition_id = "id"
        self.description = "i am supposed to describe the Alert definition"
        self.category = "category"
        self.level = Level.HIGH
        self.status = AlertDefinitionStatus.INACTIVE
        self.previous_notification = None
        self.meter_ids = [1]

        # Notification Part
        self.notification_id = 1
        self.notification_period_quantity = 1
        self.notification_period_unit = NotificationPeriod.DAY
        self.email = "test@test.com"
        self.notification_days = [
            Day.MONDAY, Day.TUESDAY
        ]
        self.notification_hours = [
            Hour.H_1, Hour.H_2
        ]

        # Calculator Part
        self.operator = MyOperator.MAX
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True
        # data
        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.DAY
        self.data_period_quantity = 1
        self.hour_start = None
        self.hour_end = None
        # value
        self.value_number = 15
        self.value_type = ValueGeneratorType.PERIOD_BASED_VALUE
        self.value_period_type = ValuePeriodType.LAST_DATA_PERIOD

        self.last_check = self.today - timedelta(days=2)


    def generate_setup(self):
        self.setup = {
            "name": self.name,
            "id": self.alert_definition_id,
            "description": self.description,
            "category": self.category,
            "level": self.level.value,
            "meter_ids": self.meter_ids,
            "status": self.status.value,
            "notification_id": self.notification_id,
            "notification_period_quantity": self.notification_period_quantity,
            "notification_period_unit": self.notification_period_unit.name,
            "notification_email": self.email,
            "notification_days": generate_days_flag(notification_days=self.notification_days),
            "notification_hours": generate_hours_flag(notification_hours=self.notification_hours),
            "operator": self.operator.name,
            "comparator": self.comparator.name,
            "data_period_type": self.data_period_type.name,
            "data_period_quantity": self.data_period_quantity,
            "data_period_unit": self.data_period_unit.name,
            "value_type": self.value_type.name,
            "value_number": self.value_number,
            "value_period_type": self.value_period_type.name,
            "acceptable_diff": self.acceptable_diff,
            "hour_start": self.hour_start,
            "hour_end": self.hour_end,
        }

    def get_alert_definition(self):
        return AlertDefinition(
            setup=self.setup,
            last_check=self.last_check,
            today=self.today)

    def update_setup_and_get_alert_definition(self):
        self.generate_setup()
        return self.get_alert_definition()

    def test__init(self):
        with patch("model.alert.AlertCalculator") as calculator_mock:
            with patch("model.alert.AlertNotification") as notification_mock:
                alert_definition = self.update_setup_and_get_alert_definition()
                self.assertEqual(self.name, alert_definition.name)
                self.assertEqual(self.alert_definition_id, alert_definition.id)
                self.assertEqual(self.category, alert_definition.category_id)
                self.assertEqual(self.description, alert_definition.description)
                self.assertEqual(self.meter_ids, alert_definition.meter_ids)
                calculator_mock.assert_called_with(
                    operator=self.operator.name,
                    comparator=self.comparator.name,
                    data_period_type=self.data_period_type.name,
                    data_period_quantity=self.data_period_quantity,
                    data_period_unit=self.data_period_unit.name,
                    value_type=self.value_type.name,
                    value_number=self.value_number,
                    value_period_type=self.value_period_type.name,
                    hour_start=self.hour_start,
                    hour_end=self.hour_end,
                    acceptable_diff=self.acceptable_diff,
                    today=self.today,
                    last_check=self.last_check
                )
                notification_mock.assert_called_with(
                    notification_id=self.notification_id,
                    period_unit=self.notification_period_unit.name,
                    period_quantity=self.notification_period_quantity,
                    email=self.email,
                    days=generate_days_flag(notification_days=self.notification_days),
                    hours=generate_hours_flag(notification_hours=self.notification_hours)
                )


    # IS ACTIVE
    def test__is_active(self):
        self.status = AlertDefinitionStatus.INACTIVE
        with patch("model.alert.AlertCalculator"):
            with patch("model.alert.AlertNotification"):
                alert_definition = self.update_setup_and_get_alert_definition()
                self.assertFalse(alert_definition.is_active)
                self.status = AlertDefinitionStatus.ACTIVE
                alert_definition = self.update_setup_and_get_alert_definition()
                self.assertTrue(alert_definition.is_active)

    # LEVEL
    def test__level(self):
        self.level = Level.LOW
        with patch("model.alert.AlertCalculator"):
            with patch("model.alert.AlertNotification"):
                alert_definition = self.update_setup_and_get_alert_definition()
                self.assertTrue(alert_definition.level == Level.LOW)




class AlertManager(unittest.TestCase):

    alert_manager: AlertManager

    def test__init(self):
       pass  # TODO



if __name__ == '__main__':
    unittest.main()
