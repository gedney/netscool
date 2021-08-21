Lesson 1 - InterFace Off
========================

This first lesson introduces layer 2 interfaces and Ethernet frames, and serves more generally to show the vague structure of lessons.

I Just Want To Run Some F*ckn Code Already
------------------------------------------

Alright, dont yell at me. Open two terminals in the ``l1`` directory. In the first run ``lesson.py``, and in the second run ``network.py``. You should now have two ``IPython`` interactive shells (with autocomplete).

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

Each side of the network has one layer 2 device (``L2Device``), and each device has a single layer 2 interface (``L2Interface``). The two interfaces are connected via a cable (``SocketCable``). On the ``lesson.py`` side the ``<TODO>`` represents the part that you have to do. ``L2Interface`` is only partially completed in ``lesson.py``.

What Do?
--------

Open ``lesson.py`` and start filling in the methods for the ``L2Interface`` class.

Very Good... But What Is An "L2Interface"?
------------------------------------------

All networking devices need a physical way to connect to a network. This physical connection on the device is called an interface. This physical interface could be a plug, an antenna, or in our case a python class called ``BaseInterface``.

The ``BaseInterface`` deals with connecting our devices at layer 1 (physical layer). When two interfaces are connected and working at layer 1 we say the "line" is up.

Unfortunately in the real world we can't just send random electrical signals and expect devices to understand each other. This is where layer 2 comes in. Layer 2 protocols provide some rules so devices can communicate across the physical link. We are only going to worry about the ``Ethernet`` layer 2 protocol for now, and our ``L2Interface`` is going to handle ``Ethernet`` messages.

Each ``Ethernet`` message is called frame. We can't send frames across our link until we have determined that on top of layer 1 connectivity ("Line Up"), we also have layer 2 connectivity ("Protocol Up", "Line Protocol Up"). Normally layer 1 is sending some kind of electrical signal, and ``Ethernet`` has to figure out how to turn those signals into discreet frames. The different statuses for an interface.

 * down/down - No layer 1 connection eg. broken cable, device powered off
 * admin down/down - The interfaces has been admistratively shutdown.
 * down/down err - The interface is 'error disabled', most likely from port security
 * up/down - There is an issue at layer 2.
 * up/up - The interface is working and ready to send/receive.

Once the interface is up/up we can send frames across the link. There are a few different ``Ethernet`` types, but the one thing they all have in common is that every frame has a source and destination MAC address. Every interface has a MAC address, which should be unique. Normally an interface will drop any frame it receives if the destination MAC doesnt match the interfaces MAC address. We can change this behaviour by setting the interface to promiscuous mode, meaning it will process any frame it receives and not just those explicitly addressed to it.

I've Written Some Code, How Do I Know It Works?
-----------------------------------------------

You can manually test your interface using the ``lesson.py`` and ``network.py`` interactive shells. Once you are confident your interface is working through manual testing you can run the supplied automated tests. These tests use ``pytest`` and can be run as follows.

::

    pytest lesson.py

Once your tests pass, congratulations you are done!

Am I Really Done?
-----------------

Lol no, this course is also secretly about not writing trash code. Write some comments and docstrings. Maybe add some extra tests if relevant. If you really want bonus points get someone to do a code review and roast your comments for not having full stops. Although the code for this lesson is relatively straight forward, later lessons will grow in complexity, and bad practices will bite you in the long run (I will literally bite you if you dont put full stops on your comments).
