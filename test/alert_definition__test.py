#!/usr/bin/python3
# -*-coding:Utf-8 -*
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from model.day import Day
from model.alert import AlertDefinition, AlertDefinitionFlag, Level, MyOperator, MyComparator, PeriodUnitDefinition, \
    PeriodDefinition, AlertCalculator, LastCheckBasedPeriodGenerator, PeriodGenerator, Period, UserBasedPeriodGenerator, \
    UserBasedValueGenerator, ValueGenerator, PeriodBasedValueGenerator, DataBaseValueGenerator, PeriodGeneratorType, \
    ValueGeneratorType

from model.alert import AlertDefinitionStatus
from model.my_exception import DayTypeError


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

        self.assertEqual(user_based_value_generator.get_value(), user_data)

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

        # -- Datetime --
        self.data = None
        self.value = None

        # -- Datetime --
        self.today = datetime(year=2019, month=8, day=13)
        self.last_check = datetime(year=2019, month=8, day=8)

    def generate_setup(self):
        # -- Data --
        data = {
            "data_name": self.data_name,
            "data_period_type": self.data_period_type.value
        }

        if self.data_period_type is PeriodGeneratorType.USER_BASED:
            data["data_period"] = {
                "quantity": self.period_quantity,
                "unit": self.period_unit.value
            }

        # -- Value --
        value = {
            "value_number": self.value_number,
            "value_type": self.value_generator_type.value
        }

        if self.value_generator_type is ValueGeneratorType.PERIOD_BASED_VALUE:
            value["value_period"] = {
                "quantity": self.period_quantity,
                "unit": self.period_unit.value
            }

        # -- SETUP --
        self.setup = {
            "data": data,
            "value": value,
            "operator": self.operator.value,
            "acceptable_diff": self.acceptable_diff,
            "comparator": self.comparator.value
        }

    def test__init(self):
        alert_calculator = AlertCalculator(
            setup=self.setup,
            last_check=self.last_check,
            today=self.today
        )

        self.assertIsInstance(alert_calculator, AlertCalculator)

        # Attributes
        self.assertEqual(self.data_name, alert_calculator.data_name)




  #  def test__get_comparative_value_from_reference(self):
      #  percent_calculator = PercentBasedCalculator(self.setup)





if __name__ == '__main__':
    unittest.main()
