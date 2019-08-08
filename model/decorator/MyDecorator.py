

def controller_types(*a_args, **a_kwargs):
    """we expect to have types needed as parameters to check the function one with them"""

    def decorator(fonction_a_executer):
        """It will return the function modified"""

        def function_modified(*args, **kwargs):
            """The modified function. We will check that its parameters are as expected in the controller_type
            function """

            # Expected Params = a_args
            # Received Params = args

            print("A_ARGS")
            print(a_args)

            print("ARGS")
            print(args)

            print("A_kwargs")
            print(a_kwargs)

            print("kwargs")
            print(kwargs)

            if len(a_args) != len(args):
                raise TypeError("The number of params is not the one expected")
            # We check the list of params received but not named
            for i, arg in enumerate(args):
                print("arg : ", arg)
                print("a_arg : ", a_args[i])
                if not isinstance(args[i], type(a_args[i])):
                    raise TypeError("Argument {0} : {1} is not " \
                                    "{2}".format(i, args[i], type(a_args[i])))

            # We check the list of params received and named
            for cle in kwargs:
                if cle not in a_kwargs:
                    raise TypeError("l'argument {0} n'a aucun type " \
                                    "précisé".format(repr(cle)))
                if a_kwargs[cle] is not type(kwargs[cle]):
                    raise TypeError("l'argument {0} n'est pas de type" \
                                    "{1}".format(repr(cle), a_kwargs[cle]))
            return fonction_a_executer(*args, **kwargs)

        return function_modified

    return decorator
