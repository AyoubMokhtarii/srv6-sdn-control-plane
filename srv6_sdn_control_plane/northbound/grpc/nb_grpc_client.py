#!/usr/bin/python

# Copyright (C) 2018 Carmine Scarpitta, Pier Luigi Ventre, Stefano Salsano -
# (CNIT and University of Rome "Tor Vergata")
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Client of a Northbound interface based on gRPC protocol
#
# @author Carmine Scarpitta <carmine.scarpitta.94@gmail.com>
# @author Pier Luigi Ventre <pier.luigi.ventre@uniroma2.it>
# @author Stefano Salsano <stefano.salsano@uniroma2.it>
#

from __future__ import absolute_import, division, print_function

# General imports
from six import text_type
import grpc
import sys
from socket import AF_INET, AF_INET6
import logging

from srv6_sdn_control_plane import srv6_controller_utils

from srv6_sdn_control_plane.srv6_controller_utils import(
    InterfaceType
)

import json
from google.protobuf.json_format import MessageToDict
from google.protobuf.json_format import MessageToJson


# Add path of proto files
# sys.path.append(srv6_controller_utils.PROTO_FOLDER)

# SRv6 dependencies
from srv6_sdn_proto import srv6_vpn_pb2_grpc
from srv6_sdn_proto import srv6_vpn_pb2
from srv6_sdn_proto.status_codes_pb2 import NbStatusCode

# The IP address and port of the gRPC server started on the SDN controller
DEFAULT_GRPC_SERVER_IP = '11.3.192.117'
DEFAULT_GRPC_SERVER_PORT = 54321
# Define wheter to use SSL or not
DEFAULT_SECURE = False
# SSL cerificate for server validation
DEFAULT_CERTIFICATE = 'cert_client.pem'

# Enable STAMP support
ENABLE_STAMP_SUPPORT = True

if ENABLE_STAMP_SUPPORT:
    from srv6_delay_measurement import nb_controller_api
    # from srv6_delay_measurement.nb_controller_api import STAMPError


# ENCAP = {
#    'SRv6': srv6_vpn_pb2.SRv6,
#    'IPsec_ESP_GRE': srv6_vpn_pb2.IPsec_ESP_GRE,
#    'SRv6_IPsec_ESP_GRE': srv6_vpn_pb2.SRv6_IPsec_ESP_GRE,
#    'SRv6_IPsec_ESP_IP': srv6_vpn_pb2.SRv6_IPsec_ESP_IP
# }


# Parser for gRPC errors
def parse_grpc_error(e, ip, port):
    status_code = e.code()
    details = e.details()
    logging.error('gRPC client reported an error: %s, %s'
                  % (status_code, details))
    if grpc.StatusCode.UNAVAILABLE == status_code:
        code = NbStatusCode.STATUS_SERVICE_UNAVAILABLE
        reason = ('Unable to contact controller - gRPC server is '
                  'unreachable (ip %s, port %s)' % (ip, port))
    elif grpc.StatusCode.UNAUTHENTICATED == status_code:
        code = NbStatusCode.STATUS_UNAUTHORIZED
        reason = details
    else:
        code = NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        reason = details
    # Return an error message
    return code, reason


class NorthboundInterface:

    def __init__(self, server_ip=DEFAULT_GRPC_SERVER_IP,
                 server_port=DEFAULT_GRPC_SERVER_PORT,
                 secure=DEFAULT_SECURE, certificate=DEFAULT_CERTIFICATE):
        self.server_ip = server_ip
        self.server_port = server_port
        self.SECURE = secure
        if secure is True:
            if certificate is None:
                logging.error('Error: "certificate" variable cannot be None '
                              'in secure mode')
                sys.exit(-2)
            self.certificate = certificate
        if ENABLE_STAMP_SUPPORT:
            self.stamp_nb_interface = nb_controller_api.NorthboundInterface(
                server_ip=server_ip,
                server_port=server_port,
                secure=secure,
                certificate=certificate
            )

    # Build a grpc stub 
    def get_grpc_session(self, ip_address, port, secure):
        addr_family = srv6_controller_utils.getAddressFamily(ip_address)
        if addr_family == AF_INET6:
            ip_address = "ipv6:[%s]:%s" % (ip_address, port)
        elif addr_family == AF_INET:
            ip_address = "ipv4:%s:%s" % (ip_address, port)
        else:
            # Address is a hostname
            ip_address = "%s:%s" % (ip_address, port)
        # If secure we need to establish a channel with the secure endpoint
        if secure:
            # Open the certificate file
            with open(self.certificate, 'rb') as f:
                certificate = f.read()
            # Then create the SSL credentials and establish the channel
            grpc_client_credentials = grpc.ssl_channel_credentials(certificate)
            channel = grpc.secure_channel(ip_address,
                                          grpc_client_credentials)
        else:
            channel = grpc.insecure_channel(ip_address)
        return srv6_vpn_pb2_grpc.NorthboundInterfaceStub(channel), channel

    def configure_tenant(self, tenantid, tenant_info='', vxlan_port=-1):
        # Create request
        request = srv6_vpn_pb2.Tenant()
        request.tenantid = tenantid
        request.tenant_info = tenant_info
        request.config.vxlan_port = vxlan_port
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Configure the tenant
            response = srv6_vpn_stub.ConfigureTenant(request)
            # Create the response
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def remove_tenant(self, tenantid):
        # Create request
        request = srv6_vpn_pb2.RemoveTenantRequest()
        request.tenantid = tenantid
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Remove tenant
            response = srv6_vpn_stub.RemoveTenant(request)
            # Return
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def enable_device(self, deviceid, tenantid):
        # Create the request
        request = srv6_vpn_pb2.EnableDeviceRequest()
        device = request.devices.add()
        device.id = deviceid
        device.tenantid = tenantid
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Configure the devices
            response = srv6_vpn_stub.EnableDevice(request)
            # Return
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def disable_device(self, deviceid, tenantid):
        # Create the request
        request = srv6_vpn_pb2.DisableDeviceRequest()
        device = request.devices.add()
        device.id = deviceid
        device.tenantid = tenantid
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Configure the devices
            response = srv6_vpn_stub.DisableDevice(request)
            # Return
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def configure_device(self, device_id, tenantid, device_name='',
                         device_description='', interfaces=[]):



        #FIXE removethis logging
        #============================================
        logging.info("\n\n\n\n&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
        logging.info("device_id")
        logging.info(device_id)
        logging.info("tenantid")
        logging.info(tenantid)
        logging.info("device_name")
        logging.info(device_name)
        logging.info("device_description")
        logging.info(device_description)
        logging.info("interfaces")
        logging.info(interfaces)
        logging.info("\n\n\n\n&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")

        #============================================


        # Create the request
        request = srv6_vpn_pb2.ConfigureDeviceRequest()         
        device = request.configuration.devices.add()
        device.id = device_id
        device.name = device_name
        device.description = device_description
        device.tenantid = tenantid
        for _interface in interfaces:
            interface = device.interfaces.add()
            interface.name = _interface['name']
            if 'ipv4_addrs' in _interface:
                for ip_addr in _interface['ipv4_addrs']:
                    addr = ip_addr
                    if not srv6_controller_utils.validate_ipv4_address(addr):
                        logging.error('Provided an invalid address: %s' % addr)
                        return None
                    interface.ipv4_addrs.append(ip_addr)
            if 'ipv4_subnets' in _interface:
                for _subnet in _interface['ipv4_subnets']:
                    if not srv6_controller_utils.validate_ipv4_address(
                            _subnet['subnet']):
                        logging.error(
                            'Provided an invalid subnet: %s' % _subnet)
                        return None
                    subnet = interface.ipv4_subnets.add()
                    subnet.subnet = _subnet['subnet']
                    if 'gateway' in _subnet:
                        subnet.gateway = _subnet['gateway']
            if 'ipv6_addrs' in _interface:
                for ip_addr in _interface['ipv6_addrs']:
                    addr = ip_addr
                    if not srv6_controller_utils.validate_ipv6_address(addr):
                        logging.error('Provided an invalid address: %s' % addr)
                        return None
                    interface.ipv6_addrs.append(ip_addr)
            if 'ipv6_subnets' in _interface:
                for _subnet in _interface['ipv6_subnets']:
                    if not srv6_controller_utils.validate_ipv6_address(
                            _subnet['subnet']):
                        logging.error(
                            'Provided an invalid subnet: %s' % _subnet)
                        return None
                    subnet = interface.ipv6_subnets.add()
                    subnet.subnet = _subnet['subnet']
                    if 'gateway' in _subnet:
                        subnet.gateway = _subnet['gateway']
            if 'type' in _interface:
                interface.type = _interface['type']
                interface.underlay_wan_id = ""
                if (_interface['type'] == InterfaceType.WAN):
                    interface.underlay_wan_id = _interface['underlay_wan_id']
                    # # FIXME remove this just logging-------------------------------------------------
                    # print(" ++++++++++++++++ WAN interface : " )
                    # print(interface)
                    # # print(interface)
                    # #-------------------------------------------------
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Configure the devices
            response = srv6_vpn_stub.ConfigureDevice(request)
            # Return
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def get_devices_jsonf(self, devices=[], tenantid=''):
        # Create the request
        request = srv6_vpn_pb2.InventoryServiceRequest()
        request.deviceids.extend(devices)
        request.tenantid = tenantid
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Get devices
            response = srv6_vpn_stub.GetDevices(request)
            if response.status.code == NbStatusCode.STATUS_OK:
                # Parse response and retrieve devices information
                devices = []
                for device in response.device_information.devices:
                    # device_dict = MessageToDict(device)
                    device_json = MessageToJson(device)
                    devices.append(device_json)
            else:
                devices = None
            # Return
            response = response.status.code, response.status.reason, devices
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
            response = response[0], response[1], None
        finally:
            # Let's close the session
            channel.close()
        # Return the response
        return response




    def get_devices(self, devices=[], tenantid=''):
        # Create the request
        request = srv6_vpn_pb2.InventoryServiceRequest()
        request.deviceids.extend(devices)
        request.tenantid = tenantid
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Get devices
            response = srv6_vpn_stub.GetDevices(request)
            if response.status.code == NbStatusCode.STATUS_OK:
                # Parse response and retrieve devices information
                devices = list()
                for device in response.device_information.devices:
                    device_id = None
                    mgmtip = None
                    device_name = None
                    device_description = None
                    device_connected = None
                    device_configured = None
                    device_enabled = None
                    loopbackip = 'None'       # TODO?
                    loopbacknet = 'None'      # TODO?
                    managementip = 'None'     # TODO?
                    interfaces = None
                    if device.id is not None:
                        device_id = text_type(device.id)
                    if device.mgmtip is not None:
                        mgmtip = text_type(device.mgmtip)
                    if device.name is not None:
                        device_name = text_type(device.name)
                    if device.description is not None:
                        device_description = text_type(device.description)
                    if device.connected is not None:
                        device_connected = text_type(device.connected)
                    if device.configured is not None:
                        device_configured = text_type(device.configured)
                    if device.enabled is not None:
                        device_enabled = text_type(device.enabled)
                    '''
                    if device.loopbackip is not None:
                        loopbackip = text_type(device.loopbackip)
                    if device.loopbacknet is not None:
                        loopbacknet = text_type(device.loopbacknet)
                    if device.managementip is not None:
                        managementip = text_type(device.managementip)
                    if device.interfaces is not None:
                        interfaces = list()
                        for intf in device.interfaces:
                            ipaddrs = list()
                            for ipaddr in intf.ipaddrs:
                                ipaddrs.append(ipaddr)
                            interfaces.append({
                                'ifindex': text_type(intf.index),
                                'ifname': text_type(intf.name),
                                'macaddr': text_type(intf.macaddr),
                                'ipaddrs': intf.ipaddrs,
                                'state': text_type(intf.state),
                            })
                    '''
                    interfaces = list()
                    if device.interfaces is not None:
                        for intf in device.interfaces:
                            ifname = intf.name
                            type = intf.type
                            mac_addr = intf.mac_addr
                            underlay_wan_id = intf.underlay_wan_id

                            ipv4_addrs=list()
                            if intf.ipv4_addrs is not None :
                                for ipv4_a in intf.ipv4_addrs:
                                    ipv4_addrs.append(text_type(ipv4_a))

                            ipv6_addrs=list()
                            if intf.ipv6_addrs is not None :
                                for ipv6_a in intf.ipv6_addrs:
                                    ipv6_addrs.append(text_type(ipv6_a))
                            
                            ipv4_subnets=list()
                            if intf.ipv4_subnets is not None : 
                                for ipv4_s in intf.ipv4_subnets:
                                    _subnet_ = ipv4_s.subnet
                                    _gateway_ = ipv4_s.gateway
                                    ipv4_subnets.append({
                                        'subnet': text_type(_subnet_),
                                        'gateway': text_type(_gateway_),
                                    })

                            ipv6_subnets=list()
                            if intf.ipv6_subnets is not None:
                                for ipv6_s in intf.ipv6_subnets:
                                    _subnet_ = ipv6_s.subnet
                                    _gateway_ = ipv6_s.gateway
                                    ipv6_subnets.append({
                                        'subnet': text_type(_subnet_),
                                        'gateway': text_type(_gateway_),
                                    })

                            ext_ipv4_addrs=list()
                            if intf.ext_ipv4_addrs is not None :
                                for ext_ipv4_a in intf.ext_ipv4_addrs:
                                    ext_ipv4_addrs.append(text_type(ext_ipv4_a))

                            ext_ipv6_addrs=list()
                            if intf.ext_ipv6_addrs is not None :
                                for ext_ipv6_a in intf.ext_ipv6_addrs:
                                    ext_ipv6_addrs.append(text_type(ext_ipv6_a))
       
                            intf__data = {
                                'name': text_type(ifname),
                                'mac_addr': text_type(mac_addr),
                                'ipv4_addrs': ipv4_addrs,
                                'ipv6_addrs': ipv6_addrs,
                                'ext_ipv4_addrs': ext_ipv4_addrs,
                                'ext_ipv6_addrs': ext_ipv6_addrs,
                                'ipv4_subnets': ipv4_subnets,
                                'ipv6_subnets': ipv6_subnets,
                                'type': text_type(type),
                            }

                            if underlay_wan_id is not None and  underlay_wan_id != "" :
                                intf__data['underlay_wan_id'] = text_type(underlay_wan_id)

                       
                            interfaces.append(intf__data)


                    devices.append({
                        'device_id': text_type(device_id),
                        'name': text_type(device_name),
                        'description': text_type(device_description),
                        'mgmtip': text_type(mgmtip),
                        'connected': device_connected,
                        'configured': device_configured,
                        'enabled': device_enabled,
                        'interfaces': interfaces,
                        'loopbackip': text_type(loopbackip),
                        'loopbacknet': text_type(loopbacknet),
                        'managementip': text_type(managementip),
                    })
            else:
                devices = None

            
            # Return
            response = response.status.code, response.status.reason, devices
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
            response = response[0], response[1], None
        # Let's close the session
        channel.close()
        # Return the response
        return response


    def create_application_identifier(self, device_name, tenantid, application_name='', description='', category='', service_class='', importance='', pathss={}, rules={}, match={}):

        # TODO should improve error handling and parameters validation

        # Create request
        request = srv6_vpn_pb2.ApplicationIdentifier()
        request.device_name = device_name
        request.tenantid = tenantid
        request.application_name = application_name
        request.description = description
        request.category = category
        request.service_class = service_class
        request.importance = importance
      

        # paths = list()
        # for path in pathss:
        #     paths.append(str(path))
        path_mode = pathss['mode']
        request.paths.mode = path_mode

        # logging.info('path_mode: {}'.format(path_mode))
        # 11/0

        if path_mode == 'static':
            paths= list()
            paths = pathss['overlay_paths']
            if len(paths)>= 2:
                logging.error("Multiple paths not implemented in this version.")
                raise NotImplementedError
            request.paths.paths.extend(paths)

        elif path_mode == 'dynamic':
            # request.paths.policy = pathss['policy']
            # request.paths.delay_threshold = pathss['delay_threshold']
            logging.error("dynamic paths not implemented in this version.")
            raise NotImplementedError

        else:
            err = 'Invalid path mode: {}'.format(path_mode)
            response = parse_grpc_error(err, self.server_ip, self.server_port)
            return response
        



        
        request.rules.source_ip = rules['source_ip']


        request.rules.destination_ip = rules['destination_ip']
        request.rules.protocol = rules['protocol']
        request.rules.source_port = rules['source_port']
        request.rules.destination_port = rules['destination_port']
        

        if match is not None and match != {}:
            request.matches.match_name = str(match['match_name'])

            for attribute in match['match_attributes']:
                match_att = request.matches.match_attributes.add()
                match_att.attribute_name = str(attribute['attribute_name'])
                match_att.attribute_value = str(attribute['attribute_value'])


        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Configure the tenant
            response = srv6_vpn_stub.CreateAppIdentifier(request)
            # Create the response
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response


    def get_applications_identifiers(self, apps_identif_ids=[], tenantid=''):
        apps_identifs = None
        request = srv6_vpn_pb2.GetAppsIdentifiersRequest()
        request.tenantid = tenantid
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)

            response = srv6_vpn_stub.GetAppsIdentifiers(request)
            if not response.status.code == NbStatusCode.STATUS_OK:
                apps_identifs = None
                response = response.status.code, response.status.reason, apps_identifs
                return response

            apps_identifs = []
            for app_identifier in response.applications_identifiers:
                paths={
                        "paths_mode": str(app_identifier.paths.mode),
                        "paths": [
                            str(p) for p in app_identifier.paths.paths
                        ],
                        "policy": str(app_identifier.paths.policy),
                        "delay_threshold": float(app_identifier.paths.delay_threshold)
                    }

                rules={
                            "source_ip": str(app_identifier.rules.source_ip),
                            "destination_ip": str(app_identifier.rules.destination_ip),
                            "protocol": str(app_identifier.rules.protocol),
                            "source_port": str(app_identifier.rules.source_port),
                            "destination_port": str(app_identifier.rules.destination_port)
                        }

                matches={
                    "match_name": app_identifier.matches.match_name,
                    "match_attributes": [
                        {
                            "attribute_name": match_att.attribute_name,
                            "attribute_value": match_att.attribute_value
                        }
                        for match_att in app_identifier.matches.match_attributes
                    ]
                }

        

                app_identif_info = {
                    "device_name": str(app_identifier.device_name),
                    "tenantid": str(app_identifier.tenantid),
                    "id": str(app_identifier.app_identifier_id),
                    "application_name": str(app_identifier.application_name),
                    "description": str(app_identifier.description),
                    "category": str(app_identifier.category),
                    "service_class": str(app_identifier.service_class),
                    "importance": str(app_identifier.importance),
                    "overlay_paths": paths,
                    "rules":rules,
                    
                    "matches": matches
                }
                apps_identifs.append(app_identif_info)

            
            
            response = response.status.code, response.status.reason, apps_identifs
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
            response = response[0], response[1], None

        channel.close()
        return response

    def remove_application_identifier(self, app_identif_id='', tenantid=''):
        # Create the request
        request = srv6_vpn_pb2.RemoveAppsIdentifiersRequest()

        # TODO : add validation and verifications.

        request.tenantid = tenantid
        request.apps_identifiers_id = app_identif_id

        try:
            # Get the reference of the stub
            srv6_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            
            response = srv6_stub.RemoveAppsIdentifiers(request)

            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)


        channel.close()
        return response



    def get_tunnels_traffic_statistics(self, device_name, tenantid):

        request = srv6_vpn_pb2.DeviceTunnelsTrafficStatsRequest()
        request.tenantid = tenantid
        request.device_name = device_name

        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Configure the tenant
            response = srv6_vpn_stub.GetTunnelsTrafficStatistics(request)
            # Create the response
            response = response.status.code, response.status.reason

        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response


    def start_delay_monitor(self):
        # Create request
        request = srv6_vpn_pb2.StartDelayMonitorRequest()

        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            
            response = srv6_vpn_stub.StartDelayMonitor(request)
            # Create the response
            response = response.status.code, response.status.reason

        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response
        

    def stop_delay_monitor(self):
        # Create request
        request = srv6_vpn_pb2.StopDelayMonitorRequest()

        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            
            response = srv6_vpn_stub.StopDelayMonitor(request)
            # Create the response
            response = response.status.code, response.status.reason

        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        
        # Let's close the session
        channel.close()
        # Return the response
        return response
    

    def start_traffic_adaptation(self):
        # Create request
        request = srv6_vpn_pb2.StartTrafficAdaptationRequest()

        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            
            response = srv6_vpn_stub.StartTrafficAdaptation(request)
            # Create the response
            response = response.status.code, response.status.reason

        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    
    def stop_traffic_adaptation(self):
        # Create request
        request = srv6_vpn_pb2.StopTrafficAdaptationRequest()

        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            
            response = srv6_vpn_stub.StopTrafficAdaptation(request)
            # Create the response
            response = response.status.code, response.status.reason

        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        
        # Let's close the session
        channel.close()
        # Return the response
        return response


    def get_topology_information(self):
        # Create the request
        request = srv6_vpn_pb2.InventoryServiceRequest()
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Get topology
            response = srv6_vpn_stub.GetTopologyInformation(request)
            if response.status.code == NbStatusCode.STATUS_OK:
                # Parse response and retrieve topology information
                topology = dict()
                topology['routers'] = list()
                topology['links'] = list()
                for router in response.topology_information.routers:
                    topology['routers'].append(text_type(router))
                for link in response.topology_information.links:
                    topology['links'].append(
                        (text_type(link.l_router), text_type(link.r_router)))
            else:
                topology = None
            # Create the response
            response = response.status.code, response.status.reason, topology
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
            response = response[0], response[1], None
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def get_overlays(self, overlayids=[], tenantid=''):
        # Create the request
        request = srv6_vpn_pb2.InventoryServiceRequest()
        request.overlayids.extend(overlayids)
        request.tenantid = tenantid
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Get overlays
            response = srv6_vpn_stub.GetOverlays(request)
            if response.status.code == NbStatusCode.STATUS_OK:
                # Parse response and retrieve tunnel information
                tunnels = list()
                for tunnel in response.overlays:
                    overlayid = tunnel.overlayid
                    name = tunnel.overlay_name
                    type = tunnel.overlay_type
                    tunnel_mode = tunnel.tunnel_mode
                    tenantid = tunnel.tenantid
                    underlay_wan_id = tunnel.underlay_wan_id

                    tunnel_interfaces = list()
                    for interface in tunnel.slices:
                        deviceid = None
                        interface_name = None
                        device_name = None
                        
                        if interface.deviceid is not None:
                            deviceid = text_type(interface.deviceid)

                        if interface.interface_name is not None:
                            interface_name = text_type(interface.interface_name)
                        
                        if interface.device_name is not None:
                            device_name = text_type(interface.device_name)
                        
                        tunnel_interfaces.append({
                            'device_name' : device_name,
                            'deviceid': deviceid,
                            'interface_name': interface_name

                        })
                    tunnels.append({
                        'id': overlayid,
                        'name': name,
                        'type': type,
                        'underlay_wan_id' : underlay_wan_id,
                        'mode': tunnel_mode,
                        'tenantid': tenantid,
                        'interfaces': tunnel_interfaces  
                    })
            else:
                tunnels = None
            # Create the response
            response = response.status.code, response.status.reason, tunnels
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
            response = response[0], response[1], None
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def create_overlay(self, name, type, interfaces, tenantid, tunnel_mode):
        # Create the request
        request = srv6_vpn_pb2.OverlayServiceRequest()
        intent = request.intents.add()
        intent.overlay_name = text_type(name)
        intent.overlay_type = type
        intent.tenantid = tenantid
        intent.tunnel_mode = tunnel_mode
        for intf in interfaces:
            interface = intent.slices.add()
            interface.deviceid = text_type(intf[0])
            interface.interface_name = text_type(intf[1])
            interface.underlay_wan_id = text_type(intf[2])

        try:
            # Get the reference of the stub
            srv6_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Create the VPN
            response = srv6_stub.CreateOverlay(request)
            # Return
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def remove_overlay(self, overlayid, tenantid):
        # Create the request
        request = srv6_vpn_pb2.OverlayServiceRequest()
        intent = request.intents.add()
        intent.overlayid = text_type(overlayid)
        intent.tenantid = tenantid
        try:
            # Get the reference of the stub
            srv6_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Remove the VPN
            response = srv6_stub.RemoveOverlay(request)
            # Return
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def assign_slice_to_overlay(self, overlayid, tenantid, interfaces):
        # Create the request
        request = srv6_vpn_pb2.OverlayServiceRequest()
        intent = request.intents.add()
        intent.overlayid = text_type(overlayid)
        intent.tenantid = tenantid
        for intf in interfaces:
            interface = intent.slices.add()
            interface.deviceid = text_type(intf[0])
            interface.interface_name = text_type(intf[1])
        try:
            # Get the reference of the stub
            srv6_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Add the interface to the VPN
            response = srv6_stub.AssignSliceToOverlay(request)
            # Return
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def remove_slice_from_overlay(self, overlayid, tenantid, interfaces):
        # Create the request
        request = srv6_vpn_pb2.OverlayServiceRequest()
        intent = request.intents.add()
        intent.overlayid = text_type(overlayid)
        intent.tenantid = tenantid
        for intf in interfaces:
            interface = intent.slices.add()
            interface.deviceid = text_type(intf[0])
            interface.interface_name = text_type(intf[1])
        try:
            # Get the reference of the stub
            srv6_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Remove the interface from the VPN
            response = srv6_stub.RemoveSliceFromOverlay(request)
            # Return
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def print_overlays(self, overlayids=[], tenantid=""):
        # Get overlays
        status_code, reason, overlays = self.get_overlays(
            overlayids=[], tenantid="")
        # Print all overlays
        if status_code == NbStatusCode.STATUS_OK:
            print
            i = 1
            if len(overlays) == 0:
                print("No overlay in the network")
                print()
            for overlay in overlays:
                print("****** Overlay %s ******" % i)
                print("Overlay ID:", overlay['id'])
                print("Name:", overlay['name'])
                print("Tenant ID:", overlay["tenantid"])
                print("Interfaces:")
                for intf in overlay["interfaces"]:
                    print(intf['deviceid'], intf['interface_name'])
                print()
                i += 1
        else:
            logging.error('Error while retrieving the overlays list')

    def unregister_device(self, deviceid, tenantid):
        # Create the request
        request = srv6_vpn_pb2.UnregisterDeviceRequest()
        request.tenantid = tenantid
        request.deviceid = deviceid
        try:
            # Get the reference of the stub
            srv6_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Unregister the device
            response = srv6_stub.UnregisterDevice(request)
            # Return
            response = response.status.code, response.status.reason
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def get_sid_lists(self, ingress_deviceid, egress_deviceid, tenantid):
        # Create the request
        request = srv6_vpn_pb2.GetSIDListsRequest()
        request.ingress_deviceid = ingress_deviceid
        request.egress_deviceid = egress_deviceid
        request.tenantid = tenantid
        try:
            # Get the reference of the stub
            srv6_vpn_stub, channel = self.get_grpc_session(
                self.server_ip, self.server_port, self.SECURE)
            # Get SID lists between the edge devices
            response = srv6_vpn_stub.GetSIDLists(request)
            if response.status.code == NbStatusCode.STATUS_OK:
                # Parse response and retrieve SID list information
                sid_lists = list()
                for sid_list in response.sid_lists:
                    sid_lists.append({
                        'overlayid': sid_list.overlayid,
                        'overlay_name': sid_list.overlay_name,
                        'direct_sid_list': list(sid_list.direct_sid_list),
                        'return_sid_list': list(sid_list.return_sid_list),
                        'tenantid': sid_list.tenantid
                    })
            else:
                sid_lists = None
            # Create the response
            response = response.status.code, response.status.reason, sid_lists
        except grpc.RpcError as e:
            response = parse_grpc_error(e, self.server_ip, self.server_port)
            response = response[0], response[1], None
        # Let's close the session
        channel.close()
        # Return the response
        return response

    def register_stamp_sender(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.register_stamp_sender(*args, **kwargs)

    def register_stamp_reflector(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.register_stamp_reflector(
            *args, **kwargs
        )

    def unregister_stamp_node(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.unregister_stamp_node(*args, **kwargs)

    def init_stamp_node(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.init_stamp_node(*args, **kwargs)

    def reset_stamp_node(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.reset_stamp_node(*args, **kwargs)

    def create_stamp_session(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.create_stamp_session(*args, **kwargs)

    def start_stamp_session(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.start_stamp_session(*args, **kwargs)

    def stop_stamp_session(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.stop_stamp_session(*args, **kwargs)

    def destroy_stamp_session(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.destroy_stamp_session(*args, **kwargs)

    def get_stamp_results(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.get_stamp_results(*args, **kwargs)

    def get_stamp_sessions(self, *args, **kwargs):
        if self.stamp_nb_interface is None:
            raise NotImplementedError("STAMP Support not enabled")
        return self.stamp_nb_interface.get_stamp_sessions(*args, **kwargs)


if __name__ == '__main__':
    '''# Test IPv6-VPN APIs
    srv6_vpn_manager = SRv6VPNManager()

    # Controller address and port
    controller_addr = '::'
    controller_port = 54321

    # Create VPN 10-research
    name = 'research'
    # Create interfaces
    # First interface
    if1 = Interface('fcff:0:1::1', 'ads1-eth3', 'fd00:0:1:1::1',
                    'fd00:0:1:1::/48')
    # Second interface
    if2 = Interface('fcff:0:2::1', 'ads2-eth3', 'fd00:0:1:3::1',
                    'fd00:0:1:3::/48')
    # List of interfaces
    interfaces = [
        if1,
        if2
    ]
    # Tenant ID
    tenantid = 10
    # Send creation command through the northbound API
    srv6_vpn_manager.create_vpn(controller_addr, controller_port,
                                name, VPNType.IPv6VPN, interfaces,
                                tenantid)
    # Remove all addresses in the hosts
    srv6_controller_utils.flush_ipv6_addresses_ssh('2000::4', 'hads11-eth1')
    srv6_controller_utils.flush_ipv6_addresses_ssh('2000::6', 'hads21-eth1')
    # Add the private addresses to the interfaces in the hosts
    srv6_controller_utils.add_ipv6_address_ssh('2000::4', 'hads11-eth1',
                                       'fd00:0:1:1::2/48')
    srv6_controller_utils.add_ipv6_address_ssh('2000::6', 'hads21-eth1',
                                       'fd00:0:1:3::2/48')

    # Add interface to the VPN
    name = 'research'
    # Create the interface
    if1 = Interface('fcff:0:1::1', 'ads1-eth4', 'fd00:0:1:2::1',
                    'fd00:0:1:2::/48')
    tenantid = 10
    srv6_vpn_manager.assign_interface_to_vpn(controller_addr,
                                             controller_port,
                                             name, tenantid, if1)
    # Remove all addresses in the hosts
    srv6_controller_utils.flush_ipv6_addresses_ssh('2000::5', 'hads12-eth1')
    # Add the public addresses to the interfaces in the hosts
    srv6_controller_utils.add_ipv6_address_ssh('2000::5', 'hads12-eth1',
                                       'fd00:0:1:2::2')

    # Remove interface from the VPN
    name = 'research'
    # Create the interface
    if1 = Interface('fcff:0:1::1', 'ads1-eth4')
    # Tenant ID
    tenantid = 10
    # Run remove interface command
    srv6_vpn_manager.remove_interface_from_vpn(controller_addr,
                                               controller_port, name,
                                               tenantid, if1)
    # Add the public prefixes to the interfaces in the routers
    srv6_controller_utils.add_ipv6_nd_prefix_quagga('2000::1', 'ads1-eth4',
                                            'fd00:0:1:3:2::/64')
    # Add the public addresses to the interfaces in the routers
    srv6_controller_utils.add_ipv6_address_quagga('2000::1', 'ads1-eth4',
                                          'fd00:0:1:3:2::1')
    # Remove all addresses in the hosts
    srv6_controller_utils.flush_ipv6_addresses_ssh('2000::5',
                                           'hads12-eth1')
    # Add the public addresses to the interfaces in the hosts
    srv6_controller_utils.add_ipv6_address_ssh('2000::5', 'hads12-eth1',
                                       'fd00:0:1:3:2::2')

    # Remove VPN 10-research
    srv6_vpn_manager.remove_vpn(controller_addr,
                                controller_port, 'research', 10)
    # Add the public prefixes addresses to the interfaces in the routers
    srv6_controller_utils.add_ipv6_nd_prefix_quagga('2000::1', 'ads1-eth3',
                                            'fd00:0:1:3:1::/64')
    srv6_controller_utils.add_ipv6_nd_prefix_quagga('2000::2', 'ads2-eth3',
                                            'fd00:0:2:3:1::/64')
    # Add the public addresses to the interfaces in the routers
    srv6_controller_utils.add_ipv6_address_quagga('2000::1', 'ads1-eth3',
                                          'fd00:0:1:3:1::1')
    srv6_controller_utils.add_ipv6_address_quagga('2000::2', 'ads2-eth3',
                                          'fd00:0:2:3:1::1')
    # Remove all addresses in the hosts
    srv6_controller_utils.flush_ipv6_addresses_ssh('2000::5', 'hads11-eth1')
    srv6_controller_utils.flush_ipv6_addresses_ssh('2000::6', 'hads21-eth1')
    # Add the public addresses to the interfaces in the hosts
    srv6_controller_utils.add_ipv6_address_ssh('2000::5', 'hads11-eth1',
                                       'fd00:0:2:3:1::/64')
    srv6_controller_utils.add_ipv6_address_ssh('2000::6', 'hads21-eth1',
                                       'fd00:0:2:3:1::/64')

    # Test IPv4-VPN APIs

    # Create VPN 10-research
    name = 'research'
    # Create interfaces
    # First interface
    if1 = Interface('fdff::1', 'ads1-eth3',
                    '172.16.1.1/24', '172.16.1.0/24')
    # Second interface
    if2 = Interface('fdff:0:0:100::1', 'ads2-eth3',
                    '172.16.3.1/24', '172.16.3.0/24')
    # List of interfaces
    interfaces = [
        if1,
        if2
    ]
    # Tenant ID
    tenantid = 10
    # Send creation command through the northbound API
    srv6_vpn_manager.create_vpn(controller_addr, controller_port,
                                name, VPNType.IPv4VPN,
                                interfaces, tenantid)

    # Add interface
    name = 'research'
    # Create the interface
    if1 = Interface('fdff::1', 'ads1-eth4',
                    '172.16.40.1/24', '172.16.40.0/24')
    tenantid = 10
    srv6_vpn_manager.assign_interface_to_vpn(controller_addr,
                                             controller_port, name,
                                             tenantid, if1)

    # Remove interface
    name = 'research'
    # Create the interface
    if1 = Interface('fdff::1', 'ads1-eth4')
    # Tenant ID
    tenantid = 20
    # Run remove interface command
    srv6_vpn_manager.remove_interface_from_vpn(controller_addr,
                                               controller_port, name,
                                               tenantid, if1)
    # Add the public addresses to the interfaces in the routers
    srv6_controller_utils.add_ipv4_address_quagga('fdff::1',
                                          'ads1-eth4', '10.3.0.1/16')

    # Remove VPN 10-research
    srv6_vpn_manager.remove_vpn(controller_addr,
                                controller_port, 'research', 10)
    # Add the public addresses to the interfaces in the hosts
    srv6_controller_utils.add_ipv4_address_quagga('fdff::1',
                                          'ads1-eth3', '10.3.0.1/16')
    srv6_controller_utils.add_ipv4_address_quagga('fdff:0:0:200::1',
                                          'sur1-eth3', '10.2.0.1/24')
    srv6_controller_utils.add_ipv4_address_quagga('fdff:0:0:200::1',
                                          'sur1-eth4', '10.5.0.1/24')'''

    '''
    InventoryService = InventoryService()
    response = InventoryService.configure_tenant('11.3.192.117', 54321, 40000, '')
    print('Risponse tenant cration: %s --- %s --- %s' % (response[0], response[1], response[2]))
    response2 = InventoryService.remove_tenant('11.3.192.117', 54321, 'mG4rESBHVO5byMoKq2CJifPZHLjqeYpAYRYrEEenNQe17BzfZRNLY3XVLvaSezdtEzWmz1sq14RIsBWsRoXLZuRffSztIJ3kywqDp1YAdEpMAwCMuTYa6jlIb4F8a5TI')  # noqa: E501
    print('Response remove tenat: %s' % response2)
    '''
