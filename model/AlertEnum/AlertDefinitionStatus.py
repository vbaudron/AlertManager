#!/usr/bin/python3
# -*-coding:Utf-8 -*

from enum import Enum, auto, unique


@unique
class AlertDefinitionStatus(Enum):
    INACTIVE = 0
    ACTIVE = auto()
    ARCHIVE = auto()
