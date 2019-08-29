from model.utility import my_sql, CREATE_ALERT_TABLE, ALERT_TABLE_COMPO, ALERT_TABLE_NAME, FOREIGN_KEY
import logging as log


def __generate_one_compo(key: str, value: str):
    return key + " " + value


def __generate_alert_table_creation_param():
    my_params = tuple(__generate_one_compo(key, value) for key, value in ALERT_TABLE_COMPO.items())
    return my_params


def __generate_alert_table_creation_query():
    i = 0
    params = __generate_alert_table_creation_param()
    my_format = " ("
    size = len(ALERT_TABLE_COMPO)
    while i < size:
        my_format += params[i]
        i += 1
        my_format += ", "
    my_format += FOREIGN_KEY + ")"
    return str(CREATE_ALERT_TABLE + my_format)

def __show_tables_request():
    request = "SHOW TABLES"
    cursor = my_sql.generate_cursor()
    cursor.execute(request)
    result = list()
    for x in cursor.fetchall():
        for y in x:
            result.append(y)
    cursor.close()
    return result

def create_alert_tab_script():
    # create
    query = __generate_alert_table_creation_query()
    cursor = my_sql.generate_cursor()
    cursor.execute(operation=query)
    cursor.close()

    # check
    result = __show_tables_request()
    if ALERT_TABLE_NAME in result:
        log.debug("{} table exists".format(ALERT_TABLE_NAME))
    else:
        log.error("{} table NOT created".format(ALERT_TABLE_NAME))
    my_sql.close()






if __name__ == '__main__':
    create_alert_tab_script()
