#!/usr/bin/python3
# -*-coding:Utf-8 -*

from model.day import Day

import unittest

from model.tokill.my_decorator import controller_types


class MyDecoratorTest(unittest.TestCase):

    def test_controllerTypes(self):
        # BASIC function : One Single Args
        self.controller_types_function_test_simple(int(5))
        self.assertRaises(TypeError, self.controller_types_function_test_simple("hello"))

        # MULTIPLE function : Many Args
        self.controller_types_function_test_simple(5, "hello", Day.SATURDAY)
        self.assertRaises(TypeError, self.controller_types_function_test_simple(5, "hello", "SATURDAY"))
        self.assertRaises(TypeError, self.controller_types_function_test_simple(5, Day.MONDAY, Day.SATURDAY))
        self.assertRaises(TypeError, self.controller_types_function_test_simple(Day.SATURDAY, "hello", Day.SATURDAY))

    # FUNCTIONS TESTS
    @controller_types(type(self), int)
    def controller_types_function_test_simple(self, my_number):
        print(my_number, " type : ", type(my_number))

    @controller_types(unittest.TestCase, int, str, Day)
    def controller_types_function_test_multiple(self, my_number):
        print(my_number, " type : ", type(my_number))


if __name__ == '__main__':
    unittest.main()
