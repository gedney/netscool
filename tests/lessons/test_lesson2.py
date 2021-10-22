import time
import collections

import pytest
from scapy.all import Ether

import netscool
import netscool.layer1
import netscool.layer2

# Get classes that need to be reused from the previous lesson.
from tests.lessons.test_lesson1 import L2Device, L2Interface

class Switch(netscool.layer1.BaseDevice):
    """
    Test implementation of Switch for lesson2.
    """
    CAMEntry = collections.namedtuple(
        'CAMEntry', ['interface', 'last_seen'])

    def __init__(self, name, mac, interfaces):
        super().__init__(name, interfaces)
        self.mac = mac
        self.cam = {}
        self.cam_timeout = 300
        for interface in self.interfaces:
            interface.promiscuous = True

    def show_cam(self):
        pass

    def event_loop(self):
        self._timeout_cam_entries()

        for interface in self.interfaces:
            frame = interface.receive()
            if not frame:
                continue

            if self._is_local_frame(frame):
                continue

            src_mac = frame.src.lower()
            dst_mac = frame.dst.lower()
            self.cam[src_mac] = Switch.CAMEntry(interface, time.time())

            if dst_mac in self.cam:
                self.cam[dst_mac].interface.send(frame)
            else:
                self._flood(interface, frame)

    def _is_local_frame(self, frame):
        for interface in self.interfaces:
            if frame.dst.lower() == interface.mac.lower():
                return True
        return False

    def _flood(self, src_interface, frame):
        for interface in self.interfaces:
            if not interface.upup:
                continue
            if interface == src_interface:
                continue
            interface.send(frame)

    def _timeout_cam_entries(self):
        now = time.time()
        to_remove = []
        for mac, entry in self.cam.items():
            if now - self.cam_timeout > entry.last_seen:
                to_remove.append(mac)
        for mac in to_remove:
            self.cam.pop(mac)

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.mac)

#@pytest.fixture
#def two_device_network():
#    switch = Switch(
#        'sw0', '00:00:00:00:00:00', [
#            L2Interface('0/0', '00:00:00:00:00:01'),
#            L2Interface('0/1', '00:00:00:00:00:02')])
#    device0 = L2Device(
#        'dev0', [
#            L2Interface('0/0', '11:11:11:11:11:00')])
#    device1 = L2Device(
#        'dev1', [
#            L2Interface('0/0', '11:11:11:11:11:01')])
#
#    cable = netscool.layer1.Cable()
#    switch.interface('0/0').plug_cable(cable)
#    device0.interface('0/0').plug_cable(cable)
#
#    cable = netscool.layer1.Cable()
#    switch.interface('0/1').plug_cable(cable)
#    device1.interface('0/0').plug_cable(cable)
#
#    event = netscool.Event()
#    try:
#        switch.start()
#        device0.start()
#        device1.start()
#
#        while event.wait:
#            with event.conditions:
#                assert device0.interface('0/0').upup
#                assert device1.interface('0/0').upup
#                assert switch.interface('0/0').upup
#                assert switch.interface('0/1').upup
#
#        yield switch, device0, device1
#
#    finally:
#        switch.shutdown()
#        device0.shutdown()
#        device1.shutdown()
#        while event.wait:
#            with event.conditions:
#                assert not device0.powered
#                assert not device1.powered
#                assert not switch.powered
#
#@pytest.fixture
#def three_device_network():
#    switch = Switch(
#        'sw0', '00:00:00:00:00:00', [
#            L2Interface('0/0', '00:00:00:00:00:01'),
#            L2Interface('0/1', '00:00:00:00:00:02'),
#            L2Interface('0/2', '00:00:00:00:00:03')])
#    device0 = L2Device(
#        'dev0', [
#            L2Interface('0/0', '11:11:11:11:11:00')])
#    device1 = L2Device(
#        'dev1', [
#            L2Interface('0/0', '11:11:11:11:11:01')])
#    device2 = L2Device(
#        'dev2', [
#            L2Interface('0/0', '11:11:11:11:11:02')])
#
#    cable = netscool.layer1.Cable()
#    switch.interface('0/0').plug_cable(cable)
#    device0.interface('0/0').plug_cable(cable)
#
#    cable = netscool.layer1.Cable()
#    switch.interface('0/1').plug_cable(cable)
#    device1.interface('0/0').plug_cable(cable)
#
#    cable = netscool.layer1.Cable()
#    switch.interface('0/2').plug_cable(cable)
#    device2.interface('0/0').plug_cable(cable)
#
#    event = netscool.Event()
#    try:
#        switch.start()
#        device0.start()
#        device1.start()
#        device2.start()
#        while event.wait:
#            with event.conditions:
#                assert device0.interface('0/0').upup
#                assert device1.interface('0/0').upup
#                assert device2.interface('0/0').upup
#                assert switch.interface('0/0').upup
#                assert switch.interface('0/1').upup
#                assert switch.interface('0/2').upup
#        yield switch, device0, device1, device2
#
#    finally:
#        switch.shutdown()
#        device0.shutdown()
#        device1.shutdown()
#        device2.shutdown()
#
#        while event.wait:
#            with event.conditions:
#                assert not device0.powered
#                assert not device1.powered
#                assert not device2.powered
#                assert not switch.powered
#
#def test_populate_cam_table(two_device_network):
#    """
#    Test CAM table is properly populated when the switch receives frames.
#    """
#    event = netscool.Event()
#    switch, device0, device1 = two_device_network
#    to_device0 = Ether(
#        src='11:11:11:11:11:01', dst='11:11:11:11:11:00')
#    to_device1 = Ether(
#        src='11:11:11:11:11:00', dst='11:11:11:11:11:01')
#
#    send_interface = device0.interface('0/0')
#    recv_interface = device1.interface('0/0')
#    send_interface.send(to_device1)
#    while event.wait:
#        with event.conditions:
#            assert send_interface.captured(to_device1, netscool.DIR_OUT)
#            assert recv_interface.captured(to_device1, netscool.DIR_IN)
#
#            assert len(switch.cam) == 1
#            mac = send_interface.mac
#            assert mac in switch.cam
#            assert switch.cam[mac].interface == switch.interface('0/0')
#    netscool.clear_captures(device0, device1, switch)
#
#    send_interface = device1.interface('0/0')
#    recv_interface = device0.interface('0/0')
#    send_interface.send(to_device0)
#
#    while event.wait:
#        with event.conditions:
#            assert send_interface.captured(to_device0, netscool.DIR_OUT)
#            assert recv_interface.captured(to_device0, netscool.DIR_IN)
#
#            assert len(switch.cam) == 2
#            mac = send_interface.mac
#            assert mac in switch.cam
#            assert switch.cam[mac].interface == switch.interface('0/1')
#    netscool.clear_captures(device0, device1, switch)

#def test_flood_frames(three_device_network):
#    """
#    Test switch appropriately floods frames.
#    """
#    event = netscool.Event()
#    sw, dev0, dev1, dev2 = three_device_network
#
#    to_dev0 = Ether(src='11:11:11:11:11:01', dst='11:11:11:11:11:00')
#    to_dev1 = Ether(src='11:11:11:11:11:00', dst='11:11:11:11:11:01')
#
#    # Frame should be flooded to device1 and device2
#    dev0.interface('0/0').send(to_dev1)
#    while event.wait:
#        with event.conditions:
#
#            # Frame should got out dev0 but shouldn't be flooded back in.
#            assert dev0.interface('0/0').captured(
#                to_dev1, netscool.DIR_OUT)
#            assert not dev0.interface('0/0').captured(
#                to_dev1, netscool.DIR_IN)
#
#            # Frame should come in 0/0 on switch an be flooded out 0/1 and
#            # 0/2.
#            assert sw.interface('0/0').captured(to_dev1, netscool.DIR_IN)
#            assert sw.interface('0/1').captured(to_dev1, netscool.DIR_OUT)
#            assert sw.interface('0/2').captured(to_dev1, netscool.DIR_OUT)
#            assert not sw.interface('0/0').captured(
#                to_dev1, netscool.DIR_OUT)
#
#            # dev1 should get frame.
#            assert dev1.interface('0/0').captured(to_dev1, netscool.DIR_IN)
#
#            # Frame was flooded to dev2 but it should have dropped it.
#            assert not dev2.interface('0/0').captured(to_dev1)
#    netscool.clear_captures(dev0, dev1, dev2, sw)
#
#    dev1.interface('0/0').send(to_dev0)
#    while event.wait:
#        with event.conditions:
#            # Frame should got out dev1 and shouldnt come back in.
#            assert dev1.interface('0/0').captured(
#                to_dev0, netscool.DIR_OUT)
#            assert not dev1.interface('0/0').captured(
#                to_dev0, netscool.DIR_IN)
#
#            # Frame should come in 0/1 on switch an be sent out 0/0 only.
#            assert sw.interface('0/1').captured(to_dev0, netscool.DIR_IN)
#            assert sw.interface('0/0').captured(to_dev0, netscool.DIR_OUT)
#            assert not sw.interface('0/2').captured(to_dev0)
#            assert not sw.interface('0/1').captured(
#                to_dev0, netscool.DIR_OUT)
#
#            # dev0 should get frame.
#            assert dev0.interface('0/0').captured(to_dev0, netscool.DIR_IN)
#
#            # dev2 should not see the frame.
#            assert not dev2.interface('0/0').captured(to_dev0)
#    netscool.clear_captures(dev0, dev1, dev2, sw)

#def test_cam_entry_timeout(two_device_network):
#    """
#    Test CAM table entries expire as expected.
#    """
#    event = netscool.Event()
#    sw, dev0, dev1 = two_device_network
#
#    to_dev1 = Ether(src='11:11:11:11:11:00', dst='11:11:11:11:11:01')
#
#    dev0.interface('0/0').send(to_dev1)
#    while event.wait:
#        with event.conditions:
#
#            # dev1 should get frame, and CAM table should be populated.
#            assert dev1.interface('0/0').captured(to_dev1, netscool.DIR_IN)
#            assert len(sw.cam) == 1
#            mac = dev0.interface('0/0').mac
#            assert mac in sw.cam
#            assert sw.cam[mac].interface == sw.interface('0/0')
#
#    # Set timeout to a short time and wait for entries to expire.
#    sw.cam_timeout = 2
#    start = time.time()
#    while event.wait:
#        with event.conditions:
#            assert len(sw.cam) == 0
#
#    # The cam timeout doesnt happen at the exact time. As long as its
#    # within a reasonable range thats fine.
#    assert sw.cam_timeout <= time.time() - start <= sw.cam_timeout + 1

@pytest.fixture
def reference_network():
    """
    Test the our switch works with the reference switch. Mostly to try
    determine if future changes to the reference switch break this lesson.
    """
    switch0 = Switch(
        'sw0', '00:00:00:00:00:00', [
            L2Interface('0/0', '00:00:00:00:00:01'),
            L2Interface('0/1', '00:00:00:00:00:02'),
            L2Interface('0/2', '00:00:00:00:00:03')])

    switch1 = netscool.layer2.Switch(
        'sw1', '00:00:00:00:11:00', [
            netscool.layer2.SwitchPort('0/0', '00:00:00:00:11:01'),
            netscool.layer2.SwitchPort('0/1', '00:00:00:00:11:02'),
            netscool.layer2.SwitchPort('0/2', '00:00:00:00:11:03')])

    device0 = L2Device(
        'dev0', [
            L2Interface('0/0', '11:11:11:11:11:00')])
    device1 = L2Device(
        'dev1', [
            L2Interface('0/0', '11:11:11:11:11:01')])
    device2 = L2Device(
        'dev2', [
            L2Interface('0/0', '11:11:11:11:11:02')])
    device3 = L2Device(
        'dev3', [
            L2Interface('0/0', '11:11:11:11:11:03')])

    cable = netscool.layer1.Cable()
    switch0.interface('0/0').plug_cable(cable)
    switch1.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    switch0.interface('0/1').plug_cable(cable)
    device0.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    switch0.interface('0/2').plug_cable(cable)
    device1.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    switch1.interface('0/1').plug_cable(cable)
    device2.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    switch1.interface('0/2').plug_cable(cable)
    device3.interface('0/0').plug_cable(cable)

    event = netscool.Event()
    try:
        switch0.start()
        switch1.start()
        device0.start()
        device1.start()
        device2.start()
        device3.start()
        while event.wait:
            with event.conditions:
                assert device0.interface('0/0').upup
                assert device1.interface('0/0').upup
                assert device2.interface('0/0').upup
                assert device3.interface('0/0').upup
                assert switch0.interface('0/0').upup
                assert switch0.interface('0/1').upup
                assert switch0.interface('0/2').upup
                assert switch1.interface('0/0').upup
                assert switch1.interface('0/1').upup
                assert switch1.interface('0/2').upup

        yield switch0, switch1, device0, device1, device2, device3

    finally:
        switch0.shutdown()
        switch1.shutdown()
        device0.shutdown()
        device1.shutdown()
        device2.shutdown()
        device3.shutdown()

        while event.wait:
            with event.conditions:
                assert not device0.powered
                assert not device1.powered
                assert not device2.powered
                assert not device3.powered
                assert not switch0.powered
                assert not switch1.powered

def test_reference_switch(reference_network):
    """
    Test our switch works with the reference implementation.
    """
    event = netscool.Event()
    sw0, sw1, dev0, dev1, dev2, dev3 = reference_network

    dev0_to_dev3 = Ether(
        src=dev0.interface('0/0').mac,
        dst=dev3.interface('0/0').mac)
    dev0.interface('0/0').send(dev0_to_dev3)
    while event.wait:
        with event.conditions:
            assert dev0.interface('0/0').captured(
                dev0_to_dev3, netscool.DIR_OUT)

            assert sw0.interface('0/1').captured(
                dev0_to_dev3, netscool.DIR_IN)
            assert sw0.interface('0/0').captured(
                dev0_to_dev3, netscool.DIR_OUT)
            assert sw0.interface('0/2').captured(
                dev0_to_dev3, netscool.DIR_OUT)

            assert not dev1.interface('0/0').captured(dev0_to_dev3)
            assert not dev2.interface('0/0').captured(dev0_to_dev3)
            assert dev3.interface('0/0').captured(
                dev0_to_dev3, netscool.DIR_IN)
    netscool.clear_captures(dev0, dev1, dev2, dev3, sw0, sw1)

    dev3_to_dev0 = Ether(
        src=dev3.interface('0/0').mac,
        dst=dev0.interface('0/0').mac)
    dev3.interface('0/0').send(dev3_to_dev0)
    while event.wait:
        with event.conditions:
            assert dev3.interface('0/0').captured(
                dev3_to_dev0, netscool.DIR_OUT)

            assert sw0.interface('0/0').captured(
                dev3_to_dev0, netscool.DIR_IN)
            assert sw0.interface('0/1').captured(
                dev3_to_dev0, netscool.DIR_OUT)
            assert not sw0.interface('0/2').captured(dev3_to_dev0)

            assert not dev1.interface('0/0').captured(dev3_to_dev0)
            assert not dev2.interface('0/0').captured(dev3_to_dev0)
            assert dev0.interface('0/0').captured(
                dev3_to_dev0, netscool.DIR_IN)
    netscool.clear_captures(dev0, dev1, dev2, dev3, sw0, sw1)
