from abc import ABC
import calendar


class DateUtils(ABC):
    @staticmethod
    def get_day_name(datetime):
        return calendar.day_name[datetime.weekday()]


if __name__ == '__main__':
    for i in range(0, 7):
        print(calendar.day_name[i])
