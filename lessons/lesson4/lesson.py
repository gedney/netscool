import collections
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
    Basic Address Resolution Protocol (ARP) table implementation.
    """
    def __init__(self):
        self.table = {}

    def lookup(self, ip):
        return self.table.get(ip, None)

class IPInterface(L2Interface):
    """
    Layer 3 interface that send and receives IPv4 packets.
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

        # Using the ipaddress.IPv4Network object makes interacting with
        # ipaddresses much easier eg.
        # ipv4.ip in IPv4Network("127.0.0.1/24")
        self.ipv4 = ipaddress.IPv4Interface(ipv4)

        # This should be set by the device this interface is attached to.
        self.arp = None

    def receive(self):
        """
        Receive layer 3 IP packet.

        :return: scapy.all.IP packet.
        """

        # You should check self.arp has been set appropriately before
        # trying to receive anything.

        # Receive a frame from layer 2.
        frame = super().receive()
        if not frame:
            return None

        # Things to do once we have a frame.
        #  * Check the frame is encapsulating an IP packet. You can do
        #    this by checking frame.type. Hint in scapy the ethertype for
        #    IP is scapy.all.ETH_P_IP.
        #  * Get the encapsulated IP packet from the frame. Hint
        #    frame.payload is very useful here.
        #  * Do any other checks you think appropriate.
        #  * Return the IP packet.
        pass

    def send(self, packet):
        """
        Send an IP packet.

        :param packet: scapy.all.IP() packet.
        """
        # You should check self.arp has been set appropriately before
        # trying to send anything.

        # Things to do to send a packet.
        #  * Validate you have been passed an IP packet as expected.
        #  * Lookup the packet.dst in the ARP table to determine the dst
        #    MAC for our Ethernet frame.
        #  * Create an Ethernet frame with src mac of this interface, and
        #    dst mac as previously determined.

        dst_mac = "..."
        src_mac = "..."
        ethernet = scapy.all.Ether(src=src_mac, dst=dst_mac)

        # This will encapsulate packet in the provided Ethernet frame
        # and send it to the next layer of the network stack.
        super().send(ethernet/packet)

class L3Device(netscool.layer1.BaseDevice):
    """
    A basic layer 3 device that logs any packet it receives.
    """
    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)

        # Create a single ARP table that can be shared between all
        # interfaces on the device. Our layer 3 device only supports
        # IPv4Interfaces for now so we also 
        self.arp = ARP()
        for interface in self.interfaces:
            assert isinstance(interface, IPInterface)
            interface.arp = self.arp

    def event_loop(self):
        for interface in self.interfaces:
            packet = interface.receive()
            if not packet:
                continue
            # Log or print details of packet using packet.show().

class Router(netscool.layer1.BaseDevice):
    """
    A basic router that can forward IP packets between directly connected
    subnets.
    """
    
    # Currently only route between networks directly connected to the
    # router.
    ROUTE_TYPE_DIRECT = "directly connected"

    # Every route has a network, and an interface to forward any packets
    # whose destination is in the network. We only have one route_type for
    # now so this field does nothing useful yet.
    Route = collections.namedtuple(
        "Route", ['network', 'interface', 'route_type'])

    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)

        # A single ARP table that can be shared between all interfaces.
        self.arp = ARP()

        # A list of Route tuples the router knows about.
        self.routes = []

        for interface in self.interfaces:
            # For every interface ...
            #  * Check it is an IPInterface.
            #  * Set interface.arp to the shared ARP table.
            #  * Add interface network as a directly connected route.
            pass

    def event_loop(self):
        # Things our router needs to do.
        #  * Check all interfaces for recevied packets.
        #  * Check if the packet is destined for the router itself. In
        #    which case it can be dropped for now.
        #  * Check if packet destination matches any route, and send out
        #    interface for first route that matches.
        #  * If no routes match the packet can be dropped.
        pass

    def show_routes(self):
        # Print some details about the current routes on the device.
        pass

if __name__ == "__main__":
    r0 = Router("r0", [
            IPInterface("0/0", "10.0.0.1/24", "00:00:00:00:00:00"),
            IPInterface("0/1", "10.0.1.1/24", "00:00:00:00:01:00"),
        ])
    dev0 = L3Device("dev0", [
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
        '10.0.1.2' : '00:00:00:00:00:00',
        '10.0.0.1' : '00:00:00:00:00:00',
        '10.0.1.1' : '00:00:00:00:00:00',
    }

    dev0_dev1 = IP(src="10.0.0.2", dst="10.0.1.2")
    try:
        r0.start()
        dev0.start()
        IPython.embed()
    finally:
        r0.shutdown()
        dev0.shutdown()
