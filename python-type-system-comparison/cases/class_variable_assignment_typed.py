from typing import reveal_type

class A:
    attr: int|str = 1

a = A()
reveal_type(a.attr)
a.attr = 's'
reveal_type(a.attr)
