import collections
from scapy.all import Ether
import IPython
import netscool.layer1

# These are classes that should have been made in previous lessons. If you
# would like to use your own implementations, import or copy them here,
# and remove these imports. Doing "from <module> import <object>" is
# generally discouraged because it removes the namespace for whatever is
# being imported, and increases the risk of name conflicts. Here we are
# doing it intentionally to make replacing these classes with your own
# implementation simpler.
from netscool.layer2 import L2Device
from netscool.layer2 import L2Interface

# If using the provided classes, setting up netscool logging will give you
# some output of what they are doing. You can also add similar logging to
# your own classes.
import netscool.log
netscool.log.setup()
netscool.log.add('netscool.layer2')

# A namedtuple for CAM table entries. Every entry has an interface to send
# frames out of, and the last time we saw a frame for this entry so we can
# time it out.
CAMEntry = collections.namedtuple('CAMEntry', ['interface', 'last_seen'])

class Switch(netscool.layer1.BaseDevice):
    """
    A basic switch with a CAM table.
    """
    def __init__(self, name, mac, interfaces):
        super().__init__(name, interfaces)

        # On top of each interface having a MAC, the switch also has its
        # own MAC. This is used as an identifier in some layer 2
        # protocols. You cannot send a frame to this address.
        self.mac = mac

        # The CAM (content addressable memory) table that tracks
        # interface -> MAC mappings. Once a MAC is 'learned' and in the
        # CAM table the switch no longer has to flood frames out every
        # interface to deliver the frame.
        self.cam = {}

        # If we dont see a MAC address for this many seconds, then remove
        # the mapping from the table. This timeout removes stale entries
        # from the table eg. A device in unplugged.
        self.cam_timeout = 300

        # Interfaces in a switch need to be in promiscuous mode because
        # they are generally forwarding frames not destined for them. If
        # they were not promiscuous they would drop all those frames
        # instead of forwarding them.
        for interface in self.interfaces:
            interface.promiscuous = True

    def show_cam(self):
        # This shoud print some details about the entries in the CAM table.
        pass

    def event_loop(self):
        # Things that our switch needs to do.
        #  * Timeout stale entries from the CAM table.
        #  * Check if the frame is destined for one of the switch
        #    interfaces (shouldn't forward anything for us).
        #  * Add source MAC for received frames to CAM table.
        #  * If we have a CAM entry for the destination MAC, send frame
        #    out that interface.
        #  * If we dont have a CAM entry for the destination MAC, flood
        #    the frame out every interface (except the interface we
        #    received it on).
        pass

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.mac)

# TODO: Remove.
from netscool.layer2 import Switch

if __name__ == "__main__":
    switch = Switch(
        "sw0", "00:00:00:00:00:00",  [
            L2Interface("0/1", "00:00:00:00:00:01"),
            L2Interface("0/2", "00:00:00:00:00:02")
        ])

    device = L2Device(
        "dev0", [
            L2Interface("0/1", "22:22:22:22:22:00")
        ])

    cable = netscool.layer1.Cable()
    device.interface('0/1').plug_cable(cable)
    switch.interface('0/2').plug_cable(cable)

    cable = netscool.layer1.SocketCable(22222, 11111)
    switch.interface('0/1').plug_cable(cable)

    # Some example frames. 
    frame_to_dev1 = Ether(
        src="22:22:22:22:22:00", dst="22:22:22:22:22:01")
    frame_to_dev2 = Ether(
        src="22:22:22:22:22:00", dst="22:22:22:22:22:02")

    try:
        switch.start()
        device.start()
        IPython.embed()
    finally:
        switch.shutdown()
        device.shutdown()

import time
import pytest

@pytest.fixture
def two_device_network():
    switch = Switch(
        'sw0', '00:00:00:00:00:00', [
            L2Interface('0/0', '00:00:00:00:00:01'),
            L2Interface('0/1', '00:00:00:00:00:02')])
    device0 = L2Device(
        'dev0', [
            L2Interface('0/0', '11:11:11:11:11:00')])
    device1 = L2Device(
        'dev1', [
            L2Interface('0/0', '11:11:11:11:11:01')])

    cable = netscool.layer1.Cable()
    switch.interface('0/0').plug_cable(cable)
    device0.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    switch.interface('0/1').plug_cable(cable)
    device1.interface('0/0').plug_cable(cable)

    try:
        switch.start()
        device0.start()
        device1.start()
        time.sleep(0.5)
        yield switch, device0, device1

    finally:
        switch.shutdown()
        device0.shutdown()
        device1.shutdown()

@pytest.fixture
def three_device_network():
    switch = Switch(
        'sw0', '00:00:00:00:00:00', [
            L2Interface('0/0', '00:00:00:00:00:01'),
            L2Interface('0/1', '00:00:00:00:00:02'),
            L2Interface('0/2', '00:00:00:00:00:03')])
    device0 = L2Device(
        'dev0', [
            L2Interface('0/0', '11:11:11:11:11:00')])
    device1 = L2Device(
        'dev1', [
            L2Interface('0/0', '11:11:11:11:11:01')])
    device2 = L2Device(
        'dev2', [
            L2Interface('0/0', '11:11:11:11:11:02')])

    cable = netscool.layer1.Cable()
    switch.interface('0/0').plug_cable(cable)
    device0.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    switch.interface('0/1').plug_cable(cable)
    device1.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    switch.interface('0/2').plug_cable(cable)
    device2.interface('0/0').plug_cable(cable)

    try:
        switch.start()
        device0.start()
        device1.start()
        device2.start()
        time.sleep(0.5)
        yield switch, device0, device1, device2

    finally:
        switch.shutdown()
        device0.shutdown()
        device1.shutdown()
        device2.shutdown()

def test_populate_cam_table(two_device_network):
    switch, device0, device1 = two_device_network
    frame_to_device0 = Ether(
        src='11:11:11:11:11:01', dst='11:11:11:11:11:00')
    frame_to_device1 = Ether(
        src='11:11:11:11:11:00', dst='11:11:11:11:11:01')

    send_interface = device0.interface('0/0')
    send_interface.send(frame_to_device1)
    time.sleep(0.5)

    assert device1.last_frame == frame_to_device1
    assert len(switch.cam) == 1
    assert send_interface.mac in switch.cam
    assert switch.cam[send_interface.mac].interface == switch.interface('0/0')

    send_interface = device1.interface('0/0')
    send_interface.send(frame_to_device0)
    time.sleep(0.5)

    assert device0.last_frame == frame_to_device0
    assert len(switch.cam) == 2
    assert send_interface.mac in switch.cam
    assert switch.cam[send_interface.mac].interface == switch.interface('0/1')

def test_flood_frames(three_device_network):
    switch, device0, device1, device2 = three_device_network

    # Make promiscuous so we can see frames flooded to these devices.
    device1.interface('0/0').promiscuous = True
    device2.interface('0/0').promiscuous = True

    frame_to_device0 = Ether(
        src='11:11:11:11:11:01', dst='11:11:11:11:11:00')
    frame_to_device1 = Ether(
        src='11:11:11:11:11:00', dst='11:11:11:11:11:01')

    # Frame should be flooded to device1 and device2
    send_interface = device0.interface('0/0')
    send_interface.send(frame_to_device1)
    time.sleep(0.5)

    assert device0.last_frame == None
    assert device1.last_frame == frame_to_device1
    assert device2.last_frame == frame_to_device1

    # Send frame so switch learns device1 MAC.
    send_interface = device1.interface('0/0')
    send_interface.send(frame_to_device0)
    time.sleep(0.5)

    # Reset last_frame for each device.
    device0.last_frame = None
    device1.last_frame = None
    device2.last_frame = None

    # Switch has learnt MAC for device1 so frame should only go there.
    send_interface = device0.interface('0/0')
    send_interface.send(frame_to_device1)
    time.sleep(0.5)

    assert device0.last_frame == None
    assert device1.last_frame == frame_to_device1
    assert device2.last_frame == None

def test_cam_entry_timeout(two_device_network):
    switch, device0, device1 = two_device_network

    frame_to_device1 = Ether(
        src='11:11:11:11:11:00', dst='11:11:11:11:11:01')

    send_interface = device0.interface('0/0')
    send_interface.send(frame_to_device1)
    time.sleep(0.5)

    assert device1.last_frame == frame_to_device1
    assert len(switch.cam) == 1
    assert send_interface.mac in switch.cam
    assert switch.cam[send_interface.mac].interface == switch.interface('0/0')

    switch.cam_timeout = 1
    # Theoretically the CAM table should timeout after 1 second, however
    # in practice the entries can only be removed when the switch event
    # loop runs. This means the timeout will probably take slightly more
    # than one second.
    time.sleep(1.5)

    assert len(switch.cam) == 0
