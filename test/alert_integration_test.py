from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from unittest.mock import patch

from model.alert import PeriodUnitDefinition, Hour, Day, MyOperator, MyComparator, PeriodGeneratorType, \
    ValueGeneratorType, ValuePeriodType, Level, AlertDefinitionStatus, NotificationPeriod, AlertManager
from model.utils import MySqlConnection, my_sql, generate_days_flag, generate_hours_flag, get_day_name_from_datetime
from scripts.alert_tables_creation import alert_notification_table, alert_calculator_table, alert_definition_table, alert_alert_table, \
    alert_definition_meter_table, alert_definition_notification_table, alert_manager_table
from scripts.test__create_and_insert_data_in_fake_tables import bi_compteurs_table, bi_objectif_table, \
    bi_comptages_donnees, insert_in_bi_compteurs, insert_in_bi_objectifs, insert_in_notification, insert_in_calculator, \
    insert_in_alert_definition, insert_in_alert_definition_meter, insert_in_bi_comptage_donnees, \
    insert_in_alert_definition_notification_time


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
        self.create_tables()

    def start(self):
        for test in self._tests:
            print("\n____SET UP___")
            self.set_up_test()
            print("\n \t\t\t------->\t\tSTART TEST :", test.__name__, "\n")
            test()

    def __del__(self):
        print("\n_________________DEL_________________")
        self.__delete_db()

    # -- PREPARE --

    @abstractmethod
    def set_tests_to_run(self):
        raise NotImplementedError

    def set_up_test(self):
        pass

    @abstractmethod
    def create_tables(self):
        raise NotImplementedError

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
    def clean_table(table_name: str):
        query = "DELETE FROM {}".format(table_name)
        print(query)
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

        self.today = datetime.today()

        # -- METER --
        self.meter_id = None
        self.is_meter_index = False

        # -- Alert Definition --
        self.alert_definition_id = None
        self.name = "alert_definition_name"
        self.description = "i am supposed to describe the Alert definition"
        self.category = "category"
        self.level = Level.HIGH
        self.status = AlertDefinitionStatus.INACTIVE

        # -- Notification --
        self.alert_notification_id = None
        self.notification_period_quantity = 1
        self.notification_period_unit = NotificationPeriod.DAY
        self.email = "test@test.com"
        self.notification_days = [
            Day.MONDAY, Day.TUESDAY
        ]
        self.notification_hours = [
            Hour.H_1, Hour.H_2
        ]

        # -- Calculator --
        self.calculator_id = None
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
        self.value_type = ValueGeneratorType.USER_BASED_VALUE
        self.value_period_type = None

        # -- OBJECTIF --
        self.objectif_value = 20
        self.objectif_time_unit = None

        # -- DONNEE COMPTAGE --
        self.donnee_comptage_list = [3, 2, 5, 1, 4]
        self.donnee_comptage_end_day = self.today - timedelta(days=1)
        self.donnee_comptage_delta = timedelta(hours=1)

        # DEFINITION - NOTIFICATION
        self.last_notification_time = None

    def set_tests_to_run(self):
        return [
            self.test__notif_true__no_data,
            self.test__notif_true__with_data,
            self.test__notif_false__time_between,
            self.test__notif_false__days,
            self.test__notif_false__hours
        ]

    def create_tables(self):
        for table in AlertManagerTest.__tables:
            print(table, "start creation ...")
            table.request_table_creation()

    # SET UP

    def set_up_test(self):
        for table in reversed(AlertManagerTest.__tables):
            print(table, "cleaning ...")
            MyIntegrationTest.clean_table(table.name)


    def insert_defined_data(self):
        self.meter_id = insert_in_bi_compteurs(
            name="meter_1",
            is_index=self.is_meter_index
        )
        print("meter_id inserted :", self.meter_id)

        insert_in_bi_objectifs(
            objectif_value=self.objectif_value,
            time_unit=self.objectif_time_unit,
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
            data_period_unit=self.data_period_unit.name,
            value_type=self.value_type.name,
            value_number=self.value_number,
            value_period_type=self.value_period_type if not isinstance(self.value_period_type, ValuePeriodType) else self.value_period_type.name,
            hour_start=self.hour_start,
            hour_end=self.hour_end,
            acceptable_diff=self.acceptable_diff
        )

        self.alert_definition_id = insert_in_alert_definition(
            name="definition_name_1",
            category="definition_category_1",
            description="description_1",
            level=Level.HIGH.value,
            status=AlertDefinitionStatus.ACTIVE.value,
            notification_id=self.alert_notification_id,
            calculator_id=self.alert_calculator_id
        )

        insert_in_alert_definition_meter(
            meter_id=self.meter_id,
            alert_definition_id=self.alert_definition_id
        )

        # DONNEE COMPTAGE
        end_day = self.donnee_comptage_end_day

        for data in self.donnee_comptage_list:
            end_day -= self.donnee_comptage_delta
            insert_in_bi_comptage_donnees(
                donnee_comptage_value=data,
                meter_id=self.meter_id,
                time=end_day
            )

        # Definition - Notification TIME
        if self.last_notification_time:
            notification_time_id = insert_in_alert_definition_notification_time(
                notification_id=self.alert_notification_id,
                alert_definition_id=self.alert_definition_id,
                notification_datetime=self.last_notification_time
            )



    def test_it(self):
        self.insert_defined_data()
        AlertManager.start()

    # -----------------    SET DATA TO INSERT    -----------------

    # ---->  CALCULATOR  <----

    # -- DATA --

    # Data Period Type
    def is_alert__true__acceptable_diff_data_user_based(self):
        self.donnee_comptage_list = [3, 2, 5, 1, 4]
        self.donnee_comptage_delta = timedelta(hours=1)

        self.operator = MyOperator.MAX
        self.comparator = MyComparator.INF
        self.acceptable_diff = False
        self.value_number = max(self.donnee_comptage_list) + 10

        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_quantity = 5

        self.value_number = 15
        self.value_type = ValueGeneratorType.USER_BASED_VALUE
        self.value_period_type = None


    def is_alert__false__acceptable_diff_data_user_based(self):
        self.donnee_comptage_list = [3, 2, 5, 1, 4]
        self.donnee_comptage_delta = timedelta(hours=1)

        self.operator = MyOperator.MAX
        self.comparator = MyComparator.SUP
        self.acceptable_diff = False
        self.value_number = max(self.donnee_comptage_list) + 10

        self.data_period_type = PeriodGeneratorType.USER_BASED
        self.data_period_quantity = 5

        self.value_number = 15
        self.value_type = ValueGeneratorType.USER_BASED_VALUE
        self.value_period_type = None

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

    # -----------------    CHECK DATA IN DB    -----------------

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
        print(results)

        # len result
        assert len(results) == expected_id
        results = results[expected_id - 1]

        # alert_definition_id
        index = columns_name.index("alert_definition_id")
        assert self.alert_definition_id == results[index]
        print("alert {} saved".format(expected_id))

    def assert_alert__not_saved(self, expected_id=1):
        columns_name, results = self.query_select_all(table_name=alert_definition_notification_table.name)
        print(results)

        # len result
        assert len(results) == expected_id - 1

    # NOTIFICATION
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
        index = columns_name.index("notification_id")
        assert self.alert_definition_id == results[index]
        print("notif {} saved".format(expected_id))

    def assert_notification__not_saved(self, expected_id=1):
        columns_name, results = self.query_select_all(table_name=alert_definition_notification_table.name)
        print(results)

        # len result
        assert len(results) == expected_id - 1


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
            email_mock.assert_called()
            self.assert_alert__saved()
            self.assert_notification__saved()

    def test__notif_true__with_data(self):
        # alert true
        self.is_alert__true__acceptable_diff_data_user_based()

        # Notif true - with data
        self.notification_day__true()
        self.notification_hour__true()
        self.notification_enough_time_between__true__with_data()

        with patch('model.alert.Email.send', return_value=True) as email_mock:
            self.test_it()
            email_mock.assert_called()
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

























if __name__ == "__main__":
    print("\nTEST INIT\n")
    test_manager = AlertManagerTest()
    print("\n\nTEST START\n\n")
    test_manager.start()
