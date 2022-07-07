===============
Getting Started
===============

Here you will understand how to use our WatcherMixins to decorate your Django Models and take advantage of the Hooks

#. Extend a base mixin, implementing the desired hook. check :ref:`the_watcher` and :ref:`available_mixins`.
#. Decorate you Model with **watched** decorator, check :ref:`the_model`

The Hooks
---------

Every basic data operation in Django can trigger a hook (Except read operations).
And we have these hooks availables:

- **pre_create** called by: :ref:`create_mixin`, and :ref:`save_mixin`
- **pre_update** called by: :ref:`update_mixin`, and :ref:`save_mixin`
- **pre_save** called by: :ref:`save_mixin`
- **pre_delete** called by: :ref:`delete_mixin`
- **post_create** called by: :ref:`create_mixin`, and :ref:`save_mixin`
- **post_update** called by: :ref:`update_mixin`, and :ref:`save_mixin`
- **post_save** called by: :ref:`save_mixin`
- **post_delete** called by: :ref:`delete_mixin`

Each hook is a classmethod, it will always have the `target` param, update and create hooks will also have the `meta_params` param.

Target
~~~~~~

| The Target represents the objects afected by the current operation.
| It can be a already filtered QuerySet or a List which instances.
| Each hook signature will specify the type of the target, but you can infer thinking like: "Is possible to have a queryset here?" in pre_create hooks is not so you will receive a list of objects.
| To check hook signature go to the specific mixin.

.. _meta_params:

MetaParams
~~~~~~~~~~

The Metaparams is a TypedDict which will inform you about the trigger of the current operation::

    source: str  # "queryset" or "instance"
    operation_params: dict  # is the kwargs of the trigger operation
    instance_ref: optional[models.Model]  # in instance operations triggered by instances it will bring the reference to the instance that the operation was called

.. _the_watcher:

Create Your Watcher
-------------------

The Watcher class is the core of our project, on that you will coordinate the hooks of your model.

We do give 3 basic mixins (`DeleteWatcherMixin`, `CreateWatcherMixin`, `UpdateWatcherMixin`) which will control your data flow.

Also, exists a 4th mixin that is a mix up of Create and Update mixins: `SaveWatcherMixin`.

These mixins will call the hooks in the approprieted order together with the desired operation everything inside a transaction, and it will Rollback if something goes wrong.

How to extend a basic mixins::

    # my_app.watchers.py

    from __future__ import annotation

    from typing import TYPE_CHECKING, List

    from django_watcher.mixins import CreateWatcherMixin, DeleteWatcherMixin

    from .tasks import send_deletion_email

    if TYPE_CHECKING:
        from .models import MyModel


    class MyModelWatcher(CreateWatcherMixin, DeleteWatcherMixin):
        @classmethod
        def post_delete(cls, undeleted_instances: List[MyModel]):
            send_deletetion_email(undeleted_instances)

        @classmethod
        def pre_create(cls, target: List[MyModel], meta_params: dict):
            # do transformation, call functions, whatever you feel necessary

Usage of type hints is optional::

    # my_app.watchers.py

    from django_watcher.mixins import CreateWatcherMixin, DeleteWatcherMixin

    from .tasks import send_deletion_email


    class MyModelWatcher(CreateWatcherMixin, DeleteWatcherMixin):
        @classmethod
        def post_delete(cls, undeleted_instances):
            send_deletetion_email(undeleted_instances)

        @classmethod
        def pre_create(cls, target, meta_params):
            # do transformation, call functions, whatever you feel necessary


This section is only to show how easy is to use, but you can dive deep on the next section :ref:`available_mixins` to check what are the available parameters of the hooks.

.. _available_mixins:

Available Mixins
----------------

.. _delete_mixin:

DeleteWatcherMixin
~~~~~~~~~~~~~~~~~~

The DeleteWatcherMixin extends our `AbstractWatcher` has the following hooks::

    @classmethod
    def pre_delete(cls, target: models.QuerySet) -> None:
        ...

    @classmethod
    def post_delete(cls, undeleted_instances: List[D]) -> None:
        ...

.. _create_mixin:

CreateWatcherMixin
~~~~~~~~~~~~~~~~~~

The CreateWatcherMixin extends our `AbstractWatcher` has the following hooks::

    @classmethod
    def pre_create(cls, target: List['CreatedModel'], meta_params: MetaParams) -> None:
        ...

    @classmethod
    def post_create(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        ...


To understand what is :ref:`meta_params`, click on the link.

.. _update_mixin:

UpdateWatcherMixin
~~~~~~~~~~~~~~~~~~

The UpdateWatcherMixin extends our `AbstractWatcher` and has the following hooks::

    @classmethod
    def pre_update(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        ...

    @classmethod
    def post_update(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        ...


To understand what is :ref:`meta_params`, click on the link.

.. _save_mixin:

SaveWatcherMixin
~~~~~~~~~~~~~~~~~~

The SaveWatcherMixin extends `CreateWatcherMixin` and `UpdateWatcherMixin` has the same hooks of it supers and::

    @classmethod
    def pre_save(cls, target: Union[List['CreatedModel'], models.QuerySet], meta_params: MetaParams) -> None:
        pass

    @classmethod
    def post_save(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        pass

`pre_save` and `post_save` hooks will **always** run.

Create hooks order:

#. **pre_save**
#. **pre_create**
#. **create**
#. **post_create**
#. **post_save**

Update hooks order:

#. **pre_save**
#. **pre_update**
#. **update**
#. **post_update**
#. **post_save**


To understand what is :ref:`meta_params`, click on the link.

.. _the_model:

Decorate Your Model
-------------------

Setting the Watcher on the model::

    # You will always decorate your model
    from django_watcher.decorators import watched

    # Approach #1 - Import the watcher locally
    from my_app.whatchers import MyWatcher

    @watched(MyWatcher)
    class MyModel(models.Model):
        ...

    # Approach #2 - Give a custom path
    @watched('my_app.services.watchers.MyWatcher')
    class MyModel(models.Model):
        ...

    # Approach #3 - Give de module name + watcher name if is inside a `watchers.py` of the same django app
    @watched('my_app.MyWatcher')
    class MyModel(models.Model):
        ...


Using others than default django managers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Also if you have other managers (aside from `objects`) you can declarate it, on the seccond param of the `watched` decorator, default value is `['objects']`::

    from django_watcher.decorators import watched

    @watched('my_app.MyWatcher', ['objects', 'deleted_objects'])
    class MyModel(models.Model):
        ...
