import calendar
import json
from abc import ABC
from enum import Enum


def get_day_name_from_datetime(datetime):
    return calendar.day_name[datetime.weekday()]


def get_dict_from_json_file(file_path_name):
    with open(file_path_name, 'r') as f:
        my_dict = json.load(f)
    return my_dict






if __name__ == '__main__':
    for i in range(0, 7):
        print(calendar.day_name[i])
