from scapy.all import Ether

import IPython
import netscool.layer1
import netscool.layer2
import netscool.log

INTERFACE_SRC_PORT = 11111
INTERFACE_DST_PORT = 22222

if __name__ == "__main__":
    netscool.log.setup()
    netscool.log.add('netscool.layer1')
    netscool.log.add('netscool.layer2')
    netscool.log.list()

    interface = netscool.layer2.L2Interface(
        "Interface1", "11:11:11:11:11:11")
    device = netscool.layer2.L2Device('Device', [interface])
    cable = netscool.layer1.SocketCable(
        INTERFACE_SRC_PORT, INTERFACE_DST_PORT)
    interface.plug_cable(cable)
    frame = Ether(src=interface.mac, dst='22:22:22:22:22:22')

    try:
        device.start()
        IPython.embed()
    finally:
        device.shutdown()
