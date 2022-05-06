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
        return self.table.get(str(ip), None)

ROUTE_AD_DIRECT = 0
ROUTE_AD_STATIC = 1

class Route():
    def __init__(self, network, interface, ad, metric, nexthop=None):
        self.network = network
        self.interface = interface
        self.nexthop = nexthop
        self.ad = ad
        self.metric = metric
        self.balance_metric = 0

    def __eq__(self, other):
        return (
            self.network == other.network and
            self.interface == other.interface and
            self.nexthop == other.nexthop and
            self.ad == other.ad and
            self.metric == other.metric)

    def __str__(self):
        return "{} -> {}({}) [{}/{}]".format(
            self.network, self.interface, self.nexthop, self.ad,
            self.metric)

    def __repr__(self):
        return self.__str__()

class RouteTable():
    def __init__(self):
        self.routes = []

    def install(self, route):

        if not route.network or not route.interface:
            return False

        new_routes = []

        add_route = True
        for existing_route in self.routes:

            if existing_route.network != route.network:
                new_routes.append(existing_route)
                continue
            if existing_route.ad < route.ad:
                add_route = False
                new_routes.append(existing_route)
                continue
            if existing_route.ad > route.ad:
                continue
            if existing_route.metric < route.metric:
                add_route = False
                new_routes.append(existing_route)
                continue
            if existing_route.metric > route.metric:
                continue
            new_routes.append(existing_route)

        if add_route:
            new_routes.append(route)

        self.routes = new_routes
        return add_route

    def lookup(self, ip):
        matched_route = None
        for route in self.routes:
            if ip not in route.network:
                continue
            if not matched_route:
                matched_route = route
                continue
            if matched_route.network.prefixlen > route.network.prefixlen:
                continue
            if matched_route.network.prefixlen < route.network.prefixlen:
                matched_route = route
                continue
            if matched_route.balance_metric > route.balance_metric:
                matched_route = route
                continue
        matched_route.balance_metric += 1
        return matched_route

class L3Device(netscool.layer1.BaseDevice):
    def __init__(self, name, gateway_ip, interfaces):
        super().__init__(name, interfaces)
        self.arp = ARP()
        self.routetable = RouteTable()

        gateway = ipaddress.IPv4Address(gateway_ip)
        for interface in self.interfaces:
            assert isinstance(interface, IPInterface)

            network = ipaddress.IPv4Network(interface.ipv4, strict=False)

            self.routetable.install(
                Route(
                    network=network,
                    interface=interface,
                    ad=ROUTE_AD_DIRECT,
                    metric=0))
            if gateway in network:
                self.routetable.install(
                    Route(
                        network=ipaddress.IPv4Network('0.0.0.0/0'),
                        interface=interface,
                        nexthop=gateway,
                        ad=ROUTE_AD_STATIC,
                        metric=0,))

    def event_loop(self):
        logger = logging.getLogger("netscool.layer3.device.receive")
        for interface in self.interfaces:
            packet = interface.receive()
            if not packet:
                continue
            logger.info(
                "{} got packet\n{}".format(self, packet.show(dump=True)))

    def send(self, packet):
        dst_ip = ipaddress.IPv4Address(packet.dst)
        route = self.routetable.lookup(dst_ip)
        if not route:
            logger.info("{} no route matched {}".format(self, dst_ip))
            return

        nexthop = route.nexthop
        if nexthop is None:
            nexthop = dst_ip
        dst_mac = self.arp.lookup(nexthop)
        route.interface.send(packet, dst_mac)

class Router(netscool.layer1.BaseDevice):
    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)
        self.arp = ARP()
        self.routetable = RouteTable()

        for interface in self.interfaces:
            assert isinstance(interface, IPInterface)

            network = ipaddress.IPv4Network(interface.ipv4, strict=False)

            self.routetable.install(
                Route(
                    network=network,
                    interface=interface,
                    ad=ROUTE_AD_DIRECT,
                    metric=0))

    def event_loop(self):
        logger = logging.getLogger("netscool.layer3.router")
        for interface in self.interfaces:
            packet = interface.receive()
            if not packet:
                continue

            if self._is_local(packet):
                logger.info("{} Receive Packet".format(self))
                continue

            ip = ipaddress.IPv4Address(packet.dst)
            route = self.routetable.lookup(ip)
            if not route:
                logger.info("{} no route for {}".format(self, ip))
                continue

            nexthop = route.nexthop
            if nexthop is None:
                nexthop = ip
            dst_mac = self.arp.lookup(nexthop)
            logger.info(
                "{} route {} matched, forwarding out {}".format(
                    self, route.network, route.interface))
            route.interface.send(packet, dst_mac)

    def add_static_route(self, network, nexthop=None, out_interface=None):
        logger = logging.getLogger("netscool.layer3.router")
        if (
            (nexthop is None and out_interface is None) or
            (nexthop and out_interface)):

            logger.error(
                "{} must specify nexthop OR out interface for static"
                " route".format(self))
            return

        network = ipaddress.IPv4Network(network)

        if nexthop:
            nexthop = ipaddress.IPv4Address(nexthop)

        if out_interface is None:
            for interface in self.interfaces:
                if nexthop not in interface.ipv4.network:
                    continue
                if nexthop == interface.ipv4.ip:
                    logger.error(
                        "{} nexthop must be remote address not local"
                        " interface address".format(self))
                    return
                out_interface = interface
                break

        if out_interface is None:
            logger.error(
                "{} could not determine out interface for"
                " nexthop {}".format(nexthop))
            return

        return self.routetable.install(
            Route(
                network=network,
                nexthop=nexthop,
                interface=out_interface,
                ad=ROUTE_AD_STATIC,
                metric=0,
                ))

    def show_routes(self):
        print("-- {} Routes --".format(self))
        for route in self.routetable.routes:
            print("{} via {}".format(
                route.network, route.interface))

    def _is_local(self, packet):
        dst_ip = ipaddress.IPv4Address(packet.dst)
        for interface in self.interfaces:
            if interface.ipv4.ip == dst_ip:
                return True
        return False

class IPInterface(netscool.layer2.L2Interface):
    def __init__(
        self, name, ipv4, mac, bandwidth=1000, mtu=1500, promiscuous=False):
        super().__init__(name, mac, bandwidth, mtu, promiscuous)
        self.ipv4 = ipaddress.IPv4Interface(ipv4)

    def receive(self):
        logger = logging.getLogger('netscool.layer3.ip.receive')

        frame = super().receive()
        if not frame:
            return None
        if frame.type != scapy.all.ETH_P_IP:
            logger.error(
                "{} Invalid ethtype for ipv4 0x{0:x}".format(
                    self, frame.type))
            return None
        packet = frame.payload
        if type(packet) != scapy.all.IP:
            logger.error(
                "{} Frame payload not parsed as ipv4".format(self))
            return None
        return packet

    def send(self, packet, dst_mac):
        logger = logging.getLogger('netscool.layer3.ip.send')

        if not isinstance(packet, scapy.all.IP):
            logger.error("{} can only send IPv4 packets".format(self))
            return

        ethernet = scapy.all.Ether(src=self.mac, dst=dst_mac)
        super().send(ethernet/packet)

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.ipv4)



def test_lesson4_reference_router():
    assert False
def test_lesson4_reference_l3device():
    assert False
def test_lesson4_reference_ipinterface():
    assert False
