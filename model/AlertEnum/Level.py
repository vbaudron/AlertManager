#!/usr/bin/python3
# -*-coding:Utf-8 -*

from enum import Enum, auto, unique


@unique
class Level(Enum):
    LOW = 0
    HIGH = 1
