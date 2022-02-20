import logging
import ipaddress
import scapy.all
import netscool.layer1
import netscool.layer2

class ARP():
    def __init__(self):
        self.table = {}

    def lookup(self, ip):
        return self.table.get(ip, None)

class L3Device(netscool.layer1.BaseDevice):
    def __init__(self, name, interfaces, *args, **kwargs):
        super().__init__(name, interfaces, *args, **kwargs)
        self.arp = ARP()
        for interface in self.interfaces:
            assert hasattr(interface, 'arp')
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
    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)
        self.arp = ARP()
        self.routes = []

        # Add directly connected routes.
        for interface in self.interfaces:
            assert isinstance(interface, IPv4Interface)
            assert hasattr(interface, 'arp')
            interface.arp = self.arp
            network = ipaddress.IPv4Network(interface.ipv4, strict=False)
            self.routes.append((network, interface))

    def event_loop(self):
        logger = logging.getLogger("netscool.layer3.router")
        for interface in self.interfaces:
            packet = interface.receive()
            if not packet:
                continue

            # Packet is for the router. We dont have anything to do with
            # it yet so just drop for now.
            if self._is_local(packet):
                logger.info("{} Receive Packet".format(self))
                continue

            # Send the packet out the interface for the first route that
            # matches. If not route matches then the packet is silently
            # dropped.
            ip = ipaddress.IPv4Address(packet.dst)
            for network, interface in self.routes:
                if ip in network:
                    logger.info(
                        "{} route {} matched, forwarding out {}".format(
                            self, network, interface))
                    interface.send(packet)
                    break

    def show_routes(self):
        print("-- {} Routes --".format(self))
        for network, interface in self.routes:
            print("{} -> {} - Directly Connected".format(
                network, interface))

    def _is_local(self, packet):
        dst_ip = ipaddress.IPv4Address(packet.dst)
        for interface in self.interfaces:
            if interface.ipv4.ip == dst_ip:
                return True
        return False

class IPv4Interface(netscool.layer2.L2Interface):
    def __init__(
        self, name, ipv4, mac, bandwidth=1000, promiscuous=False):
        super().__init__(name, mac, bandwidth, promiscuous)
        self.ipv4 = ipaddress.IPv4Interface(ipv4)
        self.arp = None

    def receive(self):
        logger = logging.getLogger('netscool.layer3.ipv4.receive')
        frame = super().receive()
        if not frame:
            return None

        if frame.type != scapy.all.ETH_P_IP:
            logger.error(
                "{} Invalid ethtype for ipv4 0x{0:x}".format(
                    self, frame.type))
            return None

        if not self.arp:
            logger.error("{} no arp table set".format(self))

        packet = frame.payload
        if type(packet) != scapy.all.IP:
            logger.error(
                "{} Frame payload not parsed as ipv4".format(self))
            return None
        return packet

    def send(self, packet):
        logger = logging.getLogger('netscool.layer3.ipv4.send')
        if not isinstance(packet, scapy.all.IP):
            logger.error("{} can only send IP packets".format(self))
            return

        if not self.arp:
            logger.error("{} no arp table set".format(self))
            return

        # Add Ether header.
        dst_mac = self.arp.lookup(packet.dst)
        if not dst_mac:
            logger.error(
                "{} failed ARP lookup for {}".format(self, packet.dst))
            return

        ethernet = scapy.all.Ether(src=self.mac, dst=dst_mac)
        super().send(ethernet/packet)
