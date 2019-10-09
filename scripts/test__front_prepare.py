from datetime import timedelta, datetime

from model.alert import my_sql, HandleDataFromDB, PeriodUnitDefinition, AlertManager
from model.utils import ALERT_DEFINITION_NOTIFICATION_TIME, ALERT_MANAGER_TABLE_NAME, METER_TABLE_NAME, ALERT_TABLE_NAME
from scripts.test__create_and_insert_data_in_fake_tables import insert_in_alert_definition_notification_time, \
    insert_in_alert_manager, insert_in_bi_comptage_donnees, insert_in_bi_objectifs, OBJECTIF_TABLE_NAME


def erase_meter_id_data(table_name:str, meter_id:int):
    query = "DELETE FROM {} WHERE r_compteur=%s".format(table_name)
    print(query)
    params = [meter_id]
    my_sql.execute_and_close(query=query, params=params)

def erase_data_in_table(table_name:str):
    query = "DELETE FROM {}".format(table_name)
    print(query)
    my_sql.execute_and_close(query=query)

def update_meter_is_index(meter_id, is_index):
    query = "UPDATE {} SET is_index={} WHERE id=%s".format(METER_TABLE_NAME, is_index)
    params = [meter_id]
    print(query)
    print(params)
    my_sql.execute_and_close(query=query, params=params)


class MyFrontContextPreparation:
    def __init__(self,
                 meter_id,
                 notification_id,
                 alert_definition_id,
                 calculator_id,
                 is_index=False,
                 objectif_value=20,
                 objectif_time_unit=None,
                 donnee_comptage_list=[3, 2, 5, 1, 4],
                 donnee_comptage_end_day=datetime.today(),
                 donnee_comptage_delta=timedelta(hours=1),
                 last_notification_time=None,
                 notification_period_unit=None,
                 notification_period_quantity=None,
                 last_check=None):

        self.today = datetime.today()

        # -- METER --
        self.meter_id = meter_id
        self.is_index = is_index

        # -- ID --
        self.notification_id = notification_id
        self.alert_definition_id = alert_definition_id
        self.calculator_id = calculator_id

        # -- OBJECTIF --
        self.objectif_value = objectif_value
        self.objectif_time_unit = objectif_time_unit

        # -- DONNEE COMPTAGE --
        self.donnee_comptage_list = donnee_comptage_list
        self.donnee_comptage_end_day = donnee_comptage_end_day
        self.donnee_comptage_delta = donnee_comptage_delta


        # DEFINITION - NOTIFICATION
        self.last_notification_time = last_notification_time

        # MANAGER
        self.last_check = last_check

    def prepare(self):
        # PREVIOUS NOTIFICATION
        erase_data_in_table(table_name=ALERT_DEFINITION_NOTIFICATION_TIME)
        if self.last_notification_time:
            notification_time_id = insert_in_alert_definition_notification_time(
                notification_id=self.notification_id,
                alert_definition_id=self.alert_definition_id,
                notification_datetime=self.last_notification_time
            )

        # MANAGER
        erase_data_in_table(table_name=ALERT_MANAGER_TABLE_NAME)
        if self.last_check:
            insert_in_alert_manager(
                launch_datetime=self.last_check
            )

        # METER
        update_meter_is_index(meter_id=self.meter_id, is_index=self.is_index)

        # DONNEE COMPTAGE

        erase_meter_id_data(table_name=HandleDataFromDB.table_name, meter_id=self.meter_id)

        end_day = self.donnee_comptage_end_day

        for data in self.donnee_comptage_list:
            end_day -= self.donnee_comptage_delta
            insert_in_bi_comptage_donnees(
                donnee_comptage_value=data,
                meter_id=self.meter_id,
                time=end_day
            )

        # OBJECTIF
        erase_meter_id_data(table_name=OBJECTIF_TABLE_NAME, meter_id=self.meter_id)
        insert_in_bi_objectifs(
            objectif_value=self.objectif_value,
            time_unit=self.objectif_time_unit,
            meter_id=self.meter_id
        )


METER_ID = 358
ALERT_DEFINITION_ID_BASE = 21
NOTIFICATION_ID_BASE = 21
CALCULATOR_ID_BASE = 31


test__notif_true__no_data_1 = MyFrontContextPreparation(
    meter_id=METER_ID,
    notification_id=NOTIFICATION_ID_BASE,
    alert_definition_id=ALERT_DEFINITION_ID_BASE,
    calculator_id=CALCULATOR_ID_BASE,
    is_index=False,
    objectif_value=20,
    objectif_time_unit=None,
    donnee_comptage_list=[3, 2, 5, 1, 4],
    donnee_comptage_end_day=datetime.today(),
    donnee_comptage_delta=timedelta(hours=1),
    last_notification_time=None,
    notification_period_unit=None,
    notification_period_quantity=None,
    last_check=None
)

test__notif_true__with_data_2 = MyFrontContextPreparation(
    meter_id=METER_ID,
    notification_id=NOTIFICATION_ID_BASE + 1,
    alert_definition_id=ALERT_DEFINITION_ID_BASE + 1,
    calculator_id=CALCULATOR_ID_BASE + 1,
    is_index=False,
    objectif_value=20,
    objectif_time_unit=None,
    donnee_comptage_list=[3, 2, 5, 1, 4],
    donnee_comptage_end_day=datetime.today(),
    donnee_comptage_delta=timedelta(hours=1),
    last_notification_time=datetime.today() - timedelta(days=20),
    notification_period_unit=PeriodUnitDefinition.DAY,
    notification_period_quantity=10,
    last_check=None
)

class TestGenerator:

    tests: list

    def __init__(self):
        self.tests = self.tests_to_run()

        self.today = datetime.today()

        # -- METER --
        self.meter_id = None
        self.is_index = 0

        # -- ID --
        self.notification_id = None
        self.alert_definition_id = None
        self.calculator_id = None

        # -- OBJECTIF --
        self.objectif_value = None
        self.objectif_time_unit = None

        # -- DONNEE COMPTAGE --
        self.donnee_comptage_list = []
        self.donnee_comptage_end_day = None
        self.donnee_comptage_delta = None


        # DEFINITION - NOTIFICATION
        self.last_notification_time = None

        # MANAGER
        self.last_check = None


    def start(self, id_start=None):
        for test in self.tests:
            index = self.tests.index(test) + 1
            if not id_start or id_start == index:
                id_def = ALERT_DEFINITION_ID_BASE + self.tests.index(test)
                print("\n\n", index, "\t\t\t------->\t\tSTART TEST :", test.__name__, "\n\n")
                self.set_ids(alert_definition_id=id_def)
                test()

    def tests_to_run(self):
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
            self.test__simple_alert__false__data_last_check__accept_false__value_user_based__max__equal,
            self.test__simple_alert__true__data_last_check__accept_false__value_user_based__average__equal,
            self.test__simple_alert__false__data_last_check__accept_false__value_user_based__average__equal,
            self.test__simple_alert__true__data_last_check__accept_false__value_user_based__average__equal,
            self.test__simple_alert__false__data_last_check__accept_false__value_user_based__average__equal,
            self.test__simple_alert__true__data_user_based,
            self.test__simple_alert__false__data_user_based
        ]

    def prepare(self):
        # PREVIOUS NOTIFICATION
        erase_data_in_table(table_name=ALERT_DEFINITION_NOTIFICATION_TIME)
        if self.last_notification_time:
            notification_time_id = insert_in_alert_definition_notification_time(
                notification_id=self.notification_id,
                alert_definition_id=self.alert_definition_id,
                notification_datetime=self.last_notification_time
            )

        # MANAGER
        erase_data_in_table(table_name=ALERT_MANAGER_TABLE_NAME)
        if self.last_check:
            insert_in_alert_manager(
                launch_datetime=self.last_check
            )

        # METER
        update_meter_is_index(meter_id=self.meter_id, is_index=self.is_index)

        # DONNEE COMPTAGE

        erase_meter_id_data(table_name=HandleDataFromDB.table_name, meter_id=self.meter_id)

        end_day = self.donnee_comptage_end_day

        for data in self.donnee_comptage_list:
            end_day -= self.donnee_comptage_delta
            insert_in_bi_comptage_donnees(
                donnee_comptage_value=data,
                meter_id=self.meter_id,
                time=end_day
            )

        # OBJECTIF
        erase_meter_id_data(table_name=OBJECTIF_TABLE_NAME, meter_id=self.meter_id)
        insert_in_bi_objectifs(
            objectif_value=self.objectif_value,
            time_unit=self.objectif_time_unit,
            meter_id=self.meter_id
        )

    def set_ids(self, alert_definition_id:int):
        self.alert_definition_id = alert_definition_id
        self.notification_id = alert_definition_id
        self.calculator_id = alert_definition_id + 10

    def query_select_all(self):
        query = "SELECT * FROM {} WHERE alert_definition_id=%s".format(ALERT_TABLE_NAME)
        params = [self.alert_definition_id]
        cursor = my_sql.generate_cursor()
        cursor.execute(operation=query, params=params)
        columns_name = cursor.column_names
        results = cursor.fetchall()
        return columns_name, results


    def assert_alert__saved(self):
        columns_name, results = self.query_select_all()
        print("RESULT", results)

        # len result
        assert len(results) == 1
        results = results[0]

        print("alert saved")
        return columns_name, results

    def assert_alert__not_saved(self):
        columns_name, results = self.query_select_all()
        print(results)

        # len result
        assert len(results) == 0

    def test__notif_true__no_data(self):
        self.last_notification_time = None
        self.is_index = True

        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__saved()

    def test__notif_true__with_data(self):
        self.last_notification_time = self.today - timedelta(days=20)

        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__saved()

    def test__notif_false__time_between(self):
        self.last_notification_time = self.today - timedelta(days=5)

        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__saved()

    def test__notif_false__days(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__saved()

    def test__notif_false__hours(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)
        self.assert_alert__saved()

    def test__notif_false__not_alert(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)
        self.assert_alert__not_saved()

    # CALCULATOR TEST

    # SIMPLE - Inf

    def test__simple_alert__true__data_last_check__accept_false__value_user_based__max__inf(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_last_check__accept_false__value_user_based__max__inf(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__not_saved()

        # SIMPLE - Sup

    def test__simple_alert__true__data_last_check__accept_false__value_user_based__max__sup(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_last_check__accept_false__value_user_based__max__sup(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__not_saved()

        # SIMPLE - Equal

    def test__simple_alert__true__data_last_check__accept_false__value_user_based__max__equal(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_last_check__accept_false__value_user_based__max__equal(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__not_saved()

        # SIMPLE - Min

    def test__simple_alert__true__data_last_check__accept_false__value_user_based__min__equal(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert min(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_last_check__accept_false__value_user_based__min__equal(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__not_saved()

        # SIMPLE - AVERAGE

    def test__simple_alert__true__data_last_check__accept_false__value_user_based__average__equal(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert mean(self.donnee_comptage_list) == results[index]

        # Value check
        index = columns_name.index("value")
        assert self.value_number == results[index]

    def test__simple_alert__false__data_last_check__accept_false__value_user_based__average__equal(self):

        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__not_saved()

        # DATA - Data Period Type - LAST_CHECK

    def test__simple_alert__true__data_last_check__not_all(self):
        self.last_check = self.today - timedelta(days=2)
        self.donnee_comptage_delta = timedelta(days=1)

        self.prepare()
        AlertManager.start(self.alert_definition_id)

        result_expected = self.donnee_comptage_list[:2]
        value_number = max(result_expected)

        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(result_expected) == results[index]

        # Value check
        index = columns_name.index("value")
        assert value_number == results[index]

    def test__simple_alert__false__data_last_check__accept_false__value_user_based__max__equal(self):

        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__not_saved()

        # DATA - Data Period Type - USER_BASED

    def test__simple_alert__true__data_user_based(self):

        self.prepare()
        AlertManager.start(self.alert_definition_id)

        result_expected = self.donnee_comptage_list[:2]
        value_number = max(result_expected)


        columns_name, results = self.assert_alert__saved()

        # Data check
        index = columns_name.index("data")
        assert max(result_expected) == results[index]

        # Value check
        index = columns_name.index("value")
        assert value_number == results[index]

    def test__simple_alert__false__data_user_based(self):
        self.prepare()
        AlertManager.start(self.alert_definition_id)

        self.assert_alert__not_saved()


if __name__ == '__main__':
   tg = TestGenerator()
   tg.start(1)

