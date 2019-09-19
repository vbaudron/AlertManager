from model.utils import TableToGenerate, ALERT_TABLE_NAME, ALERT_FOREIGN_KEY, ALERT_TABLE_COMPO, NOTIFICATION_NAME, \
    NOTIFICATION_COMPO, DEFINITION_TABLE_NAME, DEFINITON_ALERT_FOREIGN_KEY, DEFINITION_COMPO, CALCULATOR_NAME, \
    CALCULATOR_COMPO, METER_DEFINITIONS_ALERT_TABLE_NAME, METER_DEFINITION_COMPO, \
    METER_DEFINITION_ALERT_FOREIGN_KEY

# NOTIFICATION
notification_table = TableToGenerate(
    table_name=NOTIFICATION_NAME,
    compo=NOTIFICATION_COMPO,
    foreign_keys=None
)


# CALCULATOR
calculator_table = TableToGenerate(
    table_name=CALCULATOR_NAME,
    compo=CALCULATOR_COMPO,
    foreign_keys=None
)


# DEFINITION
definition_table = TableToGenerate(
    table_name=DEFINITION_TABLE_NAME,
    compo=DEFINITION_COMPO,
    foreign_keys=DEFINITON_ALERT_FOREIGN_KEY
)

# ALERT
alert_table = TableToGenerate(
    table_name=ALERT_TABLE_NAME,
    compo=ALERT_TABLE_COMPO,
    foreign_keys=ALERT_FOREIGN_KEY
)

definition_meter_table = TableToGenerate(
    table_name=METER_DEFINITIONS_ALERT_TABLE_NAME,
    compo=METER_DEFINITION_COMPO,
    foreign_keys=METER_DEFINITION_ALERT_FOREIGN_KEY
)

# CREATE TABLES
if __name__ == '__main__':

    tables = [
        notification_table,
        calculator_table,
        definition_table,
        alert_table,
        definition_meter_table
    ]

    for table in tables:
        print(table, " start creation ...")
        table.request_table_creation()

