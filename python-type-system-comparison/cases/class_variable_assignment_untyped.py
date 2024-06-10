from typing import reveal_type

class A:
    attr = 1

a = A()
reveal_type(a.attr)
a.attr = 's'
reveal_type(a.attr)
