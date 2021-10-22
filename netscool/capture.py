"""
Some utilities for handling interface captures. The actual logic for
capturing traffic on an interface is in netscool.layer1.BaseInterface.
"""
import scapy.all

def write_pcap(filename, capture):
    """
    Write a capture (eg. device.interface('0/0').capture) to a pcap file.

    :param filename: Where to write the pcap.
    :param capture: List of netscool.layer1.Capture namedtuples.
    """
    with scapy.all.PcapWriter(filename) as writer:
        for cap in capture:
            frame = scapy.all.Ether(cap.data)
            frame.time = cap.time
            writer.write(frame)

def clear_captures(*devices):
    """
    Clear captures for all interfaces for the specified devices.

    :param device: Devices to clear captures for.
    """
    for device in devices:
        for interface in device.interfaces:
            interface.clear_capture()
