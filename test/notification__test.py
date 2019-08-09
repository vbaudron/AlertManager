from datetime import datetime, timedelta

import unittest

from model.notification import Notification, NotificationPeriod


class NotificationTest(unittest.TestCase):

    def test__is_notification_allowed(self):
        today = datetime(2019, 7, 29)
        yesterday = datetime(2019, 7, 28)
        twenty_days_ago = datetime(2019, 7, 9)
        fourty_days_ago = today - timedelta(days=40)

        # 2 DAY
        notification = Notification(number=2)
        self.assertFalse(notification.is_notification_allowed(yesterday, today))
        self.assertTrue(notification.is_notification_allowed(twenty_days_ago, today))

        notification = Notification(number=1, period=NotificationPeriod.MONTH)
        self.assertFalse(notification.is_notification_allowed(yesterday, today))
        self.assertFalse(notification.is_notification_allowed(twenty_days_ago, today))
        self.assertTrue(notification.is_notification_allowed(fourty_days_ago, today))



