# under_construction.gif

import IPython
import netscool
from netscool.layer1 import Cable
from netscool.layer3 import Router, IPv4Interface, L3Device
from scapy.all import IP

import netscool.log
netscool.log.setup()
netscool.log.add('netscool.layer3')
netscool.log.list()

if __name__ == "__main__":
    r0 = Router("r0", [
            IPv4Interface("0/0", "10.0.0.1/24", "00:00:00:00:00:00"),
            IPv4Interface("0/1", "10.0.1.1/24", "00:00:00:00:01:00"),
        ])
    dev0 = L3Device("dev0", [
            IPv4Interface("0/0", "10.0.0.2/24", "00:00:00:00:00:02"),
        ])
    dev1 = L3Device("dev1", [
            IPv4Interface("0/0", "10.0.1.2/24", "00:00:00:00:01:02"),
        ])

    cable = Cable()
    dev0.interface('0/0').plug_cable(cable)
    r0.interface('0/0').plug_cable(cable)

    cable = Cable()
    dev1.interface('0/0').plug_cable(cable)
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
    dev1.arp.table = {
        '10.0.0.2' : '00:00:00:00:01:00',
        '10.0.0.1' : '00:00:00:00:01:00',
        '10.0.1.1' : '00:00:00:00:01:00',
    }

    dev0_dev1 = IP(src="10.0.0.2", dst="10.0.1.2")
    dev1_dev0 = IP(src="10.0.1.2", dst="10.0.0.2")
    dev0_r0 = IP(src="10.0.0.2", dst="10.0.0.1")
    dev1_r0 = IP(src="10.0.1.2", dst="10.0.1.1")
    try:
        r0.start()
        dev0.start()
        dev1.start()
        IPython.embed()
    finally:
        r0.shutdown()
        dev0.shutdown()
        dev1.shutdown()
