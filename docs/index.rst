Welcome to django-data-watcher's documentation!
===============================================

Release v\ |version|.

Django Data Watcher is a library that will make easier to create/mantain side-effects of data operations in your django models.

It tries to fix some django signals problems, beeing reusable, giving visibility of the side-effects of doing data operations in a specific model, also if some hook is triggered by a queryset operation the hook you run only once for, giving you responsability of dealing with the queryset instead run once for each affected instance.

It's very easy to use and you can improve the readbility and performance of your data services.

.. toctree::
    :maxdepth: 3
    :caption: User Guide

    guide/install
    guide/usage
    guide/tutorial

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
