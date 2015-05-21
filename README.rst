pypicloud-tools
===============

`View this on GitHub
Pages <http://ccpgames.github.io/pypicloud-tools/>`__

|Build Status| |Coverage Status| |Version| |Download format| |Downloads
this month| |Development Status| |License|

Tools to bypass a PyPICloud installation and communicate directly with
S3

Utilities
---------

Upload
~~~~~~

Uploads file(s) to the PyPICloud S3 bucket directly and performs an
admin API call to rebuild the PyPICloud index after.

Example:

.. code:: bash

    $ upload dist/*
    Uploading example_project/example-project-0.0.1.tar.gz .....1 done!
    Uploading example_project/example_project-0.0.1-py2-none-any.whl .....1 done!
    Uploading example_project/example_project-0.0.1-py2.7.egg ......1 done!
    PyPICloud server at http://your.pypicloud.server/pypi updated

The numbers displayed are the amount of 50MB chunks you've sent to S3 as
they send. It's fine if the file names use altering hypens/underscores
per release type like you see above, they only need to match the initial
part of the key before the ``/`` to be considered the same package.

Download
~~~~~~~~

Downloads the latest or a specific version directly from S3. Does not
talk to PyPICloud and does not install the downloaded package. You can
use pip to do either/both of those things.

Also possible with the download command is the ``--url`` flag to only
print a download URL (usable for 5 minutes).

By default, if there are multiple releases of the same package+release,
download will prefer wheels, then eggs, then source distributions. You
can override that behavior with the ``--egg`` and ``--src`` flags.

Examples:

.. code:: bash

    $ download example_project=0.0.1
    example_project-0.0.1-py2-none-any.whl

.. code:: bash

    $ download example_project --egg
    example_project-0.0.1-py2.7.egg

Pipes and redirects work like you'd expect:

.. code:: bash

    $ download example_project --src | tar -xzf -

List
~~~~

Lists a package's releases, or releases of a package at a specific
version. Again, talks straight to S3 and bypasses the PyPICloud
installation.

Example:

.. code:: bash

    $ list example_project
    example-project-0.0.1.tar.gz
    example_project-0.0.1-py2.7.egg
    example_project-0.0.1-py2-none-any.whl

Listing multiple packages or packages with a version specifier is also
supported.

When called without any arguments, ``list`` will display all known
packages.

Rehost
~~~~~~

Rehosts an upstream package from PyPI into the pypicloud installation.
This can be handy if you have pypicloud clients which only have access
to it and s3 but not the rest of the internet.

Example:

.. code:: bash

    $ rehost requests==1.0.0
    Collecting requests==1.0.0
      Downloading requests-1.0.0.tar.gz (335kB)
        100% |████████████████████████████████| 335kB 929kB/s
      Saved /var/folders/53/kl4v4_9509ng148kp_pwmc5h0000gn/T/tmpuj5JUJ/requests-1.0.0.tar.gz
    Successfully downloaded requests
    Uploading requests/requests-1.0.0.tar.gz ............1 done!
    PyPICloud server at http://your_pypicloud_server/pypi updated

If a specific version is not provided, the latest will be used. Multiple
packages can be used in the same command.

Installation
------------

Simple
~~~~~~

.. code:: bash

    $ pip install pypicloud-tools

From source
~~~~~~~~~~~

.. code:: bash

    $ git clone https://github.com/ccpgames/pypicloud-tools.git
    $ cd pypicloud-tools
    $ python setup.py install

Configuration
-------------

Configuration for pypicloud-tools piggybacks on your ``~/.pypirc`` file.
You can specify an alternate config file with the ``--config`` flag, but
it must be in the same syntax. That syntax is:

.. code:: conf

    [pypicloud]
        repository:http://your.pypicloud.server/pypi
        username:admin
        password:hunter7
        bucket:your_bucket
        access:some_key
        secret:other_key
        acl:optional_acl

The key **must** be ``pypicloud``, it is the only key pypicloud-tools
will look at. The username/password combination should have admin
credentials on the PyPICloud installation as it needs to call
``/admin/rebuild`` after a succesful upload.

Copyright and License
=====================

pypicloud-tools was written by Adam Talsma

Copyright (c) 2015 CCP hf.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

.. |Build Status| image:: https://travis-ci.org/ccpgames/pypicloud-tools.png?branch=master
   :target: https://travis-ci.org/ccpgames/pypicloud-tools
.. |Coverage Status| image:: https://coveralls.io/repos/ccpgames/pypicloud-tools/badge.svg?branch=master
   :target: https://coveralls.io/r/ccpgames/pypicloud-tools?branch=master
.. |Version| image:: https://img.shields.io/pypi/v/pypicloud-tools.svg
   :target: https://pypi.python.org/pypi/pypicloud-tools/
.. |Download format| image:: https://img.shields.io/badge/format-wheel-green.svg?
   :target: https://pypi.python.org/pypi/pypicloud-tools/
.. |Downloads this month| image:: https://img.shields.io/pypi/dm/pypicloud-tools.svg
   :target: https://pypi.python.org/pypi/pypicloud-tools/
.. |Development Status| image:: https://img.shields.io/badge/status-beta-orange.svg
   :target: https://pypi.python.org/pypi/pypicloud-tools/
.. |License| image:: https://img.shields.io/github/license/ccpgames/pypicloud-tools.svg
   :target: https://pypi.python.org/pypi/pypicloud-tools/
