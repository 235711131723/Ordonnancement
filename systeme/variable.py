from typing import *
from uuid import uuid4

class Variable:
    VARIABLES = {}

    def __init__(self, name:str, value:Optional[int]=None):
        try:
            old = self.__class__.VARIABLES[name]
        except KeyError:
            old = None

        self.name = name
        self.history = (old.history if old else []) + [value]
        self._value = value

        # Add itself to the list of variables,
        # otherwise overwrite the existing one based on the name.
        self.__class__.VARIABLES[self.name] = self

    def __hash__(self) -> int:
        # It will be stored in set(), so it is needed to be hashable.
        return hash(self.name)

    def __eq__(self, o:Any) -> bool:
        # * Variables will be compared by their name
        if not isinstance(o, Variable):
            return False
        return self.name == o.name

    def __class_getitem__(cls, name:str) -> 'Variable':
        """The variables can be accessed like this :

            Variable[name]
        
        If it does not exist, it will be created.

        Args:
            name (str): The name of the variable.

        Returns:
            Variable: The searched variable, or a newly created variable (always non-initialized, which means no value is provided).
        """
        if name not in cls.VARIABLES.keys():
            return cls(name)
        return cls.VARIABLES[name]

    def __repr__(self) -> str:
        return '<Variable({}={})>'.format(self.name, self.value)

    def __int__(self) -> int:
        if not self.value:
            raise ValueError("The variable {} has not been initialized.".format(self))
        return int(self.value)

    def reset(self):
        """Un-set its value and empty the history.

        NOTE: It should be used only in the System() class.
        """
        self.value = None
        self.history = []

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, value:int):
        """Each time a value is affected to the variable,
        the previous one is stored in the history.
        """
        self._value = value
        self.history.append(value)