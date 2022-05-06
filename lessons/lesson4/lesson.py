import ipaddress
import IPython
import netscool

import netscool.layer1

from scapy.all import IP

from <your_module> import L2Interface

# When sending with our IPv4Interface we provide an IPv4 packet and rely
# on the interface to add the necessary layer 2 Ethernet header. This
# means the interface needs to be able to determine the appropriate
# destination MAC address for the Ethernet frame. Normally the Address
# Resolution Protocol is used to determine the mapping from IPv4 address
# to MAC address, however to avoid adding too much in a single lesson, for
# now we will use this placeholder that we can manually populate.
class ARP():
    """
    ARP table with mapping of nexthop IP to destination MAC address.
    """
    def __init__(self):
        self.table = {}

    def lookup(self, ip):
        return self.table.get(str(ip), None)

# A skeleton data class to represent a route. This provides the minimum
# members required for a route, feel free to add extra functionality
# required for your implementation.
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

        # May also have to add extra members to help with load balancing
        # between equal routes.

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

# A route table that can be used by any layer 3 device.
class RouteTable():
    def __init__(self):
        self.routes = []

    def install(self, route):
        """
        Attempt to install the given route into the route table.

        :param route: Route to install.
        :return: True if it was added, False if there was an error or better
            route already installed.
        """

        # Conditions that this route can be added.
        #  * There is no existing route for this routes network.
        #  * There is an existing route for this network, but this route
        #    has a lower ad.
        #  * There is an existing route for this network, and ad is equal,
        #    but this route has a lower metric.
        #  * There is an existing route with equal network, ad, and
        #    metric, in which case keep both routes and load balance
        #    between them.
        pass

    def lookup(self, ip):
        """
        Given a destination IP address, lookup best route to send via.

        :param ip: ipaddress.IPv4Address to lookup route for.
        :return: Best route to send via or None if no route.
        """

        # If install works correctly then only the best route for each
        # network should be installed, however our IP can still match
        # multiple networks. We should select the route with the most
        # specific prefix ie. /28 better than /24. If there are two
        # routes for the same network you should add a mechanism to load
        # balance between those routes.
        pass

class IPInterface(L2Interface):
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

        # Using the ipaddress.IPv4Network object makes interacting with
        # ipaddresses much easier eg.
        # ipv4.ip in IPv4Network("127.0.0.1/24")
        self.ipv4 = ipaddress.IPv4Interface(ipv4)

    def receive(self):
        """
        Receive layer 3 IP packet.

        :return: scapy.all.IP packet.
        """
        # Receive a frame from layer 2.
        frame = super().receive()
        if not frame:
            return None

        # Things to do once we have a frame.
        #  * Check the frame is encapsulating an IP packet. You can do
        #    this by checking frame.type. Hint in scapy the ethertype for
        #    IP is scapy.all.ETH_P_IP.
        #  * Get the encapsulated IP packet from the frame. Hint
        #    frame.payload.
        #  * Do any other checks you think appropriate.
        #  * Return the IP packet.
        pass

    def send(self, packet, dst_mac):
        """
        Send a IP packet.

        :param packet: scapy.all.IP() packet.
        :param dst_mac: Destination MAC or ethernet header.
        """

        # Things to do to send a packet.
        #  * Validate you have been passed an IP packet as expected.
        #  * Create an Ethernet frame with src mac of this interface, and
        #    dst_mac as provided.

        ethernet = ...

        # This will encapsulate packet in the provided Ethernet frame
        # and send it to the next layer of the network stack.
        super().send(ethernet/packet)

class L3Device(netscool.layer1.BaseDevice):
    """
    A basic layer 3 device that logs any packet it receives.
    """
    def __init__(self, name, gateway_ip, interfaces):
        super().__init__(name, interfaces)

        self.arp = ARP()
        self.routetable = RouteTable()

        # For each interface you will have to add a directly connected
        # route to the routetable. You will also have to add an
        # appropriate static route for the default gateway.

    def event_loop(self):
        """
        Receive packets and log them.
        """
        for interface in self.interfaces:
            packet = interface.receive()
            if not packet:
                continue
            # Log or print details of packet using packet.show().

    def send(self, packet):
        """
        Send an IP packet from this device. Will do a route lookup to
        determine the best interface to send, and determine an
        appropriate destination MAC using this devices ARP table.

        :param packet: scapy.all.IP packet.
        """

        # You will have to do the following things.
        #  * Lookup the most appropriate route to send via.
        #  * Determine the next ip to send this packet towards
        #  * Lookup the MAC for the next ip.
        #  * Send the packet out the appropriate interface.
        pass

class Router(netscool.layer1.BaseDevice):
    """
    Router to forward IP packets between subnets.
    """

    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)

        self.arp = ARP()
        self.routetable = RouteTable()

        # For each interface you will have to add a directly connected
        # route.

    def event_loop(self):
        """
        Receive IP packets and forward them out an appropriate interface
        according to the configured routes.
        """

        # Things our router needs to do.
        #  * Check all interfaces for recevied packets.
        #  * Check if the packet is destined for the router itself. In
        #    which case it can be dropped for now.
        #  * Drop packet if it matches no installed route.
        #  * Determine next ip to send packet (route nexthop, or packet
        #    dst ip).
        #  * Lookup destination mac for next IP.
        #  * Send packet out appropriate interface.

    def add_static_route(self, network, nexthop=None, out_interface=None):
        """
        Convenience function for adding static routes to router. Must
        specify a nexthop ip or out interface, but not both. If only next
        hop is provided then it will be used to determine an appropriate
        out interface. If only out interface is provided then the route
        will have no nexthop.

        :param network: String of network this route is for.
        :param nexthop: 
        """
        # * Check on nexthop or out_interface specified (not both).
        # * If there is no out_interface determine out_interface from
        #   nexthop.
        # * Install route into route table.
        pass

    def show_routes(self):
        """
        Show all current routes active on the device.
        """
        pass

if __name__ == "__main__":
    r0 = Router("r0", [
            IPInterface("0/0", "10.0.0.1/24", "00:00:00:00:00:00"),
            IPInterface("0/1", "10.0.1.1/24", "00:00:00:00:01:00"),
        ])
    dev0 = L3Device("dev0", "10.0.0.1", [
            IPInterface("0/0", "10.0.0.2/24", "00:00:00:00:00:02"),
        ])

    cable = netscool.layer1.Cable()
    dev0.interface('0/0').plug_cable(cable)
    r0.interface('0/0').plug_cable(cable)

    cable = netscool.layer1.SocketCable(22222, 11111)
    r0.interface('0/1').plug_cable(cable)

    # Manually populate ARP table for each device.
    r0.arp.table = {
        '10.0.0.2' : '00:00:00:00:00:02',
        '10.0.1.2' : '00:00:00:00:01:02',
    }
    dev0.arp.table = {
        '10.0.0.1' : '00:00:00:00:00:00',
    }

    dev0_dev1 = IP(src="10.0.0.2", dst="10.0.1.2")
    try:
        r0.start()
        dev0.start()
        IPython.embed()
    finally:
        r0.shutdown()
        dev0.shutdown()
