from typing import *
import operator
import time

from systeme.variable import Variable

class Instruction:
    """A prototype class used to forge simple instructions like +, -, *, /, = (assigning).
    
    If the instruction belongs to these types : {str, int, Variable},
    then it gets converted to an instance of Instruction.

    Respectfully, x being the given command :
        - str => Read(Variable[x])
        - int => Constant(x)
        - Variable => Read(x)
    """

    def __init__(self, *args, **kwargs):
        """Every arguments such as instances of Variable, etc...

        Raises:
            NotImplementedError: Shall be overwritten.
        """
        raise NotImplementedError()

    def execute(*args, **kwargs) -> int:
        """Execute the instructions recursively.

        Raises:
            NotImplementedError: Shall be overwritten.

        Returns:
            int: The value of the instruction.
        """
        raise NotImplementedError()

class Sleep(Instruction):
    def __init__(self, seconds:int):
        self.seconds = seconds

    def __str__(self) -> str:
        return 'Sleep({})'.format(self.seconds)

    def execute(self):
        time.sleep(self.seconds)

class Constant(Instruction):
    """Represents a simple integer as an Instruction.
    """
    def __init__(self, value:int):
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    def execute(self) -> int:
        return self.value

class Read(Instruction):
    def __init__(self, variable:Variable):
        self.variable = variable

    def __str__(self) -> str:
        return self.variable.name
    
    def execute(self) -> int:
        return int(self.variable)

def convert_to_variable(variable:Union[Variable, str, None]) -> Union[Variable, None]:
    """Convert a string to a variable."""

    if isinstance(variable, str):
        variable = Variable[variable]
    elif variable is None: 
        pass
    elif not isinstance(variable, Variable):
        raise ValueError("Something else than a Variable() instance has been detected : {}.".format(variable))
    return variable

def convert_to_instruction(instruction:Union[Variable, Instruction, str, int]) -> Instruction:
    """Convert a variable, an integer, a string to an instruction."""

    if isinstance(instruction, Variable) or isinstance(instruction, str):
        # Attempt to read the given variable
        # to convert it to a variable
        # then to an instruction
        instruction = Read(convert_to_variable(instruction))
    elif isinstance(instruction, int):
        # Transform the integer to a Constant
        instruction = Constant(instruction)
    return instruction

class Assign(Instruction):
    """Implements the assigning operation.
    
    This class can be used in the following ways :
    
        Assign(Variable('x'), 10)
        Assign('x', 10)

        Assign('y', 20)
        Assign('x', 'y')

    Suppose the second variable has already been initialized (= contains a value).
    These are equivalent :

        Assign('x', Variable('y'))
        Assign(Variable('x'), 'y')
        Assign(Variable('x'), Variable('y'))
    """

    def __init__(self, variable:Union[Variable, str], instruction:Union[Variable, Instruction, str, int]):
        self.variable = convert_to_variable(variable)

        instruction = convert_to_instruction(instruction)
        if isinstance(instruction, Sleep):
            raise ValueError('Assign() is not intended to work with Sleep().')
        self.instruction = instruction
    
    def __str__(self) -> str:
        i = str(self.instruction)
        if isinstance(self.instruction, Operator):
            i = '({})'.format(i)
        return '{} = {}'.format(self.variable.name, i)

    def execute(self):
        value = self.instruction.execute()
        self.variable.value = value

########################################
# Operators
########################################
class Operator(Instruction):
    def __init__(self, i1:Union[Variable, Instruction, str, int], i2:Union[Variable, Instruction, str, int], operation:Callable[[int, int], int], variable:Optional[Union[Variable, str]]=None):
        """Initialize a prototype type later used for basic operations like +, -, /, *.

        Args:
            i1 (Variable, Instruction, int]): First "instruction". May be converted, depending of its type.
            i2 (Variable, Instruction, int]): Second "instruction". May be converted, depending of its type.
            operation (Callable[[int, int], int]): A function that mimics basic operations.
            variable (Optional[Variable], optional): The variable where the result will be stored in. If no one is provided, only the result will be returned in __call__(). Otherwise, the variable will be returned.
        """
        self.variable = convert_to_variable(variable)
        self.operation = operation
        self.i1 = self.__convert(i1)
        self.i2 = self.__convert(i2)

    def __str__(self) -> str:
        i1 = str(self.i1)
        i2 = str(self.i2)

        if isinstance(self.i1, Operator):
            i1 = '({})'.format(i1)
        if isinstance(self.i2, Operator):
            i2 = '({})'.format(i2)

        if self.operation == operator.add:
            op = '+'
        elif self.operation == operator.sub:
            op = '-'
        elif self.operation == operator.floordiv:
            op = '/'
        elif self.operation == operator.mul:
            op = '*'

        if not self.variable:
            return '({} {} {})'.format(i1, op, i2)
        else:
            return '{} = {} {} {}'.format(self.variable.name , i1, op, i2)

    def execute(self) -> Union[Variable, int] :
        """Returns a variable or a int.
        
        In the latter case, no variable has been provided to store the result.
        Used when nesting operations inside outer ones like this (althought it is possible to store the nested result in a variable then read the variable just after) :

            Add('z', Add(10, 10), 'y')
            Add('z', Add(10, 10, 'n'), 'y')

        Returns:
            Union[Variable, int]: Returns a variable to store the result. Otherwise an integer.
        """
        value = self.operation(int(self.i1.execute()), int(self.i2.execute()))
        if not self.variable:
            return value

        self.variable.value = value
        return self.variable

    def __convert(self, instruction:Union[Variable, Instruction, str, int]) -> Instruction:
        instruction = convert_to_instruction(instruction)
        if isinstance(instruction, Assign):
            raise ValueError("You cannot assign while performing operations.")
        if isinstance(instruction, Sleep):
            raise ValueError("Sleeping is not an instruction compatible with basic operations.")
        return instruction

class Add(Operator):
    def __init__(self, i1:Union[Variable, Instruction, str, int], i2:Union[Variable, Instruction, str, int], variable:Optional[Union[Variable, str]]=None):
        super().__init__(i1, i2, operator.add, variable)

class Sub(Operator):
    def __init__(self, i1:Union[Variable, Instruction, str, int], i2:Union[Variable, Instruction, str, int], variable:Optional[Union[Variable, str]]=None):
        super().__init__(i1, i2, operator.add, variable)

class Mul(Operator):
    def __init__(self, i1:Union[Variable, Instruction, str, int], i2:Union[Variable, Instruction, str, int], variable:Optional[Union[Variable, str]]=None):
        super().__init__(i1, i2, operator.mul, variable)

class Div(Operator):
    def __init__(self, i1:Union[Variable, Instruction, str, int], i2:Union[Variable, Instruction, str, int], variable:Optional[Union[Variable, str]]=None):
        super().__init__(i1, i2, operator.floordiv, variable)