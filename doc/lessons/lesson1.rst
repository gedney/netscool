Lesson 1 - InterFace Off
========================

This first lesson introduces layer 2 interfaces and Ethernet frames, and serves more generally to show the vague structure of lessons.

I Just Want To Run Some F*ckn Code Already
------------------------------------------

Alright, dont yell at me. Open two terminals in the ``lessons/lesson1`` directory. In the first run ``lesson.py``, and in the second run ``network.py``. You should now have two ``IPython`` interactive shells.

In the ``lesson.py`` shell run. ::

    interface.send(frame)

You should see some activity in ``network.py`` as it prints out the ethernet frame you just sent it.

This is all very cool, but what does any of it mean?

The Lesson Network
------------------

Each lesson provides a reference network in ``network.py``, that ``lesson.py`` can 'plug' into.

In this lesson our network looks like this ::

    lesson.py        | network.py
                     |
    +----------+     |     +-------------+
    | L2Device |     |     | L2Device    |
    | < TODO > <-----|-----> L2Interface |
    +----------+     |     +-------------+

Each side of the network has one layer 2 device (``L2Device``), and each device has a single layer 2 interface (``L2Interface``). The two interfaces are connected via a cable (``SocketCable``). On the ``lesson.py`` side the ``<TODO>`` represents the part that you have to do. ``L2Interface`` only partially works in ``lesson.py``.

What Do?
--------

Open ``lesson.py`` and start filling in the methods for the ``L2Interface`` class. The ``TODO`` comments give a good indication of where you need to add code.

Very Good... But What Is An "L2Interface"?
------------------------------------------

All networking devices need a physical way to connect to a network. This physical connection on the device is called an interface. This physical interface could be a plug, an antenna, or in our case a python class called ``L1Interface``.

The ``L1Interface`` deals with connecting our devices at layer 1 (physical layer). When two interfaces are connected and working at layer 1 we say the "line" is up.

Unfortunately in the real world we can't just send random electrical signals and expect devices to understand each other. This is where layer 2 comes in. Layer 2 protocols provide some rules so devices can communicate across the physical link. We are only going to worry about the ``Ethernet II`` layer 2 protocol for now, and our ``L2Interface`` is going to handle ``Ethernet`` messages (``Ethernet II`` is the most common type of ``Ethernet``, and any future references to ``Ethernet`` refer to ``Ethernet II``).

Each ``Ethernet`` message is called a frame. We can't send frames across our link until we have determined that on top of layer 1 connectivity ("Line Up"), we also have layer 2 connectivity ("Protocol Up" or "Line Protocol Up"). Normally layer 1 is sending some kind of electrical signal, and ``Ethernet`` has to figure out how to turn those signals into discreet frames. The different statuses for an interface.

 * down/down - No layer 1 connection eg. broken cable, device powered off
 * admin down/down - The interface has been admistratively shutdown.
 * down/down err - The interface is 'error disabled', most likely from port security.
 * up/down - We are getting activity across the line, but ``Ethernet`` can't make sense of it.
 * up/up - The interface is working and ready to send/receive.

Luckily for us our layer 1 is already sending discreet chunks of data, so our layer 2 interface doesnt have much work to do to turn the chunks into frames.

Once the interface is up/up we can send frames across the link. Every layer 2 interface has a MAC address, which is a unique identifier for that interface (duplicate MAC addresses cause bad times). Every ``Ethernet`` frame has a source and destination MAC address, which are the interface that sent the frame, and interface it is destined for. Normally an interface will drop any frame it receives if the destination MAC doesnt match its MAC address. There are some situations where we still want to process a frame even if it isn't addressed to us. In this case we can put the interface into promiscuos mode, and it will process any frame it receives regardless of the destination MAC of the frame.

The other fields of the ``Ethernet`` header are the ethertype, and the frame check sequence (FCS). The ethertype indicates the type of payload our frame is carrying. The FCS is appended to the end of the frame after the payload and is used to detect transmission errors.

.. note::
    Scapy does not define an FCS field in its Ether type, this means to create a valid ``Ethernet`` frame we need to append an FCS when sending a frame and remove it when receiving a frame. You can also calculate and validate the FCS when sending/receiving, but this is not necessary. Appending and stripping 4 bytes is more than sufficient for our purposes.

The final thing we have to worry about is the maximum size of our frames. This is calculated by Maximum Transfer Unit (MTU) (the maximum size of a frame payload) + size of the ``Ethernet`` headers themselves. We can choose anything for the MTU for our ``L2Interface``, but for simplicity we will use 1500 bytes as this is the standard for ``Ethernet``. An ``Ethernet`` header is source MAC (6 bytes) + destination MAC (6 bytes) + ether type (2 bytes) + frame check sequence (4 bytes) = 18 bytes. So our maximum frame size will be 1500 + 18 = 1518 byte. For every frame sent and received by our ``L2Interface`` we should check the overall frame size is less than the maximum frame size.

.. warning::
    MTU can sometimes be confusingly used in multiple contexts to mean multiple things. Sometimes the maximum frame size is referred to as MTU, or layer2 MTU, or physical MTU. Sometimes MTU is used to refer to the maximum size of a payload in higher level protocols. For the purposes of this course MTU will always reference the maximum payload size of an ``Ethernet`` frame, however you should be aware when doing your own reading that it my be used to mean something different depending on context.

I've Written Some Code, How Do I Know It Works?
-----------------------------------------------

You can manually test your interface using the ``lesson.py`` and ``network.py`` interactive shells. Once you are confident your interface is working you can run the supplied automated tests. These tests use ``pytest`` and can be run as follows.

::

    pytest lesson.py

Once your tests pass, congratulations you are done!

Am I Really Done?
-----------------

Lol no, this course is also secretly about not writing trash code. Write some comments and docstrings. Maybe add some extra tests if relevant. Refactor your code into a module you can reuse in later lessons. If you really want bonus points get someone to do a code review and roast your comments for not having full stops. The code for this lesson is relatively straight forward, however later lessons will grow in complexity, and bad practices will bite you in the long run (I will literally bite you if you dont put full stops on your comments).
