import logging
import ipaddress
import collections

import scapy.all

import netscool.layer1
import netscool.layer2

class ARP():
    def __init__(self):
        self.table = {}

    def lookup(self, ip):
        return self.table.get(ip, None)

class L3Device(netscool.layer1.BaseDevice):
    """
    A basic layer 3 device that logs any packet it receives.
    """
    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)

        # Create a single ARP table that can be shared between all
        # interfaces on the device.
        self.arp = ARP()
        for interface in self.interfaces:
            assert isinstance(interface, IPInterface)
            interface.arp = self.arp

    def event_loop(self):
        logger = logging.getLogger("netscool.layer3.device.receive")
        for interface in self.interfaces:
            packet = interface.receive()
            if not packet:
                continue
            logger.info(
                "{} got packet\n{}".format(self, packet.show(dump=True)))

class Router(netscool.layer1.BaseDevice):
    """
    Router to forward IP packets between subnets.
    """
    ROUTE_TYPE_DIRECT = "directly connected"
    Route = collections.namedtuple(
        "Route", ['network', 'interface', 'route_type'])

    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)
        self.arp = ARP()
        self.routes = []

        # Set interface ARP table and add directly connected routes.
        for interface in self.interfaces:
            assert isinstance(interface, IPInterface)
            interface.arp = self.arp

            network = ipaddress.IPv4Network(interface.ipv4, strict=False)
            route = Router.Route(
                network=network,
                interface=interface,
                route_type=Router.ROUTE_TYPE_DIRECT)
            self.routes.append(route)

    def event_loop(self):
        """
        Receive IP packets and forward them out an appropriate interface
        according to the configured routes.
        """
        logger = logging.getLogger("netscool.layer3.router")
        for interface in self.interfaces:
            packet = interface.receive()
            if not packet:
                continue

            # Packet is addressed to the router. We dont have anything
            # to do with it yet so just drop for now.
            if self._is_local(packet):
                logger.info("{} Receive Packet".format(self))
                continue

            # Send the packet out the interface for the first route that
            # matches. If no route matches then the packet is silently
            # dropped.
            ip = ipaddress.IPv4Address(packet.dst)
            for route in self.routes:
                if ip in route.network:
                    logger.info(
                        "{} route {} matched, forwarding out {}".format(
                            self, route.network, route.interface))
                    route.interface.send(packet)
                    break

    def show_routes(self):
        """
        Show all current routes active on the device.
        """
        print("-- {} Routes --".format(self))
        for route in self.routes:
            print("{} via {} - {}".format(
                route.network, route.interface, route.route_type))

    def _is_local(self, packet):
        """
        Is the packet destined to a local interface IP.
        """
        dst_ip = ipaddress.IPv4Address(packet.dst)
        for interface in self.interfaces:
            if interface.ipv4.ip == dst_ip:
                return True
        return False

class IPInterface(netscool.layer2.L2Interface):
    """
    Layer 3 interface that sends and receives IPv4 packets.
    """
    def __init__(
        self, name, ipv4, mac, bandwidth=1000, promiscuous=False):
        """
        :param name: Name of interface to make identifaction simpler.
        :param ipv4: String of ipv4 address eg. "127.0.0.1"
        :param mac: Layer 2 MAC address for interface in the form
            XX:XX:XX:XX:XX:XX.
        :param bandwidth: Bandwidth of interfaces in bits per second.
            Each interface at the end of a link must have the same
            bandwidth.
        :param promiscuous: A promiscuous interface will accept frames
            destined to any MAC address. A non-promiscuous interface
            will drop frames that are not destined for it.

        """
        super().__init__(name, mac, bandwidth, promiscuous)
        self.ipv4 = ipaddress.IPv4Interface(ipv4)
        self.arp = None

    def receive(self):
        """
        Receive layer 3 IP packet.

        :return: scapy.all.IP packet.
        """
        logger = logging.getLogger('netscool.layer3.ip.receive')

        # Get the received frame from layer 2.
        frame = super().receive()
        if not frame:
            return None

        # If the frame does not encapsulate an IPv4 packet then discard
        # it. This does not account IP packets encapsulated in other
        # headers eg. LLC/SNAP.
        if frame.type != scapy.all.ETH_P_IP:
            logger.error(
                "{} Invalid ethtype for ipv4 0x{0:x}".format(
                    self, frame.type))
            return None

        # The ARP table has not been set by the parent device.
        if not self.arp:
            logger.error("{} no arp table set".format(self))
            return None

        # Check we got an IP packet.
        packet = frame.payload
        if type(packet) != scapy.all.IP:
            logger.error(
                "{} Frame payload not parsed as ipv4".format(self))
            return None
        return packet

    def send(self, packet):
        """
        Send a IP packet.

        :param packet: scapy.all.IP() packet.
        """
        logger = logging.getLogger('netscool.layer3.ip.send')

        # We only support sending IP packets.
        if not isinstance(packet, scapy.all.IP):
            logger.error("{} can only send IPv4 packets".format(self))
            return

        # The ARP table has not been set by the parent device.
        if not self.arp:
            logger.error("{} no arp table set".format(self))
            return

        # To send our packet we need to encapsulate it in an Ethernet
        # frame. This means we need a source MAC (this interfaces MAC),
        # and a destination MAC (MAC of next layer 3 interface). If our
        # ARP lookup fails then we have no destination MAC for our frame
        # and cant send the packet.
        dst_mac = self.arp.lookup(packet.dst)
        if not dst_mac:
            logger.error(
                "{} failed ARP lookup for {}".format(self, packet.dst))
            return

        # Create Ethernet frame and encapsulate IP packet before sending.
        ethernet = scapy.all.Ether(src=self.mac, dst=dst_mac)
        super().send(ethernet/packet)
