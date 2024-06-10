import argparse
import os

import libcst as cst


ANY_TYPE = 'any'
INT_TYPE = 'int'
STR_TYPE = 'str'


class SemanticAnalyzer:
    """ A just-enough semantic analyzer for the type checker to reproduce the
        same output mypy generated for the unit tests. """

    # Class variables to keep the top-level type information.
    # This is very rough, and unable to handle nested functions and classes.
    GENERICS_TYPE_INFO: dict
    FUNCTION_TYPE_INFO: dict
    VARIABLE_TYPE_INFO: dict

    def __init__(self):
        self.GENERICS_TYPE_INFO = {}
        self.FUNCTION_TYPE_INFO = {}
        self.VARIABLE_TYPE_INFO = {}
        self.done = False  # to indicate the analyzer has scanned the codee.

    def debug(self):
        print("generics: ", self.GENERICS_TYPE_INFO)
        print("function: ", self.FUNCTION_TYPE_INFO)
        print("variable: ", self.VARIABLE_TYPE_INFO)

    def _analyze_annotation(self, node: cst.Annotation):
        return node.annotation.value if isinstance(node, cst.Annotation) else ANY_TYPE

    def _analyze_function_def(self, node: cst.FunctionDef):
        function_def_body = node.body.body
        for node_in_function_def_body in function_def_body:
            if isinstance(node_in_function_def_body, cst.SimpleStatementLine):
                self._analyze_simple_statement_line(node_in_function_def_body)
            else:
                raise NotImplementedError(f'Unsupported node type: {type(node)}')
        # handle function type consistency infos.
        function_def_params = node.params.params
        self.FUNCTION_TYPE_INFO[node.name.value] = {
            "args": [(param.name.value, self._analyze_annotation(param.annotation)) for param in function_def_params],
            "return": self._analyze_annotation(node.returns),
        }

    def _analyze_simple_statement_line(self, node: cst.SimpleStatementLine):
        # only 0 index of SimpleStatementLine's body has type info.
        body = node.body[0]
        if isinstance(body, cst.Assign):
            # handle unnotated TypeVar.
            # this is hacky as we know the test case's TypeVar defined by Assign node.
            if body.value.func.value == 'TypeVar':
                variable_key = body.targets[0].target.value
                # another hacky eval to identify the value.
                variable_value = eval(body.value.args[0].value.value)
                self.GENERICS_TYPE_INFO[variable_key] = variable_value
            else:
                # skip unannotated "assignment".
                pass
        elif isinstance(body, cst.AnnAssign):
            # handle variable type consistency infos.
            self.VARIABLE_TYPE_INFO[body.target.value] = self._analyze_annotation(body.annotation)
        elif isinstance(body, cst.Return):
            # left "return" for type checker.
            pass
        elif isinstance(body, cst.Expr):
            # left "expression" for type checker.
            # e.g., function call, variable assignment.
            pass
        elif isinstance(body, cst.ImportFrom):
            # skip "import".
            pass
        else:
            raise NotImplementedError(f'Unsupported node type: {type(body)}')

    def analyze(self, root: cst.CSTNode):
        """ semantic analyze the code and store the type information into class variables. """
        for node in root.body:
            if isinstance(node, cst.SimpleStatementLine):
                self._analyze_simple_statement_line(node)
            elif isinstance(node, cst.FunctionDef):
                self._analyze_function_def(node)
            else:
                raise NotImplementedError(f'Unsupported node type: {type(node)}.')
        self.done = True


arg_type_error_tmpl = 'Argument {} to "{}" has incompatible type "{}"; expected "{}"  [arg-type]'
assignment_error_tmpl = 'Incompatible types in assignment (expression has type "{}", variable has type "{}") [assignment]'
return_value_error_tmpl = 'Incompatible return value type (got "{}", expected "{}")  [return-value]'
operand_error_tmpl = 'Unsupported operand types for {} ("{}" and "{}")  [operator]'


class TypeChecker:
    """ A just-enough type checker to reproduce the same output mypy generated
        for the unit tests. """
    ANALYZER: SemanticAnalyzer

    def __init__(self, analyzer: SemanticAnalyzer):
        if not analyzer.done:
            raise RuntimeError("SemanticAnalyzer is not done yet.")
        self.ANALYZER = analyzer

    def _resolve_node(self, node):
        """ resolve the node into type for the consistency check.
        In this type checker, we roughly present types as string.
        """
        if isinstance(node, cst.Return):
            return self._resolve_node(node.value)
        if isinstance(node, cst.Add):
            return '+'
        if isinstance(node, cst.Integer):
            return INT_TYPE
        if isinstance(node, cst.SimpleString):
            return STR_TYPE
        if isinstance(node, cst.Call):
            func_name = node.func.value
            # Semantic analyzer has no such a type info.
            if func_name not in self.ANALYZER.FUNCTION_TYPE_INFO:       
                return ANY_TYPE
            return self.ANALYZER.FUNCTION_TYPE_INFO[func_name]['return']
        if isinstance(node, cst.Name):
            # TODO:
            # technically we can infer the name's type.
            # but we decide not to here for now.
            return ANY_TYPE
        if isinstance(node, cst.BinaryOperation):
            return self._check_and_resolve_binary_operation(node)
        return ANY_TYPE

    def _check_args(self, node):
        """ check the type consistency of a function call's arguments. """
        func_name = node.value.func.value

        # Semantic analyzer has no such a type info.
        if func_name not in self.ANALYZER.FUNCTION_TYPE_INFO:
            return

        for i, arg in enumerate(node.value.args):
            annotated_type = self.ANALYZER.FUNCTION_TYPE_INFO[func_name]['args'][i][1]
            if annotated_type == ANY_TYPE:
                # Any always pass the check.
                continue
            if annotated_type in self.ANALYZER.GENERICS_TYPE_INFO.values():
                # Generics types are checked in _check_return logic.
                continue

            # Actual checks
            if isinstance(arg.value, cst.SimpleString):
                if annotated_type != STR_TYPE:
                    print(arg_type_error_tmpl.format(
                        i+1,
                        func_name,
                        STR_TYPE,
                        annotated_type))
            elif isinstance(arg.value, cst.Integer):
                if annotated_type != INT_TYPE:
                    print(arg_type_error_tmpl.format(
                        i+1,
                        func_name,
                        INT_TYPE,
                        annotated_type))
            else:
                raise NotImplementedError(f'Unsupported node type: {type(arg.value)}.')

    def _check_return(self, node):
        """ check the type consistency of a function return's type. """
        func_name = node.value.func.value

        # Semantic analyzer has no such a type info.
        if func_name not in self.ANALYZER.FUNCTION_TYPE_INFO:       
            return

        annotated_return = self.ANALYZER.FUNCTION_TYPE_INFO[func_name]['return']

        # Generics type search + check.
        if annotated_return in self.ANALYZER.GENERICS_TYPE_INFO:
            typed_args = [arg.value for arg in node.value.args]
            annotated_args = self.ANALYZER.FUNCTION_TYPE_INFO[func_name]['args']

            # check if args has the same TypeVar
            actual_type = ANY_TYPE
            for i, annotation in enumerate(annotated_args):
                if annotation[1] == annotated_return:
                    if isinstance(typed_args[i], cst.Integer):
                        actual_type = INT_TYPE

            if self.ANALYZER.VARIABLE_TYPE_INFO[node.target.value] != actual_type:
                print(assignment_error_tmpl.format(
                    actual_type,
                    self.ANALYZER.VARIABLE_TYPE_INFO[node.target.value]))
            return

        # Return type check.
        if annotated_return != ANY_TYPE:
            if isinstance(node, cst.AnnAssign):
                actual_type = self.ANALYZER.VARIABLE_TYPE_INFO[node.target.value]
            elif isinstance(node, cst.Return):
                actual_type = self.ANALYZER.FUNCTION_TYPE_INFO[node.value.func.value]['return']  
            else:
                raise NotImplementedError(f'Unsupported node type: {type(node)}')

            if actual_type != annotated_return:
                print(assignment_error_tmpl.format(
                    annotated_return,
                    actual_type))

    def _check_call(self, node):
        """ check type consistency of a function call. """
        self._check_args(node)
        self._check_return(node)

    def _check_assignment(self, node):
        """ check type consistency for an annotated variable assignment. """
        if isinstance(node.value, cst.Integer):
            # check var: annotation = INT
            if self.ANALYZER.VARIABLE_TYPE_INFO[node.target.value] != INT_TYPE:
                print(assignment_error_tmpl.format(
                    INT_TYPE,
                    self.ANALYZER.VARIABLE_TYPE_INFO[node.target.value]))
        if isinstance(node.value, cst.Call):
            # check var: annotation = func(...)
            self._check_call(node)

    def _check_and_resolve_binary_operation(self, node):
        """ check type consistency for a binary operation. """
        operator = self._resolve_node(node.operator)
        left = self._resolve_node(node.left)
        right = self._resolve_node(node.right)
        if left is ANY_TYPE or right is ANY_TYPE:
            # Tentatively consider the ANY_TYPE the return type.
            return ANY_TYPE
        if left != right:
            print(operand_error_tmpl.format(
                operator,
                left,
                right))
        # Tentatively consider the left type the return type.
        return left

    def _check_simple_statement_line(self, node):
        """ check type consistency for a plain expression if needed.
        Support only AnnAssign and Call.
        """
        # only 0 index of SimpleStatementLine's body has type info.
        body = node.body[0]
        if isinstance(body, cst.AnnAssign):
            self._check_assignment(body)
        elif isinstance(body, cst.Expr) and isinstance(body.value, cst.Call):
            # check func(...)
            self._check_call(body)

    def _check_function_return(self, node):
        """ check type consistency for a return value annotated function. """
        function_name = node.name.value

        if function_name not in self.ANALYZER.FUNCTION_TYPE_INFO:
            # return value is not annotated.
            return

        # Find and compare "annotated type" and "actual type".
        annotated_return_type = self.ANALYZER.FUNCTION_TYPE_INFO[function_name]['return']
        actual_return_type = ANY_TYPE
        for _node in node.body.body:
            # only 0 index of SimpleStatementLine's body has type info. 
            if (isinstance(_node, cst.SimpleStatementLine) and
                isinstance(_node.body[0], cst.Return)):
                actual_return_type = self._resolve_node(_node.body[0])
                break
        if annotated_return_type == ANY_TYPE or actual_return_type == ANY_TYPE:
            return
        if annotated_return_type != actual_return_type:
            print(return_value_error_tmpl.format(
                actual_return_type,
                annotated_return_type))

    def _check_function_content(self, node):
        """ check type consistency of the plain code in a function. """
        self.check(node.body)

    def _check_function_def(self, node):
        """ check type consistency of a function. """
        self._check_function_content(node)
        self._check_function_return(node)

    def check(self, root: cst.CSTNode):
        """ check type consistency of the plain code.
        Support only the SimpleStatementLine and FunctionDef.
        """
        for node in root.body:
            if isinstance(node, cst.SimpleStatementLine):
                self._check_simple_statement_line(node)
            elif isinstance(node, cst.FunctionDef):
                self._check_function_def(node)
            else:
                raise NotImplementedError(f'Unsupported node type: {type(node)}.')


def run(target_file_name, debug=False):
    with open(f"./{target_file_name}", "r") as fptr:
        code = fptr.read()

    root_node: cst.CSTNode = cst.parse_module(code)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(root_node)

    if debug:
        analyzer.debug()

    checker = TypeChecker(analyzer)
    checker.check(root_node)



parser = argparse.ArgumentParser("Run code on mini python type checker")
parser.add_argument('-f', '--filename', help='The Python code to be type checked.')
args = parser.parse_args()

print('>>> mypy <<<')
os.system(f'./env/bin/mypy {args.filename}')
print('>>> mini python type checker <<<')
run(f'{args.filename}', debug=False)
