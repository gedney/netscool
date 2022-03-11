"""
Completed examples of classes for lesson1. Currently the reference
implementations in netscool.layer2 are similar enough that them and these
examples can be tested by the same tests in test_layer2.
"""
import logging
from scapy.all import Ether
import netscool.layer1

class L2Device(netscool.layer1.BaseDevice):
    """
    Test implementation of L2Device for lesson1.
    """
    def event_loop(self):
        logger = logging.getLogger("netscool.test.lesson1")
        for interface in self.interfaces:
            frame = interface.receive()
            if not frame:
                continue

            logger.info(
                "{} got frame\n{}".format(self, frame.show(dump=True)))

class L2Interface(netscool.layer1.L1Interface):
    """
    Test implementation of L2Interface for lesson1.
    """

    PROTOCOL_DOWN = 'down'
    PROTOCOL_UP = 'up'

    def __init__(self, name, mac, bandwidth=1000, mtu=1500, promiscuous=False):
        super().__init__(name, bandwidth)
        self.mac = mac
        self.promiscuous = promiscuous
        self.protocol_status = L2Interface.PROTOCOL_DOWN
        self.mtu = mtu
        self.maximum_frame_size = mtu + 18

    @property
    def protocol_up(self):
        return self.protocol_status == L2Interface.PROTOCOL_UP

    @property
    def upup(self):
        return self.line_up and self.protocol_up

    @property
    def status(self):
        return (self.line_status, self.protocol_status)

    def negotiate_connection(self):
        super().negotiate_connection()
        if self.line_up:
            if self.protocol_status == L2Interface.PROTOCOL_DOWN:
                self.protocol_status = L2Interface.PROTOCOL_UP
        else:
            if self.protocol_status == L2Interface.PROTOCOL_UP:
                self.protocol_status = L2Interface.PROTOCOL_DOWN

    def receive(self):
        if not self.upup:
            return
        data = super().receive()
        if not data:
            return
        if len(data) > self.maximum_frame_size:
            return
        data = data[:-4]
        try:
            frame = Ether(data)
        except:
            return
        if not self.promiscuous and frame.dst.lower() != self.mac.lower():
            return
        return frame

    def send(self, frame):
        if not self.upup:
            return
        if not isinstance(frame, Ether):
            return
        data = bytes(frame) + b'\0\0\0\0'
        if len(data) > self.maximum_frame_size:
            return
        super().send(data)

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.mac)
