import time
import pytest
import netscool
import netscool.event

def assert_exception_messages(message, expected_messages):
    """
    Utility to assert a list of assertion error strings appear in the
    correct order in the combined exception messages from a
    ConditionsNotMetError.

    :param message: Combined exception string from ConditionsNotMetError.
    :param expected_messages: List of messages we expect to see, in the
        spcified order.
    :raises: AssertionError for unexpected or excess messages.
    """
    split_token = "Traceback (most recent call last):"
    messages = [ m for m in message.split(split_token) if m ]

    for expected_message in expected_messages:
        message = messages.pop(0)
        assert expected_message in message
    assert not messages

def test_event_success():
    event = netscool.Event()
    start = time.time()

    a = 1
    while event.wait:
        with event.conditions:
            assert a == 1

    assert a == 1
    assert event.conditions.suppressed == []
    assert event.conditions._start == None
    assert time.time() - start < event.conditions._timeout

def test_event_eventual_success():
    event = netscool.Event()
    start = time.time()

    a = 0
    while event.wait:
        with event.conditions:
            a += 1
            assert a == 15

    assert a == 15
    assert event.conditions.suppressed == []
    assert event.conditions._start == None

    # There is a 0.1 second sleep so 15 loops should take ~1.5 seconds.
    assert time.time() - start < 2

def test_event_fail_with_default_timeout():
    event = netscool.Event()
    start = time.time()

    with pytest.raises(netscool.event.ConditionsNotMetError) as exc_info:
        a = 1
        while event.wait:
            with event.conditions:
                assert a == 2

    assert_exception_messages(
        str(exc_info.value), [f"AssertionError: assert {a} == 2"])
    assert event.conditions.suppressed == []
    assert event.conditions._start == None
    assert time.time() - start >= event.conditions._timeout

def test_event_fail_combined_exceptions():
    event = netscool.Event(timeout=1)
    start = time.time()

    loop = 0
    with pytest.raises(netscool.event.ConditionsNotMetError) as exc_info:
        while event.wait:
            with event.conditions:
                loop += 1

                # Duplicate exceptions combined.
                # AssertionError: assert 1 == 2
                if 0 < loop <= 2:
                    a = 1
                    assert a == 2

                # Alternating duplicates not combined.
                # AssertionError: assert 2 == 1
                # AssertionError: assert 2 == 0
                # AssertionError: assert 2 == 1
                # AssertionError: assert 2 == 0
                if 2 < loop <= 6:
                    a = 2
                    b = loop % 2
                    assert a == b

                # Custom messages work.
                # AssertionError: 7 != 1
                # AssertionError: 8 != 1
                if 6 < loop <= 8:
                    assert loop == 1, f"{loop} != 1"

                # Make sure the event doesnt pass and we get an
                # exception.
                # AssertionError: assert False     
                assert False

    assert_exception_messages(
        str(exc_info.value), [
            "AssertionError: assert 1 == 2",
            "AssertionError: assert 2 == 1",
            "AssertionError: assert 2 == 0",
            "AssertionError: assert 2 == 1",
            "AssertionError: assert 2 == 0",
            "AssertionError: 7 != 1",
            "AssertionError: 8 != 1",
            "AssertionError: assert False",
        ])

    assert event.conditions.suppressed == []
    assert event.conditions._start == None
    assert time.time() - start >= event.conditions._timeout

def test_event_unknown_exception():
    event = netscool.Event()
    start = time.time()

    with pytest.raises(Exception):
        a = 1
        while event.wait:
            with event.conditions:
                assert a == 1
                raise Exception("Unknown Error")

    assert a == 1
    assert event.conditions.suppressed == []
    assert event.conditions._start == None
    assert time.time() - start < event.conditions._timeout

def test_event_success_reuse():
    event = netscool.Event()
    a = 1

    start = time.time()
    while event.wait:
        with event.conditions:
            assert a == 1

    assert a == 1
    assert event.conditions.suppressed == []
    assert event.conditions._start == None
    assert time.time() - start < event.conditions._timeout

    start = time.time()
    while event.wait:
        with event.conditions:
            assert a == 1

    assert a == 1
    assert event.conditions.suppressed == []
    assert event.conditions._start == None
    assert time.time() - start < event.conditions._timeout

def test_event_fail_reuse():
    event = netscool.Event(timeout=1)
    a = 1

    start = time.time()
    with pytest.raises(netscool.event.ConditionsNotMetError):
        while event.wait:
            with event.conditions:
                assert a == 2

    assert event.conditions.suppressed == []
    assert event.conditions._start == None
    assert time.time() - start >= event.conditions._timeout

    start = time.time()
    with pytest.raises(netscool.event.ConditionsNotMetError):
        while event.wait:
            with event.conditions:
                assert a == 2

    assert event.conditions.suppressed == []
    assert event.conditions._start == None
    assert time.time() - start >= event.conditions._timeout

def test_event_exception_reuse():
    event = netscool.Event(timeout=1)
    a = 1

    start = time.time()
    with pytest.raises(Exception):
        while event.wait:
            with event.conditions:
                assert a == 1
                raise Exception("Unknown Error")

    assert event.conditions.suppressed == []
    assert event.conditions._start == None
    assert time.time() - start < event.conditions._timeout

    start = time.time()
    with pytest.raises(Exception):
        while event.wait:
            with event.conditions:
                assert a == 1
                raise Exception("Unknown Error")

    assert event.conditions.suppressed == []
    assert event.conditions._start == None
    assert time.time() - start < event.conditions._timeout
