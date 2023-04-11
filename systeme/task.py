from typing import *
from rich import print
from rich.panel import Panel
from rich.pretty import Pretty
from uuid import uuid4
import copy

from systeme.variable import Variable
from systeme.instruction import Instruction, Assign, Operator, Read, Constant

class Task:
    """A 'task' will consist of only simple instructions like :

        x = 10
        y = x
        z = x + y
        w = z - 10
        w = w / 10
        z = z * 10
    
    Here is an exemple of how to write instructions for a task :

        t = Task(instructions=[
            Assign('x', 10),
            Assign('y', 22),
            Add('x', 'y', 'z'),
            Sub('z', 40, 'z')
        ])
    """
    ID = 1

    def __init__(self,
        instructions:Optional[List[Instruction]] = None,
        dependencies:Optional[Union['Task', Iterable['Task']]]=None,
        name:Optional[Union[str, int]]=None
    ):
        if name is not None and isinstance(name, int):
            self.__class__.ID = name
        else:
            if not name:
                name = self.__class__.ID
                self.__class__.ID += 1

        self.name = name
        self.instructions = instructions if instructions else []
        self.dependencies = dependencies if dependencies else []
        self.executed = False

        self.read_domain = self.__get_read_domain()
        self.write_domain = self.__get_write_domain()

    def __repr__(self) -> str:
        return 'Task({})'.format(self.name)
    
    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, o:Any) -> bool:
        if not isinstance(o, Task):
            return False
        return self.name == o.name

    def __lt__(self, o:Any) -> bool:
        if not isinstance(o, Task):
            return False

        return self.name < o.name

    def execute(self, verbose:bool=True):
        """Execute the instructions sequentially."""

        for i, instruction in enumerate(self.instructions):
            if verbose:
                print('{} : [red]Starting [bold]{}[/bold][/red]...'.format(str(self), str(instruction)))
                instruction.execute()
                if i < len(self.instructions) - 1:
                    print('{} : [green]Finished [bold]{}[/bold][/green].'.format(str(self), str(instruction)))
                else:
                    print('[strike]{}[/strike] : [green]Finished [bold]{}[/bold][/green].'.format(str(self), str(instruction)))
            else:
                instruction.execute()

        self.executed = True

    @property
    def dependencies(self) -> Iterable['Task']:
        return self._dependencies

    @dependencies.setter
    def dependencies(self, dependencies:Union['Task', Iterable['Task']]):
        if isinstance(dependencies, Task):
            self._dependencies = set([dependencies])
        else:
            self._dependencies = set(dependencies)

    def get_memory_cells(self) -> Set[Variable]:
        """Returns every memory cells used by the task.

        Returns:
            Set[Variable]: The union of the read and write domains.
        """
        return self.write_domain.union(self.read_domain)

    def __get_read_domain(self) -> Set[Variable]:
        """Get the read domain recursively throught each of its dependencies."""

        def recurse(i:Instruction) -> Set[Variable]:
            result = set()

            if isinstance(i, Read):
                result.add(i.variable)
            elif isinstance(i, Operator):
                result = result.union(recurse(i.i1), recurse(i.i2))

            return result

        result = set()

        # Recurse throught nested instructions
        for i in self.instructions:
            result = result.union(recurse(i))
        
        # Recurse throught dependencies
        for task in self.dependencies:
            result = result.union(task.read_domain)
        
        return result

    def __get_write_domain(self) -> Set[Variable]:
        """Get the write domain recursively."""

        def recurse(i:Instruction, nested:bool=False) -> Set[Variable]:
            result = set()

            if isinstance(i, Assign):
                result.add(i.variable)
            elif isinstance(i, Operator) and i.variable:
                # nested=True indicates that we are parsing nested operations with a defined variable
                # so the variable will be read, so it is added to the read domain.
                if nested:
                    self.read_domain.add(i.variable)
                result = result.union(recurse(i.i1, nested=True), recurse(i.i2, nested=True))
                result.add(i.variable)

            return result

        result = set()

        # Recurse throught nested instructions
        for i in self.instructions:
            result = result.union(recurse(i))

        # Recurse throught dependencies
        for task in self.dependencies:
            result = result.union(task.write_domain)
        
        return result

    def is_connected(self, task:'Task') -> bool:
        """Determines if the current task is connected to the supplied one.

        T(searched) ---- T(0) ----> T(1) ----> ... ----> T(k) ----> T(current)

        Args:
            task (Task): The searched task.

        Returns:
            bool: Indicates if it is connected.
        """
        def recurse(search_task:'Task', current_task:'Task') -> bool:
            if search_task in current_task.dependencies:
                return True

            for dependency in current_task.dependencies:
                if recurse(search_task, dependency):
                    return True
            
            return False

        return recurse(task, self)

    def get_successive_ancestors(self, task:'Task') -> Optional[List['Task']]:
        """Determines the successive tasks from the current task to the searched one.

        T(searched) ---- T(0) ----> T(1) ----> ... ----> T(k) ----> T(current)

        Args:
            task (Task): The searched task.

        Returns:
            Optional[List[Task]]: The successive tasks, None if there is not any.
        """
        def recurse(search_task:'Task', current_task:'Task') -> int:
            solution = []

            for dependency in current_task.dependencies:
                solution += [dependency] + recurse(search_task, dependency)
            
            return solution

        if not self.is_connected(task):
            return None
        return recurse(task, self)
    
    def is_interfering(self, task:'Task') -> bool:
        """Returns a boolean, indicating if the task is interfering with the supplied one.

        Args:
            task (Task): The task to be tested on.

        Returns:
            bool: Indicates if it interferes.
        """
        conditions = [
            not self.read_domain.intersection(task.write_domain) \
            and not task.read_domain.intersection(self.write_domain) \
            and not self.write_domain.intersection(task.write_domain),

            self.is_connected(task) or task.is_connected(self)
        ]

        return not (conditions[0] or conditions[1])

    def panel(self) -> Panel:
        """Show all instructions and the name of the task.
        """
        panel = Panel(Pretty([str(instruction) for instruction in self.instructions], expand_all=True), title=str(self))
        return panel