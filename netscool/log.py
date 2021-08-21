"""
Module to control what logs will be displayed while doing lessons. Should
primarily be used from ``network.py`` to investigate how our code is
interacting with the reference device.

``network.py`` should setup applicable logs.
::

    import netscool.log
    netscool.log.setup()
    netscool.log.add(<logger name>)

Further logs can be added and removed as you see fit in the
``network.py`` console.
::

    netscool.log.add(<logger name>)
    netscool.log.remove(<logger name>)

To figure out what logger names are valid.
::

    netscool.log.list_all()

To list the current logs being displayed.
::

    netscool.log.list()

"""
import logging

# List of logger names we want to see logs from.
_name_filters = []

def add(name):
    """
    Add a logger to the list of loggers we want to see logs from.

    :param name: Name of logger to add.
    """
    global _name_filters
    if name in _name_filters:
        return
    _name_filters.append(name)

def remove(name):
    """
    Remove a logger from the list of loggers we want to see logs from.

    :param name: Name of logger to remove.
    """
    global _name_filters
    if name not in _name_filters:
        return
    _name_filters.remove(name)

def clear():
    """
    Clear list of loggers we want to see. Won't see any logs until a
    logger is added user add().
    """
    global _name_filters
    _name_filters = []

def list():
    """
    List loggers we will see logs for.
    """
    global _name_filters
    print("Showing logs for ...")
    for name in _name_filters:
        print("\t", name)

def list_all(list_filter=''):
    """
    List all loggers

    :param list_filter: Only show loggers that start with this string
        eg. netscool.layer1
    """
    loggers = logging.root.manager.loggerDict.keys()
    for name in sorted(loggers):
        if not name.startswith(list_filter):
            continue
        print(name)

class LogFilter():
    """
    Filter to only show logs that we have said we want to see with add().
    """
    def filter(self, record):
        global _name_filters
        for name_filter in _name_filters:
            if record.name.startswith(name_filter):
                return True
        return False

def setup(log_format="%(message)s"):
    """
    Setup logger to show logs we are interested in.

    :param log_format: Format of log message. See python logging
        documentation for possible fields.
    """
    logger = logging.getLogger()
    logger.handlers = []

    log_handler = logging.StreamHandler()
    log_handler.setFormatter(logging.Formatter(log_format))
    log_handler.addFilter(LogFilter())

    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
