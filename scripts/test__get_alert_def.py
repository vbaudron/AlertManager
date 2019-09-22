from model.alert import AlertDefinitionStatus
from model.utils import DEFINITION_TABLE_NAME, my_sql

QUERY = "select d.*, n.*, c.*, dm.meter_id from alert_definition d, alert_notification n, alert_calculator c, alert_definition_meter dm WHERE d.status=1 INNER JOIN d.id="

QUERY = 'select d.*, n.period_unit "notification_period_unit", n.period_quantity "notification_period_quantity", n.email "notification_email", n.days_flag "notification_days", n.hours_flag "notification_hours", c.operator, c.comparator, c.data_period_type, c.data_period_quantity, c.data_period_unit, c.value_type, c.value_number, c.value_period_quantity, c.value_period_unit, dm.meter_id from alert_definition d LEFT JOIN alert_definition_meter dm ON d.id=dm.alert_definition_id LEFT JOIN alert_notification n ON d.notification_id=n.id LEFT jOIN alert_calculator c ON d.calculator_id=c.id'

cursor = my_sql.generate_cursor()
cursor.execute(operation=QUERY)

column_names = cursor.column_names
results = cursor.fetchall()

tmp = {}

for result in results:
    i = 0
    id_def = result[0]
    if id_def not in tmp.keys():
        tmp[id_def] = {}
        tmp[id_def]["meter_ids"] = []
    while i < len(column_names):
        if column_names[i] == "meter_id":
            tmp[id_def]["meter_ids"].append(result[i])
        else:
            tmp[id_def][column_names[i]] = result[i]
        i += 1
    print("tmp\n", tmp)

print(tmp)

alert_def = []

for key in tmp.keys():
    alert_def.append(tmp[key])

print("_____________________________________ ALERT DEF ARRAY")
for a in alert_def:
    print(a)


