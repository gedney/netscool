from scapy.all import Ether

import IPython

# This is some special boilerplate to tell netscool which lesson we are
# running. This becomes important when different lessons require different
# implementations of the same class. This should be done before any other
# netscool imports.
import netscool
netscool.lesson('lesson1')

import netscool.layer1

class L2Device(netscool.layer1.BaseDevice):
    """
    A simple layer 2 device that prints any frame it receives. The
    interface we are making needs to be attached to a device, so this acts
    as a placeholder until we have built a more functional layer 2 device.
    """
    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)

        # Keep track of the last frame the device received to make testing
        # easier.
        self.last_frame = None

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

            print("{} got frame\n{}".format(self, frame.show(dump=True)))
            self.last_frame = frame

class L2Interface(netscool.layer1.L1Interface):
    """ A Layer 2 interface. """

    # Possible protocol status for our L2Interface.
    PROTOCOL_DOWN = 'down'
    PROTOCOL_UP = 'up'

    def __init__(self, name, mac, speed=1000, promiscuous=False):
        """
        :param name: Name of interface to make identification simpler.
        :param mac: Layer2 MAC address for interface in the form
            XX:XX:XX:XX:XX:XX. 
        :param speed: Speed of interfaces in bits per second.
        :param promiscuous: A promiscuous interface will accept frames
            destined to any MAC address. A non-promiscuous interface
            will drop frames that are not destined for it.
        """
        super().__init__(name, speed)
        self.mac = mac
        self.promiscuous = promiscuous
        self.protocol_status = L2Interface.PROTOCOL_DOWN

    @property
    def protocol_up(self):
        """ Is the protocol status up (Layer2 connectivity). """
        pass

    @property
    def upup(self):
        """
        True if the layer 1 line status and layer 2 protocol status are
        both up.
        """
        # Hint: L1Interface has a line_status member indicating the
        # status of the layer 1 link status.
        pass

    @property
    def status(self):
        """
        Get a tuple of the layer 1 line status and layer 2 protocol status
        for the interface.
        """
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
        pass

    def receive(self):
        """
        Receive a layer 2 frame.

        :returns: Scapy Ether object of frame or None.
        """
        # There a few things that should be done when receiving a layer 2
        # frame
        #  * Check the layer 1 link and layer 2 protocol up ie. interface
        #    is up/up.
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

        # This receives data from layer 1.
        data = super().receive()
        if not data:
            return None
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

        # This will send our frame to layer 1, where it will be sent
        # across the cable the other attached interface.
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
import time
import pytest

# Note: The various sleeps throughout the tests are necessary because each
# devices event_loop has a delay between each run, and they don't run
# simultaneously. This means there is a delay between device.start() and
# interfaces transitioning to up/up. There is also a delay between sending
# out an interface and the remote end receiving for the same reason.
# Sleeping 0.5 seconds means every device will have a chance to run its
# event loop, and all actions in the network to take place.

@pytest.fixture
def network():
    interface1 = L2Interface("Int1", "11:11:11:11:11:11")
    interface2 = L2Interface("Int2", "22:22:22:22:22:22")
    device1 = L2Device("Dev1", [interface1])
    device2 = L2Device("Dev2", [interface2])
    cable = netscool.layer1.Cable()
    interface1.plug_cable(cable)
    interface2.plug_cable(cable)

    try:
        device1.start()
        device2.start()
        time.sleep(0.5)
        yield device1, device2

    finally:
        device1.shutdown()
        device2.shutdown()
    
def test_interface_status(network):

    device1, device2 = network
    interface1 = device1.interfaces[0]
    interface2 = device2.interfaces[0]

    assert interface1.upup == True
    assert interface2.upup == True
    assert interface1.protocol_status == L2Interface.PROTOCOL_UP
    assert interface2.protocol_status == L2Interface.PROTOCOL_UP
    assert interface1.protocol_up == True
    assert interface2.protocol_up == True
    assert interface1.status == ('up', 'up')
    assert interface2.status == ('up', 'up')

    interface2.shutdown()
    time.sleep(0.5)
    assert interface1.upup == False
    assert interface2.upup == False
    assert interface1.protocol_up == False
    assert interface2.protocol_up == False
    assert interface1.status == ('down', 'down')
    assert interface2.status == ('admin down', 'down')

    interface2.no_shutdown()
    time.sleep(0.5)

    device2.shutdown()
    time.sleep(0.5)
    assert interface1.upup == False
    assert interface2.upup == False
    assert interface1.protocol_up == False
    assert interface2.protocol_up == False
    assert interface1.status == ('down', 'down')
    assert interface2.status == ('down', 'down')

def test_interface_send_receive(network):
    device1, device2 = network
    interface1 = device1.interfaces[0]
    interface2 = device2.interfaces[0]

    good_frame = Ether(src=interface1.mac, dst=interface2.mac)
    wrong_dst_frame = Ether(src=interface1.mac, dst='00:00:00:00:00:00')
    bad_frame = b'aaa'

    interface1.send(good_frame)
    time.sleep(0.5)
    assert device2.last_frame == good_frame
    device2.last_frame = None

    interface1.send(wrong_dst_frame)
    time.sleep(0.5)
    assert device2.last_frame == None

    interface2.promiscuous = True
    interface1.send(wrong_dst_frame)
    time.sleep(0.5)
    assert device2.last_frame == wrong_dst_frame
    interface2.promiscuous = False
    device2.last_frame = None

    interface1.send(bad_frame)
    time.sleep(0.5)
    assert device2.last_frame == None
