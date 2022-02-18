"""
Test switch implementation for lesson 3 continues to work with reference
switch which is used in network.py for the lesson. More specific tests
for vlans are covered in test_layer2.py
"""
import time
import collections
import scapy.all
import pytest

import netscool.layer1
import netscool.layer2
from netscool.layer2 import _tag_frame, _untag_frame

from tests.lessons.test_lesson1 import L2Device, L2Interface

class Switch(netscool.layer1.BaseDevice):

    CAMKey = collections.namedtuple('CAMKey', ['mac', 'vlan'])
    CAMEntry = collections.namedtuple(
        'CAMEntry', ['interface', 'last_seen'])

    def __init__(self, name, mac, interfaces):
        super().__init__(name, interfaces)
        self.mac = mac

        for interface in self.interfaces:
            assert isinstance(interface, SwitchPort)
            assert interface.promiscuous
        self.cam = {}
        self.cam_timeout = 300

    def show_cam(self):
        pass

    def event_loop(self):
        self._timeout_cam_entries()
        for interface in self.interfaces:
            frame = interface.receive()
            if not frame:
                continue

            assert isinstance(frame.payload, scapy.all.Dot1Q), "Switch expects only dot1q frames from SwitchPort"
            if self._is_local_frame(frame):
                continue

            src_mac = frame.src.lower()
            dst_mac = frame.dst.lower()
            vlan = frame.payload.vlan

            src_key = Switch.CAMKey(src_mac, vlan)
            entry = Switch.CAMEntry(interface, time.time())
            self.cam[src_key] = entry

            dst_key = Switch.CAMKey(dst_mac, vlan)
            if dst_key in self.cam:
                self.cam[dst_key].interface.send(frame)
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
        for key, entry in self.cam.items():
            if now - self.cam_timeout > entry.last_seen:
                to_remove.append(key)

        for key in to_remove:
            self.cam.pop(key)

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.mac)

class SwitchPort(L2Interface):
    ACCESS = 'access'
    TRUNK = 'trunk'

    def __init__(self, name, mac, bandwidth=1000):
        super().__init__(name, mac, bandwidth, True)
        self.default_vlan = 1
        self.set_access_port()

    def set_access_port(self, vlan=None):
        self._vlan = vlan
        if self._vlan == None:
            self._vlan = self.default_vlan

        self._mode = SwitchPort.ACCESS
        self._allowed_vlans = None
        self._native_vlan = None

    def set_trunk_port(self, allowed_vlans=None, native_vlan=None):
        self._allowed_vlans = allowed_vlans
        self._native_vlan = native_vlan
        if self._native_vlan == None:
            self._native_vlan = self.default_vlan

        self._mode = SwitchPort.TRUNK
        self._vlan = None

    @property
    def allow_all_vlan(self):
        return self._allowed_vlans == None

    def vlan_allowed(self, vlan):
        if self._mode != SwitchPort.TRUNK:
            return False
        return self.allow_all_vlan or vlan in self._allowed_vlans

    def receive(self):
        frame = super().receive()
        if not frame:
            return None

        if self._mode == SwitchPort.ACCESS:
            if isinstance(frame.payload, scapy.all.Dot1Q):
                return None
            return _tag_frame(frame, self._vlan)

        elif self._mode == SwitchPort.TRUNK:
            if not isinstance(frame.payload, scapy.all.Dot1Q):
                frame = _tag_frame(frame, self._native_vlan)

            vlan = frame.payload.vlan
            if not self.vlan_allowed(vlan):
                return None
            return frame
        
    def send(self, frame):
        if not isinstance(frame.payload, scapy.all.Dot1Q):
            return

        if self._mode == SwitchPort.ACCESS:
            vlan = frame.payload.vlan

            if vlan != self._vlan:
                return
            frame = _untag_frame(frame)

        elif self._mode == SwitchPort.TRUNK:
            vlan = frame.payload.vlan

            if not self.vlan_allowed(vlan):
                return
            if vlan == self._native_vlan:
                frame = _untag_frame(frame)
        super().send(frame)

    def __str__(self):
        return "{}({})".format(super().__str__(), self._mode)

@pytest.fixture
def reference_network():
    """
    Test the our switch works with the reference switch. Mostly to try
    determine if future changes to the reference switch break this lesson.
    """
    switch0 = Switch(
        'sw0', '00:00:00:00:00:00', [
            SwitchPort('0/0', '00:00:00:00:00:01'),
            SwitchPort('0/1', '00:00:00:00:00:02'),
            SwitchPort('0/2', '00:00:00:00:00:03')])

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

    switch0.interface('0/0').set_trunk_port()
    switch1.interface('0/0').set_trunk_port()

    switch0.interface('0/1').set_access_port(100)
    switch1.interface('0/1').set_access_port(100)

    switch0.interface('0/2').set_access_port(200)
    switch1.interface('0/2').set_access_port(200)

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

def test_lesson3_reference_switch(reference_network):
    """
    Test our switch works with the reference implementation.
    """
    event = netscool.Event()
    sw0, sw1, dev0, dev1, dev2, dev3 = reference_network

    # Send from dev0 to dev2 (vlan 100) and make sure it works.
    dev0_to_dev2 = scapy.all.Ether(
        src=dev0.interface('0/0').mac,
        dst=dev2.interface('0/0').mac)
    dev0.interface('0/0').send(dev0_to_dev2)
    while event.wait:
        with event.conditions:
            assert dev2.interface('0/0').captured(dev0_to_dev2, netscool.DIR_IN)
            assert not dev1.interface('0/0').captured(dev0_to_dev2)
            assert not dev3.interface('0/0').captured(dev0_to_dev2)

            assert len(sw0.interface('0/0').capture) == 1
            assert len(sw1.interface('0/0').capture) == 1
            assert len(sw0.interface('0/1').capture) == 1
            assert len(sw1.interface('0/1').capture) == 1
            assert len(sw0.interface('0/2').capture) == 0
            assert len(sw1.interface('0/2').capture) == 0
    netscool.clear_captures(dev0, dev1, dev2, dev3, sw0, sw1)

    # Send from dev1 to dev3 (vlan 200) and make sure it works.
    dev1_to_dev3 = scapy.all.Ether(
        src=dev1.interface('0/0').mac,
        dst=dev3.interface('0/0').mac)
    dev1.interface('0/0').send(dev1_to_dev3)
    while event.wait:
        with event.conditions:
            assert dev3.interface('0/0').captured(dev1_to_dev3, netscool.DIR_IN)
            assert not dev0.interface('0/0').captured(dev1_to_dev3)
            assert not dev2.interface('0/0').captured(dev1_to_dev3)

            assert len(sw0.interface('0/0').capture) == 1
            assert len(sw1.interface('0/0').capture) == 1
            assert len(sw0.interface('0/1').capture) == 0
            assert len(sw1.interface('0/1').capture) == 0
            assert len(sw0.interface('0/2').capture) == 1
            assert len(sw1.interface('0/2').capture) == 1
    netscool.clear_captures(dev0, dev1, dev2, dev3, sw0, sw1)
