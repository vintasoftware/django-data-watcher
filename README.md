# Django Data Watcher

## _Django models/data operations observer_

Django Data Watcher is a library that will make easier to create/mantain side-effects of data operations in your django models.

-   Write once
-   Have visibility
-   Acts always on querysets, avoinding bottlenecks

## Requirements

-   Poetry [(installation)](https://python-poetry.org/docs/#installation)
-   Python 3.6.8

## Development and installation

### VsCode installation

1. copy devcontainer-example.json to devcontainer.json `cp .devcontainer/devcontainer-example.json .devcontainer/devcontainer.json`
2. click in reopen in container

### VsCode development (after installation)

1. inside vscode integrated terminal run `poetry run which python`
2. type choose the python returned in the step 1 as the interpretor for vscode

## Roadmap

-   [x] Override save for models
-   [x] Limit the number of functions on watcher eg. instead of save, \_save and watched_save have only \_save and \_watched_save or maybe just one of those
-   [x] Make watched_operations restrict
-   [x] Delete and Create Mixins
-   [x] Update and Save Mixins
-   [x] Take a look into \_default_manager and \_base_manager (Create specific test cases)
-   [ ] [C] Test
    -   [x] Configure pytest with coverage
    -   [x] Use Django models and querysets inside tests
    -   [x] test abstract_watcher
    -   [ ] test decorators
        -   [ ] Override django base QueryTools (Manager and QuerySet)
        -   [ ] Override different models using the QueryTools
        -   [ ] Override a single model using the same QueryTools twice
    -   [x] test mixins
        -   [x] Create
            -   [x] Hooks Calleds
            -   [x] Hooks Order
            -   [x] Entire flows works for QT
            -   [x] Entire flows works for instances
            -   [x] Running inside transaction
        -   [x] Delete
        -   [x] Update
        -   [x] Save
        -   [x] Save and Delete Union
    -   [ ] Relational Testing (A model hook call another model with has hooks)
    -   [ ] Model with more than 1 manager
-   [x] Packaging [C]
    -   [x] [C] Deploy with poetry
    -   [x] [F] Poetry configuration vscode
    -   [ ] [F] Make devcontainer better works with poetry, move the venv and create a docker volume
-   [x] Set gh actions to test and build
-   [ ] [C] Receive params on hooks to check modifications (Update/Save)
-   [ ] [C] Revisite string import for watchers
-   [ ] [D] [C] Limit the watched operations (only delete, create, update, save)
-   [ ] [D] [C] Remove the need of saying which operation is beeing whatched, infer based on the watcher
-   [ ] [C] Docs
-   [ ] [F] Implement for bulk operations on qs (bulk_create and bulk_update)
-   [ ] [D] [F] Whave a way of ignoring hooks by param
-   [ ] [P] Remove is_overriden func, documment what is needed to be overriden on watchers
-   [ ] [P] Remove Django dependencies
-   [ ] [D] [F] Use tox (GH actions is as good as we need?)
-   [ ] [P] Better manage QueryTools - Memory management of numerous qs. Should de watcher decorator always create a new QT, try to reuse it and solve or skip conflicts. (test decorators specified cases in this file.)
-   [ ] [C] Model.objects.create() calls instance.save().
    -   [ ] [D] [F] Do we want to support possible overrides of qs.create() that don't call instance.save()?
    -   [x] [C] queryset UNWATCHED_create needs to call UNWATCHED_save of instance
-   [ ] Application Example also comparing with Django signals
-   [ ] Talk
