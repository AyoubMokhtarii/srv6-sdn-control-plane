#!/usr/bin/python

from __future__ import absolute_import, division, print_function

# General imports
from six import text_type
import grpc
import json
import sys
import os
from socket import AF_INET
from threading import Thread


################## Setup these variables ##################

# Path of the proto files
#PROTO_FOLDER = "../../../srv6-sdn-proto/"

###########################################################

# Adjust relative paths
#script_path = os.path.dirname(os.path.abspath(__file__))
#PROTO_FOLDER = os.path.join(script_path, PROTO_FOLDER)

# Check paths
#if PROTO_FOLDER == '':
#    print('Error: Set PROTO_FOLDER variable '
#          'in sb_grpc_client.py')
#    sys.exit(-2)
#if not os.path.exists(PROTO_FOLDER):
#    print('Error: PROTO_FOLDER variable in sb_grpc_client.py '
#          'points to a non existing folder\n')
#    sys.exit(-2)

# Add path of proto files
#sys.path.append(PROTO_FOLDER)

# SRv6 dependencies
from srv6_sdn_proto import srv6_manager_pb2
from srv6_sdn_proto import srv6_manager_pb2_grpc
from srv6_sdn_proto import status_codes_pb2
from srv6_sdn_proto import network_events_listener_pb2
from srv6_sdn_proto import network_events_listener_pb2_grpc
from srv6_sdn_proto import empty_req_pb2
from srv6_sdn_proto import empty_req_pb2_grpc

# Network event types
EVENT_TYPES = {
    'CONNECTION_ESTABLISHED': (network_events_listener_pb2.NetworkEvent
                               .CONNECTION_ESTABLISHED),
    'INTF_UP': network_events_listener_pb2.NetworkEvent.INTF_UP,
    'INTF_DOWN': network_events_listener_pb2.NetworkEvent.INTF_DOWN,
    'INTF_DEL': network_events_listener_pb2.NetworkEvent.INTF_DEL,
    'NEW_ADDR': network_events_listener_pb2.NetworkEvent.NEW_ADDR,
    'DEL_ADDR': network_events_listener_pb2.NetworkEvent.DEL_ADDR
}

# Define wheter to use SSL or not
DEFAULT_SECURE = False
# SSL cerificate for server validation
DEFAULT_CERTIFICATE = 'cert_client.pem'

class SRv6Manager:

    def __init__(self, secure=DEFAULT_SECURE, certificate=DEFAULT_CERTIFICATE):
        self.SECURE = secure
        if secure is True:
            if certificate is None:
                print('Error: "certificate" variable cannot be None '
                      'in secure mode')
                sys.exit(-2)
            self.CERTIFICATE = certificate

    # Build a grpc stub
    def get_grpc_session(self, ip_address, port, secure):
        # If secure we need to establish a channel with the secure endpoint
        if secure:
            # Open the certificate file
            with open(self.CERTIFICATE) as f:
                certificate = f.read()
            # Then create the SSL credentials and establish the channel
            grpc_client_credentials = grpc.ssl_channel_credentials(certificate)
            channel = grpc.secure_channel("ipv6:[%s]:%s" % (ip_address, port),
                                          grpc_client_credentials)
        else:
            channel = grpc.insecure_channel("ipv6:[%s]:%s"
                                            % (ip_address, port))
        return (srv6_manager_pb2_grpc
                .SRv6ManagerStub(channel), channel)

    # CRUD SRv6 Explicit Path

    def create_srv6_explicit_path(self, server_ip, server_port, destination,
                                  device, segments, encapmode="encap",
                                  table=-1):
        # Get the reference of the stub
        srv6_stub, channel = self.get_grpc_session(server_ip, server_port, self.SECURE)
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.SRv6ExplicitPath
        # Create a new SRv6 explicit path request
        path_request = srv6_request.srv6_ep_request
        # Create a new path
        path = path_request.paths.add()
        # Set destination, device, encapmode, table and segments
        path.destination = text_type(destination)
        path.device = text_type(device)
        path.encapmode = text_type(encapmode)
        path.table = int(table)
        for segment in segments:
            # Create a new segment
            srv6_segment = path.sr_path.add()
            srv6_segment.segment = text_type(segment)
        # Add the SRv6 path
        response = srv6_stub.Create(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    def create_srv6_explicit_path_from_json(self, server_ip, server_port, data):
        json_data = json.loads(data)
        # Iterate over the array and delete one by one all the paths
        for data in json_data:
            # Each time we create a new session
            srv6_stub, channel = self.get_grpc_session(server_ip, server_port, self.SECURE)
            # Create message request
            srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
            # Set the type of the carried entity
            srv6_request.entity_type = srv6_manager_pb2.SRv6ExplicitPath
            # Create a new SRv6 explicit path request
            path_request = srv6_request.srv6_ep_request
            # Process JSON file
            for jpath in data['paths']:
                # Create a new path
                path = path_request.paths.add()
                # Set destination, device, encapmode,
                # table and segments
                path.destination = text_type(jpath['destination'])
                path.device = text_type(jpath['device'])
                path.encapmode = text_type(jpath['encapmode'])
                for segment in jpath['segments']:
                    srv6_segment = path.sr_path.add()
                    srv6_segment.segment = text_type(segment)
                # Add the SRv6 path
                response = srv6_stub.Create(srv6_request)
                # Let's close the session
                channel.close()
        # Create the response
        return response.status

    def get_srv6_explicit_path(self, server_ip, server_port, destination,
                               device, segments=[],
                               encapmode="encap", table=-1):
        print('Not yet implemented')

    def update_srv6_explicit_path(self, server_ip, server_port, destination,
                                  device, segments=[],
                                  encapmode="encap", table=-1):
        print('Not yet implemented')

    def remove_srv6_explicit_path(self, server_ip, server_port, destination,
                                  device='', segments=[],
                                  encapmode="encap", table=-1):
        # Get the reference of the stub
        srv6_stub, channel = self.get_grpc_session(server_ip, server_port, self.SECURE)
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.SRv6ExplicitPath
        # Create a new SRv6 explicit path request
        path_request = srv6_request.srv6_ep_request
        # Create a new path
        path = path_request.paths.add()
        # Set destination, device, encapmode, table and segments
        path.destination = text_type(destination)
        path.device = text_type(device)
        path.encapmode = text_type(encapmode)
        path.table = int(table)
        for segment in segments:
            # Create a new segment
            srv6_segment = path.sr_path.add()
            srv6_segment.segment = text_type(segment)
        # Remove the SRv6 path
        response = srv6_stub.Remove(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    def remove_srv6_explicit_path_from_json(self, server_ip, server_port, data):
        json_data = json.loads(data)
        # Iterate over the array and delete one by one all the paths
        for data in json_data:
            # Each time we create a new session
            srv6_stub, channel = self.get_grpc_session(server_ip, server_port, self.SECURE)
            # Create message request
            srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
            # Set the type of the carried entity
            srv6_request.entity_type = (srv6_manager_pb2
                                        .SRv6ExplicitPath)
            # Create a new SRv6 explicit path request
            path_request = srv6_request.srv6_ep_request
            for jpath in data['paths']:
                path = path_request.paths.add()
                # Set destination, device, encapmode
                path.destination = text_type(jpath['destination'])
                path.device = text_type(jpath['device'])
                path.encapmode = text_type(jpath['encapmode'])
                for segment in jpath['segments']:
                    # Create a new segment
                    srv6_segment = path.sr_path.add()
                    srv6_segment.segment = text_type(segment)
                # Remove the SRv6 path
                response = srv6_stub.Remove(srv6_request)
                # Let's close the session
                channel.close()
        # Create the response
        return response.status

    # CRUD SRv6 Local Processing Function

    def create_srv6_local_processing_function(self, server_ip, server_port,
                                              segment, action, device,
                                              localsid_table, nexthop="",
                                              table=-1, interface="",
                                              segments=[]):
        # Get the reference of the stub
        srv6_stub, channel = self.get_grpc_session(server_ip, server_port, self.SECURE)
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = (srv6_manager_pb2
                                    .SRv6LocalProcessingFunction)
        # Create a new SRv6 Lccal Processing Function request
        function_request = srv6_request.srv6_lpf_request
        # Create a new local processing function
        function = function_request.functions.add()
        # Set segment, action, device, locasid table and other params
        function.segment = text_type(segment)
        function.action = text_type(action)
        function.nexthop = text_type(nexthop)
        function.table = int(table)
        function.interface = text_type(interface)
        function.device = text_type(device)
        function.localsid_table = int(localsid_table)
        for segment in segments:
            # Create a new segment
            srv6_segment = function.segs.add()
            srv6_segment.segment = text_type(segment)
        # Create the SRv6 local processing function
        response = srv6_stub.Create(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    def get_srv6_local_processing_function(self, server_ip, server_port, segment,
                                           action, device, localsid_table,
                                           nexthop="", table=-1,
                                           interface="", segments=[]):
        print('Not yet implemented')

    def update_srv6_local_processing_function(self, server_ip, server_port, segment,
                                              action, device, localsid_table,
                                              nexthop="", table=-1,
                                              interface="", segments=[]):
        print('Not yet implemented')

    def remove_srv6_local_processing_function(self, server_ip, server_port, segment,
                                              localsid_table, action="",
                                              nexthop="", table=-1,
                                              interface="", segments=[],
                                              device=""):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = (srv6_manager_pb2
                                    .SRv6LocalProcessingFunction)
        # Create a new SRv6 Lccal Processing Function request
        function_request = srv6_request.srv6_lpf_request
        # Create a new local processing function
        function = function_request.functions.add()
        # Set segment, action, device, locasid table and other params
        function.segment = text_type(segment)
        function.action = text_type(action)
        function.nexthop = text_type(nexthop)
        function.table = int(table)
        function.interface = text_type(interface)
        function.device = text_type(device)
        function.localsid_table = int(localsid_table)
        for segment in segments:
            # Create a new segment
            srv6_segment = function.segs.add()
            srv6_segment.segment = text_type(segment)
        # Remove
        response = srv6_stub.Remove(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    # CRUD VRF Device

    def create_vrf_device(self, server_ip, server_port, name, table, interfaces=[]):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.VRFDevice
        # Create a new VRF device request
        vrf_device_request = srv6_request.vrf_device_request
        # Create a new VRF device
        device = vrf_device_request.devices.add()
        # Set name, table
        device.name = text_type(name)
        device.table = int(table)
        for ifname in interfaces:
            # Create a new interface
            device.interfaces.add(text_type(ifname))
        # Create VRF device
        response = srv6_stub.Create(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    def get_vrf_device(self, server_ip, server_port, name, table, interfaces=[]):
        print('Not yet implemented')

    def update_vrf_device(self, server_ip, server_port, name, table=-1, interfaces=[]):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.VRFDevice
        # Create a new VRF device request
        vrf_device_request = srv6_request.vrf_device_request
        # Create a new VRF device
        device = vrf_device_request.devices.add()
        # Set name, table
        device.name = text_type(name)
        if table != -1:
            device.table = int(table)
        # Create a new interfaces
        device.interfaces.extend(interfaces)
        # Create VRF device
        response = srv6_stub.Update(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    def remove_vrf_device(self, server_ip, server_port, name):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.VRFDevice
        # Create a new VRF device request
        vrf_device_request = srv6_request.vrf_device_request
        # Create a new VRF device
        device = vrf_device_request.devices.add()
        # Set name
        device.name = text_type(name)
        # Remove
        response = srv6_stub.Remove(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    # CRUD Interface

    def create_interface(self, server_ip, server_port, ifindex, name, macaddr,
                         ipaddrs, state, ospf_adv):
        print('Not yet implemented')

    def get_interface(self, server_ip, server_port, interfaces=[]):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.Interface
        # Create a new interface request
        interface_request = srv6_request.interface_request
        # Add interfaces
        for interface in interfaces:
            intf = interface_request.interfaces.add()
            intf.name = text_type(interface)
        # Get interfaces
        response = srv6_stub.Get(srv6_request)
        if response.status == status_codes_pb2.STATUS_SUCCESS:
            # Parse response and retrieve interfaces information
            interfaces = dict()
            for interface in response.interfaces:
                ifindex = int(interface.index)
                ifname = text_type(interface.name)
                macaddr = text_type(interface.macaddr)
                ips = interface.ipaddrs
                ipaddrs = list()
                for ip in ips:
                    ipaddrs.append(text_type(ip))
                state = interface.state
                interfaces[ifindex] = {
                    "ifindex": int(ifindex),
                    "ifname": text_type(ifname),
                    "macaddr": text_type(macaddr),
                    "ipaddr": ipaddrs,
                    "state": text_type(state)
                }
        else:
            interfaces = None
        # Let's close the session
        channel.close()
        return interfaces

    def update_interface(self, server_ip, server_port, ifindex=None, name=None, macaddr=None,
                         ipaddrs=None, state=None, ospf_adv=None):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.Interface
        # Create a new interface request
        interface_request = srv6_request.interface_request
        # Create a new interface
        intf = interface_request.interfaces.add()
        # Set name, MAC address and other params
        if ifindex is not None:
            intf.ifindex = int(ifindex)
        if name is not None:
            intf.name = text_type(name)
        if macaddr is not None:
            intf.macaddr = text_type(macaddr)
        if ipaddrs is not None:
            intf.ipaddrs = ipaddrs
        if state is not None:
            intf.state = text_type(state)
        if ospf_adv is not None:
            intf.ospf_adv = bool(ospf_adv)
        # Create interface
        response = srv6_stub.Update(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    def remove_interface(self, server_ip, server_port, ifindex, name, macaddr,
                         ipaddrs, state, ospf_adv):
        print('Not yet implemented')

    # CRUD IP rule

    def create_iprule(self, server_ip, server_port, family, table=-1,
                      priority=-1, action="", scope=-1,
                      destination="", dst_len=-1, source="",
                      src_len=-1, in_interface="", out_interface=""):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.IPRule
        # Create a new interface request
        rule_request = srv6_request.iprule_request
        # Create a new rule
        rule = rule_request.rules.add()
        # Set family and optional params
        rule.family = int(family)
        rule.table = int(table)
        rule.priority = int(priority)
        rule.action = text_type(action)
        rule.scope = int(scope)
        rule.destination = text_type(destination)
        rule.dst_len = int(dst_len)
        rule.source = text_type(source)
        rule.src_len = int(src_len)
        rule.in_interface = text_type(in_interface)
        rule.out_interface = text_type(out_interface)
        # Create IP rule
        response = srv6_stub.Create(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    def get_iprule(self, server_ip, server_port, family, table=-1,
                   priority=-1, action="", scope=-1,
                   destination="", dst_len=-1, source="",
                   src_len=-1, in_interface="", out_interface=""):
        print('Not yet implemented')

    def update_iprule(self, server_ip, server_port, family, table=-1,
                      priority=-1, action="", scope=-1,
                      destination="", dst_len=-1, source="",
                      src_len=-1, in_interface="", out_interface=""):
        print('Not yet implemented')

    def remove_iprule(self, server_ip, server_port, family, table=-1,
                      priority=-1, action="", scope=-1,
                      destination="", dst_len=-1, source="",
                      src_len=-1, in_interface="", out_interface=""):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.IPRule
        # Create a new interface request
        rule_request = srv6_request.iprule_request
        # Create a new rule
        rule = rule_request.rules.add()
        # Set family and optional params
        rule.family = int(family)
        rule.table = int(table)
        rule.priority = int(priority)
        rule.action = text_type(action)
        rule.scope = int(scope)
        rule.destination = text_type(destination)
        rule.dst_len = int(dst_len)
        rule.source = text_type(source)
        rule.src_len = int(src_len)
        rule.in_interface = text_type(in_interface)
        rule.out_interface = text_type(out_interface)
        # Remove IP rule
        response = srv6_stub.Remove(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    # CRUD IP Route

    def create_iproute(self, server_ip, server_port, family=-1, tos="", type="",
                       table=-1, proto=-1, destination="", dst_len=-1,
                       scope=-1, preferred_source="", src_len=-1,
                       in_interface="", out_interface="", gateway=""):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.IPRoute
        # Create a new interface request
        route_request = srv6_request.iproute_request
        # Create a new route
        route = route_request.routes.add()
        # Set params
        route.family = int(family)
        route.tos = text_type(tos)
        route.type = text_type(type)
        route.table = int(table)
        route.scope = int(scope)
        route.proto = int(proto)
        route.destination = text_type(destination)
        route.dst_len = int(dst_len)
        route.preferred_source = text_type(preferred_source)
        route.src_len = int(src_len)
        route.in_interface = text_type(in_interface)
        route.out_interface = text_type(out_interface)
        route.gateway = text_type(gateway)
        # Create IP Route
        response = srv6_stub.Create(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    def get_iproute(self, server_ip, server_port, family=-1, tos="", type="",
                    table=-1, proto=-1, destination="", dst_len=-1,
                    scope=-1, preferred_source="", src_len=-1,
                    in_interface="", out_interface="", gateway=""):
        print('Not yet implemented')

    def update_iproute(self, server_ip, server_port, family=-1, tos="", type="",
                       table=-1, proto=-1, destination="", dst_len=-1,
                       scope=-1, preferred_source="", src_len=-1,
                       in_interface="", out_interface="", gateway=""):
        print('Not yet implemented')

    def remove_iproute(self, server_ip, server_port, family=-1, tos="", type="",
                       table=-1, proto=-1, destination="", dst_len=-1,
                       scope=-1, preferred_source="", src_len=-1,
                       in_interface="", out_interface="", gateway=""):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.IPRoute
        # Create a new interface request
        route_request = srv6_request.iproute_request
        # Create a new route
        route = route_request.routes.add()
        # Set params
        route.family = int(family)
        route.tos = text_type(tos)
        route.type = text_type(type)
        route.table = int(table)
        route.proto = int(proto)
        route.scope = int(scope)
        route.destination = text_type(destination)
        route.dst_len = int(dst_len)
        route.preferred_source = text_type(preferred_source)
        route.src_len = int(src_len)
        route.in_interface = text_type(in_interface)
        route.out_interface = text_type(out_interface)
        route.gateway = text_type(gateway)
        # Remove IP Route
        response = srv6_stub.Remove(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    # CRUD IP Address

    def create_ipaddr(self, server_ip, server_port,
                      ip_addr, device, net, family=AF_INET):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.IPAddr
        # Create a new interface request
        addr_request = srv6_request.ipaddr_request
        # Create a new route
        addr = addr_request.addrs.add()
        # Set address, device, family
        addr.ip_addr = text_type(ip_addr)
        addr.device = text_type(device)
        addr.family = int(family)
        addr.net = text_type(net)
        # Create IP Address
        response = srv6_stub.Create(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    def get_ipaddr(self, server_ip, server_port,
                   ip_addr, device, net, family=AF_INET):
        print('Not yet implemented')

    def update_ipaddr(self, server_ip, server_port,
                      ip_addr, device, net, family=AF_INET):
        print('Not yet implemented')

    def remove_ipaddr(self, server_ip, server_port, ip_addr, net, device, family=-1):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.IPAddr
        # Create a new interface request
        addr_request = srv6_request.ipaddr_request
        # Create a new route
        addr = addr_request.addrs.add()
        # Set address, device, family
        addr.ip_addr = text_type(ip_addr)
        addr.device = text_type(device)
        addr.family = int(family)
        addr.net = text_type(net)
        # Remove IP Address
        response = srv6_stub.Remove(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status

    def remove_many_ipaddr(self, server_ip, server_port, addrs, nets,
                           device, family=-1):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        srv6_request = srv6_manager_pb2.SRv6ManagerRequest()
        # Set the type of the carried entity
        srv6_request.entity_type = srv6_manager_pb2.IPAddr
        # Create a new interface request
        addr_request = srv6_request.ipaddr_request
        for (ip_addr, net) in zip(addrs, nets):
            # Create a new route
            addr = addr_request.addrs.add()
            # Set address, device, family
            addr.ip_addr = text_type(ip_addr)
            addr.device = text_type(device)
            addr.family = int(family)
            addr.net = text_type(net)
        # Remove IP Address
        response = srv6_stub.Remove(srv6_request)
        # Let's close the session
        channel.close()
        # Create the response
        return response.status


class NetworkEventsListener:

    def __init__(self, secure=DEFAULT_SECURE, certificate=DEFAULT_CERTIFICATE):
        self.SECURE = secure
        if secure is True:
            if certificate is None:
                print('Error: "certificate" variable cannot be None '
                      'in secure mode')
                sys.exit(-2)
            self.CERTIFICATE = certificate

    # Build a grpc stub
    def get_grpc_session(self, ip_address, port, secure):
        # If secure we need to establish a channel with the secure endpoint
        if secure:
            # Open the certificate file
            with open(self.CERTIFICATE) as f:
                certificate = f.read()
            # Then create the SSL credentials and establish the channel
            grpc_client_credentials = grpc.ssl_channel_credentials(certificate)
            channel = grpc.secure_channel("ipv6:[%s]:%s" % (ip_address, port),
                                          grpc_client_credentials)
        else:
            channel = grpc.insecure_channel("ipv6:[%s]:%s"
                                            % (ip_address, port))
        return (network_events_listener_pb2_grpc
                .NetworkEventsListenerStub(channel), channel)

    def listen(self, server_ip, server_port):
        # Get the reference of the stub
        srv6_stub, channel = (self
                              .get_grpc_session(server_ip, server_port, self.SECURE))
        # Create message request
        request = empty_req_pb2.EmptyRequest()
        # Listen for Netlink notifications
        for event in srv6_stub.Listen(request):
            # Parse the event
            _event = dict()
            if event.type == EVENT_TYPES['CONNECTION_ESTABLISHED']:
                # Connection established event
                _event['type'] = text_type('CONNECTION_ESTABLISHED')
            elif event.type == EVENT_TYPES['INTF_UP']:
                # Interface UP event
                _event['interface'] = dict()
                _event['type'] = 'INTF_UP'
                # Extract interface index
                _event['interface']['index'] = int(event.interface.index)
                # Extract interface name
                _event['interface']['name'] = text_type(event.interface.name)
                # Extract interface MAC address
                _event['interface']['macaddr'] = text_type(event.interface.macaddr)
            elif event.type == EVENT_TYPES['INTF_DOWN']:
                # Interface DOWN event
                _event['interface'] = dict()
                _event['type'] = 'INTF_DOWN'
                # Extract interface index
                _event['interface']['index'] = int(event.interface.index)
                # Extract interface name
                _event['interface']['name'] = text_type(event.interface.name)
                # Extract interface MAC address
                _event['interface']['macaddr'] = text_type(event.interface.macaddr)
            elif event.type == EVENT_TYPES['INTF_DEL']:
                # Interface DEL event
                _event['interface'] = dict()
                _event['type'] = 'INTF_DEL'
                # Extract interface index
                _event['interface']['index'] = int(event.interface.index)
            elif event.type == EVENT_TYPES['NEW_ADDR']:
                # NEW address event
                _event['interface'] = dict()
                _event['type'] = 'NEW_ADDR'
                # Extract interface index
                _event['interface']['index'] = int(event.interface.index)
                # Extract address
                _event['interface']['ipaddr'] = text_type(event.interface.ipaddr)
            elif event.type == EVENT_TYPES['DEL_ADDR']:
                # DEL address event
                _event['interface'] = dict()
                _event['type'] = 'DEL_ADDR'
                # Extract interface index
                _event['interface']['index'] = int(event.interface.index)
                # Extract address
                _event['interface']['ipaddr'] = text_type(event.interface.ipaddr)
            # Pass the event to the caller
            yield _event
        # Let's close the session
        channel.close()


# Test features
if __name__ == "__main__":
    # Test Netlink messages
    net_events_listener = NetworkEventsListener()
    # Create a thread for each router and subscribe netlink notifications
    routers = ["2000::1", "2000::2", "2000::3"]
    thread_pool = []
    for router in routers:
        thread = Thread(target=net_events_listener.listen,
                        args=(router, ))
        thread.start()
        thread_pool.append(thread)
    for thread in thread_pool:
        thread.join()