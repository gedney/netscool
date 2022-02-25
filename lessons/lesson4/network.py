import IPython
import netscool.layer1
import netscool.layer3

from scapy.all import IP

import netscool.log
netscool.log.setup()
netscool.log.add('netscool.layer3')
netscool.log.list()

if __name__ == "__main__":
    dev1 = netscool.layer3.L3Device("dev1", [
            netscool.layer3.IPInterface("0/0", "10.0.1.2/24", "00:00:00:00:01:02"),
        ])

    cable = netscool.layer1.SocketCable(11111, 22222)
    dev1.interface('0/0').plug_cable(cable)

    # Manually populate ARP table for device.
    dev1.arp.table = {
        '10.0.0.2' : '00:00:00:00:01:00',
        '10.0.0.1' : '00:00:00:00:01:00',
        '10.0.1.1' : '00:00:00:00:01:00',
    }

    dev1_dev0 = IP(src="10.0.1.2", dst="10.0.0.2")
    try:
        dev1.start()
        IPython.embed()
    finally:
        dev1.shutdown()
