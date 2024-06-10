from typing import reveal_type

a: int|str = 1
reveal_type(a)
a = 's'
reveal_type(a)
