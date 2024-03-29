# Django Data Watcher

[![Documentation Status](https://readthedocs.org/projects/django-data-watcher/badge/?version=latest)](https://django-data-watcher.readthedocs.io/en/latest/?badge=latest)

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
3. run poetry install

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
-   [x] Set gh actions to test and build
-   [x] Receive params on hooks to check modifications (Update/Save)
-   [x] Revisite string import for watchers
-   [x] Remove the need of saying which operation is beeing whatched, infer based on the watcher
-   [x] Limit the watched operations (only delete, create, update, save)
-   [x] Packaging
-   [x] Model.objects.create() calls instance.save().
-   [x] Publish v1
-   [ ] Test
    -   [x] Configure pytest with coverage
    -   [x] Use Django models and querysets inside tests
    -   [x] test abstract_watcher
    -   [x] test decorators
    -   [x] test mixins [Create, Delete, Update, Save, Union of Save and Delete]
    -   [x] Relational Testing (A model hook call another model with has hooks)
    -   [ ] Hooks params
    -   [ ] Be sure to manager have the model
    -   [ ] Test with Heritage
-   [ ] [C] Docs
    -   [x] Usage
    -   [x] Tutorial
    -   [x] Installation
    -   [x] Badge
    -   [x] Fix theme
    -   [ ] Docstrings on the code
    -   [ ] Hooks params
    -   [ ] How to Ignore the Hooks
    -   [ ] Fix Dynamic Version
    -   [ ] Query and Instance hooks
    -   [ ] How does it help? Bond or Arch?
    -   [ ] Redefine docs sections
    -   [ ] Update Readme (after finishing roadmap)
-   [x] [F] Have a way of ignoring hooks by param
-   [x] [F] Should unsaved instance come in all operations
-   [x] [M] Split decorators.py in a module and reorganzing its typings
-   [x] [C] Reorganize the imports from root
-   [x] [F] Create Stubs for decorated models
-   [x] [F] Hooks Params
-   [ ] [F] Implement for bulk operations on qs (bulk_create and bulk_update)
-   [ ] [P] Remove is_overriden func, documment what is needed to be overriden on watchers
-   [ ] [P] Remove Django dependencies
-   [ ] [D] [F] Use tox (GH actions is as good as we need?)
    -   [ ] Create testing matrix for Django versions
-   [ ] [B] Fix generate_settable Doc
-   [ ] [B] Verify if the transaction should be durable
-   [ ] [F] Set MetaParams as model
-   [ ] [M] Use `_ignore_hooks` instead of `UNWATCHED_operation`, rename it for `_unwatched_operation` and let only run method ref to it.
-   [ ] [P] Better manage QueryTools - Memory management of numerous qs. Should the watcher decorator always create a new QT, try to reuse it and solve or skip conflicts. (test decorators specified cases in this file.)
-   [ ] [F] SoftDeletion Mixin
-   [x] [M] `_generate_settable_for_manager`, `_generate_settable_for_qs`, and `_generate_settable_for_model` should be the same function, and fix typing
-   [ ] [M] Use [from_queryset and contribute_to_class](https://github.com/django/django/blob/653a7bd7b7c2f7c3ffe6b22be53da1472c491474/django/db/models/manager.py#L103-L118) to generate the manager and associate it with the model
-   [ ] Application Example also comparing with Django signals
-   [ ] Talk
