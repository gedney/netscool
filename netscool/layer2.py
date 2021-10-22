"""
Contains classes and methods that operate at Layer 2.
"""

import copy
import time
import logging
import collections

import scapy.all

import netscool
import netscool.layer1

class L2Device(netscool.layer1.BaseDevice):
    """
    A basic layer 2 device that just logs any frame it receives.
    """
    def event_loop(self):
        """ Log each frame the device receives. """
        logger = logging.getLogger("netscool.layer2.device.receive")
        for interface in self.interfaces:

            frame = interface.receive()
            if not frame:
                continue

            logger.info(
                '{} got frame\n{}'.format(self, frame.show(dump=True)))

class L2Interface(netscool.layer1.L1Interface):
    """ A Layer 2 interface. """

    PROTOCOL_DOWN = 'down'
    PROTOCOL_UP = 'up'
    PROTOCOL_ERR = 'down err'
    def __init__(self, name, mac, bandwidth=1000, promiscuous=False):
        """
        :param name: Name of interface to make identification simpler.
        :param mac: Layer2 MAC address for interface in the form
            XX:XX:XX:XX:XX:XX. 
        :param bandwidth: Bandwidth of interfaces in bits per second.
            Each interface at the end of a link must have the same
            bandwidth.
        :param promiscuous: A promiscuous interface will accept frames
            destined to any MAC address. A non-promiscuous interface
            will drop frames that are not destined for it.
        """
        super().__init__(name, bandwidth)
        self.mac = mac
        self.promiscuous = promiscuous
        self.protocol_status = L2Interface.PROTOCOL_DOWN

    @property
    def upup(self):
        """
        True if the line status and protocol status are both up. An
        interface can only send and receive frames if it is up/up.
        """
        return self.line_up and self.protocol_up

    @property
    def status(self):
        """
        Get a tuple of the line and protocol status for the interface.
        Line status is the status of the link at Layer 1, and protocol
        status is the status of the link at Layer 2. Protocol status
        can only be up if line status is also up.
        """
        return (self.line_status, self.protocol_status)

    @property
    def protocol_up(self):
        """ Is the protocol status up (Layer2 connectivity). """
        return self.protocol_status == L2Interface.PROTOCOL_UP

    def negotiate_connection(self):
        """
        Negotiate the Layer 2 protocol for the interface. For now we only
        have one L2 protocol and we assume its connectivity always works.
        We also haven't implemented port security so err disabled does
        not apply.
        """
        super().negotiate_connection()
        logger = logging.getLogger('netscool.layer2.interface.status')
        if self.line_up:
            if self.protocol_status == L2Interface.PROTOCOL_DOWN:
                logger.info(
                    "{} line protocol up".format(self, self.mac))
                self.protocol_status = L2Interface.PROTOCOL_UP
        else:
            if self.protocol_status == L2Interface.PROTOCOL_UP:
                logger.info(
                    "{} line protocol down".format(self, self.mac))
                self.protocol_status = L2Interface.PROTOCOL_DOWN

    def receive(self):
        """
        Receive a layer 2 frame.

        :returns: Scapy Ether object of frame or None.
        """
        logger = logging.getLogger('netscool.layer2.interface.receive')
        if not self.upup:
            return
        data = super().receive()
        if not data:
            return

        try:
            frame = scapy.all.Ether(data)
        except:
            # scapy couldn't recognise the frame so log the exception and
            # drop it. We catch all exceptions because scapy can raise a
            # wide range on exceptions, and we want to do the same thing
            # in all cases.
            logger.exception("Invalid Ethernet frame received.")
            return

        if not self.promiscuous and frame.dst.lower() != self.mac.lower():
            logger.error(
                '{} frame dst {} didnt match interface mac {}'.format(
                    self, frame.dst.lower(), self.mac.lower()))
            return
        logger.info("{} received layer2 frame".format(self))
        return frame

    def send(self, frame):
        """
        Send a layer 2 frame.

        :param frame: Scapy Ether object of frame.
        """
        logger = logging.getLogger('netscool.layer2.interface.send')
        if not self.upup:
            logger.error('{} not up/up'.format(self))
            return

        if not isinstance(frame, scapy.all.Ether):
            logger.error('{} can only send Ether frames'.format(self))
            return

        logger.info("{} sending layer2 frame".format(self))
        super().send(bytes(frame))

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.mac)


#@netscool.implementation('lesson2')
#class Switch(netscool.layer1.BaseDevice):
#
#    CAMEntry = collections.namedtuple(
#        'CAMEntry', ['interface', 'last_seen'])
#
#    def __init__(self, name, mac, interfaces):
#        super().__init__(name, interfaces)
#
#        # On top of each interface having a MAC, the switch also has its
#        # own MAC. This is used as an identifier in some layer 2
#        # protocols. You cannot send a frame to this address.
#        self.mac = mac
#
#        # Interfaces in a switch need to be in promiscuous mode because
#        # they are generally forwarding frames not destined for them. If
#        # they were not promiscuous they would drop all those frames
#        # instead of forwarding them.
#        for interface in self.interfaces:
#            interface.promiscuous = True
#
#        # The CAM (content addressable memory) table that tracks
#        # interface -> MAC mappings. Once a MAC is 'learned' and in the
#        # CAM table the switch no longer has to flood frames out every
#        # interface to deliver the frame.
#        self.cam = {}
#
#        # If we dont see a MAC address for this many seconds, then remove
#        # the mapping from the table. This timeout removes stale entries
#        # from the table eg. A device in unplugged.
#        self.cam_timeout = 300
#
#    def show_cam(self):
#        """
#        Print out current entries in the switch CAM table.
#        """
#        now = time.time()
#
#        print('MAC\t\t\tInterface\tExpires')
#        print('-' * 55)
#        for mac, entry in self.cam.items():
#            expires = int((entry.last_seen + self.cam_timeout) - now)
#            print("{}\t{}\t\t{}".format(
#                mac, entry.interface.name, expires))
#
#    def event_loop(self):
#        """
#        Receive frames and forward them out appropriate interfaces.
#        """
#        logger_cam = logging.getLogger('netscool.layer2.switch.cam')
#        logger_recv = logging.getLogger('netscool.layer2.switch.receive')
#        self._timeout_cam_entries()
#
#        for interface in self.interfaces:
#            frame = interface.receive()
#            if not frame:
#                continue
#
#            # We have nothing to do with frames send directly to us for
#            # now, so log and ignore.
#            if self._is_local_frame(frame):
#                logger_recv.info("{} Received Frame".format(self))
#                continue
#
#            src_mac = frame.src.lower()
#            dst_mac = frame.dst.lower()
#
#            logger_cam.info(
#                "{} Update CAM entry {} -> {}".format(
#                    self, src_mac, interface.name))
#            self.cam[src_mac] = Switch.CAMEntry(interface, time.time())
#
#            if dst_mac in self.cam:
#                logger_cam.info(
#                    "{} CAM entry found {}, sending frame".format(
#                        self, dst_mac))
#                self.cam[dst_mac].interface.send(frame)
#            else:
#                logger_cam.info(
#                    "{} CAM entry not found {}, flooding frame".format(
#                        self, dst_mac))
#                self._flood(interface, frame)
#
#    def _is_local_frame(self, frame):
#        """
#        Check if this frame destined for any of our local interfaces.
#
#        :param frame: Received frame.
#        :returns: True or False
#        """
#        for interface in self.interfaces:
#            if frame.dst.lower() == interface.mac.lower():
#                return True
#        return False
#
#    def _flood(self, src_interface, frame):
#        """
#        Flood frame out all interfaces, except src_interface.
#
#        :param src_interface: The interface that received the frame.
#        :param frame: The frame to flood.
#        """
#        for interface in self.interfaces:
#            if not interface.upup:
#                continue
#            if interface == src_interface:
#                continue
#            interface.send(frame)
#
#    def _timeout_cam_entries(self):
#        """
#        Remove any CAM entries we haven't seen frames for, for
#        ``cam_timeout`` seconds.
#        """
#        logger = logging.getLogger('netscool.layer2.switch.cam')
#        now = time.time()
#        to_remove = []
#        for mac, entry in self.cam.items():
#            if now - self.cam_timeout > entry.last_seen:
#                to_remove.append(mac)
#
#        # Python doesnt like it when you modify a dictionary you are
#        # iterating, so we flag entries for removal, then remove them in
#        # this second loop.
#        for mac in to_remove:
#            logger.info("{} timeout CAM entry {}".format(self, mac))
#            self.cam.pop(mac)
#
#    def __str__(self):
#        return "{} ({})".format(super().__str__(), self.mac)

#@netscool.implementation('lesson3')
#@netscool.implementation('default')
class Switch(netscool.layer1.BaseDevice):

    CAMKey = collections.namedtuple('CAMKey', ['mac', 'vlan'])
    CAMEntry = collections.namedtuple(
        'CAMEntry', ['interface', 'last_seen'])

    def __init__(self, name, mac, interfaces):
        super().__init__(name, interfaces)

        # On top of each interface having a MAC, the switch also has its
        # own MAC. This is used as an identifier in some layer 2
        # protocols. You cannot send a frame to this address.
        self.mac = mac

        # Our switch should be using SwitchPorts, which are by default
        # in promiscuous mode.
        for interface in self.interfaces:
            assert isinstance(interface, SwitchPort)
            assert interface.promiscuous

        # The CAM (content addressable memory) table that tracks
        # MAC -> interface mappings. Once a MAC is 'learned' and in the
        # CAM table the switch no longer has to flood frames out every
        # interface to deliver the frame.
        self.cam = {}

        # If we dont see a MAC address for this many seconds, then remove
        # the mapping from the table. This timeout removes stale entries
        # from the table eg. A device in unplugged.
        self.cam_timeout = 300

    def show_cam(self):
        """
        Print out current entries in the switch CAM table.
        """
        now = time.time()

        print('MAC\t\t\tVLAN\tInterface\tExpires')
        print('-' * 55)
        for key, entry in self.cam.items():
            expires = int((entry.last_seen + self.cam_timeout) - now)
            print("{}\t{}\t{}\t\t{}".format(
                key.mac, key.vlan, entry.interface.name, expires))

    def event_loop(self):
        """
        Receive frames and forward them out appropriate interfaces.
        """
        logger_cam = logging.getLogger('netscool.layer2.switch.cam')
        logger_recv = logging.getLogger('netscool.layer2.switch.receive')
        self._timeout_cam_entries()

        for interface in self.interfaces:
            frame = interface.receive()
            if not frame:
                continue

            assert isinstance(frame.payload, scapy.all.Dot1Q), "Switch expects only dot1q frames"

            # We have nothing to do with frames send directly to us for
            # now, so log and ignore.
            if self._is_local_frame(frame):
                logger_recv.info("{} Received Frame".format(self))
                continue

            src_mac = frame.src.lower()
            dst_mac = frame.dst.lower()
            vlan = frame.payload.vlan

            src_key = Switch.CAMKey(src_mac, vlan)
            entry = Switch.CAMEntry(interface, time.time())
            logger_cam.info(
                "{} Update CAM entry {} -> {}".format(
                    self, src_key, entry.interface.name))
            self.cam[src_key] = entry

            dst_key = Switch.CAMKey(dst_mac, vlan)
            if dst_key in self.cam:
                logger_cam.info(
                    "{} CAM entry found {}, sending frame".format(
                        self, dst_key))
                self.cam[dst_key].interface.send(frame)
            else:
                logger_cam.info(
                    "{} CAM entry not found {}, flooding frame".format(
                        self, dst_key))
                self._flood(interface, frame)

    def _is_local_frame(self, frame):
        """
        Check if this frame destined for any of our local interfaces.

        :param frame: Received frame.
        :returns: True or False
        """
        for interface in self.interfaces:
            if frame.dst.lower() == interface.mac.lower():
                return True
        return False

    def _flood(self, src_interface, frame):
        """
        Flood frame out all interfaces, except src_interface.

        :param src_interface: The interface that received the frame.
        :param frame: The frame to flood.
        """
        for interface in self.interfaces:
            if not interface.upup:
                continue
            if interface == src_interface:
                continue

            # We assume the interface will ignore anything it cant send eg.
            # frame is from wrong vlan.
            interface.send(frame)

    def _timeout_cam_entries(self):
        """
        Remove any CAM entries we haven't seen frames for, for
        ``cam_timeout`` seconds.
        """
        logger = logging.getLogger('netscool.layer2.switch.cam')
        now = time.time()
        to_remove = []
        for key, entry in self.cam.items():
            if now - self.cam_timeout > entry.last_seen:
                to_remove.append(key)

        # Python doesnt like it when you modify a dictionary you are
        # iterating, so we flag entries for removal, then remove them in
        # this second loop.
        for key in to_remove:
            logger.info("{} timeout CAM entry {}".format(self, key))
            self.cam.pop(key)

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.mac)

class SwitchPort(L2Interface):
    """
    Extends L2Interface with switchport specific behaviour. Primarily
    handles dot1q vlan tags for frames coming in/out of the port. This
    interface type should only ever be used by a Switch.
    """

    # Two possible modes for a SwitchPort.
    ACCESS = 'access'
    TRUNK = 'trunk'

    def __init__(self, name, mac, bandwidth=1000):
        super().__init__(name, mac, bandwidth, True)
        self.default_vlan = 1
        self.set_access_port()

    def set_access_port(self, vlan=None):
        """
        Set switchport as an access port.

        :param vlan: The vlan to tag incoming frames with.
        """
        logger = logging.getLogger('netscool.layer2.switch.port')
        self._vlan = vlan
        if self._vlan == None:
            self._vlan = self.default_vlan

        self._mode = SwitchPort.ACCESS
        self._allowed_vlans = None
        self._native_vlan = None
        logger.info(
            "{} set as {} vlan {}".format(self, self._mode, self._vlan))

    def set_trunk_port(self, allowed_vlans=None, native_vlan=None):
        """
        Set switchport as a trunk.

        :param allowed_vlans: List of allowed vlans, or None to allow all.
        :param native_vlan: The native vlan for this port, or None to use
            default_vlan.
        """
        logger = logging.getLogger('netscool.layer2.switch.port')
        self._allowed_vlans = allowed_vlans
        self._native_vlan = native_vlan
        if self._native_vlan == None:
            self._native_vlan = self.default_vlan

        self._mode = SwitchPort.TRUNK
        self._vlan = None
        logger.info(
            "{} set as {}, allowed vlans {}, native vlan {}".format(
                self, self._mode,
                'all' if self.allow_all_vlan else self._allowed_vlans,
                self._native_vlan))

    @property
    def allow_all_vlan(self):
        """
        Are all vlans allowed.
        """
        return self._allowed_vlans == None

    def vlan_allowed(self, vlan):
        """
        Check a given vlan is allowed for this trunk port.

        :param vlan: Vlan to check is allowed.
        :return: True or False.
        """
        if self._mode != SwitchPort.TRUNK:
            return False
        return self.allow_all_vlan or vlan in self._allowed_vlans

    def receive(self):
        """
        Receive a frame on the switchport. Our switch internally expects
        all frames to be dot1q tagged so this will always return the
        frame with the appropriate tag.

        For a switchport in 'access' mode, check the frame is untagged. If
        its not then tag it with the vlan for the access port. Otherwise
        drop it.

        For a swithport in 'trunk' mode, check the frame is tagged. If it
        isnt tagged then add the native dot1q tag to the frame. Then
        check the frames' vlan is an allowed vlan for this trunk port.

        :returns: The received Ether frame with the appropriate dot1q
            vlan tag.
        """
        frame = super().receive()
        if not frame:
            return None

        logger = logging.getLogger('netscool.layer2.switch.port')
        if self._mode == SwitchPort.ACCESS:

            # Access ports should normally only receive untagged frames.
            # How access ports handle tagged frames is vendor, model, and
            # firmware specific. For simplicity we will drop any frame
            # received on an access port with a dot1q tag.
            if isinstance(frame.payload, scapy.all.Dot1Q):
                logger.info(
                    "{} got tagged frame, dropping".format(self))
                return None

            # Tag the received frame with the appropriate vlan.
            logger.info(
                "{} tag frame with vlan {}".format(self, self._vlan))
            return _tag_frame(frame, self._vlan)

        elif self._mode == SwitchPort.TRUNK:
            if not isinstance(frame.payload, scapy.all.Dot1Q):
                logger.info(
                    "{} untagged frame, add native vlan {}".format(
                        self, self._native_vlan))
                frame = _tag_frame(frame, self._native_vlan)

            vlan = frame.payload.vlan
            if not self.vlan_allowed(vlan):
                logger.info(
                    "{} {} not in allowed vlans".format(
                        self, vlan))
                return None
            return frame
        
    def send(self, frame):
        """
        Send a dot1q tagged Ethernet frame. We assume that internally the
        switch will only use dot1q frames, so any frame being sent from
        the switch should be dot1q tagged.

        For a switchport in 'access' mode, check the frame is for the
        correct vlan, and if it is send the frame with the dot1q tag
        removed.

        For a switchport in 'trunk' mode, check the frame is tagged with
        an allowed vlan for this trunk. If it is allowed and tagged with
        the native vlan, untag the frame and send it. If it is allowed
        and not the native vlan send the frame with the dot1q tag intact.

        :param frame: dot1q tagged Ethernet frame.
        """
        logger = logging.getLogger('netscool.layer2.switch.port')
        if not isinstance(frame.payload, scapy.all.Dot1Q):
            logger.info("{} only expects tagged frames".format(self))
            return

        if self._mode == SwitchPort.ACCESS:
            vlan = frame.payload.vlan

            # Frame is not for this access ports vlan, so drop it. When
            # the switch floods frames this is what stops frames leaking
            # to the wrong vlans.
            if vlan != self._vlan:
                logger.info(
                    "{} frame not for our vlan, ignoring".format(self))
                return

            # Frame is for this access ports vlan, so untag it and
            # send it.
            logger.info(
                "{} untag frame and send".format(self))
            frame = _untag_frame(frame)

        elif self._mode == SwitchPort.TRUNK:
            vlan = frame.payload.vlan

            # Vlan is not allowed on this trunk, so drop the frame.
            if not self.vlan_allowed(vlan):
                logger.info(
                    "{} {} not in allowed vlans".format(
                        self, vlan))
                return

            # Frame is tagged with the native vlan, so untag it and send
            # the frame.
            if vlan == self._native_vlan:
                logger.info(
                    "{} untag frame in native vlan".format(self))
                frame = _untag_frame(frame)
        super().send(frame)

    def __str__(self):
        return "{}({})".format(super().__str__(), self._mode)

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
    dot1q = scapy.all.Dot1Q(vlan=vlan, type=payload_type)
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
    if not isinstance(dot1q, scapy.all.Dot1Q):
        return None

    # Get the new frame header and payload.
    payload = dot1q.payload
    header = new_frame.firstlayer()

    # Remove the dot1q payload and add the underlying payload.
    header.remove_payload()
    header.type = dot1q.type
    return header/payload
