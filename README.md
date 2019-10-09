# Script to create SQL tables needed

[see script](https://github.com/SOFTEE-AHU/AlertManager/blob/master/scripts/alert_tables_creation.py)

[see tables details](https://github.com/SOFTEE-AHU/AlertManager/blob/master/model/utils.py#L270)


# INSTALL

## Install
This project is using ```python3```, so first of all make sure to have python3 installed.

You will also need ```pip```.

You have to setup a virtual environment to start AlertManager, there is plenty of doc about that ([Google me virtualenv](https://www.google.com/search?sxsrf=ACYBGNQhqRdtRpoAE-hmVKh72Dfy6yxMwQ%3A1570618422253&ei=NrydXcGXD7vKgweT04rQDg&q=virtualenv+python3&oq=virtualenv+python3&gs_l=psy-ab.3..0l2j0i203l8.24311.24311..24616...0.5..0.84.84.1......0....1..gws-wiz.......0i71.PW59HbLjjmw&ved=0ahUKEwjBiovJgY_lAhU75eAKHZOpAuoQ4dUDCAs&uact=5))


git clone the project and go into the freshly created virtualenv.

once you're in the git folder you have to install requirements :
```pip3 install -r requirements.txt```

## Launch
You can **Start AlertManager** :
```python3 main.py```

## Other scripts
Existing [scripts](https://github.com/SOFTEE-AHU/AlertManager/blob/master/scripts/) can be launch :
```python3 main.py scripts/<script_name>```

# Explaining main objects & general behaviour

## AlertManager
__Provide a static method to start the script__
```python
@staticmethod
def start(alert_definition_id=None):
    alert_manager = AlertManager(alert_definition_id=alert_definition_id)
    alert_manager.start_check()
    alert_manager.save()
```
Alert manager will create `AlertDefinition` Objects based on the json array from *alert_definitions.json* file.
For each AlerDefinition it will check if we are in alert situation, and then save back the object updated.
if an `alert_definition_id` is passed as parameter, only htis alert_definition will be create and checked.

`FILENAME = "alert_definitions.json"`

### Init
Fill its `alert_definition_list` attribute with `AlertDefinition` from the DB table

### Start
Execute check method of each `AlertDefinition` object

### Save
save time of `AlertManager` in db



## AlertDefinition

### Init
Based on table *alert_definition*

### Level
```python
@unique
class Level(Enum):
    LOW = 0
    HIGH = 1
```

### Status
```python
# STATUS
@unique
class AlertStatus(Enum):
    ARCHIVE = 0
    CURRENT = 1
```

### Meter Id
This is the list of the meter id (the primary key from the table *BI_COMPTEURS*) concerned by the alertDefinition.

### Last Check
It represent the last time the Alert Definition has been checked
will be fill by the Alert manager, the front does not care
it is a `string` based on the ISO8601 `datetime`


### Check method
```python
def check(today: datetime) -> None:
        if self.calculator.is_alert_situation():
            # CREATE ALERT
            if self.notification.is_notification_allowed(datetime_to_check=today):
                # NOTIFY
```

## AlertCalculator
It will be use to see if we are in an alert situation. Is is based on the *alert_calculator* table

### Init

```python 
def __init__(self,
                 operator: str,
                 comparator: str,
                 data_period_type: str,
                 data_period_quantity: int,
                 data_period_unit: str,
                 value_type: str,
                 value_number: float,
                 value_period_type: str,
                 hour_start: int,
                 hour_end: int,
                 acceptable_diff: bool,
                 last_check: datetime,
                 today: datetime)
```

#### Data
Represent the data to check in database.
This is how to calculate data we want to compare
It will be an `AlertData` object

#### Value
Represent the value to compare with.
Data will be compare to Value thanks to a Comparator.

#### Operator
Operator is the way the array of data will be handle
```python
class MyOperator(Enum):  # Simplified for explanation
    MAX = find_max
    MIN = find_min
    AVERAGE = calculate_average
 ```
 
 #### Comparator
 Comparator is the way Data will be compare to Value
```python
class MyComparator(Enum):  # Simplified for explanation
    SUP = is_sup, new_sup_value
    INF = is_inf, new_inf_value
    EQUAL = equal, new_equal_value
 ```
 
 #### Acceptable_diff
 This is a `bool`.
 if Acceptable_diff:
    the value to compare with will be be replace by a pourcentage of this value (manage by Comparator with `new_xxx_value` functions). `True` means this is a "*seuil*" alert definition
 
 ### Is Alert Situation method
 ```python 
 def is_alert_situation(self) -> bool:
    data_from_db = self.alert_data.get_all_data_in_db(meter_id=meter_id, is_index=is_index)
    self.__data = self.__operator.calculate(data_from_db)
    self.__value = self.__get_value(meter_id=meter_id, is_index=is_index)
    return self.comparator.compare(self.data, self.value)
 ```
 is the method called to calculate if we are in alert situation. 
Return result of Data Value comparaison (understand, is DATA comparator VALUE)

## AlertData
this will generate the data that we have to compare.
it will request in the database the list of value for a certain period.

### Init
 ```python 
   def __init__(self,
                 data_period_type: str,
                 data_period_quantity: int,
                 data_period_unit: str,
                 hour_start: int,
                 hour_end: int,
                 last_check: datetime,
                 today: datetime)
```
#### Period Generator Type
Has a `data_period_generator: PeriodGenerator` attribute that will generate the pertinent period
```python
class PeriodGeneratorType(Enum):
    LAST_CHECK = auto()  # this will give the period since the last AlertManager check
    USER_BASED = auto()  # this will give the period asked by the User --> in json
```

#### Data Period Generator
Exists only IF
```python
period_generator_type is PeriodGenerator.USER_BASED
```

```python
data_period_quantity: int
data_period_unit: str
```
Will generate the pertinent period to get value in database.

#### Period Unit

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

## Alert Value
This represents how we get the Value that will be compare to Data

### Init
```
def __init__(self, value_type: str, value_number: float)
 ```
    
#### Value Generator Type
```pyhton
 @unique
class ValueGeneratorType(Enum):
    USER_BASED_VALUE = auto()        # No Period Required - Value will be value_number
    SIMPLE_DB_BASED_VALUE = auto()   # No Period Required - Value will be found in database 
    PERIOD_BASED_VALUE = auto()      # Period Required --> value_period
 ```
 
#### Value Number
 It is the basic value. 
 - In some case it is the value itself 
 case : ValueGeneratorType.USER_BASED_VALUE
 - It can also be a pourcentage to apply to value
 case : acceptable_diff and value_type is SIMPLE_DB_BASED_VALUE
 
#### Value Period Type
when  ```python value_type is ValueGeneratorType.PERIOD_BASED_VALUE``` value_period_type can not be null (ConfigError)
```pyhton
@unique
class ValuePeriodType(Enum):
    LAST_YEAR = auto()
    LAST_DATA_PERIOD = auto()
 ```
 
WARNING :  USER_BASED_VALUE and acceptable_diff are non coherent raise a ConfigError
 

