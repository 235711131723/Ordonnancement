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

from exploit.task import Task
from exploit.instruction import Assign, Constant
from exploit.variable import Variable

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
        tasks = tasks if tasks else []
        for task in tasks:
            self.add_task(task)

        self.executed = False
        self.time = None
        self.history = {}

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

    def get_history_of_values(self, variable:Union[Variable, str]) -> List[Optional[int]]:
        """Get the history of values of a variable.

        Args:
            variable (Variable): The studied variable.

        Returns:
            List[Optional[int]]: The list of the values of the variable after each instruction.
        """
        if isinstance(variable, str):
            variable = self.history[variable]

        return variable.history

    ########################################
    # System-related methods
    ########################################
    def is_equivalent(self, system:'System') -> bool:
        """Determines if these systems are equivalent.

        Args:
            system (System): The system to compare to.

        Returns:
            bool: A boolean indicating their equivalency.
        """
        if not (self.is_deterministic() and system.is_deterministic()):
            return False

        if not (self.get_memory_cells() == system.get_memory_cells()):
            return False
        
        if not (self.executed or system.executed):
            raise RuntimeError("Au moins l'un des deux systèmes n'a pas exécuté les tâches.")

        for name, cell in self.history.items():
            if self.get_history_of_values(cell) != system.get_history_of_values(cell):
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
    
    ########################################
    # Drawing graphs
    ########################################
    def __generate_label(self, task:Task) -> str:
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
        return str(soup)

    def draw(self, view:bool=False):
        dot = graphviz.Digraph(comment='Graph')
        for layer in self.get_layers():
            for task in layer:
                dot.node(
                    name=str(task.name),
                    label='<{}>'.format(self.__generate_label(task))
                )
                for parent in task.dependencies:
                    dot.edge(tail_name=str(parent.name), head_name=str(task.name))

        filename = pathvalidate.sanitize_filepath(self.name)
        dot.render(filename + '.gv', view=view)

    ########################################
    # Tasks
    ########################################
    def get_initial_tasks(self) -> Set[Task]:
        """Get tasks at the most top-level."""
        return set(task for task in self.tasks if not task.dependencies)

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
    
    def get_layers(self):
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
    def show(self):
        console = Console()
        console.rule('Stats')
        if self.executed:
            print('Time elapsed: {:.06}s'.format(self.time))
            print('Variables : {}'.format(self.get_memory_cells()))
        else:
            print("The system has not been runned yet.")

    ########################################
    # Run
    ########################################
    def randomize_variables(self):
        """Set random integers for variables that are affected by a constant.
        
        Assign('x', 10) will be affected.
        Assign('x', 'y') won't be.
        """

        for task in self.tasks:
            for instruction in task.instructions:
                if isinstance(instruction, Assign):
                    if isinstance(instruction.instruction, Constant): 
                        new_value = random.randint(0, 100)
                        print('Changing {} with {}...'.format(str(instruction), new_value))
                        instruction.instruction.value = new_value

    def reset_memory_cells(self):
        for cell in self.get_memory_cells():
            cell.reset()

    def reset_tasks_state(self):
        for task in self.tasks:
            task.executed = False

    def reset(self):
        self.reset_memory_cells()
        self.reset_tasks_state()

    def save_history(self):
        self.history = {cell.name: cell for cell in copy.deepcopy(self.get_memory_cells())}
        self.executed = True

    def run(self, verbose:bool=True):
        """Run the tasks with threads."""
        def execute_tasks_parallel(tasks):
            threads = []
            
            for task in tasks:
                if not task.executed:
                    thread = threading.Thread(target=task.execute, kwargs={'verbose': verbose})
                    threads.append(thread)
                # Appel récursif pour les tâches dépendantes
                execute_tasks_parallel(task.dependencies)  
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        if verbose:
            console = Console()
            console.rule(title=self.name)

        self.reset()
        with timer() as measure_time:
            execute_tasks_parallel(self.get_final_tasks())
        self.time = measure_time()
        self.save_history()
        
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