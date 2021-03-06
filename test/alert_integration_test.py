import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from statistics import mean
from unittest.mock import patch
import logging as log

from model.alert import PeriodUnitDefinition, Hour, Day, MyOperator, MyComparator, PeriodGeneratorType, \
    ValueGeneratorType, ValuePeriodType, Level, AlertDefinitionStatus, NotificationPeriod, AlertManager, \
    go_past_with_years
from model.utils import MySqlConnection, my_sql, generate_days_flag, generate_hours_flag, get_day_name_from_datetime
from scripts.alert_tables_creation import alert_notification_table, alert_calculator_table, alert_definition_table, alert_alert_table, \
    alert_definition_meter_table, alert_definition_notification_table, alert_manager_table
from scripts.test__create_and_insert_data_in_fake_tables import bi_compteurs_table, bi_objectif_table, \
    bi_comptages_donnees, insert_in_bi_compteurs, insert_in_bi_objectifs, insert_in_notification, insert_in_calculator, \
    insert_in_alert_definition, insert_in_alert_definition_meter, insert_in_bi_comptage_donnees, \
    insert_in_alert_definition_notification_time, insert_in_alert_manager


class MyIntegrationTest(ABC):
    _db_name: str
    _tables: list
    _tests: list

    def __init__(self):
        print("_________________INIT_________________")
        MySqlConnection.TEST_MODE = True

        # Database creation
        my_sql.connect_without_database()
        self._db_name = my_sql.database
        print("TEST DATABASE :", self._db_name)

        self.__create_db()
        self.__use_db()

        self._tests = self.set_tests_to_run()

    def start(self, test_name=None):
        if test_name:
            if test_name in self._tests:
                test = self._tests.index(test_name)
                self.launch(test)
            else:
                log.error("{} is not a valid test name".format(test_name))
        else:
            for test in self._tests:
                self.launch(test)

    def launch(self, test):
        print("\n____SET UP___")
        self.set_up()
        print("\n\n", self._tests.index(test) + 1, "\t\t\t------->\t\tSTART TEST :", test.__name__, "\n\n")
        test()
        print("\n____THEAR DOWN___")
        self.tear_down()

    def __del__(self):
        print("\n_________________DEL_________________")
        self.__delete_db()

    # -- PREPARE --

    @abstractmethod
    def set_tests_to_run(self):
        raise NotImplementedError

    def set_up(self):
        pass

    def tear_down(self):
        pass

    # DATABASE - CREATION & DESTRUCTION

    def __delete_db(self):
        query = "DROP DATABASE {}".format(self._db_name)
        print(query)
        my_sql.execute_and_close(query=query)

    def __create_db(self):
        query = "CREATE DATABASE {}".format(self._db_name)
        print(query)
        my_sql.execute_and_close(query=query)

    def __use_db(self):
        query = "USE {}".format(self._db_name)
        print(query)
        my_sql.execute_and_close(query=query)

    # DATABASE - UTILS

    @staticmethod
    def drop_table(table_name: str):
        query = "DROP TABLES {}".format(table_name)
        my_sql.execute_and_close(query=query)


class AlertManagerTest(MyIntegrationTest):
    __tables = [
        bi_compteurs_table,
        bi_objectif_table,
        bi_comptages_donnees,
        alert_notification_table,
        alert_calculator_table,
        alert_definition_table,
        alert_alert_table,
        alert_definition_meter_table,
        alert_definition_notification_table,
        alert_manager_table
    ]

    def __init__(self):
        super().__init__()

        self.simplest_case()

    def set_tests_to_run(self):
        return [
            self.test__notif_true__no_data,
            self.test__notif_true__with_data,
            self.test__notif_false__time_between,
            self.test__notif_false__days,
            self.test__notif_false__hours,
            self.test__simple_alert__true__data_last_check__accept_false__value_user_based__max__inf,
            self.test__simple_alert__false__data_last_check__accept_false__value_user_based__max__inf,
            self.test__simple_alert__true__data_last_check__accept_false__value_user_based__max__sup,
            self.test__simple_alert__false__data_last_check__accept_false__value_user_based__max__sup,
            self.test__simple_alert__true__data_last_check__accept_false__value_user_based__max__equal,
            self.test__simple_alert__false__data_last_check__no_data,
            self.test__simple_alert__true__data_period_based__accept_false__value_user_based__average__equal,
            self.test__simple_alert__false__data_period_based__accept_false__value_user_based__average__equal,
            self.test__simple_alert__true__data_period_based__accept_false__value_user_based__average__equal,
            self.test__simple_alert__false__data_period_based__accept_false__value_user_based__average__equal,
            self.test__simple_alert__true__data_user_based,
            self.test__simple_alert__false__data_user_based,
            self.test__simple_alert__true__data_user_based__hours,
            self.test__simple_alert__false__data_user_based__hours,
            self.test__complex_alert__true__data_last_check__value_db_based,
            self.test__complex_alert__false__data_last_check__value_db_based,
            self.test__complex_alert__true__data_last_check__value_db_based__hours,
            self.test__complex_alert__false__data_last_check__value_db_based__hours,
            self.test__complex_alert__true__data_last_check__value_db_based__time_unit,
            self.test__complex_alert__false__data_last_check__value_db_based__time_unit,
            self.test__complex_alert__true__data_last_check__value_period_based__last_year,
            self.test__complex_alert__false__data_last_check__value_period_based__last_year,
            self.test__complex_alert__true__data_last_check__value_period_based__last_data_period,
            self.test__complex_alert__false__data_last_check__value_period_based__last_data_period,
            self.test__simple_alert__true__equal__is_index
        ]

    def create_tables(self):
        for table in AlertManagerTest.__tables:
            table.request_table_creation()

    # SET UP

    def set_up(self):
        self.create_tables()
        self.simplest_case()

    def tear_down(self):
        for table in reversed(AlertManagerTest.__tables):
            MyIntegrationTest.drop_table(table.name)

    def insert_defined_data(self, insert_all_donnee=True):
        self.meter_id = insert_in_bi_compteurs(
            name="meter_1",
            is_index=self.is_meter_index
        )
        print("meter_id inserted :", self.meter_id)

        insert_in_bi_objectifs(
            objectif_value=self.objectif_value,
            time_unit=self.objectif_time_unit if not isinstance(self.objectif_time_unit, PeriodUnitDefinition) else self.objectif_time_unit.name,
            meter_id=self.meter_id
        )

        self.alert_notification_id = insert_in_notification(
            period_unit=self.notification_period_unit.name,
            period_quantity=self.notification_period_quantity,
            email=self.email,
            days_flags=generate_days_flag(notification_days=self.notification_days),
            hours_flags=generate_hours_flag(notification_hours=self.notification_hours)
        )

        self.alert_calculator_id = insert_in_calculator(
            operator=self.operator.name,
            comparator=self.comparator.name,
            data_period_type=self.data_period_type.name,
            data_period_quantity=self.data_period_quantity,
            data_period_unit=self.data_period_unit if not isinstance(self.data_period_unit, PeriodUnitDefinition) else self.data_period_unit.name,
            value_type=self.value_type.name,
            value_number=self.value_number,
            value_period_type=self.value_period_type if not isinstance(self.value_period_type, ValuePeriodType) else self.value_period_type.name,
            hour_start=self.hour_start,
            hour_end=self.hour_end,
            acceptable_diff=self.acceptable_diff
        )

        self.alert_definition_id = insert_in_alert_definition(
            name=self.name,
            category=self.category,
            description=self.description,
            level=self.level.value,
            status=self.status.value,
            notification_id=self.alert_notification_id,
            calculator_id=self.alert_calculator_id
        )

        insert_in_alert_definition_meter(
            meter_id=self.meter_id,
            alert_definition_id=self.alert_definition_id
        )

        # DONNEE COMPTAGE
        self.insert_donnees_comptage(
            end_day=self.donnee_comptage_end_day,
            data_list=self.donnee_comptage_list,
            delta=self.donnee_comptage_delta,
            insert_all=insert_all_donnee
        )

        # Definition - Notification TIME
        if self.last_notification_time:
            notification_time_id = insert_in_alert_definition_notification_time(
                notification_id=self.alert_notification_id,
                alert_definition_id=self.alert_definition_id,
                notification_datetime=self.last_notification_time
            )

        if self.last_check:
            insert_in_alert_manager(
                launch_datetime=self.last_check
            )

    def insert_donnees_comptage(self, end_day, data_list: list, delta, insert_all=True):
        forgotten = 0
        for data in data_list:
            end_day -= delta
            if insert_all or forgotten is not 0 or data_list.index(data) is 0:
                insert_in_bi_comptage_donnees(
                    donnee_comptage_value=data,
                    meter_id=self.meter_id,
                    time=end_day
                )
            else:
                forgotten += 1

    def simplest_case(self):
        self.today = datetime.today()

        # -- OBJECTIF --
        self.objectif_value = 20
        self.objectif_time_unit = None

        # -- DONNEE COMPTAGE --
        self.donnee_comptage_list = [3, 2, 5, 1, 4]
        self.donnee_comptage_end_day = self.today
        self.donnee_comptage_delta = timedelta(hours=1)

        # -- METER --
        self.meter_id = None
        self.is_meter_index = False

        # -- Alert Definition --
        self.alert_definition_id = None
        self.name = "alert_definition_name"
        self.description = "i am supposed to describe the Alert definition"
        self.category = "category"
        self.level = Level.HIGH
        self.status = AlertDefinitionStatus.ACTIVE

        # -- Notification --
        self.alert_notification_id = None
        self.notification_period_quantity = 1
        self.notification_period_unit = NotificationPeriod.DAY
        self.email = "noreply-alert@softee.fr"
        self.notification_days = [
            Day[get_day_name_from_datetime(self.today).upper()]
        ]
        self.notification_hours = [
            Hour.get_from_int(self.today.hour)
        ]

        # -- Calculator --
        self.calculator_id = None
        self.operator = MyOperator.MAX
        self.comparator = MyComparator.EQUAL
        self.acceptable_diff = False
        # data
        self.data_period_type = PeriodGeneratorType.LAST_CHECK
        self.data_period_unit = None
        self.data_period_quantity = None
        self.hour_start = None
        self.hour_end = None
        # value
        self.value_number = max(self.donnee_comptage_list)
        self.value_type = ValueGeneratorType.USER_BASED_VALUE
        self.value_period_type = None


        # DEFINITION - NOTIFICATION
        self.last_notification_time = None

        # MANAGER
        self.last_check = None

    def test_it(self, insert_data=True):
        if insert_data:
            self.insert_defined_data()
        AlertManager.start()

    # -----------------    SET DATA TO INSERT    -----------------

    # ---->  CALCULATOR  <----

    # -- DATA --

    # Data Period Type
    def is_alert__true__acceptable_diff_data_user_based(self):
        self.comparator = MyComparator.EQUAL

    def is_alert__false__acceptable_diff_data_user_based(self):
        self.comparator = MyComparator.SUP

    # ---->  NOTIFICATION  <----

    # NOTIFICATION DAY
    def notification_day__true(self):
        day = Day[get_day_name_from_datetime(self.today).upper()]
        if day not in self.notification_days:
            self.notification_days.append(day)

    def notification_day__false(self):
        day = Day[get_day_name_from_datetime(self.today).upper()]
        if day in self.notification_days:
            self.notification_days.remove(day)
        # add another day if empty
        if not self.notification_days:
            day_to_add = Day[get_day_name_from_datetime(self.today + timedelta(days=1)).upper()]
            self.notification_days.append(day_to_add)

    # NOTIFICATION HOUR
    def notification_hour__true(self):
        hour = Hour.get_from_int(self.today.hour)
        if hour not in self.notification_hours:
            self.notification_hours.append(hour)

    def notification_hour__false(self):
        hour = Hour.get_from_int(self.today.hour)
        if hour in self.notification_hours:
            self.notification_hours.remove(hour)
        # add another hour if empty
        if not self.notification_hours:
            hour_to_add = Hour.get_from_int((self.today + timedelta(hours=1)).hour)
            self.notification_hours.append(hour_to_add)

    # TIME BETWEEN NOTIFICATION
    def notification_enough_time_between__true__no_data(self):
        self.last_notification_time = None

    def notification_enough_time_between__true__with_data(self):
        self.last_notification_time = self.today - timedelta(days=20)
        self.notification_period_unit = PeriodUnitDefinition.DAY
        self.notification_period_quantity = 10

    def notification_enough_time_between__false(self):
        self.last_notification_time = self.today - timedelta(days=5)
        self.notification_period_unit = PeriodUnitDefinition.DAY
        self.notification_period_quantity = 10

    # SIMPLE N0TIFICATION SETUP
    def simple_case__notification_true(self):
        self.notification_hour__true()
        self.notification_day__true()
        self.notification_enough_time_between__true__no_data()

    def simple_case__notification_false(self):
        self.simplest_case()
        self.notification_day__false()
        self.notification_hour__false()
        self.notification_enough_time_between__true__no_data()

    # -----------------      CHECK DATA IN DB     -----------------

    def query_select_all(self, table_name:str):
        query = "SELECT * FROM {}".format(table_name)
        cursor = my_sql.generate_cursor()
        cursor.execute(operation=query)
        columns_name = cursor.column_names
        results = cursor.fetchall()
        return columns_name, results

    # -----------------    ASSERT PERSONALIZED    -----------------

    # ALERT
    def assert_alert__saved(self, expected_id=1):
        columns_name, results = self.query_select_all(table_name=alert_alert_table.name)
        print("RESULT", results)

        # len result
        assert len(results) == expected_id
        results = results[expected_id - 1]

        # alert_definition_id
        index = columns_name.index("alert_definition_id")
        assert self.alert_definition_id == results[index]
        print("alert {} saved".format(expected_id))
        return columns_name, results

    def assert_alert__not_saved(self, expected_id=1):
        columns_name, results = self.query_select_all(table_name=alert_alert_table.name)
        print(results)

        # len result
        assert len(results) == expected_id - 1

    #  _____________________________________  NOTIFICATION  _____________________________________
    def assert_notification__saved(self, expected_id=1):
        columns_name, results = self.query_select_all(table_name=alert_definition_notification_table.name)
        print(results)

        # len result
        assert len(results) == expected_id
        results = results[expected_id - 1]

        # alert_definition_id
        index = columns_name.index("alert_definition_id")
        assert self.alert_definition_id == results[index]

        # alert_notification_id
        index = columns_name.index("alert_notification_id")
        assert self.alert_definition_id == results[index]
        print("notif {} saved".format(expected_id))

    def assert_notification__not_saved(self, expected_id=1):
        columns_name, results = self.query_select_all(table_name=alert_definition_notification_table.name)
        print(results)

        # len result
        assert len(results) == expected_id - 1

    # -----------------            TEST           -----------------

    # NOTIFICATION TEST
    def test__notif_true__no_data(self):
        # alert true
        self.is_alert__true__acceptable_diff_data_user_based()

        # Notif true - no data
        self.notification_day__true()
        self.notification_hour__true()
        self.notification_enough_time_between__true__no_data()

        with patch('model.alert.Email.send', return_value=True) as email_mock:
            self.test_it()
            self.assert_alert__saved()
            email_mock.assert_called()
            self.assert_notification__saved()

    def test__notif_true__with_data(self):
        # alert true
        self.is_alert__true__acceptable_diff_data_user_based()

        # Notif true - with data
        self.notification_day__true()
        self.notification_hour__true()
        self.notification_enough_time_between__true__with_data()

        self.test_it()
        self.assert_alert__saved()
        self.assert_notification__saved(expected_id=2)

    def test__notif_false__time_between(self):
        # alert true
        self.is_alert__true__acceptable_diff_data_user_based()

        # Notif true - with data
        self.notification_day__true()
        self.notification_hour__true()
        self.notification_enough_time_between__false()

        with patch('model.alert.Email.send', return_value=True) as email_mock:
            self.test_it()
            email_mock.assert_not_called()
            self.assert_alert__saved()
            self.assert_notification__not_saved(expected_id=2)

    def test__notif_false__days(self):
        # alert true
        self.is_alert__true__acceptable_diff_data_user_based()

        # Notif true - with data
        self.notification_day__false()
        self.notification_hour__true()
        self.notification_enough_time_between__true__no_data()

        with patch('model.alert.Email.send', return_value=True) as email_mock:
            self.test_it()
            email_mock.assert_not_called()
            self.assert_alert__saved()
            self.assert_notification__not_saved(expected_id=1)

    def test__notif_false__hours(self):
        # alert true
        self.is_alert__true__acceptable_diff_data_user_based()

        # Notif true - with data
        self.notification_day__true()
        self.notification_hour__false()
        self.notification_enough_time_between__true__no_data()

        with patch('model.alert.Email.send', return_value=True) as email_mock:
            self.test_it()
            email_mock.assert_not_called()
            self.assert_alert__saved()
            self.assert_notification__not_saved(expected_id=1)

    def test__notif_false__not_alert(self):
        # alert true
        self.is_alert__false__acceptable_diff_data_user_based()

        # Notif true - with data
        self.notification_day__true()
        self.notification_hour__true()
        self.notification_enough_time_between__true__no_data()

        with patch('model.alert.Email.send', return_value=True) as email_mock:
            with patch('model.alert.AlertNotification.is_notification_allowed') as check_notif_mock:
                self.test_it()
                email_mock.assert_not_called()
                check_notif_mock.assert_not_called()
                self.assert_alert__not_saved()
                self.assert_notification__not_saved(expected_id=1)

    # _____________________________________  CALCULATOR TEST  _____________________________________

    # SIMPLE - Inf
    def test__simple_alert__true__data_last_check__accept_false__value_user_based__max__inf(self):
        self.simple_case__notification_false()

        self.comparator = MyComparator.INF
        self.value_number = max(self.donnee_comptage_list) + 1

        self.test_it()
        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_last_check__accept_false__value_user_based__max__inf(self):
        self.simple_case__notification_false()
        self.comparator = MyComparator.INF
        self.value_number = max(self.donnee_comptage_list) - 1

        self.test_it()

        self.assert_alert__not_saved()

    # SIMPLE - Sup
    def test__simple_alert__true__data_last_check__accept_false__value_user_based__max__sup(self):
        self.simple_case__notification_false()
        self.comparator = MyComparator.SUP
        self.value_number = max(self.donnee_comptage_list) - 1

        self.test_it()

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_last_check__accept_false__value_user_based__max__sup(self):
        self.simple_case__notification_false()
        self.comparator = MyComparator.SUP
        self.value_number = max(self.donnee_comptage_list) + 1

        self.test_it()

        self.assert_alert__not_saved()

    # SIMPLE - Equal
    def test__simple_alert__true__data_last_check__accept_false__value_user_based__max__equal(self):
        self.simple_case__notification_false()

        self.test_it()

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_last_check__accept_false__value_user_based__max__equal(self):
        self.simple_case__notification_false()
        self.value_number = max(self.donnee_comptage_list) - 1

        self.test_it()

        self.assert_alert__not_saved()

    # SIMPLE - Min
    def test__simple_alert__true__data_last_check__accept_false__value_user_based__min__equal(self):
        self.simple_case__notification_false()

        self.operator = MyOperator.MIN
        self.value_number = min(self.donnee_comptage_list)

        self.test_it()
        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert min(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_last_check__accept_false__value_user_based__min__equal(self):
        self.simple_case__notification_false()

        self.operator = MyOperator.MIN
        self.value_number = min(self.donnee_comptage_list) - 1

        self.test_it()

        self.assert_alert__not_saved()

    # SIMPLE - AVERAGE --> data_period_based
    def test__simple_alert__true__data_period_based__accept_false__value_user_based__average__equal(self):
        self.simple_case__notification_false()

        self.operator = MyOperator.AVERAGE
        self.value_number = mean(self.donnee_comptage_list)

        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.DAY
        self.data_period_quantity = 1

        self.test_it()
        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert mean(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_period_based__accept_false__value_user_based__average__equal(self):
        self.simple_case__notification_false()

        self.operator = MyOperator.AVERAGE
        self.value_number = mean(self.donnee_comptage_list) - 1

        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.DAY
        self.data_period_quantity = 1

        self.test_it()

        self.assert_alert__not_saved()

    # DATA - Data Period Type - LAST_CHECK
    def test__simple_alert__true__data_last_check__not_all(self):
        self.simple_case__notification_false()

        self.last_check = self.today - timedelta(days=2)
        self.donnee_comptage_delta = timedelta(days=1)

        result_expected = self.donnee_comptage_list[:2]
        self.value_number = max(result_expected)

        self.test_it()

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(result_expected) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_last_check__no_data(self):
        self.simple_case__notification_false()
        self.last_check = self.today - timedelta(minutes=10)

        self.test_it()

        self.assert_alert__not_saved()

    # DATA - Data Period Type - USER_BASED
    def test__simple_alert__true__data_user_based(self):
        self.simple_case__notification_false()

        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.HOUR
        self.data_period_quantity = 2

        result_expected = self.donnee_comptage_list[:2]
        self.value_number = max(result_expected)

        self.test_it()

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(result_expected) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_user_based(self):
        self.simple_case__notification_false()

        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.HOUR
        self.data_period_quantity = 2

        self.value_number = max(self.donnee_comptage_list)
        result_expected = self.donnee_comptage_list[:2]

        self.test_it()

        self.assert_alert__not_saved()

    # DATA - Data Period Type - USER_BASED hours
    def test__simple_alert__true__data_user_based__hours(self):
        self.simple_case__notification_false()

        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.DAY
        self.data_period_quantity = 2
        self.hour_start = (self.today - timedelta(hours=5)).hour
        self.hour_end = (self.today - timedelta(hours=3)).hour

        result_expected = self.donnee_comptage_list[3:]
        self.value_number = max(result_expected)

        self.test_it()

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(result_expected) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_user_based__hours(self):
        self.simple_case__notification_false()

        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.DAY
        self.data_period_quantity = 2
        self.hour_start = (self.today - timedelta(hours=5)).hour
        self.hour_end = (self.today - timedelta(hours=3)).hour

        result_expected = self.donnee_comptage_list[:2]
        self.value_number = max(result_expected)

        self.test_it()

        self.assert_alert__not_saved()

    # -------> COMPLEXE (seuil) <--------

    # DB_BASED
    def test__complex_alert__true__data_last_check__value_db_based(self):
        self.simple_case__notification_false()
        # base
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # DB value
        self.value_type = ValueGeneratorType.SIMPLE_DB_BASED_VALUE

        self.value_number = 10
        self.objectif_value = max(self.donnee_comptage_list) - 1
        value_expected = self.objectif_value * (1 + (self.value_number / 100))

        self.test_it()

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert value_expected == results[index]

    def test__complex_alert__false__data_last_check__value_db_based(self):
        self.simple_case__notification_false()
        # base
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # DB value
        self.value_type = ValueGeneratorType.SIMPLE_DB_BASED_VALUE

        self.value_number = 10
        self.objectif_value = max(self.donnee_comptage_list)
        value_expected = self.objectif_value * (1 + (self.value_number / 100))

        self.test_it()

        self.assert_alert__not_saved()

    # DB_BASED - hours
    def test__complex_alert__true__data_last_check__value_db_based__hours(self):
        self.simple_case__notification_false()
        # base
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # data
        self.donnee_comptage_list = [3, 8, 5, 1, 6]
        self.hour_start = (self.today - timedelta(hours=5)).hour
        self.hour_end = (self.today - timedelta(hours=3)).hour
        data_expected = max(self.donnee_comptage_list[3:])

        # DB value
        self.value_type = ValueGeneratorType.SIMPLE_DB_BASED_VALUE

        self.value_number = 10
        value_expected = data_expected * (1 + (self.value_number / 100)) - 1
        self.objectif_value = value_expected / (1 + (self.value_number / 100))

        self.test_it()

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert data_expected == results[index]

        # Value check
        index = columns_name.index("value")
        assert value_expected == results[index]

    def test__complex_alert__false__data_last_check__value_db_based__hours(self):
        self.simple_case__notification_false()
        # base
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # data
        self.donnee_comptage_list = [3, 8, 5, 1, 6]
        self.hour_start = (self.today - timedelta(hours=5)).hour
        self.hour_end = (self.today - timedelta(hours=3)).hour
        data_expected = max(self.donnee_comptage_list[3:])

        # DB value
        self.value_type = ValueGeneratorType.SIMPLE_DB_BASED_VALUE

        self.value_number = 10
        value_expected = data_expected * (1 + (self.value_number / 100))
        self.objectif_value = value_expected / (1 + (self.value_number / 100))
        self.test_it()

        self.assert_alert__not_saved()

    # DB_BASED - hours
    def test__complex_alert__true__data_last_check__value_db_based__time_unit(self):
        self.simple_case__notification_false()
        # base
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # data
        self.donnee_comptage_list = [3, 8, 5, 1, 6]
        data_expected = max(self.donnee_comptage_list)

        # DB value
        self.value_type = ValueGeneratorType.SIMPLE_DB_BASED_VALUE

        self.value_number = 10
        self.objectif_time_unit = PeriodUnitDefinition.DAY
        value_expected = ((data_expected * self.objectif_time_unit.nb_hour - 1 * self.objectif_time_unit.nb_hour) * (1 + (self.value_number / 100)))
        self.objectif_value = value_expected / (1 + (self.value_number / 100))

        value_expected = value_expected / self.objectif_time_unit.nb_hour
        self.test_it()

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        print("data_expected", data_expected)
        assert data_expected == results[index]

        # Value check
        index = columns_name.index("value")
        print("value_expected", round(value_expected, 2))
        assert round(value_expected, 2) == round(results[index], 2)

    def test__complex_alert__false__data_last_check__value_db_based__time_unit(self):
        self.simple_case__notification_false()
        # base
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # data
        self.donnee_comptage_list = [3, 8, 5, 1, 6]
        data_expected = max(self.donnee_comptage_list)

        # DB value
        self.value_type = ValueGeneratorType.SIMPLE_DB_BASED_VALUE

        self.value_number = 10
        self.objectif_time_unit = PeriodUnitDefinition.DAY
        value_expected = ((data_expected * self.objectif_time_unit.nb_hour) * (1 + (self.value_number / 100)))
        self.objectif_value = value_expected / (1 + (self.value_number / 100))

        self.test_it()

        self.assert_alert__not_saved()

    # PERIOD_BASED_VALUE - last year
    def test__complex_alert__true__data_last_check__value_period_based__last_year(self):
        self.simple_case__notification_false()
        # base
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # data period
        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.DAY
        self.data_period_quantity = 1

        # value period type
        self.value_type = ValueGeneratorType.PERIOD_BASED_VALUE
        self.value_period_type = ValuePeriodType.LAST_YEAR


        value_data_list = [1, 2, 2, 1, 0]

        self.value_number = 10
        value_expected = max(value_data_list) * (1 + (self.value_number / 100))

        last_year_end_date = go_past_with_years(end_date=self.today, quantity=1)

        self.insert_defined_data()

        self.insert_donnees_comptage(
            end_day=last_year_end_date,
            data_list=value_data_list,
            delta=self.donnee_comptage_delta,
        )

        self.test_it(insert_data=False)

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert value_expected == results[index]

    def test__complex_alert__false__data_last_check__value_period_based__last_year(self):
        self.simple_case__notification_false()
        # base
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # data period
        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.DAY
        self.data_period_quantity = 1

        # value period type
        self.value_type = ValueGeneratorType.PERIOD_BASED_VALUE
        self.value_period_type = ValuePeriodType.LAST_YEAR

        value_data_list = self.donnee_comptage_list

        self.value_number = 10
        value_expected = max(value_data_list) * (1 + (self.value_number / 100))

        last_year_end_date = go_past_with_years(end_date=self.today, quantity=1)

        self.insert_defined_data()

        self.insert_donnees_comptage(
            end_day=last_year_end_date,
            data_list=value_data_list,
            delta=self.donnee_comptage_delta,
        )

        self.test_it(insert_data=False)

        self.assert_alert__not_saved()

    # PERIOD_BASED_VALUE - last data period
    def test__complex_alert__true__data_last_check__value_period_based__last_data_period(self):
        self.simple_case__notification_false()
        # base
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # data period
        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.DAY
        self.data_period_quantity = 1

        # value period type
        self.value_type = ValueGeneratorType.PERIOD_BASED_VALUE
        self.value_period_type = ValuePeriodType.LAST_DATA_PERIOD

        value_data_list = [1, 2, 2, 1, 0]

        self.value_number = 10
        value_expected = max(value_data_list) * (1 + (self.value_number / 100))

        last_data_period_end_date = self.today - timedelta(days=self.data_period_quantity)
        self.insert_defined_data()


        self.insert_donnees_comptage(
            end_day=last_data_period_end_date,
            data_list=value_data_list,
            delta=self.donnee_comptage_delta,
        )

        self.test_it(insert_data=False)

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert value_expected == results[index]

    def test__complex_alert__false__data_last_check__value_period_based__last_data_period(self):
        self.simple_case__notification_false()
        # base
        self.comparator = MyComparator.SUP
        self.acceptable_diff = True

        # data period
        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_unit = PeriodUnitDefinition.DAY
        self.data_period_quantity = 1

        # value period type
        self.value_type = ValueGeneratorType.PERIOD_BASED_VALUE
        self.value_period_type = ValuePeriodType.LAST_YEAR

        value_data_list = self.donnee_comptage_list.copy()

        self.value_number = 10
        value_expected = max(value_data_list) * (1 + (self.value_number / 100))

        last_data_period_end_date = self.today - timedelta(days=self.data_period_quantity)
        self.insert_defined_data()

        self.insert_donnees_comptage(
            end_day=last_data_period_end_date,
            data_list=value_data_list,
            delta=self.donnee_comptage_delta,
        )

        self.test_it(insert_data=False)

        self.assert_alert__not_saved()

    def test__simple_alert__true__equal__is_index(self):
        self.simple_case__notification_false()
        self.is_meter_index = True

        self.insert_defined_data(insert_all_donnee=False)
        self.test_it(insert_data=False)

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]





if __name__ == "__main__":
    print("\nTEST INIT\n")
    test_manager = AlertManagerTest()

    print("\n\nTEST START\n\n")
    test_name = None if len(sys.argv) < 2 else sys.argv[1]
    test_manager.start(test_name=test_name)
