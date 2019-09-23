import random

from model.alert import HandleDataFromDB, PeriodUnitDefinition, MyOperator, MyComparator, PeriodGeneratorType, \
    ValueGeneratorType, Level, AlertStatus, AlertDefinitionStatus, Day, Hour
from datetime import datetime, timedelta
from model.utils import my_sql, METER_TABLE_NAME, TableToGenerate, NOTIFICATION_COMPO, NOTIFICATION_NAME, \
    CALCULATOR_COMPO, CALCULATOR_NAME, DEFINITION_COMPO, DEFINITION_TABLE_NAME, METER_DEFINITION_COMPO, \
    METER_DEFINITIONS_ALERT_TABLE_NAME
from scripts.alert_tables_creation import create_tables


def __generate_valeur_comptage_table_query():
    my_format = "CREATE TABLE IF NOT EXISTS {} ( ".format(HandleDataFromDB.table_name)
    my_format += "id INT AUTO_INCREMENT PRIMARY KEY, "
    my_format += "{} DOUBLE NOT NULL, ".format(HandleDataFromDB.value_column_name)
    my_format += "{} INT(11), ".format(HandleDataFromDB.meter_id_column_name)
    my_format += "{} DATETIME NOT NULL, ".format(HandleDataFromDB.hour_column_name)

    foreign_key = "FOREIGN KEY ({}) REFERENCES {}(id)".format(HandleDataFromDB.meter_id_column_name, METER_TABLE_NAME)

    my_format += foreign_key + ")"
    return my_format


def create_BI_COMPTAGE_DONNEE_table():
    query = __generate_valeur_comptage_table_query()
    print(query)
    my_sql.execute_and_close(query=query)
    return TableToGenerate.check_if_table_created(table_name=HandleDataFromDB.table_name)


def get_insert_base_BI_COMPTAGE_DONNEE_table():
    return "INSERT INTO {} ({}, {}, {}) VALUES (%s, %s, %s)".format(
        HandleDataFromDB.table_name,
        HandleDataFromDB.value_column_name,
        HandleDataFromDB.meter_id_column_name,
        HandleDataFromDB.hour_column_name
    )

def insert_random_data_in_BI_COMPTAGE_DONNEE_table():
    insert_base = get_insert_base_BI_COMPTAGE_DONNEE_table()

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
    insert_base = get_insert_base_BI_COMPTAGE_DONNEE_table()

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


# --------------------------------------------    BI_COMPTEURS
INDEX_COLUMN_NAME = "IS_INDEX"

def __generate_table_COMPTEUR_query():
    my_format = "CREATE TABLE IF NOT EXISTS {} (".format(METER_TABLE_NAME)
    my_format += "id INT AUTO_INCREMENT PRIMARY KEY, "
    my_format += "name VARCHAR(255), "
    my_format += "{} BOOLEAN)".format(INDEX_COLUMN_NAME)
    return my_format


def create_BI_COMPTEUR_table():
    query = __generate_table_COMPTEUR_query()
    print(query)
    my_sql.execute_and_close(query=query)
    return TableToGenerate.check_if_table_created(table_name=METER_TABLE_NAME)



def insert_data_in_BI_COMPTEUR_table():
    select_base = "INSERT INTO {} ({}, {}) VALUES (%s, %s)".format(
        METER_TABLE_NAME,
        "NAME",
        INDEX_COLUMN_NAME
    )
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
        print(type(value))
        print(value)
        my_sql.execute_and_close(query=select_base, params=value)




def query_construction(compo, name):
    # PARAMS
    params_list = list(key for key in compo.keys())
    params_list.pop(0)
    params_str = ", ".join([param for param in params_list])

    # Format
    format_param = ", ".join(["%s" for param in params_list])

    # QUERY
    query = "INSERT INTO {} ({}) VALUES ({})".format(name, params_str, format_param)
    print(query)
    return query


def query_construction_without_id(compo, name):
    # PARAMS
    params_list = list(key for key in compo.keys())
    params_str = ", ".join([param for param in params_list])

    # Format
    format_param = ", ".join(["%s" for param in params_list])

    # QUERY
    query = "INSERT INTO {} ({}) VALUES ({})".format(name, params_str, format_param)
    print(query)
    return query



# --------------------------------------------    BI_ALERT_DEFINITION

def insert_in_notification(period_unit: str, period_quantity: int, email: str, days_flags: int, hours_flags: int):
    query = query_construction(compo=NOTIFICATION_COMPO, name=NOTIFICATION_NAME)
    params = [
        period_unit,
        period_quantity,
        email,
        days_flags,
        hours_flags,
    ]
    print("query", query)
    print("params", params)
    my_sql.execute_and_close(query=query, params=params)


def insert_in_calculator(operator, comparator, data_period_type, data_period_quantity, data_period_unit, value_type, value_number, value_period_quantity, value_period_unit, acceptable_diff):
    query = query_construction(compo=CALCULATOR_COMPO, name=CALCULATOR_NAME)
    params = [
        operator,
        comparator,
        data_period_type,
        data_period_quantity,
        data_period_unit,
        value_type,
        value_number,
        value_period_quantity,
        value_period_unit,
        acceptable_diff
    ]
    print("query", query)
    print("params", params)
    my_sql.execute_and_close(query=query, params=params)


def insert_in_alert_definition(name, category, level, status, notification_id, calculator_id):
    query = query_construction(compo=DEFINITION_COMPO, name=DEFINITION_TABLE_NAME)
    params = [
        name,
        category,
        level,
        status,
        notification_id,
        calculator_id
    ]
    print("query", query)
    print("params", params)
    my_sql.execute_and_close(query=query, params=params)


def insert_in_alert_definition_meter(meter_id: int, alert_definition_id: int):
    query = query_construction_without_id(compo=METER_DEFINITION_COMPO, name=METER_DEFINITIONS_ALERT_TABLE_NAME)
    params = [
        meter_id,
        alert_definition_id
    ]
    print("query", query)
    print("params", params)
    my_sql.execute_and_close(query=query, params=params)


def create_alert_def_and_other_data():
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
        value_period_quantity=1,
        value_period_unit=PeriodUnitDefinition.WEEK.name,
        acceptable_diff=False
    )

    # ALERT DEFINITION
    insert_in_alert_definition(
        name="definition_name_1",
        category="definition_name_1",
        level=Level.HIGH.value,
        status=AlertDefinitionStatus.ACTIVE.value,
        notification_id=1,
        calculator_id=1
    )

    # DEFINITION METER
    insert_in_alert_definition_meter(
        meter_id=3,
        alert_definition_id=1
    )


# CREATE
def create_all_fake():
    # BI COMPTEUR
    if create_BI_COMPTEUR_table():
        insert_data_in_BI_COMPTEUR_table()

        # BI DONNEE COMPTAGE
        if create_BI_COMPTAGE_DONNEE_table():
            insert_data_to_test_in_BI_COMPTAGE_DONNEE_table()

    if not TableToGenerate.check_if_table_created(table_name=DEFINITION_TABLE_NAME):
        create_tables()

    create_alert_def_and_other_data()


if __name__ == '__main__':
    create_all_fake()

