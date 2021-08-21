# The sacred texts "Cisco Catalyst LAN Switching" from the prophets Louis R. Rossi and Thomas Rossi.
# https://flylib.com/books/en/2.115.1.67/1/

import logging
import netscool.layer1
import scapy.all

PROTOCOL_DOWN = 'down'
PROTOCOL_UP = 'up'
PROTOCOL_ERR = 'down err'

class L2Device(netscool.layer1.BaseDevice):
    def event_loop(self):
        logger = logging.getLogger("netscool.layer2.device.receive")
        for interface in self.interfaces:

            frame = interface.receive()
            if not frame:
                continue

            logger.info(
                '{} got frame {} -> {}\n {}'.format(
                    self, frame.src, frame.dst, frame))
                
class L2Interface(netscool.layer1.BaseInterface):
    """ A Layer 2 interface. """
    def __init__(self, name, mac, bandwidth=1000, promiscuous=False):
        """
        :param name: Name of interface to make identification simpler.
        :param mac: Layer2 MAC address for interface in the form
            XX:XX:XX:XX:XX:XX. 
        :param bandwidth: Bandwidth of interfaces in bits per second.
            Each interface at the end of a link must have the same
            bandwidth.
        :param promiscuous: A promiscuous interface will accept frames
            destined to any MAC address. A non-promiscuous interface
            will drop frames that are not destined for it.
        """
        super().__init__(name, bandwidth)
        self.mac = mac
        self.promiscuous = promiscuous
        self.protocol_status = PROTOCOL_DOWN

    @property
    def upup(self):
        """
        True if the line status and protocol status are both up. An
        interface can only send and receive frames if it is up/up.
        """
        return self.line_up and self.protocol_up

    @property
    def status(self):
        """
        Get a tuple of the line and protocol status for the interface.
        Line status is the status of the link at Layer 1, and protocol
        status is the status of the link at Layer 2. Protocol status
        can only be up if line status is also up. The possible
        combinations are.

        +----------+----------+-----------------------------------------+
        | Line     | Protocol | Description                             |
        +==========+==========+=========================================+
        | down     | down     | There is a Layer1 issue with the        |
        |          |          | connection eg. Interface speed mismatch,|
        |          |          | broken cable, device powered off etc.   |
        +----------+----------+-----------------------------------------+
        |admin down| down     | The interface has been administratively |
        |          |          | shutdown.                               |
        +----------+----------+-----------------------------------------+
        | down     | down err | Interface is 'error disabled', most     |
        |          |          | likely from port security (port security|
        |          |          | is not implemented).                    |
        +----------+----------+-----------------------------------------+
        | up       | down     | The Layer2 protocol has an error, or    |
        |          |          | didnt match. Since we only have our     |
        |          |          | simulated ethernet interface this cannot|
        |          |          | happen, however it we implemented a new |
        |          |          | interface with a different Layer2       |
        |          |          | protocol then this could happen.        |
        +----------+----------+-----------------------------------------+
        | up       | up       | The interface is up and ready to        |
        |          |          | send/receive.                           |
        +----------+----------+-----------------------------------------+
        """
        return (self.line_status, self.protocol_status)

    @property
    def protocol_up(self):
        """ Is the protocol status up (Layer2 connectivity). """
        return self.protocol_status == PROTOCOL_UP

    def negotiate_connection(self):
        """
        Negotiate the Layer 2 protocol for the interface. For now we only
        have one L2 protocol and we assume its connectivity always works.
        We also haven't implemented port security so err disabled does
        not apply.
        """
        super().negotiate_connection()
        logger = logging.getLogger('netscool.layer2.interface.status')
        if self.line_up:
            if self.protocol_status == PROTOCOL_DOWN:
                logger.info(
                    "{} line protocol up".format(self, self.mac))
                self.protocol_status = PROTOCOL_UP
        else:
            if self.protocol_status == PROTOCOL_UP:
                logger.info(
                    "{} line protocol down".format(self, self.mac))
                self.protocol_status = PROTOCOL_DOWN

    def receive(self):
        """
        Receive a layer 2 frame.

        :returns: Scapy Ether object of frame or None.
        """
        logger = logging.getLogger('netscool.layer2.interface.receive')
        if not self.upup:
            return
        data = super().receive()
        if not data:
            return
        frame = scapy.all.Ether(data)
        if not self.promiscuous and frame.dst.lower() != self.mac.lower():
            logger.error(
                '{} received invalid frame {}'.format(
                    self, frame.dst.lower()))
            return
        logger.info("{} received layer2 frame".format(self))
        return frame

    def send(self, frame):
        """
        Send a layer 2 frame.

        :param frame: Scapy Ether object of frame.
        """
        logger = logging.getLogger('netscool.layer2.interface.send')
        if not self.upup:
            logger.error('{} not up/up'.format(self))
            return
        if not isinstance(frame, scapy.all.Ether):
            logger.error('{} can only send Ether frames'.format(self))
            return
        logger.info("{} sending layer2 frame".format(self))
        super().send(bytes(frame))

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.mac)
