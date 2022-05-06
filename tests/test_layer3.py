import ipaddress
import netscool.layer3

def test_routetable_install():
    routetable = netscool.layer3.RouteTable()

    # Test add invalid route tuples (must have network and interface).
    route = netscool.layer3.Route(
        network=None, interface=None, nexthop=None, ad=0, metric=0)
    assert routetable.install(route) == False
    assert routetable.routes == []

    route = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface=None,
        nexthop=None, ad=0, metric=0)
    assert routetable.install(route) == False
    assert routetable.routes == []

    route = netscool.layer3.Route(
        network=None, interface='dummy', nexthop=None, ad=0, metric=0)
    assert routetable.install(route) == False
    assert routetable.routes == []
    

    # Test add valid route.
    route = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface='dummy',
        nexthop=None, ad=0, metric=0)
    assert routetable.install(route) == True
    assert routetable.routes == [route]

    # Test add route different prefix
    route2 = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/16'), interface='dummy',
        nexthop=None, ad=0, metric=0)
    assert routetable.install(route2) == True
    assert routetable.routes == [route, route2]

    # Test add route different ad
    route = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface='dummy',
        nexthop=None, ad=0, metric=0)
    route2 = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface='dummy',
        nexthop=None, ad=1, metric=0)
    
    routetable.routes = []
    assert routetable.install(route) == True
    assert routetable.install(route2) == False
    assert routetable.routes == [route]

    routetable.routes = []
    assert routetable.install(route2) == True
    assert routetable.install(route) == True
    assert routetable.routes == [route]

    # Test add route different metric
    route = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface='dummy',
        nexthop=None, ad=0, metric=0)
    route2 = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface='dummy',
        nexthop=None, ad=0, metric=1)

    routetable.routes = []
    assert routetable.install(route) == True
    assert routetable.install(route2) == False
    assert routetable.routes == [route]

    routetable.routes = []
    assert routetable.install(route2) == True
    assert routetable.install(route) == True
    assert routetable.routes == [route]

    # Test add routes same
    route = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface='dummy',
        nexthop=None, ad=0, metric=0)
    route2 = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface='dummy',
        nexthop=None, ad=0, metric=0)

    routetable.routes = []
    assert routetable.install(route) == True
    assert routetable.install(route2) == True
    assert routetable.routes == [route, route2]

    routetable.routes = []
    assert routetable.install(route2) == True
    assert routetable.install(route) == True
    assert routetable.routes == [route, route2]

    # Replace dual routes
    route = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface='dummy',
        nexthop=None, ad=1, metric=0)
    route2 = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface='dummy',
        nexthop=None, ad=1, metric=0)
    route3 = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.10.0.0/24'), interface='dummy',
        nexthop=None, ad=0, metric=0)

    routetable.routes = []
    assert routetable.install(route) == True
    assert routetable.install(route2) == True
    assert routetable.routes == [route, route2]
    assert routetable.install(route3) == True
    assert routetable.routes == [route3]

def test_routetable_lookup():
    routetable = netscool.layer3.RouteTable()

    route = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.0.0.0/24'), interface='dummy',
        nexthop=None, ad=0, metric=0)
    route2 = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.0.0.0/16'), interface='dummy',
        nexthop=None, ad=0, metric=0)
    route3 = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.0.0.0/8'), interface='dummy',
        nexthop=None, ad=0, metric=0)

    assert routetable.install(route3) == True
    assert routetable.install(route2) == True
    assert routetable.install(route) == True

    assert routetable.lookup(ipaddress.IPv4Address('10.0.0.1')) == route
    assert routetable.lookup(ipaddress.IPv4Address('10.0.1.1')) == route2
    assert routetable.lookup(ipaddress.IPv4Address('10.1.1.1')) == route3

    routetable = netscool.layer3.RouteTable()
    route = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.0.0.0/24'), interface='dummy1',
        nexthop=None, ad=0, metric=0)
    route2 = netscool.layer3.Route(
        network=ipaddress.IPv4Network('10.0.0.0/24'), interface='dummy2',
        nexthop=None, ad=0, metric=0)

    assert routetable.install(route2) == True
    assert routetable.install(route) == True

    assert routetable.lookup(ipaddress.IPv4Address('10.0.0.1')) == route2
    assert routetable.lookup(ipaddress.IPv4Address('10.0.0.1')) == route
    assert routetable.lookup(ipaddress.IPv4Address('10.0.0.1')) == route2
    assert routetable.lookup(ipaddress.IPv4Address('10.0.0.1')) == route
