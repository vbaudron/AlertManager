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
        # get Time between both date
        delta = datetime_to_check - previous

        # Get day divided by nb_day in period (equivalent values)
        count = delta.days / self.__period.value

        return count >= self.__number
