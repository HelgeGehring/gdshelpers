***************************************************************
Installing a Python GDSII development environment under Windows
***************************************************************

Download and install Git
========================

All development of gdshelper is done it Git. Even if you do not plan on contributing by your own, you will eventually
need it. Download it from `git-scm.com <http://git-scm.com/downloads>`_. Keep the default settings.

Download and install Python
===========================

CPython as Python distribution
-------------------------------

While you can basically use any Python 3 interpreter (at least Python 3.5, preferably the newest version), in this guide we use CPython by python.org. Head there now and
`download <https://www.python.org/downloads/>`_ the Windows installer. Make sure that the installer **adds CPython to PATH** and installs the Python package managment **pip**.


PyCharm as IDE
--------------

One of the best Python IDEs is PyCharm which now also has a free community edition. Go and
`get it <http://www.jetbrains.com/pycharm/>`_.
It's recommendable to install it via te `Jetbrains toolbox <https://www.jetbrains.com/toolbox/>`_, as it simplifies upgrading Pycharm.

You can directly start it after it is installed. On the first start it will ask you about your default theme and keymap.
Change it to your own preference.

Setting up Python in PyCharm
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before doing any real work you will have to tell PyCharm which Python it should use. On the welcome screen, select
``Configure``, then ``Settings``. Add the Python interpreter in ``Project Interpreters`` and click
on the gear in the upper right and then ``Add``. There you can add the Python Interpreter by selecting ``System Interpreter``.
The right path should be already in the form.

PyCharm will then parse all the installed modules of that Python installation.

Installing the gdshelpers and optional dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Even under Windows, the command line is sometimes useful. In our case we use `pip` to install gdshelpers with image-export directly by using the single command::

    pip install gdshelpers[image_export]
    
For most users this configuration should be sufficient.

Alternatively, you can also add the gdshelpers to your project using ``VCS --> Checkout from Version Control --> Git`` (the link is https://github.com/HelgeGehring/gdshelpers.git)
and then ``Attach`` to add it to your project. Using this way, it is also possible to modify the gdshelpers and to contribute to the development.

Additionally you need extra packages for certain functions of the package.
For exporting the design to the OASIS-format you should install the library `fatamorgana` using ``pip install fatamorgana``.
In order to create GDSII-files, you can use the included GDSII-export or decide between `gdspy` (fully python 3 compatible, ``pip install gdspy``) and `gdsCAD` (also working under python 3, but not installable using `pip`).
For directly generating pictures from the designs the package `descartes` needs to be installed (``pip install descartes``).


Updating gdshelpers
^^^^^^^^^^^^^^^^^^^

In order the update to the most recent version of gdshelpers you should execute from time to time::

    pip install --upgrade gdshelpers

Finish
""""""

That's it, you are all set to generate your own GDS file. Head over to the tutorial.
