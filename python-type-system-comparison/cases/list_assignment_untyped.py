from typing import reveal_type

a = [1]
reveal_type(a)
a.append('s')
reveal_type(a)
