from model.AlertEnum.Period import Period


class Notification:

    def __init__(self, number=1, period=Period.DAY, email=None):
        self.__number = number
        self.__period = period
        self.__email = email

    def is_notification_allowed(self, previous, datetime_to_check):
        """
        check if we are allowed to send a new notification

        :param previous: datetime of the last notification
        :type previous: datetime
        :param datetime_to_check the date you want to check
        :type datetime_to_check: datetime

        """

        delta = datetime_to_check - previous

        count = delta.days
        if self.__period is Period.WEEK:
            count = count / 7
        elif self.__period is Period.MONTH:
            count = count / 30

        return count >= self.__number
