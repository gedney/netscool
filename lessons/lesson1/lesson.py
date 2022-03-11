from scapy.all import Ether
import IPython
import netscool.layer1

class L2Device(netscool.layer1.BaseDevice):
    """
    A simple layer 2 device that logs any frame it receives. The
    interface we are making needs to be attached to a device, so this acts
    as a placeholder until we have built a more functional layer 2 device.
    """
    def event_loop(self):
        """
        Each device run in a seperate thread and call their ``event_loop``
        method at regular intervals. This simple event loop gets the next
        frame from the devices interfaces, and prints the frame.
        """
        for interface in self.interfaces:

            frame = interface.receive()
            if not frame:
                continue

            # TODO: Print or log the frame here.
            # Hint: frame.show(dump=True) will give a string with the
            # full details of the frame.

class L2Interface(netscool.layer1.L1Interface):
    """ A Layer 2 interface. """

    # Possible protocol status for our L2Interface.
    PROTOCOL_DOWN = 'down'
    PROTOCOL_UP = 'up'

    def __init__(self, name, mac, bandwidth=1000, mtu=1500, promiscuous=False):
        """
        :param name: Name of interface to make identification simpler.
        :param mac: Layer2 MAC address for interface in the form
            XX:XX:XX:XX:XX:XX. 
        :param bandwidth: Bandwidth of interfaces in bits per second.
        :param promiscuous: A promiscuous interface will accept frames
            destined to any MAC address. A non-promiscuous interface
            will drop frames that are not destined for it.
        """
        super().__init__(name, bandwidth)
        self.mac = mac
        self.promiscuous = promiscuous
        self.protocol_status = L2Interface.PROTOCOL_DOWN
        self.mtu = mtu
        self.maximum_frame_size = mtu + 18

    @property
    def protocol_up(self):
        """ Is the protocol status up (Layer2 connectivity). """
        # TODO: Return the protocol status for the interface.
        pass

    @property
    def upup(self):
        """
        True if the layer 1 line status and layer 2 protocol status are
        both up.
        """
        # TODO: Return True or False if interface is up/up or not.
        # Hint: L1Interface has a line_status member indicating the
        # status of the layer 1 link status.
        pass

    @property
    def status(self):
        """
        Get a tuple of the layer 1 line status and layer 2 protocol status
        for the interface.
        """
        # TODO: Return tuple of (line status, protocol status).
        # Hint: L1Interface has a line_status member indicating the
        # status of the layer 1 link status.
        pass

    def negotiate_connection(self):
        """
        Negotiate the Layer 2 protocol for the interface.
        """
        # This call negotiates the layer 1 link status. You can check the
        # layer 1 link is up using self.line_up
        super().negotiate_connection()

        # The main reasons the layer 2 link might fail to come up are
        # * The layer 1 link is not up (self.line_up).
        # * The layer 2 protocol on the other end of the link doesnt match
        #   or is incompatible.
        # * Something sets protocol status to 'err disabled' state
        #   eg. port security.
        # We are not implementing anything that would set 'err disabled'
        # (yet), and are only implementing one layer 2 protocol (Ethernet)
        # so the only reason for our layer 2 protocol to be down at the
        # moment is if the layer 1 link is not up.
        # TODO: Determine the protocol status for the interface.
        pass

    def receive(self):
        """
        Receive a layer 2 frame.

        :returns: Scapy Ether object of frame or None.
        """
        # This receives data from layer 1.
        data = super().receive()
        if not data:
            return None

        # There a few things that should be done when receiving a layer 2
        # frame
        #  * Check the layer 1 link and layer 2 protocol up ie. interface
        #    is up/up.
        #  * Check received data is less than maximum frame size.
        #  * Strip 4 byte FCS from end of data.
        #  * Convert the data we received from layer 1 to a Scapy Ether
        #    frame eg. frame = Ether(data).
        #  * If the interface is not in promiscuous mode then check the
        #    dst mac of the frame matches our mac.
        # If anything fails while receiving the frame return None to drop
        # the frame.
        #
        # Note: Ether(data) will throw an exception if data is not a valid
        # frame. Any unhandled exceptions will cause our device to
        # 'crash'. Be careful to handle exceptions appropriately.
        # TODO: Convert layer 1 data to layer 2 frame.
        pass

    def send(self, frame):
        """
        Send a layer 2 frame.

        :param frame: Scapy Ether object of frame.
        """
        # There are some things we should check before sending our frame.
        #  * Is the layer 1 link and layer 2 protocol up ie. interface
        #    up/up
        #  * Is the frame valid. We consider the frame valid if it is a
        #    Scapy Ether object.
        #  * Append 4 byte FCS to end of frame.
        #  * Is the total frame size less than maximum frame size.
        # TODO: Make sure we are sending a valid layer 2 frame.

        # This will send our frame to layer 1, where it will be sent
        # across the cable to the other attached interface.
        super().send(bytes(frame))

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.mac)

# Running lesson.py will put you into a sandbox where you can experiment
# and check your L2Interface implementation is working.
if __name__ == "__main__":
    interface = L2Interface("MyInterface", "22:22:22:22:22:22")
    device = L2Device('MyDevice', [interface])
    cable = netscool.layer1.SocketCable(22222, 11111)
    interface.plug_cable(cable)

    # Some example frames you can use in the interactive prompt.
    frame = Ether(src=interface.mac, dst="11:11:11:11:11:11")
    bad_frame = b'aaa'
    bad_dst_frame = Ether(src=interface.mac, dst='00:00:00:00:00:00')

    try:
        device.start()

        # Once at the IPython shell you can reference anything in the
        # current namespace eg.
        # > interface.send(frame)
        # > interface.send(bad_frame)
        # > device.interface('MyInterface').send(frame)
        # > interface.status
        IPython.embed()
    finally:
        device.shutdown()

# Here are some automated tests to check your L2Interface implementation
# is working as expected. These can be run using pytest (pytest assumes
# any function starting with 'test_' is a test).
# $ pytest lesson.py
# For more details on pytest see pytest documentation.
import pytest
import netscool
import netscool.layer2
# Note: Each device has its own event_loop running in a seperate thread
# to the main thread. This means that many actions are not instantaneous
# and instead take some time to propagate as each device runs its event
# loop. The netscool.Event class is used extensively throughout the tests
# to wait for events to propagate through the network. It is advised that
# you spend some time reading the documentation for the Event class and
# have an understanding of the why/how of its use.
@pytest.fixture
def network():
    """
    Create a simple 2 device network. 'device1' is our implementation
    (L2Device, L2Interface), and 'device2' is the reference
    implementation.
    """

    interface1 = L2Interface("Int1", "11:11:11:11:11:11")
    device1 = L2Device("Dev1", [interface1])

    interface2 = netscool.layer2.L2Interface("Int2", "22:22:22:22:22:22")
    device2 = netscool.layer2.L2Device("Dev2", [interface2])

    cable = netscool.layer1.Cable()
    interface1.plug_cable(cable)
    interface2.plug_cable(cable)

    event = netscool.Event()
    try:
        device1.start()
        device2.start()

        # Starting the devices is not instantaneous. The event will wait
        # until all assert statements in the condition block are true
        # before proceeding. If the statements arent eventually True then
        # an exception will be raised. See netscool.Event documentation
        # for more details.
        while event.wait:
            with event.conditions:
                assert device1.powered == True
                assert device2.powered == True
                assert device1.interface("Int1").powered == True
                assert device2.interface("Int2").powered == True
        yield device1, device2

    finally:
        device1.shutdown()
        device2.shutdown()
        while event.wait:
            with event.conditions:
                assert device1.powered == False
                assert device2.powered == False
    
def test_interface_status(network):
    """
    Test interface status transitions correctly.
    """
    event = netscool.Event()
    device1, device2 = network
    interface1 = device1.interface("Int1")
    interface2 = device2.interface("Int2")

    # Wait for interfaces to come up.
    while event.wait:
        with event.conditions:
            assert interface1.upup == True
            assert interface2.upup == True
            assert interface1.protocol_status == L2Interface.PROTOCOL_UP
            assert interface2.protocol_status == L2Interface.PROTOCOL_UP
            assert interface1.protocol_up == True
            assert interface2.protocol_up == True
            assert interface1.status == ('up', 'up')
            assert interface2.status == ('up', 'up')

    # Shutdown our interface and make sure the other interface goes down.
    interface1.shutdown()
    while event.wait:
        with event.conditions:
            assert interface1.upup == False
            assert interface2.upup == False
            assert interface1.protocol_up == False
            assert interface2.protocol_up == False
            assert interface1.status == ('admin down', 'down')
            assert interface2.status == ('down', 'down')

    # Bring the interfaces back up.
    interface1.no_shutdown()
    while event.wait:
        with event.conditions:
            assert interface1.upup == True
            assert interface2.upup == True

    # Shutdown the other interface and make sure our interface goes down.
    interface2.shutdown()
    while event.wait:
        with event.conditions:
            assert interface1.upup == False
            assert interface2.upup == False
            assert interface1.protocol_up == False
            assert interface2.protocol_up == False
            assert interface1.status == ('down', 'down')
            assert interface2.status == ('admin down', 'down')

    # Bring the interfaces back up.
    interface2.no_shutdown()
    while event.wait:
        with event.conditions:
            assert interface1.upup == True
            assert interface2.upup == True

    # Shutdown our device and make sure both interfaces go down.
    device1.shutdown()
    while event.wait:
        with event.conditions:
            assert interface1.upup == False
            assert interface2.upup == False
            assert interface1.protocol_up == False
            assert interface2.protocol_up == False
            assert interface1.status == ('down', 'down')
            assert interface2.status == ('down', 'down')

def test_interface_send_receive(network):
    """
    Test interface can send/receive from the reference interface.
    """
    event = netscool.Event()
    device1, device2 = network
    interface1 = device1.interfaces[0]
    interface2 = device2.interfaces[0]

    # Wait for interfaces to come up.
    while event.wait:
        with event.conditions:
            assert interface1.upup
            assert interface2.upup

    bad_frame = b'aaa'
    wrong_dst_frame = Ether(src=interface1.mac, dst='00:00:00:00:00:00')
    good_frame = Ether(src=interface1.mac, dst=interface2.mac)

    # It is very difficult to prove bad_frame and wrong_dst_frame are
    # never received. If the other interface sees good_frame but not the
    # others then we can be pretty sure they will never be received.
    interface1.send(bad_frame)
    interface1.send(wrong_dst_frame)
    interface1.send(good_frame)
    while event.wait:
        with event.conditions:
            # bad_frame is not valid at all so shouldnt be sent out
            # interface1 to begin with and definitely shouldnt be seen by
            # interface2
            assert not interface1.captured(bad_frame)
            assert not interface2.captured(bad_frame)

            # wrong_dst_frame should be sent out interface1 but should be
            # dropped by interface2.
            assert interface1.captured(wrong_dst_frame, netscool.DIR_OUT)
            assert not interface2.captured(wrong_dst_frame)

            # good_frame should be seen by both interfaces.
            assert interface2.captured(good_frame, netscool.DIR_IN)
            assert interface1.captured(good_frame, netscool.DIR_OUT)

    interface1.clear_capture()
    interface2.clear_capture()

    # Send frames in the opposite direction to make sure our
    # implementation can also receive properly.
    wrong_dst_frame = Ether(src=interface2.mac, dst='00:00:00:00:00:00')
    good_frame = Ether(src=interface2.mac, dst=interface1.mac)

    interface2.send(bad_frame)
    interface2.send(wrong_dst_frame)
    interface2.send(good_frame)
    while event.wait:
        with event.conditions:
            assert not interface2.captured(bad_frame)
            assert not interface1.captured(bad_frame)

            assert interface2.captured(wrong_dst_frame, netscool.DIR_OUT)
            assert not interface1.captured(wrong_dst_frame)

            assert interface2.captured(good_frame, netscool.DIR_OUT)
            assert interface1.captured(good_frame, netscool.DIR_IN)

    interface1.clear_capture()
    interface2.clear_capture()

    # Set our interface as promiscuous and make sure we receive
    # wrong_dst_frame as well as good_frame. 
    interface1.promiscuous = True

    interface2.send(bad_frame)
    interface2.send(wrong_dst_frame)
    interface2.send(good_frame)
    while event.wait:
        with event.conditions:
            assert not interface2.captured(bad_frame)
            assert not interface1.captured(bad_frame)

            assert interface2.captured(wrong_dst_frame, netscool.DIR_OUT)
            assert interface1.captured(wrong_dst_frame, netscool.DIR_IN)

            assert interface2.captured(good_frame, netscool.DIR_OUT)
            assert interface1.captured(good_frame, netscool.DIR_IN)

    interface1.clear_capture()
    interface2.clear_capture()

def test_interface_mtu(network):
    event = netscool.Event()
    device1, device2 = network
    
    interface1 = device1.interface("Int1")
    interface2 = device2.interface("Int2")

    # Wait for interfaces to come up.
    while event.wait:
        with event.conditions:
            assert interface1.upup
            assert interface2.upup

    mtu = interface1.mtu
    big_frame = Ether(src=interface1.mac, dst=interface2.mac)/('A' * (mtu + 1))
    mtu_frame = Ether(src=interface1.mac, dst=interface2.mac)/('A' * mtu)

    interface1.send(big_frame)
    interface1.send(mtu_frame)
    while event.wait:
        with event.conditions:
            assert not interface2.captured(big_frame)
            assert not interface1.captured(big_frame)

            assert interface1.captured(mtu_frame, netscool.DIR_OUT)
            assert interface2.captured(mtu_frame, netscool.DIR_IN)

    interface1.mtu = 2000
    interface1.maximum_frame_size = 2018

    interface1.send(big_frame)
    interface1.send(mtu_frame)
    while event.wait:
        with event.conditions:
            assert interface1.captured(big_frame, netscool.DIR_OUT)
            assert not interface2.captured(big_frame)

            assert interface1.captured(mtu_frame, netscool.DIR_OUT)
            assert interface2.captured(mtu_frame, netscool.DIR_IN)
