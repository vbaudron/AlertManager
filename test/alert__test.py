#!/usr/bin/python3
# -*-coding:Utf-8 -*
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from model.day import Day
from model.alert import AlertDefinition, AlertDefinitionFlag, Level, MyOperator, MyComparator, PeriodUnitDefinition, \
    PeriodDefinition, AlertCalculator, LastCheckBasedPeriodGenerator, PeriodGenerator, Period, UserBasedPeriodGenerator, \
    UserBasedValueGenerator, ValueGenerator, PeriodBasedValueGenerator, DataBaseValueGenerator, PeriodGeneratorType, \
    ValueGeneratorType, NoPeriodBasedValueGenerator, SimpleDBBasedValueGenerator, AlertData, AlertValue, \
    AlertNotification, NotificationPeriod

from model.alert import AlertDefinitionStatus
from model.my_exception import DayTypeError

class NotificationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.number = 1
        self.period = NotificationPeriod.DAY
        self.email = "test@test.com"
        self.generate_setup()

    def generate_setup(self):
        self.setup = {
            "number": self.number,
            "period": self.period.value,
            "email": self.email
        }

    def update_and_generate_alert_notification(self) -> AlertNotification:
        self.generate_setup()
        return self.get_alert_notification()

    def get_alert_notification(self) -> AlertNotification:
        return AlertNotification(self.setup)

    def test__init(self):
        notification = AlertNotification(self.setup)
        self.assertIsInstance(notification, AlertNotification)
        self.assertEqual(notification.number, self.number)
        self.assertEqual(notification.email, self.email)
        self.assertIsInstance(notification.period, NotificationPeriod)
        self.assertEqual(notification.period, self.period)

        with patch("model.alert.NotificationPeriod") as mock:
            self.get_alert_notification()
            mock.assert_called_with(self.period.value)

    def test__is_notification_allowed(self):
        today = datetime(2019, 7, 29)
        yesterday = datetime(2019, 7, 28)
        twenty_days_ago = datetime(2019, 7, 9)
        fourty_days_ago = today - timedelta(days=40)

        # 2 DAY
        self.number = 2
        notification = self.update_and_generate_alert_notification()
        self.assertFalse(notification.is_notification_allowed(yesterday, today))
        self.assertTrue(notification.is_notification_allowed(twenty_days_ago, today))

        # MONTH
        self.number = 1
        self.period = NotificationPeriod.MONTH
        notification = self.update_and_generate_alert_notification()
        self.assertFalse(notification.is_notification_allowed(yesterday, today))
        self.assertFalse(notification.is_notification_allowed(twenty_days_ago, today))
        self.assertTrue(notification.is_notification_allowed(fourty_days_ago, today))


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


class MyOperatorTest(unittest.TestCase):

    def setUp(self):
        self.arr = [3, 5, 10, 25, 36, 174]

    def test__max(self):
        my_str = "MAX"
        elem = MyOperator(my_str)

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

        def test__sup(self):
            my_str = "INF"
            elem = MyComparator(my_str)
            self.assertIsInstance(elem, MyComparator)

            result_expected = self.data < self.value
            result = elem.compare(self.data, self.value)

            self.assertEqual(result_expected, result)

        def test__sup(self):
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
        self.data_name = "consommation"
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
            "data_name": self.data_name,
            "data_period_type": self.data_period_type.value
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

        self.assertEqual(self.data_name, alert_data.data_name)
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
            "value_type": self.value_generator_type.value
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
        self.data_name = "consommation"
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
            "data_name": self.data_name,
            "data_period_type": self.data_period_type.value
        }

        if self.data_period_type is PeriodGeneratorType.USER_BASED:
            self.data_setup["data_period"] = {
                "quantity": self.period_quantity,
                "unit": self.period_unit.value
            }

        # -- Value --
        self.value_setup = {
            "value_number": self.value_number,
            "value_type": self.value_generator_type.value
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

    def test__is_alert__get_data(self):
        todo = True  #TODO
        # -- PERIOD BASED --
        #
        # alert_calculator = self.get_alert_calculator()
        #
        # # Pertinent parameters
        # with patch("model.alert.AlertCalculator.__get_data", return_value=2) as mock:
        #     alert_calculator.is_alert_situation()
        #     mock.assert_called()



if __name__ == '__main__':
    unittest.main()
