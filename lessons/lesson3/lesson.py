import collections
from scapy.all import Ether, Dot1Q
import IPython

#import netscool
#netscool.lesson('lesson3')

import netscool.layer1

from <your_module> import L2Device, L2Interface, Switch

# For this lesson you will have to modify your existing Switch
# implementation as well as the SwitchPort interface type below.
# It might initially seem a bit awkward to be implenting switch specific
# logic in this SwithPort class, given that up until this point our
# interfaces have been generic and not device specific. In reality, beyond
# layer 1, the behaviour of an interface will mostly be controlled by
# the firmware and software running on the device. This means a switchport
# can only really exist on a Switch running Switch firmware. We could
# more accurately model this by seperating our Switch into hardware and
# software components, however doing this doesnt teach us much about
# networking, and seems an unnecessary distraction. We could also roll
# this functionality into our Switch class, however it still needs to add
# extra switch details to each of its interfaces, and having our Switch
# be a monolithic class doesnt seem great. A third solution is for 
# SwitchPort to be a special type of interface that can only be used with
# a Switch, which implements specific Switch logic. While not perfect this
# seems the most straight forward and maintainable option. If you decide
# on a different design, note that this and future lessons will assume
# Switch interfaces have a set_access_port and set_trunk_port method.
class SwitchPort(L2Interface):
    """
    Extends L2Interface with switch port specific behaviour. Primarily
    handles dot1q vlan tags for frames coming in/out of the port.
    """

    # Two possible modes for a SwitchPort.
    ACCESS = 'access'
    TRUNK = 'trunk'

    def __init__(self, name, mac, bandwidth=1000):
        super().__init__(name, mac, bandwidth, True)
        self.default_vlan = 1

        # Set the port as and access port in the default vlan.
        pass

    def set_access_port(self, vlan=None):
        """
        Set switchport as an access port.

        :param vlan: VLAN to tag incoming frames, None means use
            default_vlan.
        """
        pass

    def set_trunk_port(self, allowed_vlans=None, native_vlan=None):
        """
        Set switchport as a trunk port.

        :param allowed_vlans: List of allowed vlans, or None to allow all.
        :param native_vlan: The native vlan for this port, or None to use
            default_vlan.
        """
        pass

    # How you decide to handle frames and vlan tags internal to your
    # switch is up to you. All that ultimately matters is that
    # received frames are sent out appropriate interfaces with
    # appropriate tagging. When the tags are added/removed between being
    # received and sent is up to you.
    def receive(self):
        """
        Receive a frame on the switchport.
        """
        frame = super().receive()
        if not frame:
            return None

    def send(self, frame):
        """
        Send a frame on the switchport.
        """
        super().send(frame)

# Adding and removing vlan tags from an Ether frame using Scapy is not
# straight forward. These utilities are provided to save you some time
# messing about with Scapy. Feel free to adapt and change these as you
# see fit.
def _tag_frame(frame, vlan):
    """
    Create a copy of frame with a dot1q vlan tag.

    :param frame: Ether frame to tag with dot1q.
    :param vlan: vlan number to put in dot1q header.
    :returns: Ether frame tagged with dot1 vlan.
    """
    # Make a deepcopy to make sure we dont modify the original frame.
    new_frame = copy.deepcopy(frame)

    # Get the frame payload and ethernet header.
    payload = new_frame.payload
    header = new_frame.firstlayer()

    # Remove the current payload from the ethernet header so we can
    # insert the dot1q tag.
    header.remove_payload()

    # Backup the current payload type so we can apply it to the dot1q
    # header.
    payload_type = header.type

    # 0x8100 means the next layer is dot1q.
    header.type = 0x8100

    # Reassemble frame with dot1q header.
    dot1q = Dot1Q(vlan=vlan, type=payload_type)
    return header/dot1q/payload

def _untag_frame(frame):
    """
    Create a copy of frame with dot1q vlan tag removed.

    :param frame: Ether frame tagged with dot1q
    :returns: Ether frame with dot1q tag removed.
    """
    # Make a deepcopy to make sure we dont modify the original frame.
    new_frame = copy.deepcopy(frame)

    # Check this frame has a dot1q tag.
    dot1q = new_frame.payload
    if not isinstance(dot1q, Dot1Q):
        return None

    # Get the new frame header and payload.
    payload = dot1q.payload
    header = new_frame.firstlayer()

    # Remove the dot1q payload and add the underlying payload.
    header.remove_payload()
    header.type = dot1q.type
    return header/payload

#from netscool.layer2 import L2Device, L2Interface, Switch, SwitchPort

if __name__ == "__main__":

    switch0 = Switch(
        "sw0", "00:00:00:00:00:00",  [
            SwitchPort("0/0", "00:00:00:00:00:01"),
            SwitchPort("0/1", "00:00:00:00:00:02"),
            SwitchPort("0/2", "00:00:00:00:00:03")
        ])

    device0 = L2Device(
        "dev0", [
            L2Interface("0/0", "22:22:22:22:22:00")
        ])
    device1 = L2Device(
        "dev1", [
            L2Interface("0/0", "22:22:22:22:22:01")
        ])

    cable = netscool.layer1.Cable()
    device0.interface('0/0').plug_cable(cable)
    switch0.interface('0/1').plug_cable(cable)
    switch0.interface('0/1').set_access_port(vlan=10)

    cable = netscool.layer1.Cable()
    device1.interface('0/0').plug_cable(cable)
    switch0.interface('0/2').plug_cable(cable)
    switch0.interface('0/2').set_access_port(vlan=20)

    cable = netscool.layer1.SocketCable(22222, 11111)
    switch0.interface('0/0').plug_cable(cable)
    switch0.interface('0/0').set_trunk_port([10, 20], 10)

    frame_dev0_dev2 = Ether(
        src=device0.interface('0/0').mac, dst='22:22:22:22:22:02')

    frame_dev1_dev3 = Ether(
        src=device1.interface('0/0').mac, dst='22:22:22:22:22:03')

    try:
        switch0.start()
        device0.start()
        device1.start()

        IPython.embed()

    finally:
        switch0.shutdown()
        device0.shutdown()
        device1.shutdown()

import pytest
# Some possible tests you should implement. This is by no means an
# exhaustive list of tests, and you should add any extra tests you think
# appropriate.

def test_vlan_flood(self):
    # Test frames only flood to allowed interfaces for a vlan.
    pass

def test_vlan_address(self):
    # Test you cant address a mac in another vlan.
    pass

def test_vlan_trunk_allowed(self):
    # Test only allowed vlans traverse vlan trunk.
    pass

def test_vlan_trunk_native(self):
    # Test native vlans on trunk links work as expected.
    pass
