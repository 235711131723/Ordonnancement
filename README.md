# Projet

## Description

Le projet consiste en la manipulation de l'ordonnancement de tâches.
On y applique notamment la parallélisation maximale automatique vue en cours grâce aux conditions de Bernstein, ainsi que la séquentialisation grâce au tri topologique qui, lui, n'est pas traité dans le cours.

## Organisation du code

Le projet se présente sous forme de module appelé `systeme`. S'y trouvent les fichiers principaux :
- `__main__.py` : code principal, avec les entrées utilisateur, les tâches créées manuellement, etc.
- `variable.py` : la classe `Variable`, et sans doute la plus importante de toute, car elle est la brique la plus primitive.
- `instruction.py` : toutes les classes d'`Instruction` servant de briques pour créer une instruction, comme expliqué dans les diapositives.
- `task.py` : la classe `Task` représantant une tâche acceptant en paramètre une liste d'instances d'`Instruction` et une liste de dépendances (instances de `Task`), cette dernière éventuellement vide.
- `system.py` : la classe `System` concernant le système de tâches.

## Classes

### Variable

La classe `Variable`. S'y trouvent :
- Valeur (`int | None`). Par défaut `None` lorsque déclarée ainsi : `Variable('x')`
- Historique, qui une liste de valeurs. Elles peuvent aussi bien être des `int` que des `None`. Se remplit au fur et à mesure qu'on attribut à cette instance une nouvelle valeur.

Elle se stocke elle-même dans un dictionnaire statique `VARIABLES` de la classe lors de sa création.

En théorie, elle devrait être appelée classiquement : `Variable('y')`.

En pratique, on l'appelle comme un tableau : `Variable['x']`. De cette façon, si une variable n'existe pas, elle sera créée sur le tas avec aucune valeur, sera sauvegardée, puis sera renvoyée. Sinon la variable avec le même nom sera renvoyé, avec la valeur et l'historique.

### Instructions

La classe `Instruction`, ainsi que toutes les sous-classes.

Elle a été construite de telle façon à ce que :
- Lors de l'exécution, elle renverra toujours un `int` (à l'exception de `Sleep()`).
- Elles puissent être imbriquées l'une dans l'autre, lorsque c'est possible. Par exemple, `Add(Sleep(), 10, 'y')` est impossible et le programme le fera savoir.
- Les variables sont stockées, accédées (et/ou créées sur le tas) par la syntaxe évoquée précédemment : `Variable[nom]`.

### Tâche

La classe `Task`. S'y trouvent les méthodes suivantes :
- Interférence avec une autre tâche, implémentée à l'aide des conditions de Bernstein : `is_interfering(task)`
- Existence d'un chemin (= chaîne de dépendances) entre une tâche t<sub>1</sub> et une autre t<sub>2</sub> : `is_connected(task)`
- ~~Reconstruction du chemin existant entre deux tâches~~ (non utilisée) : ~~`get_successive_ancestors(task)`~~
- Analyse automatique du domaine de lecture et d'écriture, respectivement : `__get_read_domain()` et `get_write_domain()`. Ces deux méthodes sont cachées et ne sont pas censées être appelables depuis l'extérieur. Pour avoir les domaines, il suffit de lire les attributs `read_domain` et `write_domain`.
- **Le programme s'arrête net quand un duplicata de tâche est détecté.**
- **Un système de sauvegarde de tâches similaire à celui des variables existe pour les tâches**.

### Système

La classe `System`. S'y trouvent les méthodes suivantes :
- Déterminisme : `is_deterministic()`.
- Équivalence avec un autre système : `is_equivalent(system)`.
- Consistence (= sur plusieurs exécutions, les historiques des variables restent inchangées à la fin) : `are_histories_equal()`.
- **Existence d'un cycle : `is_cyclic()`. Le programme s'arrête net quand un cycle est détecté.**
- Représentation en graphe : `draw()`. Le module `bs4` a été utilisé pour générer de l'HTML, d'où les tableaux dans les bulles.
- Assignation aléatoire aux variables de nombres entiers : `randomize_variables()`.
- Exécution : `run(loops=1, verbose=True)`. `loops` pour répéter l'exécution, `verbose` pour afficher quelle instruction s'exécution ou non.

Elle accepte en paramètre un nom, et une liste de tâches.

En ce qui concerne la parallélisation et la séquentialisation, elles sont respectivement gérées par les deux sous-classes `Parallelize` et `Sequential`, acceptant tous deux en paramètre une instance de `System`. Les tâches y sont copiées (avec `copy.deepcopy()`, du module `copy`). Ainsi, celles d'origine ne sont pas impactées par les changements de dépendances appliquées dans les deux sous-classes.

Le système de test randomisé consiste à créer un système parallélisé depuis le système et l'exécuter 10 fois. Il est réussi quand les historiques de variable sont égaux (`are_histories_equal()`).

__PS__ : C'est à cause de l'utilisation de `copy.deepcopy()` que le système doit être acyclique.

## Exécution

    cd /chemin/vers/le/dossier/contenant/systeme

Pour afficher l'aide :

    python -m systeme -h

Pour une utilisation basique :

    python -m systeme

Pour en plus afficher le graphe :

    python -m systeme --view
    python -m systeme -v

Pour répéter l'exécution :

    python -m systeme --loops 10

Pour paralléliser :

    python -m systeme --parallelize
    python -m systeme -p

De manière analogue, pour séquentialiser :

    python -m systeme --seq
    python -m systeme --sequential

Pour tester la consistance du système :

    python -m systeme --test
    python -m systeme -t

Tous les paramètres peuvent se combiner.