#!/usr/bin/python3
# -*-coding:Utf-8 -*

from enum import Enum, auto, unique


@unique
class Period(Enum):
    DAY = auto(),
    WEEK = auto()
    MONTH = auto()