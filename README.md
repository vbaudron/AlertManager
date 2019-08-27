# AlertManager
__Provide a static method to start the script__
```python
@staticmethod
    def start_manager():
        alert_manager = AlertManager()
        alert_manager.start()
        alert_manager.save()
```
Alert manager will create `AlertDefinition` Objects based on the json array from *alert_definitions.json* file.
For each AlerDefinition it will check if we are in alert situation, and then save back the object updated

`FILENAME = "alert_definitions.json"`

## Init
Fill its `alert_definition_list` attribute with `AlertDefinition` instances based on the JsonFile

## Start
Execute check method of each `AlertDefinition` object

## Save
save the current `AlertDefinition` object to the *alert_definitions.json* file. 



# AlertDefinition

## Init
Based on json to python `dict`
```python
setup = 
{
  "name": "alertDefinition3",
  "id": "id_3",
  "sensor_ids" : [],
  "description" : "i am supposed to describe the Alert definition",
  "level" : "LOW",
  "category_id": "category_1",
  "last_check": "2019-08-27T08:42:07.962728",
  "flags": [],
  "notification": {},     # AlertNotification
  "calculator": {}        # AlertCalculator
}
```

### Level
```python
@unique
class Level(Enum):
    LOW = 0
    HIGH = auto()
```

### Flag
```python
@unique
class AlertDefinitionFlag(Flag):
    INACTIVE = 0           # Nothing
    ACTIVE = auto()        # Replace status
```

### Last Check
It represent the last time the Alert Definition has been checked
will be fill by the Alert manager, the front does not care
it is a `string` based on the ISO8601 `datetime`


## Check method
```python
def check(today: datetime) -> None:
        if self.calculator.is_alert_situation():
            # CREATE ALERT
            if self.notification.is_notification_allowed(datetime_to_check=today):
                # NOTIFY
```

# AlertCalculator
It will be use to see if we are in an alert situation.

## Init

```python 
def __init__(self, setup: dict, last_check: datetime, today: datetime):
  
```

based on dict from `setup["calculator"]`

```python
  {
    "data": {},         # AlertData
    "value": {},        # AlertValue
    "comparator": "SUP",
    "operator": "MAX",
    "acceptable_diff" : True
    }
```

### Data
Represent the data to check in database.
This is how to calculate data we want to compare
It will be an `AlertData` object

### Value
Represent the value to compare with.
Data will be compare to Value thanks to a Comparator.

### Operator
Operator is the way the array of data will be handle
```python
class MyOperator(Enum):  # Simplified for explanation
    MAX = find_max
    MIN = find_min
    AVERAGE = calculate_average
 ```
 
 ### Comparator
 Comparator is the way Data will be compare to Value
```python
class MyComparator(Enum):  # Simplified for explanation
    SUP = is_sup, new_sup_value
    INF = is_inf, new_inf_value
    EQUAL = equal, new_equal_value
 ```
 
 ### Acceptable_diff
 This is a `bool`.
 if Acceptable_diff:
    the value to compare with will be be replace by a pourcentage of this value (manage by Comparator with `new_xxx_value` functions). `True` means this is a "*seuil*" alert definition
 
 ## Is Alert Situation method
 ```python 
 def is_alert_situation(self) -> bool:
    self.__data = self.__operator.calculate(self.alert_data.get_all_data_in_db())
    self.__value = self.__get_value()
    return self.comparator.compare(self.data, self.value)
 ```
 is the method called to calculate if we are in alert situation. 
Return result of the comparaison between Data and Value

# AlertData
this will generate the data that we have to compare.
it will request in the database the list of value for a certain period.

## Init
 ```python 
"data": {
      "data_period_type" : "LAST_CHECK",
      "data_period": {} # Existence depends on period_generator_type
    }
```
### Period Generator Type
Has a `data_period_generator: PeriodGenerator` attribute that will generate the pertinent period
```python
class PeriodGeneratorType(Enum):
    LAST_CHECK = auto()  # this will give the period since the last AlertManager check
    USER_BASED = auto()  # this will give the period asked by the User --> in json
```

### Data Period Generator
Exists only IF
```python
period_generator_type is PeriodGenerator.USER_BASED
```

```python
"data_period": {
        "quantity": 2,
        "unit": "WEEK"
      }
```
Will generate the pertinent period to get value in database.

# Period Unit

```pyhton
class PeriodUnitDefinition(Enum):
    """
       Represents units of period available
       value : represent the String associated to the period - it is the KEY in json file
       go_past : it is the method associated to calculate the start date from the end_date
   """
    DAY = "DAY", go_past_with_days
    WEEK = "WEEK", go_past_with_weeks
    MONTH = "MONTH", go_past_with_months
    YEAR = "YEAR", go_past_with_years
```

# Alert Value
This represents how we get the Value that will be compare to Data

## Init
```
"value": {
      "value_type": "PERIOD_BASED_VALUE",
      "value_number": 15,
      "value_period": {} # Existence depends on value_type
    }
 ```
    
 ### Value Generator Type
```
 @unique
class ValueGeneratorType(Enum):
    USER_BASED_VALUE = auto()        # No Period Required - Value will be value_number
    SIMPLE_DB_BASED_VALUE = auto()   # No Period Required - Value will be found in database 
    PERIOD_BASED_VALUE = auto()      # Period Required --> value_period
 ```
 
 ### Value Number
 It is the basic value. 
 - In some case it is the value itself 
 case : ValueGeneratorType.USER_BASED_VALUE
 - It can also be a pourcentage to apply to value
 case : acceptable_diff and value_type is SIMPLE_DB_BASED_VALUE
 
WARNING :  USER_BASED_VALUE and acceptable_diff are non coherent raise a ConfigError
 
 
