from model.alert import my_sql

from model.utils import ALERT_MANAGER_TABLE_NAME


def erase_data_in_alert_manager_table():
    query = "DELETE FROM {}".format(ALERT_MANAGER_TABLE_NAME)
    print(query)
    my_sql.execute_and_close(query=query)

if __name__ == '__main__':
    erase_data_in_alert_manager_table()