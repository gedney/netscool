import time
import IPython

import netscool
netscool.lesson('lesson2')

import netscool.layer1
import netscool.layer2

import netscool.log
netscool.log.setup()
netscool.log.add('netscool.layer2.switch')
netscool.log.add('netscool.layer2.device')
netscool.log.list()

if __name__ == "__main__":
    switch = netscool.layer2.Switch(
        "sw1", "11:11:11:11:11:00", [
            netscool.layer2.L2Interface("0/1", "11:11:11:11:11:01"),
            netscool.layer2.L2Interface("0/2", "11:11:11:11:11:02"),
            netscool.layer2.L2Interface("0/3", "11:11:11:11:11:03")
        ])

    device1 = netscool.layer2.L2Device(
        'dev1', [
            netscool.layer2.L2Interface("0/1", "22:22:22:22:22:01"),
        ])

    device2 = netscool.layer2.L2Device(
        'dev2', [
            netscool.layer2.L2Interface("0/1", "22:22:22:22:22:02"),
        ])


    cable = netscool.layer1.Cable()
    switch.interface('0/2').plug_cable(cable)
    device1.interface('0/1').plug_cable(cable)

    cable = netscool.layer1.Cable()
    switch.interface('0/3').plug_cable(cable)
    device2.interface('0/1').plug_cable(cable)

    cable = netscool.layer1.SocketCable(11111, 22222)
    switch.interface('0/1').plug_cable(cable)

    try:
        switch.start()
        device1.start()
        device2.start()
        time.sleep(0.5)

        IPython.embed()
    finally:
        switch.shutdown()
        device1.shutdown()
        device2.shutdown()
