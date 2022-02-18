import time
import IPython

import netscool.layer1
import netscool.layer2

import netscool.log
netscool.log.setup()
netscool.log.add('netscool.layer2.switch')
netscool.log.add('netscool.layer2.device')
netscool.log.list()

if __name__ == "__main__":
    switch1 = netscool.layer2.Switch(
        "sw1", "11:11:11:11:11:00", [
            netscool.layer2.SwitchPort("0/0", "11:11:11:11:11:01"),
            netscool.layer2.SwitchPort("0/1", "11:11:11:11:11:02"),
            netscool.layer2.SwitchPort("0/2", "11:11:11:11:11:03")
        ])

    device2 = netscool.layer2.L2Device(
        'dev1', [
            netscool.layer2.L2Interface("0/0", "22:22:22:22:22:02"),
        ])

    device3 = netscool.layer2.L2Device(
        'dev2', [
            netscool.layer2.L2Interface("0/0", "22:22:22:22:22:03"),
        ])


    cable = netscool.layer1.Cable()
    device2.interface('0/0').plug_cable(cable)
    switch1.interface('0/1').plug_cable(cable)
    switch1.interface('0/1').set_access_port(vlan=10)
    
    cable = netscool.layer1.Cable()
    device3.interface('0/0').plug_cable(cable)
    switch1.interface('0/2').plug_cable(cable)
    switch1.interface('0/2').set_access_port(vlan=20)

    cable = netscool.layer1.SocketCable(11111, 22222)
    switch1.interface('0/0').plug_cable(cable)
    switch1.interface('0/0').set_trunk_port([10, 20], 10)

    try:
        switch1.start()
        device2.start()
        device3.start()
        time.sleep(0.5)

        IPython.embed()
    finally:
        switch1.shutdown()
        device2.shutdown()
        device3.shutdown()
