import time
import pytest
import netscool
import netscool.layer1

@pytest.fixture
def network(request):
    """
    An indirect fixture to allow us to run the same test against multiple
    fixtures.
    eg. Run a test with the basic_network and basic_socket_network. 
    @pytest.mark.parametrize(
        'network',
        ['basic_network', 'basic_socket_network'],
        indirect=True)

    """
    return request.getfixturevalue(request.param)

@pytest.fixture
def basedevice():
    """
    A single device with two interfaces.
    """
    int1 = netscool.layer1.L1Interface('int1')
    int2 = netscool.layer1.L1Interface('int2') 
    dev = netscool.layer1.BaseDevice('dev', [int1, int2])
    try:
        yield dev, int1, int2
    finally:
        dev.shutdown()

@pytest.fixture
def basic_network_unplugged():
    """
    A basic 2 device layer1 network.
    """
    dev1 = netscool.layer1.BaseDevice(
        'dev1', [
            netscool.layer1.L1Interface('0/0')])
    dev2 = netscool.layer1.BaseDevice(
        'dev2', [
            netscool.layer1.L1Interface('0/0')])
    dev1.event_loop = lambda *args: None
    dev2.event_loop = lambda *args: None
    cable = netscool.layer1.Cable()

    event = netscool.Event()
    try:
        dev1.start()
        dev2.start()

        while event.wait:
            with event.conditions:
                assert dev1.powered == True
                assert dev2.powered == True
                assert dev1.interface('0/0').powered == True
                assert dev2.interface('0/0').powered == True

        yield dev1, dev2, cable
    finally:
        dev1.shutdown()
        dev2.shutdown()
        while event.wait:
            with event.conditions:
                assert dev1.powered == False
                assert dev2.powered == False

@pytest.fixture
def basic_network(basic_network_unplugged):
    dev1, dev2, cable = basic_network_unplugged
    int1 = dev1.interface('0/0')
    int2 = dev2.interface('0/0')

    int1.plug_cable(cable)
    int2.plug_cable(cable)

    event = netscool.Event()
    while event.wait:
        with event.conditions:
            assert int1.line_up
            assert int2.line_up
    yield dev1, dev2

@pytest.fixture
def basic_socket_network_unplugged():
    """
    A basic 2 device layer1 network connected with a SocketCable.
    """
    dev1 = netscool.layer1.BaseDevice(
        'dev1', [
            netscool.layer1.L1Interface('0/0')])
    dev2 = netscool.layer1.BaseDevice(
        'dev2', [
            netscool.layer1.L1Interface('0/0')])
    dev1.event_loop = lambda *args: None
    dev2.event_loop = lambda *args: None
    sockcable1 = netscool.layer1.SocketCable(11111, 22222)
    sockcable2 = netscool.layer1.SocketCable(22222, 11111)

    try:
        dev1.start()
        dev2.start()

        event = netscool.Event()
        while event.wait:
            with event.conditions:
                assert dev1.powered == True
                assert dev2.powered == True
                assert dev1.interface('0/0').powered == True
                assert dev2.interface('0/0').powered == True

        yield dev1, dev2, sockcable1, sockcable2
    finally:
        dev1.shutdown()
        dev2.shutdown()
        while event.wait:
            with event.conditions:
                assert dev1.powered == False
                assert dev2.powered == False
        sockcable1.socket.close()
        sockcable2.socket.close()

@pytest.fixture
def basic_socket_network(basic_socket_network_unplugged):
    dev1, dev2, cable1, cable2 = basic_socket_network_unplugged
    int1 = dev1.interface('0/0')
    int2 = dev2.interface('0/0')

    int1.plug_cable(cable1)
    int2.plug_cable(cable2)

    event = netscool.Event()
    while event.wait:
        with event.conditions:
            assert int1.line_up
            assert int2.line_up

    yield dev1, dev2

def test_basedevice_interface(basedevice):
    """
    Test BaseDevice.interface().
    """
    dev, int1, int2 = basedevice
    assert dev.interface('int1') == int1
    assert dev.interface('int2') == int2
    assert dev.interface('fake') == None

def test_basedevice_start_stop(basedevice):
    """
    Test start and stopping a device works.
    """
    dev, int1, int2 = basedevice
    dev.event_loop = lambda *args: None

    assert dev.powered == False
    assert dev._thread == None
    assert dev.event_loop_exception == None
    assert int1.powered == False
    assert int2.powered == False

    event = netscool.Event()

    dev.start()
    while event.wait:
        with event.conditions:
            assert dev.powered == True
            assert dev._thread
            assert dev._thread.is_alive() == True
            assert dev.event_loop_exception == None
            assert int1.powered == True
            assert int2.powered == True

    dev.shutdown()
    while event.wait:
        with event.conditions:
            assert dev.powered == False
            assert dev._thread == None
            assert dev.event_loop_exception == None
            assert int1.powered == False
            assert int2.powered == False

def test_basedevice_eventloop_error(basedevice):
    """
    Test a device gracefuly shuts down if an exception is thrown in its
    event_loop.
    """
    def event_loop(*args):
        raise Exception("Event Loop Error")

    dev, int1, int2 = basedevice
    dev.event_loop = event_loop
    assert dev.powered == False
    assert dev._thread == None
    assert int1.powered == False
    assert int2.powered == False

    dev.start()

    
    # The event loop failing is not instant. So we have to wait for the
    # device to "crash" after starting it.
    event = netscool.Event()
    while event.wait:
        with event.conditions:
            assert dev.powered == False
            assert dev.event_loop_exception != None
            assert isinstance(dev.event_loop_exception, Exception)
            assert str(dev.event_loop_exception) == "Event Loop Error"

            # When a device crashes the internal event_loop thread will
            # still exist, it just wont be alive anymore. This is because
            # it isnt practical to set dev._thread to None from inside the
            # thread, and ultimately doesnt make a significant difference.
            assert dev._thread != None
            assert dev._thread.is_alive() == False
            assert int1.powered == False
            assert int2.powered == False

    # Set the event_loop to a valid not crashing function, and make sure
    # we can start the device again.
    dev.event_loop = lambda *args: None

    dev.start()
    while event.wait:
        with event.conditions:
            assert dev.powered == True
            assert dev._thread != None
            assert dev._thread.is_alive() == True
            assert dev.event_loop_exception == None
            assert int1.powered == True
            assert int2.powered == True

    dev.shutdown()
    while event.wait:
        with event.conditions:
            assert dev.powered == False
            assert dev._thread == None
            assert dev.event_loop_exception == None
            assert int1.powered == False
            assert int2.powered == False

def test_plugin_cable(basic_network_unplugged):
    """
    Test plugging and unplugging cable from interface causes it to go
    up/down appropriately.
    """
    dev1, dev2, cable = basic_network_unplugged
    int1 = dev1.interface('0/0')
    int2 = dev2.interface('0/0')

    # Interfaces should be down because no cable is plugged into either
    # interface.
    assert int1.status == netscool.layer1.LINE_DOWN
    assert int2.status == netscool.layer1.LINE_DOWN
    assert cable.active == False

    event = netscool.Event()

    # Plug cable into one interface. Doesnt come up because the other end
    # is still unplugged.
    int1.plug_cable(cable)
    while event.wait:
        with event.conditions:
            assert int1.status == netscool.layer1.LINE_DOWN
            assert int2.status == netscool.layer1.LINE_DOWN
            assert cable.active == False

    # Plug other end of cable in. Both interfaces should come up and the
    # cable should be active.
    int2.plug_cable(cable)
    while event.wait:
        with event.conditions:
            assert int1.status == netscool.layer1.LINE_UP
            assert int2.status == netscool.layer1.LINE_UP
            assert cable.active == True

    # Unplug the first end, both interfaces should go down.
    int1.unplug_cable(cable)
    while event.wait:
        with event.conditions:
            assert int1.status == netscool.layer1.LINE_DOWN
            assert int2.status == netscool.layer1.LINE_DOWN
            assert cable.active == False

    # Re-plugin the first end, both interfaces should come up and the
    # cable should be active.
    int1.plug_cable(cable)
    while event.wait:
        with event.conditions:
            assert int1.status == netscool.layer1.LINE_UP
            assert int2.status == netscool.layer1.LINE_UP
            assert cable.active == True

def test_plugin_socketcable(basic_socket_network_unplugged):
    """
    Test plugging and unplugging a socketcable from interface causes it
    to go up/down appropriately.
    """
    dev1, dev2, cable1, cable2 = basic_socket_network_unplugged
    int1 = dev1.interface('0/0')
    int2 = dev2.interface('0/0')
    
    assert int1.status == netscool.layer1.LINE_DOWN
    assert int2.status == netscool.layer1.LINE_DOWN
    assert not int1.line_up
    assert not int2.line_up
    assert cable1.active == False
    assert cable2.active == False

    event = netscool.Event()

    int1.plug_cable(cable1)
    while event.wait:
        with event.conditions:
            assert int1.status == netscool.layer1.LINE_DOWN
            assert int2.status == netscool.layer1.LINE_DOWN
            assert not int1.line_up
            assert not int2.line_up
            assert cable1.active == False
            assert cable2.active == False

    int2.plug_cable(cable2)
    while event.wait:
        with event.conditions:
            assert int1.status == netscool.layer1.LINE_UP
            assert int2.status == netscool.layer1.LINE_UP
            assert int1.line_up
            assert int2.line_up
            assert cable1.active == True
            assert cable2.active == True

    int1.unplug_cable(cable1)
    while event.wait:
        with event.conditions:
            assert int1.status == netscool.layer1.LINE_DOWN
            assert int2.status == netscool.layer1.LINE_DOWN
            assert not int1.line_up
            assert not int2.line_up
            assert cable1.active == False
            assert cable2.active == False

    int1.plug_cable(cable1)
    while event.wait:
        with event.conditions:
            assert int1.status == netscool.layer1.LINE_UP
            assert int2.status == netscool.layer1.LINE_UP
            assert int1.line_up
            assert int2.line_up
            assert cable1.active == True
            assert cable2.active == True

@pytest.mark.parametrize(
    'network', ['basic_network', 'basic_socket_network'], indirect=True)
def test_interface_shutdown(network):
    """
    Test when an interface is shutdown the link goes down, and the
    interface state remains in ADMIN_DOWN when plugging and unplugging
    the cable.
    """
    dev1, dev2 = network
    int1 = dev1.interface('0/0')
    int2 = dev2.interface('0/0')

    event = netscool.Event()
    assert int1.status == netscool.layer1.LINE_UP
    assert int2.status == netscool.layer1.LINE_UP

    int1.shutdown()
    while event.wait:
        with event.conditions:
            assert int1.status == netscool.layer1.LINE_ADMIN_DOWN
            assert int2.status == netscool.layer1.LINE_DOWN
            assert not int1.line_up
            assert not int2.line_up

    int1.no_shutdown()
    while event.wait:
        with event.conditions:
            assert int1.status == netscool.layer1.LINE_UP
            assert int2.status == netscool.layer1.LINE_UP
            assert int1.line_up
            assert int2.line_up

    int2.shutdown()
    while event.wait:
        with event.conditions:
            assert int2.status == netscool.layer1.LINE_ADMIN_DOWN
            assert not int2.line_up

    cable = int2.cable
    int2.unplug_cable(cable)
    while event.wait:
        with event.conditions:
            assert int2.status == netscool.layer1.LINE_ADMIN_DOWN
            assert not int2.line_up

    int2.plug_cable(cable)
    while event.wait:
        with event.conditions:
            assert int2.status == netscool.layer1.LINE_ADMIN_DOWN
            assert not int2.line_up

    int2.no_shutdown()
    while event.wait:
        with event.conditions:
            assert int2.status == netscool.layer1.LINE_UP
            assert int2.line_up

@pytest.mark.parametrize(
    'network', ['basic_network', 'basic_socket_network'], indirect=True)
def test_interface_send_receive(network):
    """
    Test we can send some arbitrary layer 1 bytes from one interface to a
    connected interface.
    """
    dev1, dev2 = network
    int1 = dev1.interface('0/0')
    int2 = dev2.interface('0/0')

    event = netscool.Event()

    data = b'aaa'
    int1.send(data)
    while event.wait:
        with event.conditions:
            recv = int2.receive()
            assert recv == data 
            assert int1.captured(data, netscool.layer1.DIR_OUT)
            assert int2.captured(data, netscool.layer1.DIR_IN)
