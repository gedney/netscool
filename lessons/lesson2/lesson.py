import time
import collections

import pytest
import IPython
from scapy.all import Ether

import netscool
import netscool.layer1
import netscool.layer2

# These are classes you should have made in lesson 1. Replace <your_module>
# with your own module. Doing "from <module> import <object>" is generally
# discouraged because it removes the namespace for whatever is being
# imported, and increases the risk of name conflicts. Here we are doing
# it intentionally so you dont have to update every existing reference to
# these classes in this file, and to make it clear which classes you need
# to provide.
#from <your_module> import L2Device, L2Interface

import netscool._answer
m = netscool._answer._answers_module('lesson1')
L2Device = m.L2Device
L2Interface = m.L2Interface

class Switch(netscool.layer1.BaseDevice):
    """
    A basic switch with a CAM table.
    """
    # A namedtuple for CAM table entries. Every entry has an interface to
    # send frames out of, and the last time we saw a frame for this entry
    # so we can time it out. 
    CAMEntry = collections.namedtuple(
        'CAMEntry', ['interface', 'last_seen'])

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

netscool._answer._answers(locals())
if __name__ == "__main__":
    switch = Switch(
        "sw0", "00:00:00:00:00:00",  [
            L2Interface("0/1", "00:00:00:00:00:01"),
            L2Interface("0/2", "00:00:00:00:00:02"),
            L2Interface("0/3", "00:00:00:00:00:03")
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


    cable = netscool.layer1.SocketCable(44444, 33333)
    switch.interface('0/3').plug_cable(cable)

    # Some example frames. 
    frame_to_dev1 = Ether(
        src="22:22:22:22:22:00", dst="22:22:22:22:22:01")
    frame_to_dev2 = Ether(
        src="22:22:22:22:22:00", dst="22:22:22:22:22:02")
    frame_to_dev3 = Ether(
        src="22:22:22:22:22:00", dst="22:22:22:22:22:03")

    try:
        switch.start()
        device.start()
        IPython.embed()
    finally:
        switch.shutdown()
        device.shutdown()

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

    event = netscool.Event()
    try:
        switch.start()
        device0.start()
        device1.start()

        while event.wait:
            with event.conditions:
                assert device0.interface('0/0').upup
                assert device1.interface('0/0').upup
                assert switch.interface('0/0').upup
                assert switch.interface('0/1').upup

        yield switch, device0, device1

    finally:
        switch.shutdown()
        device0.shutdown()
        device1.shutdown()
        while event.wait:
            with event.conditions:
                assert not device0.powered
                assert not device1.powered
                assert not switch.powered

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

    event = netscool.Event()
    try:
        switch.start()
        device0.start()
        device1.start()
        device2.start()
        while event.wait:
            with event.conditions:
                assert device0.interface('0/0').upup
                assert device1.interface('0/0').upup
                assert device2.interface('0/0').upup
                assert switch.interface('0/0').upup
                assert switch.interface('0/1').upup
                assert switch.interface('0/2').upup
        yield switch, device0, device1, device2

    finally:
        switch.shutdown()
        device0.shutdown()
        device1.shutdown()
        device2.shutdown()

        while event.wait:
            with event.conditions:
                assert not device0.powered
                assert not device1.powered
                assert not device2.powered
                assert not switch.powered

def test_populate_cam_table(two_device_network):
    """
    Test CAM table is properly populated when the switch receives frames.
    """
    event = netscool.Event()
    switch, device0, device1 = two_device_network
    to_device0 = Ether(
        src='11:11:11:11:11:01', dst='11:11:11:11:11:00')
    to_device1 = Ether(
        src='11:11:11:11:11:00', dst='11:11:11:11:11:01')

    send_interface = device0.interface('0/0')
    recv_interface = device1.interface('0/0')
    send_interface.send(to_device1)
    while event.wait:
        with event.conditions:
            assert send_interface.captured(to_device1, netscool.DIR_OUT)
            assert recv_interface.captured(to_device1, netscool.DIR_IN)

            assert len(switch.cam) == 1
            mac = send_interface.mac
            assert mac in switch.cam
            assert switch.cam[mac].interface == switch.interface('0/0')
    netscool.clear_captures(device0, device1, switch)

    send_interface = device1.interface('0/0')
    recv_interface = device0.interface('0/0')
    send_interface.send(to_device0)

    while event.wait:
        with event.conditions:
            assert send_interface.captured(to_device0, netscool.DIR_OUT)
            assert recv_interface.captured(to_device0, netscool.DIR_IN)

            assert len(switch.cam) == 2
            mac = send_interface.mac
            assert mac in switch.cam
            assert switch.cam[mac].interface == switch.interface('0/1')
    netscool.clear_captures(device0, device1, switch)

def test_flood_frames(three_device_network):
    """
    Test switch appropriately floods frames.
    """
    event = netscool.Event()
    sw, dev0, dev1, dev2 = three_device_network

    to_dev0 = Ether(src='11:11:11:11:11:01', dst='11:11:11:11:11:00')
    to_dev1 = Ether(src='11:11:11:11:11:00', dst='11:11:11:11:11:01')

    # Frame should be flooded to device1 and device2
    dev0.interface('0/0').send(to_dev1)
    while event.wait:
        with event.conditions:

            # Frame should got out dev0 but shouldn't be flooded back in.
            assert dev0.interface('0/0').captured(
                to_dev1, netscool.DIR_OUT)
            assert not dev0.interface('0/0').captured(
                to_dev1, netscool.DIR_IN)

            # Frame should come in 0/0 on switch an be flooded out 0/1 and
            # 0/2.
            assert sw.interface('0/0').captured(to_dev1, netscool.DIR_IN)
            assert sw.interface('0/1').captured(to_dev1, netscool.DIR_OUT)
            assert sw.interface('0/2').captured(to_dev1, netscool.DIR_OUT)
            assert not sw.interface('0/0').captured(
                to_dev1, netscool.DIR_OUT)

            # dev1 should get frame.
            assert dev1.interface('0/0').captured(to_dev1, netscool.DIR_IN)

            # Frame was flooded to dev2 but it should have dropped it.
            assert not dev2.interface('0/0').captured(to_dev1)
    netscool.clear_captures(dev0, dev1, dev2, sw)

    dev1.interface('0/0').send(to_dev0)
    while event.wait:
        with event.conditions:
            # Frame should got out dev1 and shouldnt come back in.
            assert dev1.interface('0/0').captured(
                to_dev0, netscool.DIR_OUT)
            assert not dev1.interface('0/0').captured(
                to_dev0, netscool.DIR_IN)

            # Frame should come in 0/1 on switch an be sent out 0/0 only.
            assert sw.interface('0/1').captured(to_dev0, netscool.DIR_IN)
            assert sw.interface('0/0').captured(to_dev0, netscool.DIR_OUT)
            assert not sw.interface('0/2').captured(to_dev0)
            assert not sw.interface('0/1').captured(
                to_dev0, netscool.DIR_OUT)

            # dev0 should get frame.
            assert dev0.interface('0/0').captured(to_dev0, netscool.DIR_IN)

            # dev2 should not see the frame.
            assert not dev2.interface('0/0').captured(to_dev0)
    netscool.clear_captures(dev0, dev1, dev2, sw)

def test_cam_entry_timeout(two_device_network):
    """
    Test CAM table entries expire as expected.
    """
    event = netscool.Event()
    sw, dev0, dev1 = two_device_network

    to_dev1 = Ether(src='11:11:11:11:11:00', dst='11:11:11:11:11:01')

    dev0.interface('0/0').send(to_dev1)
    while event.wait:
        with event.conditions:

            # dev1 should get frame, and CAM table should be populated.
            assert dev1.interface('0/0').captured(to_dev1, netscool.DIR_IN)
            assert len(sw.cam) == 1
            mac = dev0.interface('0/0').mac
            assert mac in sw.cam
            assert sw.cam[mac].interface == sw.interface('0/0')

    # Set timeout to a short time and wait for entries to expire.
    sw.cam_timeout = 2
    start = time.time()
    while event.wait:
        with event.conditions:
            assert len(sw.cam) == 0

    # The cam timeout doesnt happen at the exact time. As long as its
    # within a reasonable range thats fine.
    assert sw.cam_timeout <= time.time() - start <= sw.cam_timeout + 1
