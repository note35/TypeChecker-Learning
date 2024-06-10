# TypeSystem-Learning

This package contains below sub-packages to guide you the Python type systems.

- python type system comparison
- mini type checker

## Python type system comparison

This package provides you a couple of assignment code examples, you can run the popular Python type systems to compare the behavior between them:
- Python runtime `reveal_type` (supported since Python3.11).
- mypy
- pytype
- pyright
- pyre-check

If you don't want to setup your own environment, try colab: https://colab.research.google.com/drive/1FVOSKpmbcEtye73u3I751AixmdtwMrQ2

### Steps

You need to setup the environment first:

```
cd python-type-system-comparison
sh env_setup.sh
```

You can run the commands like below to play around test cases:

```
./env/bin/python3.11 runner.py -f cases/class_variable_assignment_untyped.py

>>> python runtime <<<
Runtime type is 'int'
Runtime type is 'str'
>>> mypy <<<
cases/class_variable_assignment_untyped.py:7: note: Revealed type is "builtins.int"
cases/class_variable_assignment_untyped.py:8: error: Incompatible types in assignment (expression has type "str", variable has type "int")  [assignment]
cases/class_variable_assignment_untyped.py:9: note: Revealed type is "builtins.int"
Found 1 error in 1 file (checked 1 source file)
>>> pytype <<<
...
```

## Mini type checker

This package contains a mini type checker that generates the same output as mypy for all the given input test cases.

You need to setup the environment first:

If you don't want to setup your own environment, try colab: https://colab.research.google.com/drive/1CeAyqWqADtrW6ASiDmigUpGwhK0F1Ul2

### Steps

```
cd mini-type-checker
sh env_setup.sh
```

You can run the commands like below to play around test cases:

```
./env/bin/python3.11 mini_type_checker.py -f cases/arg_type_typed_ng.py

>>> mypy <<<
cases/arg_type_typed_ng.py:4: error: Argument 1 to "add_one" has incompatible type "str"; expected "int"  [arg-type]
Found 1 error in 1 file (checked 1 source file)
>>> mini python type checker <<<
Argument 1 to "add_one" has incompatible type "str"; expected "int"  [arg-type]
```
