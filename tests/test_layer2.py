import time
import logging

import pytest
from scapy.all import Ether, Dot1Q

import netscool
import netscool.layer1
import netscool.layer2

import tests.lessons.test_lesson1 as lesson1
import tests.lessons.test_lesson2 as lesson2

@pytest.fixture
def l2device_network(request):
    """
    Two L2Device's with one L2Interface each. The 4 parameters are the
    L2Device and L2Interface classes to use for dev0, and the same for
    dev1.
    """

    # Parameterising the L2Device and L2Interface classes means we can test
    # multiple similar implementations with the same tests.
    L2Device0, L2Interface0, L2Device1, L2Interface1 = request.param
    dev0 = L2Device0("dev0", [
        L2Interface0("0/0", "11:11:11:11:11:11")
    ])
    dev1 = L2Device1("dev1", [
        L2Interface1("0/0", "22:22:22:22:22:22")
    ])

    cable = netscool.layer1.Cable()
    dev0.interface('0/0').plug_cable(cable)
    dev1.interface('0/0').plug_cable(cable)
    event = netscool.Event()
    try:
        dev0.start()
        dev1.start()
        while event.wait:
            with event.conditions:
                assert dev0.powered == True
                assert dev1.powered == True
                assert dev0.interface("0/0").powered == True
                assert dev1.interface("0/0").powered == True
        yield dev0, dev1

    finally:
        dev0.shutdown()
        dev1.shutdown()
        while event.wait:
            with event.conditions:
                assert dev0.powered == False
                assert dev1.powered == False

@pytest.fixture
def switch_network(request):
    """
    One Switch with 3 interfaces, with a L2Device connected to each interface.
    The 2 parameters are the Switch and SwitchInterface classes to use for the
    switch.
    """

    # Parameterising the Switch and SwitchInterface classes means we can test
    # multiple similar implementations with the same tests.
    Switch, SwitchInterface = request.param
    switch = Switch(
        'sw0', '00:00:00:00:00:00', [
            SwitchInterface('0/0', '00:00:00:00:00:01'),
            SwitchInterface('0/1', '00:00:00:00:00:02'),
            SwitchInterface('0/2', '00:00:00:00:00:03')])
    device0 = netscool.layer2.L2Device(
        'dev0', [
            netscool.layer2.L2Interface('0/0', '11:11:11:11:11:00')])
    device1 = netscool.layer2.L2Device(
        'dev1', [
            netscool.layer2.L2Interface('0/0', '11:11:11:11:11:01')])
    device2 = netscool.layer2.L2Device(
        'dev2', [
            netscool.layer2.L2Interface('0/0', '11:11:11:11:11:02')])

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

@pytest.fixture
def switch_vlan_network(request):
    """
    Two Switches with two L2Devices on each in different VLANs, and a trunk link
    connecting the two switches.

    |dev0 vlan100| --              -- |dev2 vlan100|
                     |sw0| -- |sw1|
    |dev1 vlan100| --              -- |dev3 vlan200|
    """

    # Parameterising the Switch and SwitchInterface classes means we can
    # test multiple similar implementations with the same tests.
    Switch, SwitchInterface = request.param

    sw0 = Switch(
        'sw0', '00:00:00:00:00:00', [
            SwitchInterface('0/0', '00:00:00:00:00:01'),
            SwitchInterface('0/1', '00:00:00:00:00:02'),
            SwitchInterface('0/2', '00:00:00:00:00:03')])

    sw1 = Switch(
        'sw1', '00:00:00:00:00:00', [
            SwitchInterface('0/0', '00:00:00:00:00:11'),
            SwitchInterface('0/1', '00:00:00:00:00:12'),
            SwitchInterface('0/2', '00:00:00:00:00:13')])

    dev0 = netscool.layer2.L2Device(
        'dev0', [
            netscool.layer2.L2Interface('0/0', '11:11:11:11:11:00')])
    dev1 = netscool.layer2.L2Device(
        'dev1', [
            netscool.layer2.L2Interface('0/0', '11:11:11:11:11:01')])
    dev2 = netscool.layer2.L2Device(
        'dev2', [
            netscool.layer2.L2Interface('0/0', '11:11:11:11:11:02')])
    dev3 = netscool.layer2.L2Device(
        'dev3', [
            netscool.layer2.L2Interface('0/0', '11:11:11:11:11:03')])

    cable = netscool.layer1.Cable()
    sw0.interface('0/1').plug_cable(cable)
    dev0.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    sw0.interface('0/2').plug_cable(cable)
    dev1.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    sw1.interface('0/1').plug_cable(cable)
    dev2.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    sw1.interface('0/2').plug_cable(cable)
    dev3.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.Cable()
    sw0.interface('0/0').plug_cable(cable)
    sw1.interface('0/0').plug_cable(cable)

    sw0.interface('0/0').set_trunk_port()
    sw1.interface('0/0').set_trunk_port()

    sw0.interface('0/1').set_access_port(100)
    sw1.interface('0/1').set_access_port(100)

    sw0.interface('0/2').set_access_port(100)
    sw1.interface('0/2').set_access_port(200)

    event = netscool.Event()
    try:
        sw0.start()
        sw1.start()
        dev0.start()
        dev1.start()
        dev2.start()
        dev3.start()
        while event.wait:
            with event.conditions:
                assert dev0.interface('0/0').upup
                assert dev1.interface('0/0').upup
                assert dev2.interface('0/0').upup
                assert dev3.interface('0/0').upup
                assert sw0.interface('0/0').upup
                assert sw0.interface('0/1').upup
                assert sw0.interface('0/2').upup
                assert sw1.interface('0/0').upup
                assert sw1.interface('0/1').upup
                assert sw1.interface('0/2').upup
        yield sw0, sw1, dev0, dev1, dev2, dev3

    finally:
        sw0.shutdown()
        sw1.shutdown()
        dev0.shutdown()
        dev1.shutdown()
        dev2.shutdown()
        dev3.shutdown()

        while event.wait:
            with event.conditions:
                assert not dev0.powered
                assert not dev1.powered
                assert not dev2.powered
                assert not dev3.powered
                assert not sw0.powered
                assert not sw1.powered

@pytest.mark.parametrize(
    'l2device_network', [
        # Test L2Device and L2Interface.
        (
            netscool.layer2.L2Device,
            netscool.layer2.L2Interface,
            netscool.layer2.L2Device,
            netscool.layer2.L2Interface
        ),
        # Test lesson1 examples of L2Device and L2Interface.
        (
            lesson1.L2Device,
            lesson1.L2Interface,
            lesson1.L2Device,
            lesson1.L2Interface
        ),
        # Test the lesson example interoperate with reference example.
        (
            netscool.layer2.L2Device,
            netscool.layer2.L2Interface,
            lesson1.L2Device,
            lesson1.L2Interface
        )],
    indirect=True)
def test_l2interface_status(l2device_network):
    """
    Test L2Interface status transitions.
    """
    event = netscool.Event()
    dev0, dev1 = l2device_network
    interface0 = dev0.interface("0/0")
    interface1 = dev1.interface("0/0")

    # Wait for interfaces to come up.
    while event.wait:
        with event.conditions:
            assert interface0.upup == True
            assert interface1.upup == True
            assert interface0.protocol_up == True
            assert interface1.protocol_up == True
            assert interface0.status == ('up', 'up')
            assert interface1.status == ('up', 'up')

    # Shutdown one interface and make sure the other interface goes down.
    interface0.shutdown()
    while event.wait:
        with event.conditions:
            assert interface0.upup == False
            assert interface1.upup == False
            assert interface0.protocol_up == False
            assert interface1.protocol_up == False
            assert interface0.status == ('admin down', 'down')
            assert interface1.status == ('down', 'down')

    # Bring the interfaces back up.
    interface0.no_shutdown()
    while event.wait:
        with event.conditions:
            assert interface0.upup == True
            assert interface1.upup == True

    # Shutdown the other interface and make sure the first interface goes
    # down.
    interface1.shutdown()
    while event.wait:
        with event.conditions:
            assert interface0.upup == False
            assert interface1.upup == False
            assert interface0.protocol_up == False
            assert interface1.protocol_up == False
            assert interface0.status == ('down', 'down')
            assert interface1.status == ('admin down', 'down')

    # Bring the interface back up.
    interface1.no_shutdown()
    while event.wait:
        with event.conditions:
            assert interface0.upup == True
            assert interface1.upup == True

    # Shutdown a device and make sure both interfaces go down.
    dev0.shutdown()
    while event.wait:
        with event.conditions:
            assert interface0.upup == False
            assert interface1.upup == False
            assert interface0.protocol_up == False
            assert interface1.protocol_up == False
            assert interface0.status == ('down', 'down')
            assert interface1.status == ('down', 'down')

@pytest.mark.parametrize(
    'l2device_network', [
        # Test L2Device and L2Interface.
        (
            netscool.layer2.L2Device,
            netscool.layer2.L2Interface,
            netscool.layer2.L2Device,
            netscool.layer2.L2Interface
        ),
        # Test lesson1 examples of L2Device and L2Interface.
        (
            lesson1.L2Device,
            lesson1.L2Interface,
            lesson1.L2Device,
            lesson1.L2Interface
        ),
        # Test the lesson example interoperate with reference example.
        (
            netscool.layer2.L2Device,
            netscool.layer2.L2Interface,
            lesson1.L2Device,
            lesson1.L2Interface
        )],
    indirect=True)
def test_l2interface_send_receive(l2device_network):
    """
    Test L2Interface can properly send and receive frames.
    """
    event = netscool.Event()
    dev0, dev1 = l2device_network
    interface0 = dev0.interface('0/0')
    interface1 = dev1.interface('0/0')

    # Wait for interfaces to come up.
    while event.wait:
        with event.conditions:
            assert interface0.upup
            assert interface1.upup

    bad_frame = b'aaa'
    wrong_dst_frame = Ether(src=interface0.mac, dst='00:00:00:00:00:00')
    good_frame = Ether(src=interface0.mac, dst=interface1.mac)

    # It is very difficult to prove bad_frame and wrong_dst_frame are
    # never received. If the other interface sees good_frame but not the
    # others then we can be pretty sure they will never be received.
    interface0.send(bad_frame)
    interface0.send(wrong_dst_frame)
    interface0.send(good_frame)
    while event.wait:
        with event.conditions:
            # bad_frame is not valid at all so shouldnt be sent out
            # interface0 to begin with and definitely shouldnt be seen by
            # interface1
            assert not interface0.captured(bad_frame)
            assert not interface1.captured(bad_frame)

            # wrong_dst_frame should be sent out interface1 but should be
            # dropped by interface1.
            assert interface0.captured(wrong_dst_frame, netscool.DIR_OUT)
            assert not interface1.captured(wrong_dst_frame)

            # good_frame should be seen by both interfaces.
            assert interface0.captured(good_frame, netscool.DIR_OUT)
            assert interface1.captured(good_frame, netscool.DIR_IN)
    netscool.clear_captures(dev0, dev1)

    # Send frames in the opposite direction to make sure our
    # implementation can also receive properly.
    wrong_dst_frame = Ether(src=interface1.mac, dst='00:00:00:00:00:00')
    good_frame = Ether(src=interface1.mac, dst=interface0.mac)

    interface1.send(bad_frame)
    interface1.send(wrong_dst_frame)
    interface1.send(good_frame)
    while event.wait:
        with event.conditions:
            assert not interface1.captured(bad_frame)
            assert not interface0.captured(bad_frame)

            assert interface1.captured(wrong_dst_frame, netscool.DIR_OUT)
            assert not interface0.captured(wrong_dst_frame)

            assert interface1.captured(good_frame, netscool.DIR_OUT)
            assert interface0.captured(good_frame, netscool.DIR_IN)
    netscool.clear_captures(dev0, dev1)

    # Set our interface as promiscuous and make sure we receive
    # wrong_dst_frame as well as good_frame. 
    interface0.promiscuous = True

    interface1.send(bad_frame)
    interface1.send(wrong_dst_frame)
    interface1.send(good_frame)
    while event.wait:
        with event.conditions:
            assert not interface1.captured(bad_frame)
            assert not interface0.captured(bad_frame)

            assert interface1.captured(wrong_dst_frame, netscool.DIR_OUT)
            assert interface0.captured(wrong_dst_frame, netscool.DIR_IN)

            assert interface1.captured(good_frame, netscool.DIR_OUT)
            assert interface0.captured(good_frame, netscool.DIR_IN)
    netscool.clear_captures(dev0, dev1)

@pytest.mark.parametrize(
    'switch_network', [
        # Test reference Switch.
        (
            netscool.layer2.Switch,
            netscool.layer2.SwitchPort
        ),
        # Test lesson2 example of Switch.
        (
            lesson2.Switch,
            lesson1.L2Interface
        )],
    indirect=True)
def test_switch_cam_populate(switch_network):
    """
    Test CAM table is properly populated when the switch receives frames.
    """
    def _find_cam_key(cam, mac):
        # Our current Switch implementations either use 'mac' or 
        # 'mac and vlan' as the key to the CAM table. We do this
        # slightly gross kludge to work around the incompatibility for
        # this test. For now this is OK but if we have more divergent
        # CAM table implementations in the future then this test should be
        # split into lesson specific tests.
        for cam_key in cam:
            # For lesson2 example Switch, where only 'mac' is used for
            # CAM table.
            if isinstance(cam_key, str):
                if cam_key == mac:
                    return cam_key
                continue

            # For lesson3 example, and reference Switch, where 'mac' and
            # 'vlan' are used for CAM table.
            if cam_key.mac == mac and cam_key.vlan == 1:
                return cam_key
        return None

    event = netscool.Event()
    switch, dev0, dev1, dev2 = switch_network
    dev0_to_dev1 = Ether(
        src=dev0.interface('0/0').mac, dst=dev1.interface('0/0').mac)
    dev1_to_dev0 = Ether(
        src=dev1.interface('0/0').mac, dst=dev0.interface('0/0').mac)

    # Send frame from dev0 to dev1 and make sure the CAM table is
    # populated.
    dev0.interface('0/0').send(dev0_to_dev1)
    while event.wait:
        with event.conditions:
            assert dev0.interface('0/0').captured(
                dev0_to_dev1, netscool.DIR_OUT)
            assert dev1.interface('0/0').captured(
                dev0_to_dev1, netscool.DIR_IN)

            assert len(switch.cam) == 1
            cam_key = _find_cam_key(switch.cam, dev0.interface('0/0').mac)
            assert cam_key != None
            assert switch.cam[cam_key].interface == switch.interface('0/0')
    netscool.clear_captures(dev0, dev1, dev2, switch)

    # Send frame from dev1 to dev0 and make sure the CAM table is
    # populated.
    dev1.interface('0/0').send(dev1_to_dev0)
    while event.wait:
        with event.conditions:
            assert dev1.interface('0/0').captured(
                dev1_to_dev0, netscool.DIR_OUT)
            assert dev0.interface('0/0').captured(
                dev1_to_dev0, netscool.DIR_IN)

            assert len(switch.cam) == 2
            cam_key = _find_cam_key(switch.cam, dev1.interface('0/0').mac)
            assert cam_key != None
            assert switch.cam[cam_key].interface == switch.interface('0/1')
    netscool.clear_captures(dev0, dev1, dev2, switch)

@pytest.mark.parametrize(
    'switch_network', [
        # Test reference Switch.
        (
            netscool.layer2.Switch,
            netscool.layer2.SwitchPort
        ),
        # Test lesson2 example of Switch.
        (
            lesson2.Switch,
            lesson1.L2Interface
        )],
    indirect=True)
def test_switch_flood(switch_network):
    """
    Test switch appropriately floods frames.
    """
    event = netscool.Event()
    switch, dev0, dev1, dev2 = switch_network

    dev0_to_dev1 = Ether(
        src=dev0.interface('0/0').mac, dst=dev1.interface('0/0').mac)
    dev1_to_dev0 = Ether(
        src=dev1.interface('0/0').mac, dst=dev0.interface('0/0').mac)

    # Frame should be flooded to device1 and device2
    dev0.interface('0/0').send(dev0_to_dev1)
    while event.wait:
        with event.conditions:

            # Frame should got out dev0 but shouldn't be flooded back in.
            assert dev0.interface('0/0').captured(
                dev0_to_dev1, netscool.DIR_OUT)
            assert not dev0.interface('0/0').captured(
                dev0_to_dev1, netscool.DIR_IN)

            # Frame should be flooded out 0/1 and 0/2, but not 0/0.
            assert switch.interface('0/1').captured(
                dev0_to_dev1, netscool.DIR_OUT)
            assert switch.interface('0/2').captured(
                dev0_to_dev1, netscool.DIR_OUT)
            assert not switch.interface('0/0').captured(
                dev0_to_dev1, netscool.DIR_OUT)

            # dev1 should get frame.
            assert dev1.interface('0/0').captured(
                dev0_to_dev1, netscool.DIR_IN)

            # Frame was flooded to dev2 but it should have dropped it.
            assert not dev2.interface('0/0').captured(dev0_to_dev1)
    netscool.clear_captures(dev0, dev1, dev2, switch)

    dev1.interface('0/0').send(dev1_to_dev0)
    while event.wait:
        with event.conditions:
            # Frame should go out dev1 and shouldnt come back in.
            assert dev1.interface('0/0').captured(
                dev1_to_dev0, netscool.DIR_OUT)
            assert not dev1.interface('0/0').captured(
                dev1_to_dev0, netscool.DIR_IN)

            # Frame should be sent out 0/0 only.
            assert switch.interface('0/0').captured(
                dev1_to_dev0, netscool.DIR_OUT)
            assert not switch.interface('0/2').captured(
                dev1_to_dev0, netscool.DIR_OUT)
            assert not switch.interface('0/1').captured(
                dev1_to_dev0, netscool.DIR_OUT)

            # dev0 should get frame.
            assert dev0.interface('0/0').captured(
                dev1_to_dev0, netscool.DIR_IN)

            # dev2 should not see the frame.
            assert not dev2.interface('0/0').captured(dev1_to_dev0)
    netscool.clear_captures(dev0, dev1, dev2, switch)

@pytest.mark.parametrize(
    'switch_network', [
        # Test reference Switch.
        (
            netscool.layer2.Switch,
            netscool.layer2.SwitchPort
        ),
        # Test lesson2 example of Switch.
        (
            lesson2.Switch,
            lesson1.L2Interface
        )],
    indirect=True)
def test_switch_cam_timeout(switch_network):
    """
    Test Switch CAM table timesout entries appropriately. 
    """
    event = netscool.Event()
    switch, dev0, dev1, dev2 = switch_network

    # Set cam_timeout to a small value so test doesnt take 5 minutes.
    switch.cam_timeout = 2
    assert len(switch.cam) == 0

    dev0_to_dev1 = Ether(
        src=dev0.interface('0/0').mac, dst=dev1.interface('0/0').mac)
    dev0.interface('0/0').send(dev0_to_dev1)
    while event.wait:
        with event.conditions:

            # dev1 should get frame, and CAM table should be populated.
            assert dev1.interface('0/0').captured(
                dev0_to_dev1, netscool.DIR_IN)
            assert len(switch.cam) == 1

    # Wait for entries to expire.
    start = time.time()
    while event.wait:
        with event.conditions:
            assert len(switch.cam) == 0

    # The cam timeout doesnt happen at the exact time. As long as its
    # within a reasonable range thats fine.
    assert switch.cam_timeout <= time.time() - start <= switch.cam_timeout + 1

@pytest.mark.parametrize(
    'switch_vlan_network', [
        # Test reference Switch.
        (
            netscool.layer2.Switch,
            netscool.layer2.SwitchPort
        )],
    indirect=True)
def test_vlan_send(switch_vlan_network):

    event = netscool.Event()
    sw0, sw1, dev0, dev1, dev2, dev3 = switch_vlan_network

    # Send from dev0 -> dev2 on vlan 100
    # Should only see traffic on vlan 100 interfaces.
    # Frame should be flooded to all vlan100 interfaces
    dev0_to_dev2 = Ether(
        src=dev0.interface('0/0').mac, dst=dev2.interface('0/0').mac)
    dev0.interface('0/0').send(dev0_to_dev2)
    while event.wait:
        with event.conditions:

            # Frame is only received by intended device.
            assert dev2.interface('0/0').captured(dev0_to_dev2, netscool.DIR_IN)
            assert not dev1.interface('0/0').captured(dev0_to_dev2)
            assert not dev3.interface('0/0').captured(dev0_to_dev2)

            # Frame is flooded out every interface in vlan100 and not the
            # vlan200 interface.
            assert len(sw0.interface('0/0').capture) == 1
            assert len(sw1.interface('0/0').capture) == 1
            assert len(sw0.interface('0/1').capture) == 1
            assert len(sw1.interface('0/1').capture) == 1
            assert len(sw0.interface('0/2').capture) == 1
            assert len(sw1.interface('0/2').capture) == 0

            # Check a vlan 100 tagged frame is sent across the trunk link.
            assert_vlan_frame(
                cap=sw0.interface('0/0').capture[0],
                src_mac=dev0.interface('0/0').mac,
                dst_mac=dev2.interface('0/0').mac,
                vlan=100)
            assert_vlan_frame(
                cap=sw1.interface('0/0').capture[0],
                src_mac=dev0.interface('0/0').mac,
                dst_mac=dev2.interface('0/0').mac,
                vlan=100)
   
    netscool.clear_captures(sw0, sw1, dev0, dev1, dev2, dev3)
     
    # Send from dev2 -> dev0 on vlan 100
    # Should only see traffic on vlan 100 interfaces.
    # Frame should not be flooded.
    dev2_to_dev0 = Ether(
        src=dev2.interface('0/0').mac, dst=dev0.interface('0/0').mac)
    dev2.interface('0/0').send(dev2_to_dev0)
    while event.wait:
        with event.conditions:

            # Frame is only received by intended device.
            assert dev0.interface('0/0').captured(dev2_to_dev0, netscool.DIR_IN)
            assert not dev1.interface('0/0').captured(dev2_to_dev0)
            assert not dev3.interface('0/0').captured(dev2_to_dev0)

            # Frame is not flooded, still doesnt go to vlan 200 interface. 
            assert len(sw0.interface('0/0').capture) == 1
            assert len(sw1.interface('0/0').capture) == 1
            assert len(sw0.interface('0/1').capture) == 1
            assert len(sw1.interface('0/1').capture) == 1
            assert len(sw0.interface('0/2').capture) == 0
            assert len(sw1.interface('0/2').capture) == 0

            # Check a vlan 100 tagged frame is sent across the trunk link.
            assert_vlan_frame(
                cap=sw0.interface('0/0').capture[0],
                src_mac=dev2.interface('0/0').mac,
                dst_mac=dev0.interface('0/0').mac,
                vlan=100)
            assert_vlan_frame(
                cap=sw1.interface('0/0').capture[0],
                src_mac=dev2.interface('0/0').mac,
                dst_mac=dev0.interface('0/0').mac,
                vlan=100)

    netscool.clear_captures(sw0, sw1, dev0, dev1, dev2, dev3)

    # Send from dev0 -> dev3
    # Should not work, different vlans.
    dev0_to_dev3 = Ether(
        src=dev0.interface('0/0').mac, dst=dev3.interface('0/0').mac)
    dev0.interface('0/0').send(dev0_to_dev3)
    while event.wait:
        with event.conditions:

            # Frame is not received by anyone because destination is
            # in another vlan.
            assert not dev2.interface('0/0').captured(dev0_to_dev3)
            assert not dev1.interface('0/0').captured(dev0_to_dev3)
            assert not dev3.interface('0/0').captured(dev0_to_dev3)

            # Frame is flooded out every interface in vlan100 and not the
            # vlan200 interface.
            assert len(sw0.interface('0/0').capture) == 1
            assert len(sw1.interface('0/0').capture) == 1
            assert len(sw0.interface('0/1').capture) == 1
            assert len(sw1.interface('0/1').capture) == 1
            assert len(sw0.interface('0/2').capture) == 1
            assert len(sw1.interface('0/2').capture) == 0

@pytest.mark.parametrize(
    'switch_vlan_network', [
        # Test reference Switch.
        (
            netscool.layer2.Switch,
            netscool.layer2.SwitchPort
        )],
    indirect=True)
def test_vlan_trunk_allowed(switch_vlan_network):
    event = netscool.Event()
    sw0, sw1, dev0, dev1, dev2, dev3 = switch_vlan_network

    # Restrict trunk link to only allow vlan 200.
    sw0.interface('0/0').set_trunk_port(allowed_vlans=[200])
    sw1.interface('0/0').set_trunk_port(allowed_vlans=[200])

    dev0_to_dev2 = Ether(
        src=dev0.interface('0/0').mac, dst=dev2.interface('0/0').mac)
    dev0.interface('0/0').send(dev0_to_dev2)
    while event.wait:
        with event.conditions:

            # Frame is not allowed across trunk link so no-one receives
            # it.
            assert not dev1.interface('0/0').captured(dev0_to_dev2)
            assert not dev2.interface('0/0').captured(dev0_to_dev2)
            assert not dev3.interface('0/0').captured(dev0_to_dev2)

            # Frame will be flooded to vlan 100 interfaces on sw0 but
            # doesnt reach sw1.
            assert len(sw0.interface('0/0').capture) == 0
            assert len(sw1.interface('0/0').capture) == 0
            assert len(sw0.interface('0/1').capture) == 1
            assert len(sw1.interface('0/1').capture) == 0
            assert len(sw0.interface('0/2').capture) == 1
            assert len(sw1.interface('0/2').capture) == 0

    netscool.clear_captures(sw0, sw1, dev0, dev1, dev2, dev3)

    dev0_to_dev1 = Ether(
        src=dev0.interface('0/0').mac, dst=dev1.interface('0/0').mac)
    dev0.interface('0/0').send(dev0_to_dev1)
    while event.wait:
        with event.conditions:

            # Frame doesnt have to cross trunk link so makes it to dev1.
            assert dev1.interface('0/0').captured(dev0_to_dev1, netscool.DIR_IN)
            assert not dev2.interface('0/0').captured(dev0_to_dev1)
            assert not dev3.interface('0/0').captured(dev0_to_dev1)

            # Frame doesnt cross trunk link.
            assert len(sw0.interface('0/0').capture) == 0
            assert len(sw1.interface('0/0').capture) == 0
            assert len(sw0.interface('0/1').capture) == 1
            assert len(sw1.interface('0/1').capture) == 0
            assert len(sw0.interface('0/2').capture) == 1
            assert len(sw1.interface('0/2').capture) == 0

    netscool.clear_captures(sw0, sw1, dev0, dev1, dev2, dev3)

@pytest.mark.parametrize(
    'switch_vlan_network', [
        # Test reference Switch.
        (
            netscool.layer2.Switch,
            netscool.layer2.SwitchPort
        )],
    indirect=True)
def test_vlan_trunk_native(switch_vlan_network):

    event = netscool.Event()
    sw0, sw1, dev0, dev1, dev2, dev3 = switch_vlan_network

    # Put dev0 and dev2 in vlan100
    sw0.interface('0/1').set_access_port(100)
    sw1.interface('0/1').set_access_port(100)

    # Put dev1 and dev3 in vlan200. 
    sw0.interface('0/2').set_access_port(200)
    sw1.interface('0/2').set_access_port(200)

    # Set the native vlan on the trunk link to vlan 100. Any vlam 100
    # frames should not be tagged when crossing the trunk link.
    sw0.interface('0/0').set_trunk_port(native_vlan=100)
    sw1.interface('0/0').set_trunk_port(native_vlan=100)

    # Send a frame across the trunk link in vlan 100. Shouldnt be tagged.
    dev0_to_dev2 = Ether(
        src=dev0.interface('0/0').mac, dst=dev2.interface('0/0').mac)
    dev0.interface('0/0').send(dev0_to_dev2)
    while event.wait:
        with event.conditions:

            # Frame is only received by intended device.
            assert dev2.interface('0/0').captured(dev0_to_dev2, netscool.DIR_IN)
            assert not dev1.interface('0/0').captured(dev0_to_dev2)
            assert not dev3.interface('0/0').captured(dev0_to_dev2)

            assert len(sw0.interface('0/0').capture) == 1
            assert len(sw1.interface('0/0').capture) == 1

            # The frame was sent unmodified (no tag added) across the
            # trunk link.
            assert sw0.interface('0/0').captured(dev0_to_dev2, netscool.DIR_OUT)

    netscool.clear_captures(sw0, sw1, dev0, dev1, dev2, dev3)
 
    # Send a frame across the trunk link in vlan 200. Should be tagged.
    dev1_to_dev3 = Ether(
        src=dev1.interface('0/0').mac, dst=dev3.interface('0/0').mac)
    dev1.interface('0/0').send(dev1_to_dev3)
    while event.wait:
        with event.conditions:

            # Frame is only received by intended device.
            assert dev3.interface('0/0').captured(dev1_to_dev3, netscool.DIR_IN)
            assert not dev0.interface('0/0').captured(dev0_to_dev2)
            assert not dev2.interface('0/0').captured(dev0_to_dev2)

            assert len(sw0.interface('0/0').capture) == 1
            assert len(sw1.interface('0/0').capture) == 1

            # Frame was tagged with vlan200 across trunk link.
            assert_vlan_frame(
                cap=sw0.interface('0/0').capture[0],
                src_mac=dev1.interface('0/0').mac,
                dst_mac=dev3.interface('0/0').mac,
                vlan=200)

    netscool.clear_captures(sw0, sw1, dev0, dev1, dev2, dev3)

def assert_vlan_frame(cap, src_mac, dst_mac, vlan):
    """
    Utility to assert a captured packet is tagged with a specific vlan.
    """
    frame = Ether(cap.data)
    dot1q = frame.payload
    assert isinstance(dot1q, Dot1Q)
    assert frame.dst.lower() == dst_mac.lower()
    assert frame.src.lower() == src_mac.lower()
    assert vlan == dot1q.vlan
