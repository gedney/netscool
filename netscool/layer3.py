import logging
import ipaddress
import collections

import scapy.all

import netscool.layer1
import netscool.layer2

class ARP():
    """
    ARP table with mapping of nexthop IP to destination MAC address.
    """
    def __init__(self):
        self.table = {}

    def lookup(self, ip):
        return self.table.get(str(ip), None)

ROUTE_AD_DIRECT = 0
ROUTE_AD_STATIC = 1

class Route():
    """
    Route to specify an interface to send packets for a specified IPv4
    network.

    :param network: Packets in this network are handled by this route.
    :param interface: Interface to send packets that match this route.
    :param ad: Administrative distance. Routes can come from different
        sources (directly connected, static, various routing protocols).
        Each source has a different administrative distance. Lower ad is
        preferred if two different sources generate a route for the same
        network.
    :param metric: Routing protocols can set a metric to specify if one
        route should be used over another. The calculating of metric is
        different between different protocols, and is only relevant for
        routes with the same ad.
    :param nexthop: Next IP address if we send out this routes interface.
        This is used to determine the L2 destination MAC for frames sent
        via this route. If there is no next hop destination IP from packet
        is used.
    """
    def __init__(self, network, interface, ad, metric, nexthop=None):
        self.network = network
        self.interface = interface
        self.nexthop = nexthop
        self.ad = ad
        self.metric = metric

        # balance_metric is used to 'load balance' between routes with
        # equal network, ad, and metric.
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

            # Route is for a different network so keep it.
            if existing_route.network != route.network:
                new_routes.append(existing_route)
                continue
            # From here these existing routes are for the same network
            # as the route we are trying to add.

            # Route has a better ad so keep it and dont add the new route.
            if existing_route.ad < route.ad:
                add_route = False
                new_routes.append(existing_route)
                continue

            # Route has a worse ad so dont keep it.
            if existing_route.ad > route.ad:
                continue
            # From here these existing routes have the same ad as the
            # route we are trying to add.

            # Route has a better metric so keep it and dont add the new
            # route.
            if existing_route.metric < route.metric:
                add_route = False
                new_routes.append(existing_route)
                continue

            # Route has a worse metric so dont keep it.
            if existing_route.metric > route.metric:
                continue

            # If we reach here then the existing route is equal to the
            # route we are adding. We should keep the existing one, add
            # the new one, and load balance between the two.
            new_routes.append(existing_route)

        if add_route:
            new_routes.append(route)

        self.routes = new_routes
        return add_route

    def lookup(self, ip):
        """
        Given a destination IP address, lookup best route to send via.

        :param ip: ipaddress.IPv4Address to lookup route for.
        :return: Best route to send via.
        """
        matched_route = None
        for route in self.routes:

            # Route is for a different network so ignore.
            if ip not in route.network:
                continue

            # This route is for our network and we havent got another
            # match yet so this is the best so far.
            if not matched_route:
                matched_route = route
                continue

            # We have matched another route with a more specific prefix
            # so ignore this one.
            if matched_route.network.prefixlen > route.network.prefixlen:
                continue

            # This route is more specific that the previous best so it
            # becomes the new best.
            if matched_route.network.prefixlen < route.network.prefixlen:
                matched_route = route
                continue

            # This route is equally as good the current match so we
            # should 'load balance' our selection. 'balance_metric' keeps
            # track of how many times we have selected a route and we
            # choose the route that has been used less.
            if matched_route.balance_metric > route.balance_metric:
                matched_route = route
                continue

        matched_route.balance_metric += 1
        return matched_route

class L3Device(netscool.layer1.BaseDevice):
    """
    A basic layer 3 device that logs any packet it receives.
    """
    def __init__(self, name, gateway_ip, interfaces):
        super().__init__(name, interfaces)

        # The ARP table need to be manually populated after L3Device is
        # initialiased.
        self.arp = ARP()
        self.routetable = RouteTable()

        gateway = ipaddress.IPv4Address(gateway_ip)

        # Add directly connected routes for each interface, and default
        # gateway route.
        for interface in self.interfaces:
            assert isinstance(interface, IPInterface)

            network = ipaddress.IPv4Network(interface.ipv4, strict=False)

            # This is a route for a directly connected network. Any packet
            # that matches this route is destined for this network and
            # therefore the packets nexthop is its destination IP.
            # Therefore it doesnt make sense for directly connected routes
            # to have a nexthop.
            self.routetable.install(
                Route(
                    network=network,
                    interface=interface,
                    ad=ROUTE_AD_DIRECT,
                    metric=0))

            # If the gateway IP matches this interfaces nextwork then
            # create a default route to match any packets and send them
            # out this interface if they match no other routes.
            if gateway in network:
                self.routetable.install(
                    Route(
                        network=ipaddress.IPv4Network('0.0.0.0/0'),
                        interface=interface,
                        nexthop=gateway,
                        ad=ROUTE_AD_STATIC,
                        metric=0,))

    def event_loop(self):
        """
        Receive packets and log them.
        """
        logger = logging.getLogger("netscool.layer3.device.receive")
        for interface in self.interfaces:
            packet = interface.receive()
            if not packet:
                continue
            logger.info(
                "{} got packet\n{}".format(self, packet.show(dump=True)))

    def send(self, packet):
        """
        Send an IP packet from this device. Will do a route lookup to
        determine the best interface to send, and determine an
        appropriate destination MAC using this devices ARP table.

        :param packet: scapy.all.IP packet.
        """

        # Lookup most appropriate route to send packet.
        dst_ip = ipaddress.IPv4Address(packet.dst)
        route = self.routetable.lookup(dst_ip)
        if not route:
            logger.info("{} no route matched {}".format(self, dst_ip))
            return

        # Determine the nexthop so we can figure out the appropriate
        # destination MAC to build an ethernet frame.
        nexthop = route.nexthop
        if nexthop is None:
            nexthop = dst_ip
        dst_mac = self.arp.lookup(nexthop)
        route.interface.send(packet, dst_mac)

class Router(netscool.layer1.BaseDevice):
    """
    Router to forward IP packets between subnets.
    """

    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)
        self.arp = ARP()
        self.routetable = RouteTable()

        # Add directly connected routes.
        for interface in self.interfaces:
            assert isinstance(interface, IPInterface)

            network = ipaddress.IPv4Network(interface.ipv4, strict=False)

            # This is a route for a directly connected network. Any packet
            # that matches this route is destined for this network and
            # therefore the packets nexthop is its destination IP.
            # Therefore it doesnt make sense for directly connected routes
            # to have a nexthop.
            self.routetable.install(
                Route(
                    network=network,
                    interface=interface,
                    ad=ROUTE_AD_DIRECT,
                    metric=0))

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
            route = self.routetable.lookup(ip)
            if not route:
                logger.info("{} no route for {}".format(self, ip))
                continue

            # Determine the nexthop so we can figure out the appropriate
            # destination MAC to build an ethernet frame.
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
        """
        Show all current routes active on the device.
        """
        print("-- {} Routes --".format(self))
        for route in self.routetable.routes:
            print("{} via {}".format(
                route.network, route.interface))

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
        self, name, ipv4, mac, bandwidth=1000, mtu=1500, promiscuous=False):
        """
        :param name: Name of interface to make identifaction simpler.
        :param ipv4: String of ipv4 address eg. "192.168.0.15"
        :param mac: Layer 2 MAC address for interface in the form
            XX:XX:XX:XX:XX:XX.
        :param bandwidth: Bandwidth of interfaces in bits per second.
            Each interface at the end of a link must have the same
            bandwidth.
        :param promiscuous: A promiscuous interface will accept frames
            destined to any MAC address. A non-promiscuous interface
            will drop frames that are not destined for it.

        """
        super().__init__(name, mac, bandwidth, mtu, promiscuous)
        self.ipv4 = ipaddress.IPv4Interface(ipv4)

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
        # headers eg. Dot1Q, LLC/SNAP.
        if frame.type != scapy.all.ETH_P_IP:
            logger.error(
                "{} Invalid ethtype for ipv4 0x{0:x}".format(
                    self, frame.type))
            return None

        # Check we got an IP packet.
        packet = frame.payload
        if type(packet) != scapy.all.IP:
            logger.error(
                "{} Frame payload not parsed as ipv4".format(self))
            return None
        return packet

    def send(self, packet, dst_mac):
        """
        Send a IP packet.

        :param packet: scapy.all.IP() packet.
        """
        logger = logging.getLogger('netscool.layer3.ip.send')

        # We only support sending IP packets.
        if not isinstance(packet, scapy.all.IP):
            logger.error("{} can only send IPv4 packets".format(self))
            return

        # Create Ethernet frame and encapsulate IP packet before sending.
        ethernet = scapy.all.Ether(src=self.mac, dst=dst_mac)
        super().send(ethernet/packet)

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.ipv4)
