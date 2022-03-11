"""
Reference implementations for lesson4.
"""
import logging
import ipaddress
import collections
import scapy.all
import netscool.layer1
import netscool.layer2

from tests.lessons.test_lesson1 import L2Interface

class ARP():
    def __init__(self):
        self.table = {}

    def lookup(self, ip):
        return self.table.get(ip, None)

class L3Device(netscool.layer1.BaseDevice):
    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)
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
    ROUTE_TYPE_DIRECT = "directly connected"
    Route = collections.namedtuple(
        "Route", ['network', 'interface', 'route_type'])

    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)
        self.arp = ARP()
        self.routes = []

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
        for interface in self.interfaces:
            packet = interface.receive()
            if not packet:
                continue

            if self._is_local(packet):
                continue

            ip = ipaddress.IPv4Address(packet.dst)
            for route in self.routes:
                if ip in route.network:
                    route.interface.send(packet)
                    break

    def show_routes(self):
        pass

    def _is_local(self, packet):
        dst_ip = ipaddress.IPv4Address(packet.dst)
        for interface in self.interfaces:
            if interface.ipv4.ip == dst_ip:
                return True
        return False

class IPInterface(netscool.layer2.L2Interface):
    def __init__(
        self, name, ipv4, mac, bandwidth=1000, promiscuous=False):
        super().__init__(name, mac, bandwidth, promiscuous)
        self.ipv4 = ipaddress.IPv4Interface(ipv4)
        self.arp = None

    def receive(self):
        frame = super().receive()
        if not frame:
            return None

        if frame.type != scapy.all.ETH_P_IP:
            return None

        if not self.arp:
            return None

        packet = frame.payload
        if type(packet) != scapy.all.IP:
            return None
        return packet

    def send(self, packet):
        if not isinstance(packet, scapy.all.IP):
            return

        if not self.arp:
            return

        dst_mac = self.arp.lookup(packet.dst)
        if not dst_mac:
            return
        ethernet = scapy.all.Ether(src=self.mac, dst=dst_mac)
        super().send(ethernet/packet)

def test_lesson4_reference_router():
    assert False
def test_lesson4_reference_l3device():
    assert False
def test_lesson4_reference_ipinterface():
    assert False
