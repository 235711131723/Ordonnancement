from typing import *
from contextlib import contextmanager
from rich import print
from rich.console import Console
from rich.pretty import pprint
import bs4
import copy
import itertools
import graphviz
import pathvalidate
import random
import threading
import time
import toposort

from systeme.task import Task
from systeme.instruction import Instruction, Assign, Constant, Operator
from systeme.variable import Variable

@contextmanager
def timer():
    start = time.time()
    yield lambda: time.time() - start

class System:
    """A class to implement a system of tasks.
    It MUST be determistic.
    """

    def __init__(self, name:str='System', tasks:Optional[List[Task]]=None):
        self.name = name

        self.tasks = []
        tasks = copy.deepcopy(tasks) if tasks else []
        for task in tasks:
            self.add_task(task)

        self.executed = False
        self.time = None
        self.history = {}

        self.executions = 0
        self.times = []
        self.histories = []

    def add_task(self, task:Task):
        try:
            existing_task = next((t for t in self.tasks if t == task))
            self.tasks.remove(existing_task)
        except StopIteration:
            pass

        self.tasks.append(task)
        if not self.is_deterministic():
            raise RuntimeError("The system is not determined.")

    ########################################
    # Tasks
    ########################################
    def get_memory_cells(self) -> Set[Variable]:
        """Get variables used by every tasks.

        Returns:
            Set[Variable]: A set of every used variable.
        """
        cells = set()

        for task in self.tasks:
            cells = cells.union(task.get_memory_cells())
        
        return cells

    ########################################
    # System-related methods
    ########################################
    def is_equivalent(self, system:'System') -> bool:
        """Determines if these systems are equivalent.

        Args:
            system (System): The system to compare to.
        
        Raises:
            RuntimeError: Raise when the systems have not been runned once.

        
        Returns:
            bool: A boolean indicating their equivalency.
        """
        if not (self.is_deterministic() and system.is_deterministic()):
            return False

        if not (self.get_memory_cells() == system.get_memory_cells()):
            return False

        # Check if for each history, the variables of the two systems have the same history.
        n = min(self.executions, system.executions)
        if n < 1:
            raise RuntimeError('The systems have to be executed at least once.')

        for i in range(min(self.executions, system.executions)):
            for name, cell in self.histories[i].items():
                if self.histories[i][name] != system.histories[i][name]:
                    return False
        return True

    def is_deterministic(self) -> bool:
        """Determines if the system is deterministic.

        Returns:
            bool: The system is determinstic if each pair of two tasks t1, t2 from the system are not interfering with each other.
        """
        for t1, t2 in itertools.combinations(self.tasks, r=2):
            if t1.is_interfering(t2):
                return False

        return True

    def are_histories_equal(self) -> bool:
        """Check if every and each one of the histories is equal to each other.
        The system must have been executed more than once.

        Raises:
            RuntimeError: Raise when conditions are not met.

        Returns:
            bool: Check if every and each one of the histories is equal to each other.
        """
        if not self.executed:
            raise RuntimeError('The system has not been executed yet.')
        if self.executions == 1:
            raise RuntimeError('The system has been executed only once.')
        return self.histories.count(self.histories[0]) == len(self.histories)

    
    ########################################
    # Drawing graphs
    ########################################
    def __generate_label(self, task:Task) -> str:
        """Generate the label to represent the task on the graph.
        It is generated by the HTML source code from the module bs4,
        as Graphviz can use HTML-like tags.

        Args:
            task (Task): The task to represent.

        Returns:
            str: The formatted label ready to be used by Graphviz.
        """
        soup = bs4.BeautifulSoup('', 'html.parser')

        table = soup.new_tag('TABLE')

        # Title
        tr = soup.new_tag('TR')
        td = soup.new_tag('TD')
        td['BGCOLOR'] = 'cyan'

        title = soup.new_tag('B')
        title.string = str(task.name)

        td.append(title)
        tr.append(td)
        table.append(tr)

        # Instructions
        for instruction in task.instructions:
            tr = soup.new_tag('TR')
            td = soup.new_tag('TD')
            td.string = str(instruction)
            tr.append(td)
            table.append(tr)

        soup.append(table)
        return '<{}>'.format(str(soup))

    def draw(self, view:bool=False):
        dot = graphviz.Digraph(comment='Graph of "{}"'.format(self.name))
        for layer in self.get_layers():
            for task in layer:
                dot.node(
                    name=str(task.name),
                    label=self.__generate_label(task)
                )
                for parent in task.dependencies:
                    dot.edge(tail_name=str(parent.name), head_name=str(task.name))

        filename = pathvalidate.sanitize_filepath(self.name)
        dot.render(filename + '.gv', view=view)

    ########################################
    # Tasks
    ########################################
    def get_final_tasks(self) -> Set[Task]:
        """Get tasks at the most bottom-level."""
        tasks = []
        for task in self.tasks:
            for t in self.tasks:
                if task in t.dependencies:
                    break
            else:
                tasks.append(task)
        return tasks
    
    def get_layers(self) -> List[Set[Task]]:
        """Get every tasks layer by layer.
        Solely used for generating graphs. 

        Returns:
            List[Set[Level]]: The layers of tasks, from the top-level tasks to the bottom-level ones.
        """
        levels = []

        explored = set()
        level = self.get_final_tasks()
        while level:
            levels.insert(0, level)
            children = set()
            for task in level:
                children = children.union(task.dependencies)
            level = children.difference(explored)
            explored = explored.union(children)
        
        return levels

    ########################################
    # Stats
    ########################################
    def show(self, show_all:bool=False):
        console = Console()
        console.rule('Stats')
        if self.executed:
            print('Time elapsed : {:.06}s'.format(self.time))
            print('Last variables state : {}'.format(self.get_memory_cells()))

            if show_all and self.executions > 1:
                print('Mean time elapsed : ~{:.06}s'.format(sum(self.times) / len(self.times)))
                print('Histories :')
                pprint(self.histories)
        else:
            print("The system has not been runned yet.")

    ########################################
    # Run
    ########################################
    def randomize_variables(self):
        """Set random integers for variables that are affected by a constant.
        
        Assign('x', 10) will be affected.
        Assign('x', 'y') won't be.

        Add('x', 10, 'y') will be affected, as there is a constant.
        """

        def recurse(instructions:List[Instruction], parent:Optional[Instruction]=None):
            for instruction in instructions:
                if isinstance(instruction, Assign):
                    recurse([instruction.instruction], parent=instruction)
                elif isinstance(instruction, Operator):
                    recurse([instruction.i1, instruction.i2], parent=instruction)
                elif isinstance(instruction, Constant): 
                    old_parent = str(parent)
                    new_value = random.randint(0, 100)
                    instruction.value = new_value
                    print('Changing {} to {}...'.format(old_parent, str(parent)))

        for task in self.tasks:
            recurse(task.instructions)

    def reset_memory_cells(self):
        """Empty every variable from their history and their value."""
        for cell in self.get_memory_cells():
            cell.reset()

    def reset_tasks_state(self):
        """Set all tasks as non-executed.
        """
        for task in self.tasks:
            task.executed = False

    def reset(self):
        self.reset_memory_cells()
        self.reset_tasks_state()

    def save_history(self):
        """Save the last state of variables.

        Also save them in dedicated arrays for future analysis.
        """
        self.history = {cell.name: cell for cell in copy.deepcopy(self.get_memory_cells())}
        self.executed = True

        self.executions += 1
        self.histories.append(self.history)
        self.times.append(self.time)

    def run(self, loops:int=1, verbose:bool=True):
        """Run the tasks with threads recursively from the bottom."""

        def execute_tasks_parallel(tasks:Set[Task]):
            """The function will recurse from the bottom,
            until no dependency is remaining.

            Once there is not any dependency left, the threads will finally start.
            Thus, the first threads to start are the one corresponding to the top-level tasks.

            Args:
                tasks (Set[Task]): The tasks to recurse from.
            """
            threads = []
            
            for task in tasks:
                if not task.executed:
                    thread = threading.Thread(target=task.execute, kwargs={'verbose': verbose})
                    threads.append(thread)

                # Recurse throught every dependencies
                execute_tasks_parallel(task.dependencies)  
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        if verbose:
            console = Console()
            console.rule(title=self.name)

        for loop in range(loops):
            if verbose and loops > 1:
                console.rule('#{}/{}'.format(loop + 1, loops))

            self.reset()
            with timer() as measure_time:
                execute_tasks_parallel(self.get_final_tasks())
            self.time = measure_time()
            self.save_history()

            if verbose:
                if loop == loops - 1:
                    self.show(show_all=True)
                else:
                    self.show()
        
class Sequential(System):
    def __init__(self, system:System):
        name = '{} - Sequential'.format(system.name)
        super().__init__(name=name, tasks=system.tasks)

        graph = {task: task.dependencies for task in self.tasks}
        flatten = toposort.toposort_flatten(graph)
        for i in range(0, len(flatten) - 1):
            flatten[i+1].dependencies = flatten[i]
        
        self.tasks = flatten
    
class Parallelize(System):
    def __init__(self, system:System):
        name = '{} - Parallelized'.format(system.name)
        super().__init__(name=name, tasks=system.tasks)

        # Adding arcs everywhere
        for t1, t2 in ((x, y) for x, y in itertools.product(self.tasks, repeat=2) if x.is_connected(y)):
            t1.dependencies.add(t2)

        # Attempting to remove arcs
        # in a way the system remains deterministic
        for t1, t2 in ((x, y) for x, y in itertools.product(self.tasks, repeat=2) if x.is_connected(y)):
            t1.dependencies.remove(t2)

            if not self.is_deterministic():
                t1.dependencies.add(t2)