from model.utils import TableToGenerate, ALERT_TABLE_NAME, ALERT_FOREIGN_KEY, ALERT_TABLE_COMPO, NOTIFICATION_NAME, \
    NOTIFICATION_COMPO, DEFINITION_TABLE_NAME, DEFINITON_ALERT_FOREIGN_KEY, DEFINITION_COMPO, CALCULATOR_NAME, \
    CALCULATOR_COMPO, METER_DEFINITIONS_ALERT_TABLE_NAME, METER_DEFINITION_COMPO, \
    METER_DEFINITION_ALERT_FOREIGN_KEY, ALERT_DEFINITION_NOTIFICATION_TIME, ALERT_DEFINITION_NOTIFICATION_TIME_COMPO, \
    ALERT_DEFINITION_NOTIFICATION_TIME_FOREIGN_KEY, ALERT_MANAGER_TABLE_NAME, ALERT_MANAGER_TABLE_COMPO

# NOTIFICATION
alert_notification_table = TableToGenerate(
    table_name=NOTIFICATION_NAME,
    compo=NOTIFICATION_COMPO,
    foreign_keys=None
)


# CALCULATOR
alert_calculator_table = TableToGenerate(
    table_name=CALCULATOR_NAME,
    compo=CALCULATOR_COMPO,
    foreign_keys=None
)


# DEFINITION
alert_definition_table = TableToGenerate(
    table_name=DEFINITION_TABLE_NAME,
    compo=DEFINITION_COMPO,
    foreign_keys=DEFINITON_ALERT_FOREIGN_KEY
)

# ALERT
alert_alert_table = TableToGenerate(
    table_name=ALERT_TABLE_NAME,
    compo=ALERT_TABLE_COMPO,
    foreign_keys=ALERT_FOREIGN_KEY
)

# ALERT_DEFINITION METER
alert_definition_meter_table = TableToGenerate(
    table_name=METER_DEFINITIONS_ALERT_TABLE_NAME,
    compo=METER_DEFINITION_COMPO,
    foreign_keys=METER_DEFINITION_ALERT_FOREIGN_KEY
)

# ALERT_DEFINITION NOTIFICATION TIME

alert_definition_notification_table = TableToGenerate(
    table_name=ALERT_DEFINITION_NOTIFICATION_TIME,
    compo=ALERT_DEFINITION_NOTIFICATION_TIME_COMPO,
    foreign_keys=ALERT_DEFINITION_NOTIFICATION_TIME_FOREIGN_KEY
)

alert_manager_table = TableToGenerate(
    table_name=ALERT_MANAGER_TABLE_NAME,
    compo=ALERT_MANAGER_TABLE_COMPO
)


# CREATE TABLES
def create_alert_related_tables():
    tables = [
        alert_notification_table,
        alert_calculator_table,
        alert_definition_table,
        alert_alert_table,
        alert_definition_meter_table,
        alert_definition_notification_table,
        alert_manager_table
    ]

    for table in tables:
        print("\n", table, " start creation ... ")
        table.request_table_creation()


# CREATE TABLES
if __name__ == '__main__':
    create_alert_related_tables()


