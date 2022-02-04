"""
Classes and utilities for the netscool.Event mechanism.
"""
import traceback
import time

class Event():
    """
    There are many operations in netscool that don't happen instantly eg.
     * Powering on a device.
     * Interfaces negotiating up/up.
     * A sent packet being received.

    This means in our tests whenever we do one of these operations we
    have to wait some amount of time before asserting the result. The
    amount of time we have to wait is arbitrary depending on the
    operation.

    One option is to sleep some amount of time after the operation and
    hope the result has happened. Another option is to poll for the
    result until it happens, and giveup after a certain number of retries
    or time period if it doesnt happen.

    The Event class provides a wrapper around this polling logic so that
    we can wait for an arbitrary set of assert conditions to be true
    after doing an operation. It is roughly equivalent to
    ::

        <do something>
        wait = True
        start = time.time()
        max_time = 5
        exceptions = []
        while wait:
            try:
                assert <result condition 1>
                assert <result condition 2>
            except AssertionError as e:
                exceptions.append(e)
                if (time.time() - start > max_time):
                    raise Exception(join_exceptions(exceptions))
                continue
            wait = False

    This becomes
    ::

        <do something>
        event = Event()
        while event.wait:
            with event.conditions:
                assert <result condition 1>
                assert <result condition 2>

    If the conditions are all true then ``event.wait`` will be set False
    and the loop will end. If the conditions are not all True after the
    timeout (default 5 seconds), then a ``ConditionsNotMetError`` will be
    raised.

    This ``ConditionsNotMetError`` shows relevant ``AssertionError`` that
    have been raised during the ``while`` loop. Contiguous blocks of the
    same ``assert`` failing are deduplicated. Any other types of
    exception raised during the ``while`` loop will not be captured by
    the ``Event`` and will propagate as usual.

    The ``Event`` object "resets" after each use, so can be reused
    multiple times.
    ::

        event = Event()

        <do something>
        while event.wait:
            with event.conditions:
                assert <condition>

        <do something else>
        while event.wait:
            with event.conditions:
                assert <a different condtion>
    """
    def __init__(self, timeout=5):
        self._wait = True
        self.conditions = _ConditionsBlock(self, timeout)

    @property
    def wait(self):
        wait = self._wait
        if not wait:
            self._wait = True
        return wait

class ConditionsNotMetError(Exception):
    """
    Error raised when conditions for ``Event`` aren't true before the
    event timeout.
    """
    pass

class _ConditionsBlock():
    """
    Context manager to suppress ``AssertionError`` exceptions so a set of
    ``assert`` statements can be polled in a loop.
    """
    def __init__(self, event, timeout):
        self.event = event
        self._timeout = timeout
        self.reset()

    def reset(self):
        """
        Whenever the condition block has determined an outcome (the block
        matches or doesnt match), then we need to reset the condition
        block state so it can be reused.
        """
        self.suppressed = []
        self._start = None

    def _add_suppressed(self, exception):
        """
        Add an exception to the list of suppressed exceptions. If the
        exception has the same filename, line number and message as the
        last suppressed exception then it is ignored.

        :param exception: Exception to add to the suppressed list.
        """
        new_line_number = exception.__traceback__.tb_lineno
        new_filename = exception.__traceback__.tb_frame.f_code.co_filename
        new_message = str(exception)

        if self.suppressed:
            exp = self.suppressed[-1]
            line_number = exp.__traceback__.tb_lineno
            filename = exp.__traceback__.tb_frame.f_code.co_filename
            message = str(exp)
            if (line_number == new_line_number and
                filename == new_filename and
                message == new_message):
                return

        self.suppressed.append(exception)

    def _conditions_failed(self):
        """
        Raise a ConditionsNotMetError when the condition block has not
        succeeded before the specified timeout.
        """
        # Join together the formatted exception string for each
        # suppressed exception into a single message. This is the best
        # way I know of to "combine" exceptions together.
        msg = []
        for exception in self.suppressed:
            tb = exception.__traceback__
            msg += traceback.format_exception(
                exception, value=exception, tb=tb)

        self.reset()
        raise ConditionsNotMetError(''.join(msg))

    def __enter__(self):
        if self._start is None:
            self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type and issubclass(exc_type, AssertionError):

            self._add_suppressed(exc_value)

            # We haven't managed to match the condition block before the
            # timeout so the condition block fails.
            if time.time() - self._start > self._timeout:
                self._conditions_failed()
                return False

            # This iteration didnt match the condition block, but we
            # havent reached the timeout so suppress the exception and try
            # again.
            self.event._wait = True
            time.sleep(0.1)
            return True

        # No exception has been raised so the block has passed, we need
        # to tell the event to stop looping.
        if exc_type is None and exc_value is None and traceback is None:
            self.event._wait = False

        # No AssertionError's were raised so either the condtion block
        # passed with no errors, or another type of exception has been
        # raised. Either way the event is over, so reset the condition
        # block and return normally from the context manager.
        self.reset()
        return False
