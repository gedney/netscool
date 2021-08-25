"""
Contains classes and methods that operate at Layer 2.
"""

import time
import logging
import collections

import scapy.all
import netscool.layer1

PROTOCOL_DOWN = 'down'
PROTOCOL_UP = 'up'
PROTOCOL_ERR = 'down err'

class L2Device(netscool.layer1.BaseDevice):
    """
    A basic layer 2 device that just logs any frame it receives.
    """
    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)

        # Keep track of the last frame the device received to make testing
        # easier.
        self.last_frame = None

    def event_loop(self):
        """ Log each frame the device receives. """
        logger = logging.getLogger("netscool.layer2.device.receive")
        for interface in self.interfaces:

            frame = interface.receive()
            if not frame:
                continue

            logger.info(
                '{} got frame {} -> {}\n {}'.format(
                    self, frame.src, frame.dst, frame))

            self.last_frame = frame
                
class L2Interface(netscool.layer1.L1Interface):
    """ A Layer 2 interface. """
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
        self.protocol_status = PROTOCOL_DOWN

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
        return self.protocol_status == PROTOCOL_UP

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
            if self.protocol_status == PROTOCOL_DOWN:
                logger.info(
                    "{} line protocol up".format(self, self.mac))
                self.protocol_status = PROTOCOL_UP
        else:
            if self.protocol_status == PROTOCOL_UP:
                logger.info(
                    "{} line protocol down".format(self, self.mac))
                self.protocol_status = PROTOCOL_DOWN

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
                '{} received invalid frame {}'.format(
                    self, frame.dst.lower()))
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

CAMEntry = collections.namedtuple('CAMEntry', ['interface', 'last_seen'])
class Switch(netscool.layer1.BaseDevice):
    def __init__(self, name, mac, interfaces):
        super().__init__(name, interfaces)

        # On top of each interface having a MAC, the switch also has its
        # own MAC. This is used as an identifier in some layer 2
        # protocols. You cannot send a frame to this address.
        self.mac = mac

        # Interfaces in a switch need to be in promiscuous mode because
        # they are generally forwarding frames not destined for them. If
        # they were not promiscuous they would drop all those frames
        # instead of forwarding them.
        for interface in self.interfaces:
            interface.promiscuous = True

        # The CAM (content addressable memory) table that tracks
        # interface -> MAC mappings. Once a MAC is 'learned' and in the
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
        print(self)
        if not self.cam:
            print("No CAM Entries")

        for mac, entry in self.cam.items():
            print(
                "{} -> {} (expires {}s)".format(
                    mac, entry.interface.name,
                    int((entry.last_seen + self.cam_timeout) - now)))

    def event_loop(self):
        """
        Receive frames and forward them out appropriate interfaces.
        """
        logger_cam = logging.getLogger('netscool.layer2.switch.cam')
        logger_recv = logging.getLogger('netscool.layer2.switch.receive')
        now = time.time()
        self._timeout_cam_entries(now)

        for interface in self.interfaces:
            frame = interface.receive()
            if not frame:
                continue
            src_mac = frame.src.lower()
            dst_mac = frame.dst.lower()

            # We have nothing to do with frames send directly to us for
            # now, so log and ignore.
            if self._is_local_frame(dst_mac):
                logger_recv.info("{} Received Frame".format(self))
                continue

            logger_cam.info(
                "{} Update CAM entry {} -> {}".format(
                    self, src_mac, interface))
            self.cam[src_mac] = CAMEntry(interface, now)

            if dst_mac in self.cam:
                logger_cam.info(
                    "{} CAM entry found {}, sending frame".format(
                        self, dst_mac))
                self.cam[dst_mac].interface.send(frame)
            else:
                logger_cam.info(
                    "{} CAM entry not found {}, flooding frame".format(
                        self, dst_mac))
                self._flood(interface, frame)

    def _is_local_frame(self, dst_mac):
        """
        Check if this frame destined for any of our local interfaces.

        :param dst_mac: Destination MAC from received frame.
        :returns: True or False
        """
        for interface in self.interfaces:
            if dst_mac == interface.mac.lower():
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
            interface.send(frame)

    def _timeout_cam_entries(self, now):
        """
        Remove any CAM entries we haven't seen frames for, for
        ``cam_timeout`` seconds.

        :param now: Current Unix timestamp.
        """
        logger = logging.getLogger('netscool.layer2.switch.cam')
        to_remove = []
        for mac, entry in self.cam.items():
            if now - self.cam_timeout > entry.last_seen:
                to_remove.append(mac)

        # Python doesnt like it when you modify a dictionary you are
        # iterating, so we flag entries for removal, then remove them in
        # this second loop.
        for mac in to_remove:
            logger.info("{} timeout CAM entry {}".format(self, mac))
            self.cam.pop(mac)

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.mac)
