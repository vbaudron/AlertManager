import random

from model.alert import HandleDataFromDB, PeriodUnitDefinition, MyOperator, MyComparator, PeriodGeneratorType, \
    ValueGeneratorType, Level, AlertDefinitionStatus, Day, Hour, ValuePeriodType, my_sql
from datetime import datetime, timedelta
from model.utils import METER_TABLE_NAME, TableToGenerate, NOTIFICATION_COMPO, NOTIFICATION_NAME, \
    CALCULATOR_COMPO, CALCULATOR_NAME, DEFINITION_COMPO, DEFINITION_TABLE_NAME, METER_DEFINITION_COMPO, \
    METER_DEFINITIONS_ALERT_TABLE_NAME, insert_query_construction, ALERT_DEFINITION_NOTIFICATION_TIME_COMPO, \
    ALERT_DEFINITION_NOTIFICATION_TIME, ALERT_MANAGER_TABLE_NAME, ALERT_MANAGER_TABLE_COMPO
from scripts.alert_tables_creation import create_alert_related_tables


# _____________________________________  ****   INSERT METHODS   ****  _______________________________________________


def insert_query_construction_without_id(compo, name):
    # PARAMS
    params_list = list(key for key in compo.keys())
    params_str = ", ".join([param for param in params_list])

    # Format
    format_param = ", ".join(["%s" for param in params_list])

    # QUERY
    query = "INSERT INTO {} ({}) VALUES ({})".format(name, params_str, format_param)
    print(query)
    return query


# _____________________________________  ****   NON ALERT (FAKE) TABLES   ****  ________________________________________

# ____________ BI_COMPTAGE_DONNEES

COMPTAGE_COMPO = {
    "id": "INT AUTO_INCREMENT PRIMARY KEY",
    HandleDataFromDB.value_column_name: "DOUBLE NOT NULL",
    HandleDataFromDB.meter_id_column_name: "INT(11)",
    HandleDataFromDB.hour_column_name: " DATETIME NOT NULL",
}

COMPTAGE_FOREIGN_KEY = {
    "FOREIGN KEY ({}) REFERENCES {}(id)".format(HandleDataFromDB.meter_id_column_name, METER_TABLE_NAME)
}


bi_comptages_donnees = TableToGenerate(
    table_name=HandleDataFromDB.table_name,
    compo=COMPTAGE_COMPO,
    foreign_keys=COMPTAGE_FOREIGN_KEY
)


def insert_in_bi_comptage_donnees(donnee_comptage_value, meter_id, time):
    query = insert_query_construction(compo=COMPTAGE_COMPO, name=HandleDataFromDB.table_name)
    params = [
        donnee_comptage_value,
        meter_id,
        time
    ]
    print("params", params)
    my_sql.execute_and_close(query=query, params=params)


def insert_random_data_in_BI_COMPTAGE_DONNEE_table():
    insert_base = insert_query_construction(compo=COMPTAGE_COMPO, name=HandleDataFromDB.table_name)

    def get_comptage(comptage):
        if comptage > 100:
            return comptage - comptage / 10
        elif comptage > 20:
            return comptage + comptage - comptage / 2
        else:
            return 20 + comptage % 3

    def __generate_values():
        start_day = datetime.today() - timedelta(days=10)
        meters_id = [1, 2, 3]
        values = list()
        comptage = 20
        while len(values) < 10:
            comptage = get_comptage(comptage)
            start_day += timedelta(days=1)

            values.append((
                comptage,
                random.choice(meters_id),
                start_day
            ))

        return values

    values = __generate_values()

    for value in values:
        my_sql.execute_and_close(query=insert_base, params=value)


def insert_data_to_test_in_BI_COMPTAGE_DONNEE_table():
    insert_base = insert_query_construction(compo=COMPTAGE_COMPO, name=HandleDataFromDB.table_name)
    meter_id = 4
    values = list()
    comptage_list = [3, 2, 5, 1, 4]
    start_day = datetime.today() - timedelta(days=1)

    for comtage in comptage_list:
        start_day += timedelta(hours=1)
        values.append((
            comtage,
            meter_id,
            start_day
        ))

    for value in values:
        my_sql.execute_and_close(query=insert_base, params=value)


# ____________ BI_COMPTEURS

METER_TABLE_COMPO = {
    "id": "INT AUTO_INCREMENT PRIMARY KEY",
    "name": "VARCHAR(15)",
    "is_index": "BOOLEAN NOT NULL DEFAULT FALSE"
}

bi_compteurs_table = TableToGenerate(
    table_name=METER_TABLE_NAME,
    compo=METER_TABLE_COMPO
)

def insert_in_bi_compteurs(name, is_index:bool):
    query = insert_query_construction(compo=METER_TABLE_COMPO, name=METER_TABLE_NAME)
    params = [
        name,
        is_index
    ]
    print("params", params)
    return my_sql.execute_and_close(query=query, params=params, return_id=True)

def insert_in_bi_compteurs_data():
    select_base = insert_query_construction(compo=METER_TABLE_COMPO, name=METER_TABLE_NAME)
    print(select_base)

    def __generate_values():
        values = list()
        my_bool = [0, 1]
        i = 1
        while len(values) < 10:
            values.append((
                "name_{}".format(i),
                random.choice(my_bool)
            ))
            i += 1

        return values

    values = __generate_values()

    for value in values:
        print(value)
        insert_in_bi_compteurs(name=value[0], is_index=value[1])


#  ____________ BI_OBJECTIF

OBJECTIF_TABLE_NAME = "bi_objectifs"
OBJECTIF_TABLE_COMPO = {
    "id": "INT AUTO_INCREMENT PRIMARY KEY",
    "value": "DOUBLE",
    "time_unit" : "VARCHAR(8) DEFAULT NULL",
    "r_compteur": "INT NOT NULL"
}
OBJECTIF_TABLE_FOREIGN_KEY = [
    "FOREIGN KEY (r_compteur) REFERENCES {}(id)".format(METER_TABLE_NAME)
]


bi_objectif_table = TableToGenerate(
        table_name=OBJECTIF_TABLE_NAME,
        compo=OBJECTIF_TABLE_COMPO,
        foreign_keys=OBJECTIF_TABLE_FOREIGN_KEY
)


def insert_in_bi_objectifs(objectif_value: float, time_unit: str, meter_id):
    query = insert_query_construction(compo=OBJECTIF_TABLE_COMPO, name=OBJECTIF_TABLE_NAME)
    params = [
        objectif_value,
        time_unit,
        meter_id
    ]
    print("params", params)
    return my_sql.execute_and_close(query=query, params=params, return_id=True)


def insert_data_in_bi_objectif():
    insert_in_bi_objectifs(
        objectif_value=2.456,
        time_unit=PeriodUnitDefinition.DAY.name,
        meter_id=4
    )

# _____________________________________  ****   ALERT TABLES INSERTION  ****  __________________________________________


# NOTIFICATION
def insert_in_notification(period_unit: str, period_quantity: int, email: str, days_flags: int, hours_flags: int):
    query = insert_query_construction(compo=NOTIFICATION_COMPO, name=NOTIFICATION_NAME)
    params = [
        period_unit,
        period_quantity,
        email,
        days_flags,
        hours_flags,
    ]
    print("query", query)
    print("params", params)
    return my_sql.execute_and_close(query=query, params=params, return_id=True)


# CALCULATOR
def insert_in_calculator(operator, comparator, data_period_type, data_period_quantity, data_period_unit, value_type, value_number, value_period_type, hour_start, hour_end, acceptable_diff):
    query = insert_query_construction(compo=CALCULATOR_COMPO, name=CALCULATOR_NAME)
    params = [
        operator,
        comparator,
        data_period_type,
        data_period_quantity,
        data_period_unit,
        value_type,
        value_number,
        value_period_type,
        hour_start,
        hour_end,
        acceptable_diff
    ]
    print("query", query)
    print("params", params)
    return my_sql.execute_and_close(query=query, params=params, return_id=True)


# DEFINITION
def insert_in_alert_definition(name, category, description, level, status, notification_id, calculator_id):
    query = insert_query_construction(compo=DEFINITION_COMPO, name=DEFINITION_TABLE_NAME)
    params = [
        name,
        category,
        description,
        level,
        status,
        notification_id,
        calculator_id
    ]
    print("query", query)
    print("params", params)
    return my_sql.execute_and_close(query=query, params=params, return_id=True)


# DEFINITION_METER
def insert_in_alert_definition_meter(meter_id: int, alert_definition_id: int):
    query = insert_query_construction_without_id(compo=METER_DEFINITION_COMPO, name=METER_DEFINITIONS_ALERT_TABLE_NAME)
    params = [
        meter_id,
        alert_definition_id
    ]
    print("query", query)
    print("params", params)
    return my_sql.execute_and_close(query=query, params=params, return_id=True)


# DEFINITION NOTIFICATION time
def insert_in_alert_definition_notification_time(notification_id, alert_definition_id, notification_datetime: datetime):
    query = insert_query_construction(compo=ALERT_DEFINITION_NOTIFICATION_TIME_COMPO, name=ALERT_DEFINITION_NOTIFICATION_TIME)
    params = [
        notification_id,
        alert_definition_id,
        notification_datetime
    ]
    print("query", query)
    print("params", params)
    return my_sql.execute_and_close(query=query, params=params, return_id=True)

# ALERT MANAGER
def insert_in_alert_manager(launch_datetime: datetime):
    query = insert_query_construction(compo=ALERT_MANAGER_TABLE_COMPO, name=ALERT_MANAGER_TABLE_NAME)
    params = [
        launch_datetime
    ]
    print("query", query)
    print("params", params)
    return my_sql.execute_and_close(query=query, params=params, return_id=True)


# MAIN
def insert_alert_def_and_other_data():
    # NOTIFICATION
    insert_in_notification(
        period_unit=PeriodUnitDefinition.DAY.name,
        period_quantity=5,
        email="virginie.baudron@gmail.com",
        days_flags=Day.MONDAY.value | Day.SUNDAY.value,
        hours_flags=Hour.H_2.value | Hour.H_3.value,
    )

    # CALCULATOR
    insert_in_calculator(
        operator=MyOperator.MAX.name,
        comparator=MyComparator.SUP.name,
        data_period_type=PeriodGeneratorType.USER_BASED.name,
        data_period_quantity=4,
        data_period_unit=PeriodUnitDefinition.DAY.name,
        value_type=ValueGeneratorType.PERIOD_BASED_VALUE.name,
        value_number=15,
        value_period_type=ValuePeriodType.LAST_YEAR.name,
        hour_start=20,
        hour_end=8,
        acceptable_diff=False
    )

    # ALERT DEFINITION
    insert_in_alert_definition(
        name="definition_name_1",
        category="definition_category_1",
        description="description_1",
        level=Level.HIGH.value,
        status=AlertDefinitionStatus.ACTIVE.value,
        notification_id=1,
        calculator_id=1
    )

    # DEFINITION METER
    insert_in_alert_definition_meter(
        meter_id=4,
        alert_definition_id=1
    )


def create_fake_tables():
    tables = [
        bi_compteurs_table,
        bi_objectif_table,
        bi_comptages_donnees
    ]

    for table in tables:
        print("\n", table, "start creation ...")
        table.request_table_creation()


# CREATE
def create_all_tables():
    # CREATE
    create_fake_tables()

    # Insert
    insert_in_bi_compteurs_data()
    insert_data_to_test_in_BI_COMPTAGE_DONNEE_table()
    insert_data_in_bi_objectif()

    if not TableToGenerate.check_if_table_created(table_name=DEFINITION_TABLE_NAME):
        create_alert_related_tables()

    insert_alert_def_and_other_data()


if __name__ == '__main__':
    create_all_tables()

