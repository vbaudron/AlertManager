#!/usr/bin/python3
# -*-coding:Utf-8 -*

from enum import Enum, auto, unique


@unique
class Period(Enum):
    DAY = 1     # 1 Day per DAY
    WEEK = 7    # 7 Days per WEEK
    MONTH = 30  # 30 Days per MONTH
