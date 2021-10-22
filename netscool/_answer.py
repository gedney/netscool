import os
import re
import sys
import inspect
import importlib

def _answers_module(lesson_name):
    # Import the tests/lessons/test_<lesson_name>.py module. This module
    # should provide example implementations for a lesson.
    path = os.path.join(os.path.dirname(__file__), '../tests/lessons')
    sys.path.append(path)
    module_name = "test_{}".format(lesson_name)
    module = importlib.import_module(module_name)
    return module

def _answers(_locals):
    # This is a handy function to use when manually testing lessons work.
    # Every lesson should have a corresponding test file at
    # tests/lessons/test_<lesson>.py. The test file should have example
    # implementations of the classes that need to be implemented for that
    # lesson. This function does several gross things to monkey patch the
    # example implementations from the test into the lesson.
    #
    #  * Gets the lesson name from the __file__ in _locals eg. lesson1.
    #  * Imports the test_<lesson>.py file by modifying sys.path
    #  * Replaces classes in _locals if there is a same named class in
    #    test_<lesson>.py
    #
    # The original lesson.py module will have its partial implementations
    # overwritten with the example implementations from the test file.
    # This function must be called after the classes to be overwritten
    # have been declared.
    # Example usages: netscool._answers(locals())

    # Make a backup of sys.path so we can restore it when we are done.
    orig_path = sys.path.copy()
    try:

        # Find the lesson name eg. lesson1, in the file path of the
        # lesson.py file.
        filepath = os.path.abspath(_locals["__file__"])
        file_re = re.compile(r"[\S/]+/(lesson[0-9]+)/lesson\.py")
        match = file_re.match(filepath)
        if not match:
            raise Exception(
                "Could not find lesson name in '{}'".format(filepath))
        lesson_name = match.group(1)

        module = _answers_module(lesson_name)

        # Override classes in lesson.py that also have implementations in
        # test_<lesson>.py. This only checks they are both classes and
        # have the same name.
        for class_name, obj in _locals.items():
            if not inspect.isclass(obj):
                continue

            new_class = module.__dict__.get(class_name)
            if not inspect.isclass(new_class):
                continue
            _locals[class_name] = new_class

    finally:
        sys.path = orig_path
