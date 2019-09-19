import random

from model.alert import HandleDataFromDB
from datetime import datetime, timedelta
from model.utils import my_sql, METER_TABLE_NAME, TableToGenerate


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


# CREATE
def create_all_fake():
    # BI COMPTEUR
    if create_BI_COMPTEUR_table():
        insert_data_in_BI_COMPTEUR_table()

        # BI DONNEE COMPTAGE
        if create_BI_COMPTAGE_DONNEE_table():
            insert_data_to_test_in_BI_COMPTAGE_DONNEE_table()


def query_construction(self, compo, name):
    # PARAMS
    params_list = list(key for key, value in compo.items())
    params_list.pop(0)
    params_str = ", ".join([param for param in params_list])

    # Format
    format_param = ", ".join(["%s" for param in params_list])

    # QUERY
    query = "INSERT INTO {} ({}) VALUES ({})".format(name, params_str, format_param)
    print(query)
    return query


# --------------------------------------------    BI_ALERT_DEFINITION
def create_alert_def_and_other_data():
    alert_def = query_construction(compo=Ale)






if __name__ == '__main__':
    create_all_fake()

