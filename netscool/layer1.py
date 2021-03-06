"""
Provides everything required to create the physical components of the
network.
"""
import time
import logging
import struct
import threading
import socket
import select
import collections

import scapy.all

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
    # TODO: This does not remove all race conditions. There is no
    # synchronisation between the ipython interactive thread and each
    # device thread. This means plugging/unplugging cables can cause
    # a device to crash (and probably numerous other race conditions).
    # This requires some serious thought to fix and has so far not
    # been an issue in practice, so im kicking the can down the road.
    _lock = threading.Lock()
    def __init__(self, name, interfaces):
        self._shutdown_event = threading.Event()
        self._thread = None
        self.interfaces = interfaces
        self.name = name
        self._event_loop_exception = None

    @property
    def event_loop_exception(self):
        return self._event_loop_exception

    def show_interfaces(self):
        """
        Print all interfaces in this device and the relevant status for
        the interface.
        """

        print(self)
        for interface in self.interfaces:
            print(interface, interface.status)

    def interface(self, interface_name):
        """
        Get a devices interface by name. Returns the first interface
        whose name matches ``interface_name``. Assumes all interfaces in
        the device have unique names.

        :param interface_name: Name of interface to get.
        :returns: The interface, or None.
        """
        for interface in self.interfaces:
            if interface.name != interface_name:
                continue
            return interface
        return None

    @property
    def powered(self):
        """
        True or False if the device is powered on. Calling start()
        powers on the devices, and calling shutdown() powers off the
        device.
        """
        return self._thread is not None and self._thread.is_alive()

    def shutdown(self):
        """
        Shutdown the event_loop thread, which is analagous to shutting
        down the device. Also powers off all interfaces in the device.
        """

        # Device is not powered on so nothing to shutdown.
        if not self.powered:
            return

        # Set the shutdown event and wait for the thread to join.
        self._shutdown_event.set()
        self._thread.join()
        self._thread = None
        self._internal_shutdown()

    def _internal_shutdown(self):
        # Power off all interfaces on the device. This will propagate
        # so any up/up links to this device will become down/down.
        for interface in self.interfaces:
            interface.powered = False
            interface.negotiate_connection()

        # Reset the shutdown event so the device can be started again.
        self._shutdown_event.clear()

        logger = logging.getLogger('netscool.layer1.device.status')
        logger.info("{} shutdown".format(self))

    def start(self):
        """
        Start the main event_loop thread for the device. Also powers on
        all interfaces on the device so that they can transistion to
        up/up if they have an active link.
        """
        # Thread is already running so nothing to do.
        if self._thread and self._thread.is_alive():
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

        # Reset any exceptions from previous runs of the event_loop.
        self._event_loop_exception = None
        try:
            while not self._shutdown_event.is_set():
                with BaseDevice._lock:
                    # Something needs to trigger the cables plugged into
                    # the interfaces to actually transfer. Instead of
                    # making each cable its own thread, we just update all
                    # the attached cables here.
                    for interface in self.interfaces:
                        interface.update()
                        if not interface.cable:
                            continue
                        interface.cable.update()

                    self.event_loop()
                time.sleep(0.1)
        except Exception as e:
            logging.exception("Error in {} event loop".format(self.name))
            self._event_loop_exception = e
        finally:
            self._shutdown_event.set()
            self._internal_shutdown()

    def __str__(self):
        return self.name

MAX_CAPTURE = 100
DIR_IN = "IN"
DIR_OUT = "OUT"
Capture = collections.namedtuple(
    "Capture", ["time", "direction", "data"])

class BaseInterface():
    """
    Base interface. This is essentially a Layer 1 interface, and takes
    the role of the physical hardware for the interface. Logic for
    higher level interfaces build on this base functionality.
    """
    def __init__(self, name):
        self.name = name

        self.cable = None
        self.recv_buffer = []
        self.send_buffer = []
        self._powered = False

        self._capture = []

        # Replace send and receive with wrappers that capture data
        # being sent and received by the interface. We keep references
        # to the 'real' send and receive so that the 'capture' variants
        # can still actually send and receive data.
        self._real_receive = self.receive
        self._real_send = self.send
        self.receive = self._capture_receive
        self.send = self._capture_send

    def captured(self, search, direction=None):
        """
        Was the given 'search' object captured. Will attempt to search for
        'search' object within captures eg. If you pass in a IP packet 
        will attempt to find that inside Ether frames. If you pass in raw
        bytes the capture will be checked exactly and no introspection will
        occur.

        :param search: The object to search for.
        :param direction: Optionally check the capture was captured going
            in or out of the interface. Valid values are "IN" 
            (netscool.layer1.DIR_IN), "OUT" (netscool.layer1.DIR_OUT), or 
            None
        :returns: True or False.
        """
        def check_direction(direction, capture):
            if direction is None:
                return True
            if direction == capture.direction:
                return True
            return False

        for capture in self._capture:
            capture_bytes = capture.data

            # Bytes passed in so check bytes match exactly.
            if type(search) == type(capture_bytes):
                if (search == capture_bytes and
                    check_direction(direction, capture)):
                    return True
                continue

            # Strip off 4 byte FCS appended to frames. This is only
            # visible on captures coming out of the interface.
            if capture.direction == DIR_OUT:
                capture_bytes = capture_bytes[:-4]

            for layer in [scapy.all.Ether, scapy.all.Dot1Q, scapy.all.IP]:
                
                # Attempt to convert bytes to next layer.
                try:
                    capture_obj = layer(capture_bytes)
                    capture_bytes = bytes(capture_obj.payload)

                # Converting to this layer didnt work so move onto the
                # next layer.
                except:
                    capture_obj = None
                    continue

                # The type of this layer was passed in so check if it
                # matches.
                if type(search) == type(capture_obj):

                    # This capture matches, so we're done!
                    if (search == capture_obj and
                        check_direction(direction, capture)):
                        return True

                    # didnt match so no point comparing against this
                    # capture anymore.
                    break

        return False

    @property
    def capture(self):
        """
        Get a list of the last MAX_CAPTURES worth of captured data.
        """
        return self._capture.copy()

    def clear_capture(self):
        """
        Clear any previous captures.
        """
        self._capture = []

    def _capture_receive(self, *args, **kwargs):
        """
        Capture any data the interface receives. The captured data will
        only be data that is valid for the inherited interface receive
        eg. Layer 2 frames dropped because they have the wrong source
        MAC will not be captured. Only keeps the last MAX_CAPTURES worth
        of messages.
        """
        data = self._real_receive(*args, **kwargs)
        if data != None:
            capture = Capture(
                time=time.time(), direction=DIR_IN,
                data=bytes(data))
            self._capture.append(capture)
            self._capture = self._capture[-MAX_CAPTURE:]
        return data

    def _capture_send(self, *args, **kwargs):
        """
        Capture any data the interface sends. The captured data will only
        be data that is valid for the inherited interface send. If the
        inherited interface drops the data it will not be captured. Only
        keeps the last MAX_CAPTURES worth of messages.
        """
        # We check the send buffer before and after the send. Anything
        # new in the send buffer is data that has been successfully sent.
        # There is a small race condition that the send buffer will be
        # drained between _real_send and assigning post_buffer. If this
        # becomes a recurring issue i'll add some locks around the
        # send_buffer.
        pre_buffer = set(self.send_buffer)
        self._real_send(*args, **kwargs)
        post_buffer = set(self.send_buffer)

        capture = [
            Capture(
                time=time.time(), direction=DIR_OUT,
                data=bytes(data))
            for data in post_buffer - pre_buffer]

        self._capture += capture
        self._capture = self._capture[-MAX_CAPTURE:]

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

    def plug_cable(self, cable):
        """
        Plug a cable into the interface.
        """
        cable.plugin(self)

    def unplug_cable(self, cable):
        cable.unplug(self)

    def update(self):
        self.negotiate_connection()

    @property
    def status(self):
        raise NotImplementedError("Interface provides no status")
    def negotiate_connection(self):
        raise NotImplementedError(
            "Interface provides no negotiate_connection.")
    def shutdown(self):
        raise NotImplementedError("Interface provides no shutdown.")
    def no_shutdown(self):
        raise NotImplementedError("Interface provides no no_shutdown.")
    def send(self, data):
        raise NotImplementedError("Interface provides no send.")
    def receive(self):
        raise NotImplementedError("Interface provides no receive.")

    def __str__(self):
        return self.name

class L1Interface(BaseInterface):
    def __init__(self, name, bandwidth=1000):
        super().__init__(name)

        # TODO check both ends bandwidth match.
        self.bandwidth = bandwidth
        self.line_status = LINE_DOWN

    @property
    def status(self):
        """ Gets the layer 1 line status for the interface. """
        return self.line_status

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
    def unplug(self, interface):
        """
        Unplug the cable from the specified interface.
        """
        raise NotImplementedError(
            "'unplug' not implemented for this cable.")

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

    def unplug(self, interface):
        """
        Unplug one end of the cable from the specified interface.
        Fails if the cable isnt plugged into the specified interface.
        """
        assert interface.cable == self, (
            "Interface not plugged into this cable.")
        if self.end1 == interface:
            self.end1 = None
        elif self.end2 == interface:
            self.end2 = None
        else:
            raise Exception("Interface not plugged into cable.")
        interface.cable = None
        self.update()

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

    def unplug(self, interface):
        """
        Unplug interface from this end of the socket cable. Will fail if
        interface is not plugged into this end of the socket cable.
        """
        assert interface.cable == self, (
            "Interface not plugged into this cable.")
        assert self.end == interface, (
            "Cable not plugged into specified interface.")
        interface.cable = None
        self.end = None
        self.update()

    def _transmit(self, data):
        assert len(data) <= self.mtu
        self.socket.sendto(data, (self._host, self._dst_port))

    def _receive(self):
        read_fds, _, _ = select.select([self.socket], [], [], 0.1)
        if not read_fds or read_fds[0] != self.socket:
            return None
        data, addr = self.socket.recvfrom(self.mtu)
        return data
