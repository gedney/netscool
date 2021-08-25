.. netscool documentation master file, created by
   sphinx-quickstart on Tue Aug 17 10:53:52 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Introduction
============

The goal of this course is to gain an in depth understanding of networking devices and protocols by implementing them in Python.

This course distinguishes itself from other networking courses by focussing less on administering and using network devices, and more on how networking devices and protocols work. The ultimate goal is that the devices we write can interoperate with real networking devices.

This course is aimed at developers, and assumes a working knowledge of Python and general programming concepts.

Building Blocks
===============

In the real world networks are made up of physical equipment. We roughly approximate the physical world in this course using the classes in the ``netscool.layer1`` module.

There a few classes from this module that are worth pointing out.

 * BaseDevice - All of our devices (routers, switches etc) will build upon this class.
 * L1Interface - Represents a physical interface, our interfaces for our devices will build on this class.
 * Cable - Used to connect interfaces locally in our own code.
 * SocketCable - Used to connect to interfaces of devices running in other processes.

The ``netscool`` library also provides working implementations of everything required for the course. These implementations provide a test bed to make sure your own implementations are working correctly. This means these implementations are effectively an answer sheet, how much you look at the answer sheet is up to you.

Most of the lessons also rely heavily on ``scapy`` to build packets. This is because building the packet structures ourselves from scratch is mandrolic and uninteresting, and our focus is on how the protocols work, and how devices use those packets, rather than the bit and bytes of each packet. ``scapy`` is not perfect but it is good enough for our purposes.

The lessons also uses ``IPython``, and ``Pytest`` to provide a console to interact with devices and test they are working.

Obligatory OSI Model Section
============================

There are many great explanations of the OSI model already, so this section is kept brief. For more detailed explanations feel free to undertake your own research.

Networking is broken down logically into 7 layers called the OSI model. This model attempts to break the responsibilities of protocols and network devices into one of the layers of the model. Practically layers 5, 6, and 7 can be treated as one, and we will mostly ignore these. Layers 1-4 are responsible for moving traffic from one application, across a network, to another application, so we will only be focussing on those.

Each layer depends and builds upon the previous layer. The layers briefly are. 

 * 1 - Physical - Physical equipment, plugs, cables.
 * 2 - Data Link - Transfers frames across physical links between each device in the network.
 * 3 - Network - Transfers packets logically between hosts in or across networks.
 * 4 - Transport - Transfers datagrams from an application on host to an application on a remote host.
 * 5,6,7 - Application - Arbitrary application specific protocol data.

Some common protocols at each layer are.

 * 2 - Data Link - Ethernet
 * 3 - Network - IPv4 and IPv6
 * 4 - Transport - TCP and UDP
 * 5 - Application - SSH, HTTP, FTP

Some common device types at each layer are.

 * 2 - Data Link - Switches
 * 3 - Network - Routers
 * 4 - Transport - Desktops

The layers of the OSI model can be seen more clearly in the structure of encapsulated datagrams.

::

    +-------------------------------------------------------- Layer 5 +
    +-------------------------------------------- Layer 4---+         |
    +----------------------------- Layer 3 ----+            |         |
    +------- Layer 2 -------+                  |            |         |
    |                       |                  |            |         |
    +-----------------------+------------------+------------+---------+
    | Ethernet Frame Header | IP Packet Header | UDP Header | Payload |
    +-----------------------+------------------+------------+---------+

.. toctree::
   :maxdepth: 1
   :caption: Lessons

   lessons/lesson1.rst
   lessons/lesson2.rst

.. toctree::
   :maxdepth: 2
   :caption: API

   api/modules.rst
