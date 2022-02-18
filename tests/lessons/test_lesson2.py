"""
Test switch implementation for lesson 2 continues to work with reference
switch which is used in network.py for the lesson. More specific tests
for this implementation are covered in tests_layer2.py. 
"""
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

def test_lesson2_reference_switch(reference_network):
    """
    Test our switch works with the reference implementation.
    """
    event = netscool.Event()
    sw0, sw1, dev0, dev1, dev2, dev3 = reference_network

    # Send from dev0 to dev3 and make sure dev1 and dev2 dont receive
    # the frame. Check the frame also goes through the appropriate
    # interfaces on the two switches.
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

    # Send back from dev3 to dev0 and make sure dev1 and dev2 dont receive
    # the frame. Check the frame also goes through the appropriate
    # interfaces on the two switches.
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
