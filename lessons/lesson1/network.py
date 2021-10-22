from scapy.all import Ether

import IPython

#import netscool
#netscool.lesson('lesson1')

import netscool.layer1
import netscool.layer2

import netscool.log
netscool.log.setup()
netscool.log.add('netscool.layer1')
netscool.log.add('netscool.layer2')
netscool.log.list()

if __name__ == "__main__":
    interface = netscool.layer2.L2Interface(
        "Interface", "11:11:11:11:11:11")
    device = netscool.layer2.L2Device('Device', [interface])
    cable = netscool.layer1.SocketCable(11111, 22222)
    interface.plug_cable(cable)
    frame = Ether(src=interface.mac, dst='22:22:22:22:22:22')

    try:
        device.start()
        IPython.embed()
    finally:
        device.shutdown()
