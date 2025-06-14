import os
import time

d = time.time()

a = os.getcwd()

a = 1
b = 2  # noqa

if a == b:
    print("hi")


def abc(a, b):
    """_summary_

    Parameters
    ----------
    a : _type_
        _description_
    b : _type_
        _description_

    Returns
    -------
    _type_
        _description_
    """
    return a + b
