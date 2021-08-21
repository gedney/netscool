# The sacred texts "Cisco Catalyst LAN Switching" from the prophets Louis R. Rossi and Thomas Rossi.
# https://flylib.com/books/en/2.115.1.67/1/

import time
import logging
import struct
import threading
import socket
import select

LINE_DOWN = 'down'
LINE_UP = 'up'
LINE_ADMIN_DOWN = 'admin down'

class BaseDevice():
    """
    Base device base class that has a name and a list of interfaces.
    All other devices inherit from this one and implement the event_loop()
    method for device specific behaviour.
    """

    # We have a lock shared between all devices so that each iteration
    # of a devices event loop cannot be interrupted by another device.
    # This makes reading logs and debugging easier because they cant
    # interleave.
    _lock = threading.Lock()
    def __init__(self, name, interfaces):
        self._shutdown_event = threading.Event()
        self._thread = None
        self.interfaces = interfaces
        self.name = name

    @property
    def powered(self):
        """
        True or False if the device is powered on. Calling start()
        powers on the devices, and calling shutdown() powers off the
        device.
        """
        return self._thread is not None

    def shutdown(self):
        """
        Shutdown the event_loop thread, which is analagous to shutting
        down the device. Also powers off all interfaces in the device.
        """

        # No thread so nothing to shut down.
        if not self._thread:
            return

        logger = logging.getLogger('netscool.layer1.device.status')
        logger.info("{} shutdown".format(self))

        # Set the shutdown event and wait for the thread to join.
        self._shutdown_event.set()
        self._thread.join()
        self._thread = None

        # Power off all interfaces on the device. This will propagate
        # so any up/up links to this device will become down/down.
        for interface in self.interfaces:
            interface.powered = False
            interface.negotiate_connection()

        # Reset the shutdown event so the device can be started again.
        self._shutdown_event.clear()

    def start(self):
        """
        Start the main event_loop thread for the device. Also powers on
        all interfaces on the device so that they can transistion to
        up/up if they have an active link.
        """
        # Thread is already running so nothing to do.
        if self._thread:
            return

        logger = logging.getLogger('netscool.layer1.device.status')
        logger.info("{} start".format(self))

        # Start the _run method which handles the shutdown event, and
        # repeatedly calls event_loop().
        self._thread = threading.Thread(
            target=self._run, name=self.name)
        self._thread.start()

        # Power on all interfaces so they can negotiate link and
        # protocol status.
        for interface in self.interfaces:
            interface.powered = True

    def event_loop(self):
        """
        Event loop for device. This is the only method that needs to be
        implemented. Generally checks interfaces for data, and acts
        according to that data.
        """
        raise NotImplementedError("No event_loop method for device")

    def _run(self):
        """
        Wrapper for event_loop() that handles the shutdown event.
        """
        while not self._shutdown_event.is_set():
            BaseDevice._lock.acquire()

            # Something needs to trigger the cables plugged into the
            # interfaces to actually transfer. Instead of making each
            # cable its own thread, we just update all the attached
            # cables here.
            for interface in self.interfaces:
                interface.update()
                if not interface.cable:
                    continue
                interface.cable.update()

            self.event_loop()
            BaseDevice._lock.release()
            time.sleep(0.1)

    def __str__(self):
        return self.name

class BaseInterface():
    """
    Base interface. This is essentially a Layer 1 interface, and takes
    the role of the physical hardware for the interface. Logic for
    higher level interfaces build on this base functionality.
    """
    def __init__(self, name, speed=1000):
        # TODO check both ends speed match.
        self.speed = speed
        self.line_status = LINE_DOWN
        self.name = name

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
        Powers the interface on or off (True/False). Also attempts to
        power the cable if one is plugged into the interface.
        """
        assert val in [True, False], (
            "Interface powered can only be True | False.")
        self._powered = val

    @property
    def line_up(self):
        """ Is the line status up (Layer1 connectivity). """
        return self.line_status == LINE_UP

    def shutdown(self):
        """ Administratively shutdown the interface. """
        logger = logging.getLogger('netscool.layer1.interface.status')
        logger.info("{} shutdown".format(self))
        self.line_status = LINE_ADMIN_DOWN

    def no_shutdown(self):
        """
        Enable the interface. This is the opposite of 'shutdown()'. On
        many devices a command can be negated by prepending 'no'. So to
        enable an interface you use the command 'no shutdown'.
        """
        logger = logging.getLogger('netscool.layer1.interface.status')
        logger.info("{} no shutdown".format(self))

        # We can set the line status to anything that isnt
        # 'LINE_ADMIN_DOWN' and update() should re-negotiate the line
        # status appropriately.
        self.line_status = LINE_DOWN

    def receive(self):
        """
        Get the next frame from the interface's receive buffer.
        """
        logger = logging.getLogger('netscool.layer1.interface.receive')
        if not self.line_up:
            return
        if not self.recv_buffer:
            return

        logger.info("{} received layer1 data".format(self))
        return self.recv_buffer.pop(0)
        
    def send(self, data):
        """
        Put data in the interface's send buffer.
        """
        logger = logging.getLogger('netscool.layer1.interface.send')
        if not self.line_up:
            logger.error(
                "{} cannot send data. Line is down".format(self))
            return

        logger.info("{} sending layer1 data".format(self))
        self.send_buffer.append(data)

    def plug_cable(self, cable):
        """
        Plug a cable into the interface.
        """
        cable.plugin(self)

    def update(self):
        self.negotiate_connection()

    def negotiate_connection(self):
        """
        Negotiate connectivity for this layer. At layer 1 this is usually
        referred to as 'line' connectivity.
        """
        logger = logging.getLogger('netscool.layer1.interface.status')
        if not self.powered:
            if self.line_status == LINE_UP:
                logger.info("{} line down".format(self))
                self.line_status = LINE_DOWN
            return

        if not self.cable or not self.cable.active:
            if self.line_status == LINE_UP:
                logger.info("{} line down".format(self))
                self.line_status = LINE_DOWN

        elif self.cable.active:
            if self.line_status == LINE_DOWN:
                logger.info("{} line up".format(self))
                self.line_status = LINE_UP

    def __str__(self):
        return self.name

class BaseCable():
    """
    Base cable class that all other cable types inherit from. A cable
    is just a class that transfers bytes from one interface to another
    interface.
    """
    def __init__(self):
        self._active = False

    @property
    def active(self):
        """
        Flag set internally by the cable to say that it is active
        and can transfer data.
        """
        return self._active

    def update(self):
        """
        Called at regular intervals when plugged into an interface
        attached to a device. Child classes must implement logic
        for setting active flag and transferring data here.
        """
        raise NotImplementedError(
            "'update' not implemented for this cable.")
    def plugin(self, interface):
        """
        Plug the cable into the specified interface.
        """
        raise NotImplementedError(
            "'plugin' not implemented for this cable.")

class Cable(BaseCable):
    """
    Generic cable with two ends, to connect two interfaces. When active
    transfers data from the send buffer of each interface to the receive
    buffer of the other interface.
    """
    def __init__(self):
        super().__init__()
        self.end1 = None
        self.end2 = None

    def update(self):
        """
        Cable becomes active if
         * Both ends (end1, end2) are connected to interfaces.
         * Bother ends are powered.
         * Neither interface is 'admin down'.

        When active drains send_buffer for each interface and puts the
        data in the recv_buffer of the opposite interface. Throws an
        error if the data is not bytes.
        """
        logger = logging.getLogger('netscool.layer1.cable')
        if not self.end1 or not self.end2:
            self._active = False
            return

        if LINE_ADMIN_DOWN in [self.end1.line_status, self.end2.line_status]:
            self._active = False
            return

        if not self.end1.powered or not self.end2.powered:
            self._active = False
            return

        self._active = True
        while self.end1.send_buffer:
            data = self.end1.send_buffer.pop(0)
            assert type(data) == bytes
            logger.info(
                "Cable transfer data {} -> {}".format(
                    self.end1.name, self.end2.name))
            self.end2.recv_buffer.append(data)

        while self.end2.send_buffer:
            data = self.end2.send_buffer.pop(0)
            assert type(data) == bytes
            logger.info(
                "Cable transfer data {} -> {}".format(
                    self.end2.name, self.end1.name))
            self.end1.recv_buffer.append(data)

    def plugin(self, interface):
        """
        Plug one end of the cable into the specified interface.
        Fails if interface already has a cable plugged in, or if both
        ends of this cable are plugged into interfaces.
        """
        assert not interface.cable, (
            "Interface already has a cable attached.")

        if not self.end1:
            self.end1 = interface
        elif not self.end2:
            self.end2 = interface
        else:
            raise Exception("Both cable ends already plugged in")
        interface.cable = self

SOCKET_CABLE_HEARTBEAT = b'\0'
class SocketCable(BaseCable):
    """
    A cable that connects via a UDP socket. The intention is that the
    other 'half' of this cable is in another process, enabling a device
    in another process to talk to our device.
    ::

        --------------            -------             -----------------
        | Our Device | --Cable--> | UDP | < --Cable-- | Remote Device |
        --------------            -------             -----------------

    This enables us to connect our device to an example device running
    in another python process.
    """
    def __init__(self, src_port, dst_port):
        """
        Create one 'end' of the cable. Two ends of the cable should have
        mirrored src and dst ports. The two ends can be in different
        processes, however must be on the same machine (listening on
        localhost).

        eg.
        SocketCable(11111, 22222)
        SocketCable(22222, 11111)

        :param src_port: UDP port to send data from.
        :param dst_port: UDP port to send data to.
        """

        super().__init__()
        self.end = None

        self._host = '127.0.0.1'
        self._src_port = src_port
        self._dst_port = dst_port
        self._last_heartbeat = time.time()
        self._heartbeat_timeout = 1

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.mtu = 1500
        self.socket.bind((self._host, self._src_port))

    def update(self):
        """
        Cable becomes active if.
         - An interface is plugged into this cable end.
         - The attached interface is powered.
         - The attached interface is not 'admin down'.
         - We have received a heartbeat message from the other end within
           the last second.

        When active sends everything in the interface send buffer down
        the src UDP socket (and a heartbeat), and reads anything sent
        to the UDP socket and puts it in the interface recv buffer.
        """
        logger = logging.getLogger('netscool.layer1.cable')
        if not self.end:
            self._active = False
            return

        if not self.end.powered:
            self._active = False
            return

        if self.end.line_status == LINE_ADMIN_DOWN:
            self._active = False
            return

        self._transmit(SOCKET_CABLE_HEARTBEAT)
        while self.end.send_buffer:
            logger.info(
                "Cable sending data from {}".format(self.end.name))
            self._transmit(self.end.send_buffer.pop(0))

        recv = self._receive()
        while recv:
            if recv == SOCKET_CABLE_HEARTBEAT:
                self._active = True
                self._last_heartbeat = time.time()
            else:
                logger.info(
                    "Cable recieved data to {} ".format(self.end.name))
                self.end.recv_buffer.append(recv)
            recv = self._receive()

        if time.time() - self._last_heartbeat > self._heartbeat_timeout:
            self._active = False

    def plugin(self, interface):
        """
        Plug interface into this end of the socket cable. Will fail if
        the interface already has a cable plugged in, or this end of the
        cable is plugged into another interface.
        """
        assert not interface.cable, (
            "Interface already has a cable attached.")
        assert self.end == None, "Cable already plugged in."
        interface.cable = self
        self.end = interface

    def _transmit(self, data):
        assert len(data) <= self.mtu
        self.socket.sendto(data, (self._host, self._dst_port))

    def _receive(self):
        read_fds, _, _ = select.select([self.socket], [], [], 0.1)
        if not read_fds or read_fds[0] != self.socket:
            return None
        data, addr = self.socket.recvfrom(self.mtu)
        return data
