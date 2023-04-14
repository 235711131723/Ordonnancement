#!/usr/bin/env python3

from rich import print
from rich.console import Console
import argparse
import random
import time

from systeme.task import Task
from systeme.instruction import Sleep, Assign, Add, Sub, Mul
from systeme.system import System, Sequential, Parallelize
from systeme.variable import Variable

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', '-s', type=int, default=int(time.time()), help='Set the seed for random. Default is the seconds elapsed since the EPOCH.')

    parser.add_argument('--loops', type=int, default=1, help='Repeat the execution of the system(s).')

    parser.add_argument('--test', '-t', action='store_true', help='Create multiple parallelized systems.')
    parser.add_argument('--randomize', '-r', action='store_true', help='Randomize variables.')

    parser.add_argument('--sequential', action='store_true', help='Run the system as sequential.')
    parser.add_argument('--parallelize', '-p', action='store_true', help='Run the system as parallelized.')

    parser.add_argument('--view', '-v', action='store_true', help='View generated graphs.')
    args = parser.parse_args()

    if args.loops <= 0:
        raise argparse.ArgumentTypeError('--loops must be > 0.')
    return args

def main():
    args = parse_args()
    random.seed(args.seed)

    console = Console()

    try:
        t1 = Task([
            Assign('x', 30),
            Sleep(1)
        ])
        t2 = Task([
            Assign('y', 10),
            Sleep(1)
        ], dependencies=t1)

        system = System(tasks=Task.get_all_tasks())
        if args.randomize:
            system.randomize_variables()
        system.draw(view=args.view)

        if args.test:
            console.rule('Test')
            parallel = Parallelize(system)
            parallel.run(loops=args.loops, verbose=False)
            if not parallel.are_histories_equal():
                print('The test is [red bold]invalid[/red bold].')
                print('Histories :')
                pprint(parallel.histories)
            else:
                print('The test is [green bold]valid[/green bold].')

        if args.parallelize:
            parallel = Parallelize(system)
            parallel.draw(view=args.view)

        if args.sequential:
            sequential = Sequential(system)
            sequential.draw(view=args.view)

        system.run(loops=args.loops)
        if args.parallelize:
            parallel.run(loops=args.loops)
            if system.is_equivalent(parallel):
                print('The system and the parallelized one are [green bold]equivalent[/green bold].')
            else:
                print('The system and the parallelized one are [red bold]not equivalent[/red bold].')

        if args.sequential:
            sequential.run(loops=args.loops)
            if system.is_equivalent(sequential):
                print('The system and the sequential one are [green bold]equivalent[/green bold].')
            else:
                print('The system and the sequential one are [red bold]not equivalent[/red bold].')

        if args.sequential and args.parallelize:
            if parallel.is_equivalent(sequential):
                print('The parallelized and the sequential systems are [green bold]equivalent[/green bold].')
            else:
                print('The parallelized and the sequential systems are [red bold]not equivalent[/red bold].')

    except (RuntimeError, ValueError) as e:
        print('[red]ERROR: [bold]{}[/bold][/red] '.format(e))
    except KeyboardInterrupt:
        pass
    
    console.rule('Parameters')
    print('Seed : {}'.format(args.seed))

if __name__ == '__main__':
    main()