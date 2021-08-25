Netscool
========

Install
-------

It is recommended to install into a virtual environment so the installed packages dont pollute your environment.

```
python setup.py install
```

Or

```
pip install .
```

If you intend to modify anything in the `netscool` library.

```
python setup.py develop
```

Or

```
pip install -e .
```

Documentation
-------------

Documentation is built from the `doc` directory

```
make html
```

The built HTML documentation will be under `doc/_build/html`. Open `index.html` in a browser to view the documentation.

The API documentation can be updated by running the following from the repo root directory.

```
sphinx-apidoc -f netscool -o doc/api
```

All diagrams in the documentation are SVG generated using `https://app.diagrams.net/`. These SVG have enough metadata that they can be reimported and edited as diagrams (nodes and connections intact).
