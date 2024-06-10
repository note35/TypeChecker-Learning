from typing import TypeVar
from copy import deepcopy

T = TypeVar("T")

def f(x: T) -> T:
    return deepcopy(x)

x: int = 1
copy_x: str = f(1)
