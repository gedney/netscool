# The sacred texts "Cisco Catalyst LAN Switching" from the prophets Louis R. Rossi and Thomas Rossi.
# https://flylib.com/books/en/2.115.1.67/1/

import time
import struct
import logging
import threading

import scapy.all
import IPython

# Possible bit rates for interfaces.
ONE_K = 1000
ONE_M = ONE_K * 1000
FOUR_M = ONE_M * 4
TEN_M = ONE_M * 10
HUN_M = TEN_M * 10
ONE_G = HUN_M * 10
TEN_G = ONE_G * 10
FORTY_G = TEN_G * 4
HUN_G = TEN_G * 10
ONE_T = HUN_G * 10

LINE_DOWN = 'down'
LINE_UP = 'up'
LINE_ADMIN_DOWN = 'admin down'

PROTOCOL_DOWN = 'down'
PROTOCOL_UP = 'up'
PROTOCOL_ERR = 'down err'

interface_mac = '00:00:00:00:00:00'
switch_mac = '11:00:00:00:00:00'
endpoint_mac = '22:00:00:00:00:00'

def mac2int(mac):
    mac_bytes = scapy.all.mac2str(mac)
    return int.from_bytes(mac_bytes, byteorder='big')

def int2mac(val):
    mac_bytes = val.to_bytes(byteorder='big', length=6)
    return scapy.all.str2mac(mac_bytes)

def increment_mac(mac):
    mac_int = mac2int(mac)
    mac_int += 1
    return int2mac(mac_int)

class Device():
    """
    Generic device base class that has a name and a list of interfaces. All other
    devices inherit from this one and implement the event_loop() method for device
    specific behaviour.
    """

    # We have a lock shared between all devices so that each iteration of a
    # devices event loop cannot be interrupted by another device. This makes
    # reading logs and debugging easier because they cant interleave.
    _lock = threading.Lock()
    def __init__(self, name, interfaces):
        self._shutdown_event = threading.Event()
        self._thread = None
        self.interfaces = interfaces
        self.name = name

    @property
    def powered(self):
        """
        True or False if the device is powered on. Calling start() powers on
        the devices, and calling shutdown() powers off the device.
        """
        return self._thread is not None

    def shutdown(self):
        """
        Shutdown the event_loop thread, which is analagous to shutting down the
        device. Also powers off all interfaces in the device.
        """

        # No thread so nothing to shut down.
        if not self._thread:
            return

        # Set the shutdown event and wait for the thread to join.
        self._shutdown_event.set()
        self._thread.join()
        self._thread = None

        # Power off all interfaces on the device. This will propagate so any up/up
        # links to this device will become down/down.
        for interface in self.interfaces:
            interface.powered = False

        # Reset the shutdown event so the device can be started again.
        self._shutdown_event.clear()

    def start(self):
        """
        Start the main event_loop thread for the device. Also powers on all
        interfaces on the device so that they can transistion to up/up if they
        have an active link.
        """
        # Thread is already running so nothing to do.
        if self._thread:
            return

        # Start the _run method which handles the shutdown event, and repeatedly
        # calls event_loop().
        self._thread = threading.Thread(
            target=self._run, name=self.name)
        self._thread.start()

        # Power on all interfaces so they can negotiate link and protocol status.
        for interface in self.interfaces:
            interface.powered = True

    def event_loop(self):
        """
        Event loop for device. This is the only method that needs to be
        implemented. Generally checks interfaces for data, and acts according
        to that data.
        """
        raise NotImplementedError("No event_loop method for device")

    def _run(self):
        """
        Wrapper for event_loop() that handles the shutdown event.
        """
        while not self._shutdown_event.is_set():
            Device._lock.acquire()
            self.event_loop()
            Device._lock.release()
            time.sleep(0.1)

class Switch(Device):
    """ A generic Layer 2 switch for forwarding ethernet frames. """

    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)
        global switch_mac

        # As well as each interface on the switch having a MAC, the switch
        # itself has a base MAC to identify the entire device. This MAC is
        # used for several purposes including generating the STP bridge ID
        # for this device.
        self.mac = switch_mac
        switch_mac = increment_mac(switch_mac)
        for interface in interfaces:
            interface.mac = switch_mac
            switch_mac = increment_mac(switch_mac)

        # Interfaces on a switch need to be in promiscuous mode because they
        # are generally handling ethernet frames that are not destined for them
        # ie. they are forwarding to the actual destination. If they weren't in
        # promiscuous mode they would just drop the frame and the switch would
        # be useless.
        for interface in self.interfaces:
            interface.promiscuous = True

        # The CAM (content addressable memory) table that keeps a track of
        # interface -> MAC mappings. This means once a MAC is 'learned' and in
        # the CAM table the switch no longer has to flood frames out every
        # interface to deliver the frame.
        self.cam = {}

        self.stp = STP(self) 

    def flood(self, source_interface, frame):
        """
        When the switch doesnt know which interface to forward a frame out
        of ie. no mapping in the CAM table. It sends the frame out every
        interface and hopes for the best. Importantly the switch doesn't send
        the frame back out the interface it was received on.

        :param source_interface: The interface we received the frame on,
            so we don't flood back out the interface we received on.
        :param frame: The frame to be flooded.
        """
        for interface in self.interfaces:
            if interface == source_interface:
                continue
            if not interface.upup:
                continue
            interface.transmit(frame)

    def event_loop(self):
        """
        Event loop for switch.
         * Checks for new frames on each interface.
         * Looks up destination MAC in CAM table
            - If it exists, forward out that interface.
            - Otherwise flood frame out all applicable interfaces.
        """
        self.stp.run()
        for interface in self.interfaces:
            frame = interface.next_frame()
            if not frame:
                continue
            ether = scapy.all.Ether(frame)

            if ether.dst.lower() == STP_MULTICAST_MAC.lower():
                self.stp.process(frame, interface)
                continue
    
            self.cam[ether.src.lower()] = interface
            if ether.dst.lower() in self.cam:
                logging.info("{} - fwd -> {}".format(self.name, interface.name))
                self.cam[ether.dst.lower()].transmit(frame)
            else:
                logging.info("{} - flood frame".format(self.name))
                self.flood(interface, frame)

    def __str__(self):
        return "{}:\n  {}\n  {}".format(
            self.name, 
            '\n  '.join([str(i) for i in self.interfaces]),
            '\n  '.join([str(i.cable) for i in self.interfaces if i.cable]))

class Endpoint(Device):
    """ A Layer 2 endpoint. """
    def __init__(self, name, interfaces):
        super().__init__(name, interfaces)

        global endpoint_mac
        for interface in interfaces:
            interface.mac = endpoint_mac
            endpoint_mac = increment_mac(endpoint_mac)

    def event_loop(self):
        for interface in self.interfaces:
            frame = interface.next_frame()
            if not frame:
                continue
            ether = scapy.all.Ether(frame)
            logging.info("{} - Got Pkt src: {} dst:{} ".format(self.name, ether.src, ether.dst))

    def __str__(self):
        return "{}: {}\n  {}".format(
            self.name, 
            ', '.join([str(i) for i in self.interfaces]),
            '\n  '.join([str(i.cable) for i in self.interfaces]))

class Interface():
    """ A Layer 2 interface. """
    def __init__(self, name, mac=None, bandwidth=ONE_G, promiscuous=False):
        """
        :param name: Name of interface to make identification simpler.
        :param mac: Layer2 MAC address for interface in form XX:XX:XX:XX:XX:XX.
            If not provided will use the next MAC from the interace MAC pool.
        :param bandwidth: Bandwidth of interfaces in bits per second. Each
            interface at the end of a link must have the same bandwidth.
        :param promiscuous: A promiscuous interface will accept frames destined
            to any MAC address. A non-promiscuous interface will drop frames that
            are not destined for it.
        """
        if not mac:
            global interface_mac
            mac = interface_mac
            interface_mac = increment_mac(interface_mac)

        self.bandwidth = bandwidth
        self.line_status = LINE_DOWN
        self.protocol_status = PROTOCOL_DOWN
        self.name = name
        self.mac = mac
        self.promiscuous = promiscuous
        self.cable = None
        self.recv_buffer = []
        self.send_buffer = []
        self._powered = False

    @property
    def powered(self):
        return self._powered

    @powered.setter
    def powered(self, val):
        """
        Powers the interface on or off (True/False). Also attempts to power the
        cable if one is plugged into the interface.
        """
        assert val in [True, False], "Interface powered can only be True | False."
        self._powered = val
        if self.cable:
            self.cable.try_power()

    @property
    def upup(self):
        """
        True if the line status and protocol status are both up. An interface
        can only send and receive frames if it is up/up.
        """
        return self.line_up and self.protocol_up

    @property
    def status(self):
        """
        Get a tuple of the line and protocol status for the interface. Line
        status is the status of the link at Layer 1, and protocol status is the
        status of the link at Layer 2. Protocol status can only be up if line
        status is also up. The possible combinations are.

        Line        Protocol    Description
        down        down        There is a Layer1 issue with the connection
                                eg. Interface speed mismatch, broken cable, device
                                powered off etc.

        admin down  down        The interface has been administratively shutdown.

        down        down err    Interface is 'error disabled', most likely from
                                port security (port security is not implemented).

        up          down        The Layer2 protocol has an error, or didnt match.
                                Since we only have our simulated ethernet interface
                                this cannot happen, however it we implemented a new
                                interface with a different Layer2 protocol then this
                                could happen.

        up          up          The interface is up and ready to transmit/receive.
        """
        return (self.line_status, self.protocol_status)

    @property
    def line_up(self):
        """ Is the line status up (Layer1 connectivity). """
        return self.line_status == LINE_UP

    @property
    def protocol_up(self):
        """ Is the protocol status up (Layer2 connectivity). """
        return self.protocol_status == PROTOCOL_UP

    def next_frame(self):
        """
        Get the next frame from the interface's receive buffer.
        """
        if not self.recv_buffer:
            return
        return self.recv_buffer.pop(0)
        
    def receive(self, frame):
        """
        Add frame to the interfaces's receive buffer. Will drop the frame
        if the interface is not up, or the destination MAC does match for
        non-promiscuous interfaces.
        """
        if not self.cable or not self.upup:
            return
        ether = scapy.all.Ether(frame)
        if ether.dst.lower() != self.mac.lower() and not self.promiscuous:
            return
        self.recv_buffer.append(frame)

    def transmit(self, frame):
        """
        Put frame in the interface's send buffer, and transmit it over the
        attached cable.
        """
        if not self.cable or not self.upup:
            return
        self.send_buffer.append(frame)
        self.cable.transmit()

    def plug_cable(self, cable):
        """
        Plug a cable into the interface.
        """
        cable.plugin(self)

    def negotiate_protocol(self):
        """
        Negotiate the Layer 2 protocol for the interface. For now we only have
        one L2 protocol and we assume its connectivity always works. We also
        haven't implemented port security so err disabled does not apply.
        """
        if self.line_up:
            self.protocol_status = PROTOCOL_UP
        else:
            self.protocol_status = PROTOCOL_DOWN

    def __str__(self):
        return "{} ({}) {}".format(self.name, self.mac, self.status)

class Cable():
    """
    Cable to provide Layer1 connectivity between 2 Layer2 interfaces. The cable
    transmits all data instantaneouly, has no MTU limits, and cant have data
    collisions or corruptions. The cable will fail to transmit if
     * Either end of the cable is not plugged in.
     * One or both interfaces are unpowered.
     * One or both interfaces not up/up.
     * The bandwidth for each interface does not match.
    """
    def __init__(self):
        self.end1 = None
        self.end2 = None
        self._powered = False

    def try_power(self):
        """
        Attempts to 'power' the cable ie. Both interfaces on either end of the cable
        are powered and transferring signals accross the cable. If both interfaces
        are not powered then cable is considered unpowered, and can't transmit signals.
        Will renegotiate the line protocol for connected interfaces each time its called.
        """
        self._powered = False
        if (self.end1 and self.end1.powered) and (self.end2 and self.end2.powered):
            self._powered = True
        self.negotiate_line()

    def transmit(self):
        """
        Move data from the send buffer of each connected interface to the 
        receive buffer of the opposite interface. Raises an error if you transmit
        when both ends of the cable are not plugged in. Does nothing if both
        interfaces are not up/up.
        """
        if not self.end1 and not self.end2:
            raise Exception("Cable ends not plugged in: {}".format(self))

        if not self.end1.upup or not self.end2.upup:
            return

        while self.end1.send_buffer:
            data = self.end1.send_buffer.pop(0)
            assert type(data) == bytes
            self.end2.receive(data)

        while self.end2.send_buffer:
            data = self.end2.send_buffer.pop(0)
            assert type(data) == bytes
            self.end1.receive(data)

    def plugin(self, interface):
        """
        'Plug' a free end of the cable into the specified interface.
        """
        interface.cable = self
        if not self.end1:
            self.end1 = interface
        elif not self.end2:
            self.end2 = interface
        else:
            raise Exception(
                "Cable ends already plugged in: {}".format(self))
        self.try_power()

    def negotiate_line(self):
        """
        Negotiate the line status (Layer1 connectivity) for each connected interface.
        Line status will fail if.
         * Either end of the cable isn't plugged in.
         * An interface is not powered.
         * An interface is 'admin down'.
         * The interface speeds dont match.
        Once line status is negotiated, this calls the interfaces negotiate_protocol(),
        to negotiate layer2 connectivity.
        """

        try:
            # Handle ends not being plugged in.
            if not self.end1 or not self.end2:
                if self.end1 and self.end1.line_up: 
                    self.end1.line_status = LINE_DOWN
                if self.end2 and self.end2.line_up:
                    self.end2.line_status = LINE_DOWN
                return

            # Handle ends not being unpowered.
            if not self.end1.powered or not self.end2.powered:
                if self.end2.line_up:
                    self.end2.line_status = LINE_DOWN
                if self.end1.line_up:
                    self.end1.line_status = LINE_DOWN
                return

            # Handle ends being admin down.
            admin_down = self.end1.line_status == LINE_ADMIN_DOWN or self.end2.line_status == LINE_ADMIN_DOWN
            if admin_down:
                if self.end2.line_up:
                    self.end2.line_status = LINE_DOWN
                if self.end1.line_up:
                    self.end1.line_status = LINE_DOWN
                return

            # Handle speed mismatch
            speed_mismatch = self.end1.bandwidth != self.end2.bandwidth
            if speed_mismatch:
                if self.end1.line_up:
                    self.end1.line_status = LINE_DOWN
                if self.end2.line_up:
                    self.end2.line_status = LINE_DOWN
                return

            self.end1.line_status = LINE_UP
            self.end2.line_status = LINE_UP

        finally:
            if self.end1:
                self.end1.negotiate_protocol()
            if self.end2:
                self.end2.negotiate_protocol()

    def __str__(self):
        return "{} -> {}".format(self.end1, self.end2)

STP_MULTICAST_MAC = '01:80:c2:00:00:00'
STP_DEFAULT_PRIORITY = 32768
STP_DEFAULT_PORT_PRIORITY = 128

STP_STATE_DISABLE = -1
STP_STATE_BLOCKING = 0
STP_STATE_LISTENING = 1
STP_STATE_LEARNING = 2
STP_STATE_FORWARDING = 3
STP_STATES = [
    "STP_STATE_BLOCKING",
    "STP_STATE_LISTENING",
    "STP_STATE_LEARNING",
    "STP_STATE_FORWARDING"]

STP_ROLE_ROOT = 0
STP_ROLE_DESIGNATED = 1
STP_ROLE_NOT_DESIGNATED = 2
STP_ROLES = [
    "STP_ROLE_ROOT",
    "STP_ROLE_DESIGNATED",
    "STP_ROLE_NOT_DESIGNATED"]

def path_cost(interface):
    costs = {
        FOUR_M: 250,
        TEN_M: 100,
        HUN_M: 19,
        ONE_G: 4,
        TEN_G: 2
    }
    if interface.bandwidth not in costs:
        raise Exception("{} Does not a have a defined STP cost".format(interface.bandwidth))
    return costs[interface.bandwidth]

class BridgeID():
    def __init__(self, priority, mac):
        self.priority = priority
        self.mac = mac
    def __lt__(self, other):
        if self.priority > other.priority:
            return False
        if self.priority < other.priority:
            return True
        if mac2int(self.mac) > mac2int(other.mac):
            return False
        if mac2int(self.mac) < mac2int(other.mac):
            return True
        return False
    def __eq__(self, other):
        return self.priority == other.priority and mac2int(self.mac) == mac2int(other.mac)
    def __gt__(self, other):
        return not self.__lt__(other) and not self.__eq__(other)
    def __str__(self):
        return "{}.{}".format(self.priority, self.mac)

class PortID():
    def __init__(self, priority, portidx):
        self.priority = priority
        self.portidx = portidx

    def toint(self):
        b = struct.pack(">BB", self.priority, self.portidx)
        return int.from_bytes(b, byteorder='big')
        
    def __lt__(self, other):
        if self.priority > other.priority:
            return False
        elif self.priority < other.priority:
            return True
        if self.portidx > other.portidx:
            return False
        elif self.portidx < other.portidx:
            return True
        return False
    def __eq__(self, other):
        return self.priority == other.priority and self.portidx == other.portidx
    def __gt__(self, other):
        return not self.__lt__(other) and not self.__eq__(other)
    def __str__(self):
        return "{}.{}".format(self.priority, self.portidx)

class BPDUScore():
    """
    Class to encapsulate how 'good' a bpdu is, the process for determining the
    best bpdu is.
     * Lower root bridge id is better.
        - This is how the root bridge is elected.
        - All the bpdu with higher root bridge ids will be dropped.
     * If root bridge is equal, lower cost to root bridge is better.
        - We favour the fastest path to the root bridge.
     * If cost is equal, lower sender bridge id is better.
        - There are two equally valid paths.
        - Bridge id is unique per bridge so we use it as a tie breaker.
     * If sender bridge, lower port id is better.
        - We probably have two cables running between two bridges (for redundancy).
        - The port ids must be different because the two cables cant plug into the same port
    """
    def __init__(self, rootbridge, rootcost, senderbridge, portid):
        self.rootbridge = rootbridge
        self.rootcost = rootcost
        self.senderbridge = senderbridge
        self.portid = portid
    def __lt__(self, other):
        if self.rootbridge < other.rootbridge:
            return True
        elif self.rootbridge > other.rootbridge:
            return False

        if self.rootcost < other.rootcost:
            return True
        elif self.rootcost < other.rootcost:
            return False

        if self.senderbridge < other.senderbridge:
            return True
        elif self.senderbridge > other.senderbridge:
            return False

        if self.portid < other.portid:
            return True
        elif self.portid < other.portid:
            return False
        return False
    def __eq__(self, other):
        return (
            self.rootbridge == other.rootbridge and
            self.senderbridge == other.senderbridge and
            self.rootcost == other.rootcost and
            self.portid == other.portid)
    def __gt__(self, other):
        return not self.__lt__(other) and not self.__eq__(other)
        
class STPPort():
    def __init__(self, interface, index):
        self.interface = interface
        self._role = STP_ROLE_DESIGNATED
        self._state = STP_STATE_LISTENING
        self._state_start_time = time.time()

        self.portid = PortID(STP_DEFAULT_PORT_PRIORITY, index)
        self.best_bpdu = None
        self.last_bpdu_time = time.time()

    @property
    def role(self):
        return self._role
    @role.setter
    def role(self, r):
        assert r in [STP_ROLE_ROOT, STP_ROLE_DESIGNATED, STP_ROLE_NOT_DESIGNATED]
        if self._role == r:
            return
        self._role = r
        if self._role == STP_ROLE_NOT_DESIGNATED:
            self.state = STP_STATE_BLOCKING
        if self._role in [STP_ROLE_DESIGNATED, STP_ROLE_ROOT]:
            self.state = STP_STATE_LISTENING
        logging.info("role  {} {}".format(self.interface.mac, STP_ROLES[r]))

    @property
    def state(self):
        return self._state
    @state.setter
    def state(self, s):
        if self._state == s:
            return
        self._state = s
        self._state_start_time = time.time()
        logging.info("state {} {}".format(self.interface.mac, STP_STATES[s]))

    @property
    def state_start_time(self):
        return self._state_start_time

class STP():
    def __init__(self, switch, priority=STP_DEFAULT_PRIORITY):
        self.switch = switch
        self.priority = priority

        self.bridge_id = BridgeID(priority, self.switch.mac)
        self.root_bridge_id = self.bridge_id
        self.root_path_cost = 0

        self.forward_delay = 15
        self.max_age = 20
        self.hellotime = 2
        self.bpdu_sent = time.time() - self.hellotime

        self.ports = {}
        self.update_ports()

    def update_ports(self):
        """
        Update the ports participating in STP.
         * Removes any ports that arent up/up
         * Adds any ports that have become up/up
         * Update states based on forward_delay
         * Clears port bpdu based on max_age
        """
        # Add/Remove ports that have been powered on/off.
        for idx, interface in enumerate(self.switch.interfaces):
            if not interface.upup:
                self.ports.pop(interface.mac, None)
                continue

            if interface.mac not in self.ports:
                self.ports[interface.mac] = STPPort(interface, idx)

        # Transition STP states for ports. Ports go from
        # Listening -> Learning -> Forwarding.
        # Ports transition if they have been in a state for forward_delay seconds.
        now = time.time()
        for mac, port in self.ports.items():
            if now - port.state_start_time < self.forward_delay:
                continue
            if port.state == STP_STATE_LEARNING:
                port.state = STP_STATE_FORWARDING
            if port.state == STP_STATE_LISTENING:
                port.state = STP_STATE_LEARNING

        # TODO: What state/role should port be in.
        now = time.time()
        for mac, port in self.ports.items():
            if now - port.last_bpdu_time < self.max_age:
                continue
            port.best_bpdu = None

    @property
    def root_port(self):
        """
        Get the current root port for this instance of STP, this is the port
        with the best path back to the root bridge. There should only be one
        port on the switch with the root role.
        """
        for mac, port in self.ports.items():
            if port.role == STP_ROLE_ROOT:
                return port
        return None

    def forward(self, bpdu):
        """
        Forward bpdu to downstream devices. We only forward out designated ports
        because sending out the root port would send it back toward the root bridge
        and non-designated ports would send down a redundant path.
        """

        # If we dont have a root path cost then we must have tried to forward
        # without processing any bpdu's.
        assert self.root_path_cost

        bpdu.pathcost = self.root_path_cost
        bpdu.bridgeid = self.bridge_id.priority
        bpdu.bridegmac = self.bridge_id.mac

        for mac, port in self.ports.items():
            if port.role != STP_ROLE_DESIGNATED:
                continue
            bpdu.portid = port.portid.toint()
            ether = scapy.all.Ether(src=mac, dst=STP_MULTICAST_MAC)
            frame = ether/scapy.all.LLC()/bpdu
            port.interface.transmit(bytes(frame))

    def process(self, frame, interface):
        # STP does not use the more common Ethernet II frame, where
        # the Ethertype field follows directly after the source MAC,
        # and is used to determine the underlying payload. Instead it
        # uses on an 802.2 Ethernet frame where Ethertype is replaced
        # by a length field, and the payload is determined using an
        # intermediary LLC (logical link control) header. Luckily
        # scapy knows how to parse all this nicley into seperate
        # protocol layers, so all we have to do is check if the layers
        # after the ethernet header are LLC and STP
        ether = scapy.all.Ether(frame)
        llc = ether.getlayer(1)
        bpdu = ether.getlayer(2)

        # Invalid STP frame, drop it.
        if type(llc) != scapy.all.LLC or type(bpdu) != scapy.all.STP:
            return 

        # Parse out values from the bpdu into a BPDUScore (how good this bpdu is).
        bpdu_port_priority, bpdu_port_idx = struct.unpack(
            ">BB", bpdu.portid.to_bytes(length=2, byteorder="big"))
        bpdu_root_id = BridgeID(bpdu.rootid, bpdu.rootmac)
        bpdu_port_id = PortID(bpdu_port_priority, bpdu_port_idx)
        bpdu_sender_id = BridgeID(bpdu.bridgeid, bpdu.bridgemac)
        bpdu_path_cost = bpdu.pathcost
        bpdu_score = BPDUScore(bpdu_root_id, bpdu_path_cost, bpdu_sender_id, bpdu_port_id)

        port = self.ports[interface.mac]
       
        port.last_bpdu_time = time.time()

        if port.best_bpdu is not None:

            # We have received a better bpdu on this port in the past, so ignore
            # this one.
            if port.best_bpdu < bpdu_score:
                return

        # port_score is how good a bpdu we could make from this port.
        port_score = BPDUScore(self.root_bridge_id, self.root_path_cost, self.bridge_id, port.portid)

        # The port and received bdpu should never be equal. If they are then
        # likely there is a duplicate mac somewhere on the segment. If they
        # are equal then there is no way to determine the designated port, so
        # give up.
        assert port_score != bpdu_score

        # Our port is better than the received bpdu so it must be the
        # designated port for this segment. Since we received an inferior bpdu
        # we can drop it.
        if port_score < bpdu_score:
            port.best_bpdu = port_score
            port.role = STP_ROLE_DESIGNATED
            return
            
        # We received a better bpdu so keep a record of it. Since the received
        # bpdu is better that means the other end of the segment is the designated port.
        # This port can therefore only be the root port or a non-designated port.
        port.best_bpdu = bpdu_score

        # If this is the best root bridge id we've seen update our recognised
        # root id.
        if bpdu_root_id < self.root_bridge_id:
            self.root_bridge_id = bpdu_root_id

        # Double check we agree on the root id before processing the bpdu any further.
        assert self.root_bridge_id == bpdu_root_id

        root_port = self.root_port

        # If we haven't got a root port yet then this port is our best guess
        # until we get more bpdu's to prove otherwise
        if not root_port:
            self.root_path_cost = bpdu_path_cost + path_cost(interface)
            port.role = STP_ROLE_ROOT
            root_port = self.root_port

        # This port is not a new root port, so it must be non-designated.
        if root_port.best_bpdu < bpdu_score:
            port.role = STP_ROLE_NOT_DESIGNATED

        # This bpdu is better than the current root port, so this port is the
        # root port, and the current root is a non-designated port.
        elif root_port.best_bpdu > bpdu_score:
            root_port.role = STP_ROLE_NOT_DESIGNATED
            self.root_port_cost = bpdu_path_cost + path_cost(interface)
            port.role = STP_ROLE_ROOT

        self.forward(bpdu)
        return None

    def run(self):
        self.update_ports()

        # Only broadcast new bpdu's at specified hello interval.
        now = time.time() 
        if now - self.bpdu_sent < self.hellotime:
            return

        #logging.info("--------------")
        #for mac, port in self.ports.items():
        #    logging.info("{} {} {}".format(self.switch.name, port.interface.mac, STP_ROLES[port.role]))
        #logging.info("--------------")

        # We aren't a root bridge so dont generate bpdu's.
        if self.root_bridge_id != self.bridge_id:
            self.bpdu_sent = now
            return

        #logging.info("{} {} I am the root bridge".format(self.switch.name, self.bridge_id))

        # Broadcast new bpdu's out all up/up interfaces.
        for mac, port in self.ports.items():
            ether = scapy.all.Ether(
                src=mac,
                dst=STP_MULTICAST_MAC)
            hello_bpdu = scapy.all.STP(
                rootid=self.root_bridge_id.priority,
                rootmac=self.root_bridge_id.mac,
                bridgeid=self.bridge_id.priority,
                bridgemac=self.bridge_id.mac,
                portid=port.portid.toint(),
                pathcost=0)
            frame = ether/scapy.all.LLC()/hello_bpdu
            port.interface.transmit(bytes(frame))
        self.bpdu_sent = now

if __name__ == "__main__":
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    sw1 = Switch(
        name='sw1', interfaces=[
            Interface('swint1', '00:00:00:00:00:aa'),
            Interface('swint2', '00:00:00:00:00:ab'),
        ])

    sw2 = Switch(
        name='sw2', interfaces=[
            Interface('swint1', '00:00:00:00:00:ca'),
            Interface('swint2', '00:00:00:00:00:cb'),
        ])

    #sw3 = Switch(
    #    name='sw3', interfaces=[
    #        Interface('swint1', '00:00:00:00:00:da'),
    #        Interface('swint2', '00:00:00:00:00:db'),
    #        Interface('swint3', '00:00:00:00:00:dc'),
    #        Interface('swint4', '00:00:00:00:00:dd'),
    #        Interface('swint5', '00:00:00:00:00:de'),
    #        Interface('swint6', '00:00:00:00:00:df')
    #    ])

    #sw4 = Switch(
    #    name='sw4', interfaces=[
    #        Interface('swint1', '00:00:00:00:00:ea'),
    #        Interface('swint2', '00:00:00:00:00:eb'),
    #        Interface('swint3', '00:00:00:00:00:ec'),
    #        Interface('swint4', '00:00:00:00:00:ed'),
    #        Interface('swint5', '00:00:00:00:00:ee'),
    #        Interface('swint6', '00:00:00:00:00:ef')
    #    ])

    #pc1 = Endpoint(name='pc1', interfaces=[
    #        Interface('pc1int1', '00:00:00:00:00:ba')
    #    ])

    #pc2 = Endpoint(name='pc2', interfaces=[
    #        Interface('pc2int1', '00:00:00:00:00:bb')
    #    ])

    #pc3 = Endpoint(name='pc3', interfaces=[
    #        Interface('pc3int1', '00:00:00:00:00:bc')
    #    ])

    #cable = Cable()
    #pc1.interfaces[0].plug_cable(cable)
    #sw1.interfaces[0].plug_cable(cable)

    #cable = Cable()
    #pc2.interfaces[0].plug_cable(cable)
    #sw2.interfaces[0].plug_cable(cable)

    #cable = Cable()
    #pc3.interfaces[0].plug_cable(cable)
    #sw3.interfaces[0].plug_cable(cable)

    cable = Cable()
    sw1.interfaces[0].plug_cable(cable)
    sw2.interfaces[0].plug_cable(cable)

    cable = Cable()
    sw1.interfaces[1].plug_cable(cable)
    sw2.interfaces[1].plug_cable(cable)

    #cable = Cable()
    #sw2.interfaces[2].plug_cable(cable)
    #sw3.interfaces[2].plug_cable(cable)

    #cable = Cable()
    #sw1.interfaces[3].plug_cable(cable)
    #sw3.interfaces[3].plug_cable(cable)

    #cable = Cable()
    #sw3.interfaces[4].plug_cable(cable)
    #sw4.interfaces[4].plug_cable(cable)

    print(sw1)
    print(sw2)
    #print(sw3)
    #print(sw4)

    sw1.start()
    sw2.start()
    #sw3.start()
    #sw4.start()
    #pc1.start()
    #pc2.start()
    #pc3.start()
    #time.sleep(35)
    IPython.embed()
    #sw2.interfaces[0].powered = False
    #print(sw1)
    #print(sw2)
    #time.sleep(35)
    #pkt = scapy.all.Ether(
    #    src=pc1.interfaces[0].mac,
    #    dst=pc2.interfaces[0].mac)
    #pkt2 = scapy.all.Ether(
    #    src=pc2.interfaces[0].mac,
    #    dst=pc1.interfaces[0].mac)

    #for i in range(10):
    #    pc1.interfaces[0].transmit(bytes(pkt))
    #    pc2.interfaces[0].transmit(bytes(pkt2))
    #    if i == 5:
    #        sw1.shutdown()
    #    time.sleep(1)

    sw1.shutdown()
    sw2.shutdown()
    #sw3.shutdown()
    #sw4.shutdown()
    #pc1.shutdown()
    #pc2.shutdown()
    #pc3.shutdown()
