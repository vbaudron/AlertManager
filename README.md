# AlertManager

Alert manager will create ```AlertDefinition``` Objects based the json list from *alert_definitions.json* file.
For each AlerDefinition it will check if we are in alert situation

## AlertDefinition

### Init
Based on json a python ```dict```
```json
  {
    "name": "alertDefinition3",
  "id": "id_3",
  "description" : "i am supposed to describe the Alert definition",
  "level" : "LOW",
  "flags": [
    "ACTIVE"
  ],
  "previous_notification": null,
    "calculator": {},
    "notification": {}
  }
```

#### Level
```python
@unique
class Level(Enum):
    LOW = 0
    HIGH = auto()
```

#### Flag
```python
@unique
class AlertDefinitionFlag(Flag):
    INACTIVE = 0           # Nothing
    ACTIVE = auto()        # Replace status
```

### Check if Alert situation
```python
def check(today: datetime) -> None:
        if self.calculator.is_alert_situation():
            # TODO CREATE ALERT
            if self.notification.is_notification_allowed(datetime_to_check=today):
                # TODO NOTIFY
```

