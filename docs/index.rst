Welcome to django-data-watcher's documentation!
===============================================


Django Data Watcher is a library that will make easier to create/mantain side-effects of data operations in your django models.

It tries to fix some of *Django Signals*' problems, being reusable, giving visibility of the side-effects of doing data operations in a specific model, and also if some hook is triggered by a queryset operation it runs only once, giving you responsability of dealing with the queryset instead running once for each affected instance.

It's very practical to use and you can improve the readbility and performance of your data services.

Document version:
|version|
|release|

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
