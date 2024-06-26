#!/usr/bin/python

from __future__ import absolute_import, division, print_function
# General imports
import logging
from bson.objectid import ObjectId
# SRv6 dependencies
from srv6_sdn_control_plane.northbound.grpc import tunnel_mode
from srv6_sdn_control_plane.southbound.grpc import sb_grpc_client
from srv6_sdn_control_plane.srv6_controller_utils import OverlayType
from srv6_sdn_control_plane.srv6_controller_utils import MAIN_ROUTING_TABLE
from srv6_sdn_controller_state import (
    srv6_sdn_controller_state as storage_helper
)
from srv6_sdn_proto.status_codes_pb2 import NbStatusCode, SbStatusCode
from socket import AF_INET, AF_INET6

# Default gRPC client port
DEFAULT_GRPC_CLIENT_PORT = 12345
# Verbose mode
DEFAULT_VERBOSE = False
# Logger reference
logger = logging.getLogger(__name__)


# FIXME reomve time import -----------------------------------------
import time
# ------------------------------------------------------------------


class VXLANTunnel(tunnel_mode.TunnelMode):
    """gRPC request handler"""

    def __init__(self, grpc_client_port=DEFAULT_GRPC_CLIENT_PORT,
                 verbose=DEFAULT_VERBOSE):
        # Name of the tunnel mode
        self.name = 'VXLAN'
        # Port of the gRPC client
        self.grpc_client_port = grpc_client_port
        # Verbose mode
        self.verbose = verbose
        # Create SRv6 Manager
        self.srv6_manager = sb_grpc_client.SRv6Manager()
        # Get connection to MongoDB
        client = storage_helper.get_mongodb_session()
        # Get the database
        db = client.EveryWan
        # Get collection
        self.overlays = db.overlays

    def add_slice_to_overlay(self, overlayid, overlay_name,
                             deviceid, interface_name, tenantid, overlay_info):
        # Get device management IP address
        mgmt_ip_site = storage_helper.get_router_mgmtip(
            deviceid, tenantid
        )
        # get table ID
        tableid = storage_helper.get_tableid(
            overlayid, tenantid
        )
        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        # get VRF name
        vrf_name = 'vrf-%s' % (tableid)
        # add slice to the VRF
        response = self.srv6_manager.update_vrf_device(
            mgmt_ip_site,
            self.grpc_client_port,
            name=vrf_name,
            interfaces=[interface_name],
            op='add_interfaces'
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot add interface %s to the VRF %s in %s',
                interface_name,
                vrf_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # Create routes for subnets
        # get subnet for local and remote site
        subnets = storage_helper.get_ip_subnets(
            deviceid, tenantid, interface_name
        )
        for subnet in subnets:
            gateway = subnet['gateway']
            subnet = subnet['subnet']
            if gateway is not None and gateway != '':
                response = self.srv6_manager.create_iproute(
                    mgmt_ip_site,
                    self.grpc_client_port,
                    destination=subnet,
                    gateway=gateway,
                    out_interface=interface_name,
                    table=tableid
                )
                if response != SbStatusCode.STATUS_SUCCESS:
                    # If the operation has failed, report an error message
                    logger.warning(
                        'Cannot set route for %s (gateway %s) in %s ',
                        subnet,
                        gateway,
                        mgmt_ip_site
                    )
                    return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # Success
        return NbStatusCode.STATUS_OK

    def create_tunnel(self, overlayid, overlay_name, overlay_type,
                      l_slice, r_slice, tenantid, overlay_info):
        
        # get devices ID
        id_remote_site = r_slice['deviceid']
        id_local_site = l_slice['deviceid']

      
        local_site_deviceid = l_slice['deviceid']
        remote_site_deviceid = r_slice['deviceid']



        # get management IP address for local and remote site
        mgmt_ip_local_site = storage_helper.get_router_mgmtip(local_site_deviceid, tenantid)
        mgmt_ip_remote_site = storage_helper.get_router_mgmtip(remote_site_deviceid, tenantid)


        # get subnet for local and remote site
        lan_sub_remote_sites = storage_helper.get_ip_subnets(
            id_remote_site, tenantid, r_slice['interface_name'])
        lan_sub_local_sites = storage_helper.get_ip_subnets(
            id_local_site, tenantid, l_slice['interface_name'])

        
       
        # get table ID
        tableid = storage_helper.get_tableid(overlayid, tenantid)

        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        
        # transport protocol
        transport_proto = storage_helper.get_overlay(overlayid=overlayid, tenantid=tenantid)['transport_proto']
        
        # get VTEP IP remote site and local site
        if transport_proto == 'ipv6':
            vtep_ip_remote_site = storage_helper.get_vtep_ipv6(
                id_remote_site, tenantid
            )
            vtep_ip_local_site = storage_helper.get_vtep_ipv6(
                id_local_site, tenantid
            )
        elif transport_proto == 'ipv4':
            vtep_ip_remote_site = storage_helper.get_vtep_ip(
                id_remote_site, tenantid
            )
            vtep_ip_local_site = storage_helper.get_vtep_ip(
                id_local_site, tenantid
            )
        else:
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
   

        
        # get VNI
        vni = storage_helper.get_vni(overlay_name, tenantid)
        
        # get VTEP name
        vtep_name = 'vxlan-%s' % (vni)

       
        
        # Check if the r_slice and l_slice are in the same underaly network 
        underlay_wan_id = None
        if r_slice['underlay_wan_id'] == l_slice['underlay_wan_id']:
            underlay_wan_id = r_slice['underlay_wan_id']
        else:
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        


        # get WAN interface name for local site and remote site
        wan_intf_local_site = storage_helper.get_wan_interface(deviceid=id_local_site, tenantid=tenantid, underlay_wan_id=underlay_wan_id)
        wan_intf_remote_site = storage_helper.get_wan_interface(deviceid=id_remote_site, tenantid=tenantid, underlay_wan_id=underlay_wan_id)  


        # transport protocol
        transport_proto = storage_helper.get_overlay(overlayid=overlayid, tenantid=tenantid)['transport_proto']

        # get external IP address for loal site and remote site
        if transport_proto == 'ipv6':
            wan_ip_local_site = storage_helper.get_ext_ipv6_addresses(id_local_site, tenantid, wan_intf_local_site)[0].split("/")[0]
            wan_ip_remote_site = storage_helper.get_ext_ipv6_addresses(id_remote_site, tenantid, wan_intf_remote_site)[0].split("/")[0]
        elif transport_proto == 'ipv4':
            wan_ip_local_site = storage_helper.get_ext_ipv4_addresses(id_local_site, tenantid, wan_intf_local_site)[0].split("/")[0]
            wan_ip_remote_site = storage_helper.get_ext_ipv4_addresses(id_remote_site, tenantid, wan_intf_remote_site)[0].split("/")[0]
        else:
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        
        # DB key creation, one per tunnel direction
        key_local_to_remote = '%s__%s' % (id_local_site, id_remote_site)
        key_remote_to_local = '%s__%s' % (id_remote_site, id_local_site)


        # get tunnel dictionaries from DB
        dictionary_local = self.overlays.find_one(
            {
                '_id': ObjectId(overlayid),
                'tenantid': tenantid,
                'created_tunnel.tunnel_key': key_local_to_remote
            },
            {
                'created_tunnel.$.tunnel_key': 1
            })
        

        dictionary_remote = self.overlays.find_one(
            {
                '_id': ObjectId(overlayid),
                'tenantid': tenantid,
                'created_tunnel.tunnel_key': key_remote_to_local
            },
            {
                'created_tunnel.$.tunnel_key': 1
            })



        # If it's the first overlay for the devices, create dictionaries
        # else take tunnel info from DB dictionaries
        #
        # local site
        if dictionary_local is None:
            tunnel_local = {
                'tunnel_key': key_local_to_remote,
                'reach_subnets': [],
                'fdb_entry_config': False, 
                'tunnel_interface_name' : vtep_name, 
                'tunnel_dst_endpoint' : vtep_ip_remote_site

            }
        
        else:
            tunnel_local = dictionary_local['created_tunnel'][0]
        # remote site
        if dictionary_remote is None:
            tunnel_remote = {
                'tunnel_key': key_remote_to_local,
                'reach_subnets': [],
                'fdb_entry_config': False, 
                'tunnel_interface_name' : vtep_name,
                'tunnel_dst_endpoint': vtep_ip_local_site
            }
        else:
            tunnel_remote = dictionary_remote['created_tunnel'][0]
        
        
        
        
        # Check if there is the fdb entry in local site for remote site
        if tunnel_local.get('fdb_entry_config') is False:
            # add FDB entry in local site
            response = self.srv6_manager.addfdbentries(
                mgmt_ip_local_site,
                self.grpc_client_port,
                ifindex=vtep_name,
                dst=wan_ip_remote_site
            )
            if response != SbStatusCode.STATUS_SUCCESS:
                # If the operation has failed, report an error message
                logger.warning(
                    'Cannot add FDB entry %s for VTEP %s in %s',
                    wan_ip_remote_site,
                    vtep_name,
                    mgmt_ip_local_site
                )
                return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
            # update local dictionary
            tunnel_local['fdb_entry_config'] = True





            
        # Check if there is the fdb entry in remote site for local site
        if tunnel_remote.get('fdb_entry_config') is False:
            # add FDB entry in remote site
            response = self.srv6_manager.addfdbentries(
                mgmt_ip_remote_site,
                self.grpc_client_port,
                ifindex=vtep_name,
                dst=wan_ip_local_site
            )
            if response != SbStatusCode.STATUS_SUCCESS:
                # If the operation has failed, report an error message
                logger.warning(
                    'Cannot add FDB entry %s for VTEP %s in %s',
                    wan_ip_local_site,
                    vtep_name,
                    mgmt_ip_remote_site
                )
                return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
            # update local dictionary
            tunnel_remote['fdb_entry_config'] = True



        
        
        # set route in local site for the remote subnet, if not present
        for lan_sub_remote_site in lan_sub_remote_sites:
            lan_sub_remote_site = lan_sub_remote_site['subnet']
            if lan_sub_remote_site not in tunnel_local.get('reach_subnets'):
                response = self.srv6_manager.create_iproute(
                    mgmt_ip_local_site,
                    self.grpc_client_port,
                    destination=lan_sub_remote_site,
                    gateway=vtep_ip_remote_site.split("/")[0],
                    table=tableid,
                    out_interface=vtep_name
                )
                if response != SbStatusCode.STATUS_SUCCESS:
                    # If the operation has failed, report an error message
                    logger.warning(
                        'Cannot set route for %s in %s ',
                        lan_sub_remote_site,
                        mgmt_ip_local_site)
                    
                    return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                # update local dictionary with the new subnet in overlay
                tunnel_local.get('reach_subnets').append(lan_sub_remote_site)
        
    




        # set route in remote site for the local subnet, if not present
        for lan_sub_local_site in lan_sub_local_sites:
            lan_sub_local_site = lan_sub_local_site['subnet']
            if lan_sub_local_site not in tunnel_remote.get('reach_subnets'):
                response = self.srv6_manager.create_iproute(
                    mgmt_ip_remote_site,
                    self.grpc_client_port,
                    destination=lan_sub_local_site,
                    gateway=vtep_ip_local_site.split("/")[0],
                    table=tableid,
                    out_interface=vtep_name
                )
                if response != SbStatusCode.STATUS_SUCCESS:
                    # If the operation has failed, report an error message
                    logger.warning(
                        'Cannot set route for %s in %s ',
                        lan_sub_local_site,
                        mgmt_ip_remote_site
                    )
                    return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                # update local dictionary with the new subnet in overlay
                tunnel_remote.get('reach_subnets').append(lan_sub_local_site)




        # Get the defualt_ip_rules lowest priority in the local site edge device
        default_ip_rules___lowest_priority_local_site = storage_helper.decrement_and_get_default_ip_rules___lowest_priority(deviceid=local_site_deviceid, tenantid=tenantid)
        

        # Get the defualt_ip_rules lowest priority in the remote site edge device
        default_ip_rules___lowest_priority_remote_site = storage_helper.decrement_and_get_default_ip_rules___lowest_priority(deviceid=remote_site_deviceid, tenantid=tenantid)

        
        if default_ip_rules___lowest_priority_local_site ==None:
            logger.warning(
                'Cannot Get the defualt_ip_rules lowest priority in the local site %s',local_site_deviceid)
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        
        if default_ip_rules___lowest_priority_remote_site ==None:
            logger.warning(
                'Cannot Get the defualt_ip_rules lowest priority in the remote site %s',remote_site_deviceid)
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        




        # Add the default ip rule to lookup for the tunnel table -  remote site 
        response = self.srv6_manager.create_iprule(
            mgmt_ip_remote_site,
            self.grpc_client_port,
            table=tableid,
            priority=default_ip_rules___lowest_priority_remote_site,
            family=AF_INET)
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                '[remote site] Cannot Add the default ip rule to lookup for the tunnel table %s in %s',
                tableid,
                mgmt_ip_remote_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR




        # Add the default ip rule to lookup for the tunnel table -  local site 
        response = self.srv6_manager.create_iprule(
            mgmt_ip_local_site,
            self.grpc_client_port,
            table=tableid,
            priority=default_ip_rules___lowest_priority_local_site,
            family=AF_INET)
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                '[local site] Cannot Add the default ip rule to lookup for the tunnel table %s in %s',
                tableid,
                mgmt_ip_local_site)
            
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        


        


        # FIXME remove this just for logging --------------------------------------------------
        # rule_match = {
        #                 'match_name' : "mark",
        #                 'match_attributes': [
        #                     {
        #                         'attribute_name': "mark",
        #                         'attribute_value': str(tableid)
        #                     },]
        #             }
        # FIXME remove this just for logging --------------------------------------------------




        # ADD iptables rule to FORWARD chain in mangle table - local site
        # Used for counting the traffic going through the tunnel
        response = self.srv6_manager.create_iptables_rule(mgmt_ip_local_site, self.grpc_client_port, table= 'mangle',
                                            chain='FORWARD', target_name='ACCEPT', out_interface=vtep_name)
        
        if response != SbStatusCode.STATUS_SUCCESS:
            err = "Cannot create iptables rule [local site]"
            logging.warning(err)
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        



        # ADD iptables rule to FORWARD chain in mangle table - remote site
        # Used for counting the traffic going through the tunnel
        response = self.srv6_manager.create_iptables_rule(mgmt_ip_remote_site, self.grpc_client_port, table= 'mangle',
                                            chain='FORWARD', target_name='ACCEPT', out_interface=vtep_name)
        
        if response != SbStatusCode.STATUS_SUCCESS:
            err = "Cannot create iptables rule [remote site]"
            logging.warning(err)
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        




        # Update the tunnel_mode virtual interfaces in the local site (in database)
        success = storage_helper.update_tunnel_mode_interfaces(tenantid=tenantid, deviceid=id_local_site,
                                            tunnel_mode_name=self.name, tunnel_interface_name=vtep_name ,
                                            tunnel_dst_endpoint= vtep_ip_remote_site)
        
        if not success:
            err = "Cannot Update the tunnel_mode virtual interfaces in the local site"
            logging.warning(err)
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR

        # Update the tunnel_mode virtual interfaces in the remote site edge device (in database)
        success = storage_helper.update_tunnel_mode_interfaces(tenantid=tenantid, deviceid=id_remote_site,
                                            tunnel_mode_name=self.name, tunnel_interface_name=vtep_name ,
                                            tunnel_dst_endpoint= vtep_ip_local_site)
        
        if not success:
            err = "Cannot Update the tunnel_mode virtual interfaces in the remote site"
            logging.warning(err)
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR




        # Insert the device overlay state in DB,
        # if there is already a state update it
        #
        # local site
        new_doc_created = self.overlays.update_one(
            {
                '_id': ObjectId(overlayid),
                'tenantid': tenantid,
                'created_tunnel.tunnel_key': {
                    '$ne': tunnel_local.get('tunnel_key')
                }
            },
            {
                '$push': {
                    'created_tunnel': {
                        'tunnel_key': tunnel_local.get('tunnel_key'),
                        'reach_subnets': tunnel_local.get('reach_subnets'),
                        'fdb_entry_config': tunnel_local.get(
                            'fdb_entry_config'
                        ), 
                        'tunnel_interface_name': tunnel_local.get('tunnel_interface_name'),
                        'tunnel_dst_endpoint': tunnel_local.get('tunnel_dst_endpoint')
                    }
                }
            }
        ).matched_count == 1




        
        if new_doc_created is False:
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid,
                    'created_tunnel.tunnel_key': tunnel_local.get(
                        'tunnel_key'
                    )
                },
                {
                    '$set': {
                        'created_tunnel.$.reach_subnets': tunnel_local.get(
                            'reach_subnets'
                        ),
                        'created_tunnel.$.fdb_entry_config': tunnel_local.get(
                            'fdb_entry_config'
                        ), 
                        'created_tunnel.$.tunnel_interface_name': tunnel_local.get(
                            'tunnel_interface_name'
                        ),'created_tunnel.$.tunnel_dst_endpoint': tunnel_local.get(
                            'tunnel_dst_endpoint'
                        ),

                    }
                },
                upsert=True
            )
        # remote site
        new_doc_created = self.overlays.update_one(
            {
                '_id': ObjectId(overlayid),
                'tenantid': tenantid,
                'created_tunnel.tunnel_key': {
                    '$ne': tunnel_remote.get('tunnel_key')
                }
            },
            {
                '$push': {
                    'created_tunnel': {
                        'tunnel_key': tunnel_remote.get('tunnel_key'),
                        'reach_subnets': tunnel_remote.get('reach_subnets'),
                        'fdb_entry_config': tunnel_remote.get(
                            'fdb_entry_config'
                        ), 
                        'tunnel_interface_name': tunnel_remote.get('tunnel_interface_name'),
                        'tunnel_dst_endpoint': tunnel_remote.get('tunnel_dst_endpoint')
                    }
                }
            }
        ).matched_count == 1
        if new_doc_created is False:
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid,
                    'created_tunnel.tunnel_key': tunnel_remote.get(
                        'tunnel_key')
                },
                {
                    '$set': {
                        'created_tunnel.$.reach_subnets': tunnel_remote.get(
                            'reach_subnets'
                        ),
                        'created_tunnel.$.fdb_entry_config': tunnel_remote.get(
                            'fdb_entry_config'
                        ),
                        'created_tunnel.$.tunnel_interface_name': tunnel_remote.get(
                            'tunnel_interface_name'
                        ),'created_tunnel.$.tunnel_dst_endpoint': tunnel_remote.get(
                            'tunnel_dst_endpoint'
                        ),
                    }
                },
                upsert=True
            )
        # Success
        return NbStatusCode.STATUS_OK

    def add_slice_to_overlay_2_0(self, overlayid, overlay_name,
                             deviceid, interface_name, tenantid, overlay_info):
        
        # Get device management IP address
        mgmt_ip_site = storage_helper.get_router_mgmtip(
            deviceid, tenantid
        )
        main_tableid = MAIN_ROUTING_TABLE


        # # get table ID
        # tableid = storage_helper.get_tableid(
        #     overlayid, tenantid
        # )
        
        # if tableid is None:
        #     logger.error(
        #         'Error while getting table ID assigned to the overlay %s',
        #         overlayid
        #     )

        
        
        # # add slice to the VRF
        # response = self.srv6_manager.update_vrf_device(
        #     mgmt_ip_site,
        #     self.grpc_client_port,
        #     name=vrf_name,
        #     interfaces=[interface_name],
        #     op='add_interfaces'
        # )
        # if response != SbStatusCode.STATUS_SUCCESS:
        #     # If the operation has failed, report an error message
        #     logger.warning(
        #         'Cannot add interface %s to the VRF %s in %s',
        #         interface_name,
        #         vrf_name,
        #         mgmt_ip_site
        #     )
        #     return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        


        # Create routes for subnets
        # get subnet for local and remote site
        subnets = storage_helper.get_ip_subnets(
            deviceid, tenantid, interface_name
        )

        configured_subnets = storage_helper.get_device_main_table_configured_LAN_subnets(deviceid, tenantid)
        for subnet in subnets:
            gateway = subnet['gateway']
            subnet = subnet['subnet']

            if subnet in configured_subnets:
                continue

            
            
            if gateway is not None and gateway != '':
                response = self.srv6_manager.create_iproute(
                    mgmt_ip_site,
                    self.grpc_client_port,
                    destination=subnet,
                    gateway=gateway,
                    out_interface=interface_name,
                    table=main_tableid
                )
                if response != SbStatusCode.STATUS_SUCCESS:
                    # If the operation has failed, report an error message
                    logger.warning(
                        'Cannot set route for %s (gateway %s) in %s ',
                        subnet,
                        gateway,
                        mgmt_ip_site
                    )
                    return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR

                storage_helper.update_device_main_table_configured_LAN_subnets(deviceid, tenantid, subnet)
        # Success
        return NbStatusCode.STATUS_OK

    def init_overlay_2_0(self, overlayid, overlay_name,
                     overlay_type, tenantid, deviceid, overlay_info):
        # get device management IP address
        mgmt_ip_site = storage_helper.get_router_mgmtip(deviceid, tenantid)

        # Get vxlan port set by user
        vxlan_port_site = storage_helper.get_tenant_vxlan_port(tenantid)

        # get table ID
        tableid = storage_helper.get_tableid(overlayid, tenantid)

        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',overlayid)
        
        
        
        # get WAN interface
        # TODO TERMIN* Add support for multiple WAN interfaces (hybrid WAN)
        # wan_intf_site = storage_helper.get_wan_interfaces(deviceid, tenantid)[0]
        underlay_wan_id = storage_helper.get_underlay_wan_id(overlayid=overlayid, tenantid=tenantid)
        wan_intf_site = storage_helper.get_wan_interface(deviceid=deviceid, tenantid=tenantid, underlay_wan_id=underlay_wan_id)


         
        
        # get VNI for the overlay
        vni = storage_helper.get_vni(overlay_name, tenantid)
        
        # get VTEP name
        vtep_name = 'vxlan-%s' % (vni)
        
        # get VTEP IP address
        if overlay_type == OverlayType.IPv6Overlay:
            vtep_ip_site = storage_helper.get_vtep_ipv6(
                deviceid, tenantid
            )
            vtep_ip_family = AF_INET6
        else:
            vtep_ip_site = storage_helper.get_vtep_ip(
                deviceid, tenantid
            )
            vtep_ip_family = AF_INET
        
        
        # transport protocol
        transport_proto = storage_helper.get_overlay(
            overlayid=overlayid, tenantid=tenantid)['transport_proto']
        
        # crete VTEP interface
        response = self.srv6_manager.createVxLAN(
            mgmt_ip_site,
            self.grpc_client_port,
            ifname=vtep_name,
            vxlan_link=wan_intf_site,
            vxlan_id=vni,
            vxlan_port=vxlan_port_site,
            vxlan_group='::' if transport_proto == 'ipv6' else '0.0.0.0'
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot create VTEP %s in %s',
                vtep_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # set VTEP IP address
        response = self.srv6_manager.create_ipaddr(
            mgmt_ip_site,
            self.grpc_client_port,
            ip_addr=vtep_ip_site,
            device=vtep_name, net='',
            family=vtep_ip_family
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot set IP %s for VTEP %s in %s',
                vtep_ip_site,
                vtep_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR

        # Success
        return NbStatusCode.STATUS_OK

    def init_overlay(self, overlayid, overlay_name,
                     overlay_type, tenantid, deviceid, overlay_info):
        # get device management IP address
        mgmt_ip_site = storage_helper.get_router_mgmtip(deviceid, tenantid)

        # Get vxlan port set by user
        vxlan_port_site = storage_helper.get_tenant_vxlan_port(tenantid)

        # get table ID
        tableid = storage_helper.get_tableid(overlayid, tenantid)

        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        
        # get VRF name
        vrf_name = 'vrf-%s' % (tableid)
        

        
        # get WAN interface
        # TODO TERMIN* Add support for multiple WAN interfaces (hybrid WAN)
        # wan_intf_site = storage_helper.get_wan_interfaces(deviceid, tenantid)[0]
        underlay_wan_id = storage_helper.get_underlay_wan_id(overlayid=overlayid, tenantid=tenantid)
        wan_intf_site = storage_helper.get_wan_interface(deviceid=deviceid, tenantid=tenantid, underlay_wan_id=underlay_wan_id)


         
        
        # get VNI for the overlay
        vni = storage_helper.get_vni(overlay_name, tenantid)
        # get VTEP name
        vtep_name = 'vxlan-%s' % (vni)
        # get VTEP IP address
        if overlay_type == OverlayType.IPv6Overlay:
            vtep_ip_site = storage_helper.get_vtep_ipv6(
                deviceid, tenantid
            )
            vtep_ip_family = AF_INET6
        else:
            vtep_ip_site = storage_helper.get_vtep_ip(
                deviceid, tenantid
            )
            vtep_ip_family = AF_INET
        # transport protocol
        transport_proto = storage_helper.get_overlay(
            overlayid=overlayid, tenantid=tenantid
        )['transport_proto']
        # crete VTEP interface
        response = self.srv6_manager.createVxLAN(
            mgmt_ip_site,
            self.grpc_client_port,
            ifname=vtep_name,
            vxlan_link=wan_intf_site,
            vxlan_id=vni,
            vxlan_port=vxlan_port_site,
            vxlan_group='::' if transport_proto == 'ipv6' else '0.0.0.0'
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot create VTEP %s in %s',
                vtep_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # set VTEP IP address
        response = self.srv6_manager.create_ipaddr(
            mgmt_ip_site,
            self.grpc_client_port,
            ip_addr=vtep_ip_site,
            device=vtep_name, net='',
            family=vtep_ip_family
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot set IP %s for VTEP %s in %s',
                vtep_ip_site,
                vtep_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # create VRF and add the VTEP interface
        response = self.srv6_manager.create_vrf_device(
            mgmt_ip_site,
            self.grpc_client_port,
            name=vrf_name,
            table=tableid,
            interfaces=[vtep_name]
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot create VRF %s in %s',
                vrf_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # Success
        return NbStatusCode.STATUS_OK

    def init_overlay_data(self, overlayid,
                          overlay_name, tenantid, overlay_info):
        # get VNI
        vni = storage_helper.get_vni(
            overlay_name, tenantid
        )
        
        if vni == -1:
            vni = storage_helper.get_new_vni(
                overlay_name, tenantid
            )

        # get table ID
        tableid = storage_helper.get_new_tableid(
            overlayid, tenantid
        )


        if tableid is None:
            logger.error(
                'Cannot get a new table ID for the overlay %s',
                overlayid
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # Success
        return NbStatusCode.STATUS_OK

    def init_tunnel_mode(self, deviceid, tenantid, overlay_info):
        # get VTEP IP address for site1
        vtep_ip_site = storage_helper.get_vtep_ip(
            deviceid, tenantid
        )
        if vtep_ip_site == -1:

            vtep_ip_site = storage_helper.get_new_vtep_ip(
                deviceid, tenantid
            )
           

        vtep_ipv6_site = storage_helper.get_vtep_ipv6(
            deviceid, tenantid
        )
        if vtep_ipv6_site == -1:
            vtep_ipv6_site = storage_helper.get_new_vtep_ipv6(
                deviceid, tenantid
            )
        # Success
        return NbStatusCode.STATUS_OK



    def init_tunnel_mode_2_0(self, deviceid, tenantid, overlay_info, overlayid):






        # # FIXME remove this just logging -----------------------------------
        # vtep_ip_site_test = storage_helper.get_new_vtep_ip_unique_2(deviceid, tenantid, overlayid, overlay_ip_net_index)
        
        # logging.info("\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
        # logging.info("overlayid")
        # logging.info(overlayid)
        # logging.info('vtep_ip_site_test')
        # logging.info(vtep_ip_site_test)

        # logging.info("\n\n\n\n\n\n\n\n\n\n\n\n\n\n")

        # # FIXME remove this just logging -----------------------------------








        overlay_ip_net_index = storage_helper.get_overlay_ip_net_index(tenantid)

        # get VTEP IP address for site1
        vtep_ip_site = storage_helper.get_new_vtep_ip_unique_2(
            deviceid, tenantid, overlayid, overlay_ip_net_index
        )
        
        # FIXME : Need to check ipv4 vtep allocation
        # vtep_ipv6_site = storage_helper.get_new_vtep_ipv6_unique(
        #         deviceid, tenantid
        #     )

        # Success
        return NbStatusCode.STATUS_OK

 


    def remove_slice_from_overlay(self, overlayid, overlay_name, deviceid,
                                  interface_name, tenantid, overlay_info,
                                  ignore_errors=False):
        if not storage_helper.is_device_connected(
            deviceid=deviceid, tenantid=tenantid
        ):
            # The device is not connected, we skip it and we schedule a reboot
            #
            # Change device state to reboot required
            success = storage_helper.change_device_state(
                deviceid=deviceid,
                tenantid=tenantid,
                new_state=(
                    storage_helper.DeviceState.REBOOT_REQUIRED
                )
            )
            if success is False or success is None:
                logging.error('Error changing the device state')
                return NbStatusCode.STATUS_INTERNAL_ERROR
            return NbStatusCode.STATUS_OK
        # get device management IP address
        mgmt_ip_site = storage_helper.get_router_mgmtip(
            deviceid, tenantid
        )
        # retrive table ID
        tableid = storage_helper.get_tableid(
            overlayid, tenantid
        )
        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        # Remove IP routes from the VRF
        # This step is optional, because the routes are
        # automatically removed when the interfaces is removed
        # from the VRF. We do it just for symmetry with respect
        # to the add_slice_to_overlay function
        #
        # get subnet for local and remote site
        subnets = storage_helper.get_ip_subnets(
            deviceid, tenantid, interface_name
        )
        for subnet in subnets:
            gateway = subnet['gateway']
            subnet = subnet['subnet']
            if gateway is not None and gateway != '':
                response = self.srv6_manager.remove_iproute(
                    mgmt_ip_site,
                    self.grpc_client_port,
                    destination=subnet,
                    gateway=gateway,
                    table=tableid
                )
                if response != SbStatusCode.STATUS_SUCCESS:
                    # If the operation has failed, report an error message
                    logger.warning(
                        'Cannot remove route for %s (gateway %s) in %s ',
                        subnet,
                        gateway,
                        mgmt_ip_site
                    )
                    return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # retrive VRF name
        vrf_name = 'vrf-%s' % (tableid)
        # Remove slice from VRF
        response = self.srv6_manager.update_vrf_device(
            mgmt_ip_site,
            self.grpc_client_port,
            name=vrf_name,
            interfaces=[interface_name],
            op='del_interfaces'
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot remove interface %s from VRF %s in %s',
                interface_name,
                vrf_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # Success
        return NbStatusCode.STATUS_OK

    def remove_slice_from_overlay_2_0(self, overlayid, overlay_name, deviceid,
                                  interface_name, tenantid, overlay_info,
                                  ignore_errors=False):
        if not storage_helper.is_device_connected(
            deviceid=deviceid, tenantid=tenantid
        ):
            # The device is not connected, we skip it and we schedule a reboot
            #
            # Change device state to reboot required
            success = storage_helper.change_device_state(
                deviceid=deviceid,
                tenantid=tenantid,
                new_state=(
                    storage_helper.DeviceState.REBOOT_REQUIRED
                )
            )
            if success is False or success is None:
                logging.error('Error changing the device state')
                return NbStatusCode.STATUS_INTERNAL_ERROR
            return NbStatusCode.STATUS_OK
        
        # get device management IP address
        mgmt_ip_site = storage_helper.get_router_mgmtip(
            deviceid, tenantid
        )

        main_tableid = MAIN_ROUTING_TABLE


        # # retrive table ID
        # tableid = storage_helper.get_tableid(
        #     overlayid, tenantid
        # )
        # if tableid is None:
        #     logger.error(
        #         'Error while getting table ID assigned to the overlay %s',
        #         overlayid
        #     )




        # Remove IP routes from the main table
        # get subnet for local and remote site
        subnets = storage_helper.get_ip_subnets(deviceid, tenantid, interface_name)
        

        logging.info("\n\n\n\n\n.....................................................")
        logging.info("subnets")
        logging.info(subnets)
        logging.info("\n\n\n\n\n.....................................................")

        # TODO : change this to get_stats
        device = storage_helper.get_device(deviceid, tenantid)
        device_stats = device["stats"]
        counter=None
        for tunnel in device_stats["counters"]["tunnels"]:
            if tunnel.get("tunnel_mode") == "VXLAN":
                counter=tunnel.get("counter")

        if counter < 2:
            for subnet in subnets:
                gateway = subnet['gateway']
                subnet = subnet['subnet']
                if gateway is not None and gateway != '':
                    response = self.srv6_manager.remove_iproute(
                        mgmt_ip_site,
                        self.grpc_client_port,
                        destination=subnet,
                        gateway=gateway,
                        table=main_tableid
                    )
                    if response != SbStatusCode.STATUS_SUCCESS:
                        # If the operation has failed, report an error message
                        logger.warning(
                            '@121 Cannot remove route for %s (gateway %s) in %s ',
                            subnet,
                            gateway,
                            mgmt_ip_site
                        )
                        return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR

                    succ = storage_helper.remove_device_main_table_configured_LAN_subnets(deviceid, tenantid, subnet)
                    if not succ:
                        logging.warning('Cannot remove subnet from main_table_configured_LAN_subnets')

        # if device_stats.counters.tunnels.?. counter>=2 dont remove the routes from the main routing table

        
    
        # Success
        return NbStatusCode.STATUS_OK

    def remove_tunnel(self, overlayid, overlay_name, overlay_type,
                      l_slice, r_slice, tenantid, overlay_info,
                      ignore_errors=False):
        # get devices ID
        id_local_site = l_slice['deviceid']
        id_remote_site = r_slice['deviceid']
        # get VNI
        vni = storage_helper.get_vni(
            overlay_name, tenantid
        )
        # get management IP local and remote site
        mgmt_ip_remote_site = storage_helper.get_router_mgmtip(
            id_remote_site, tenantid
        )
        mgmt_ip_local_site = storage_helper.get_router_mgmtip(
            id_local_site, tenantid
        )

        # get WAN interface name for local site and remote site
        # TODO TERMIN* Add support for multiple WAN interfaces (hybrid WAN)
        # wan_intf_local_site = storage_helper.get_wan_interfaces(id_local_site, tenantid)[0]
        # wan_intf_remote_site = storage_helper.get_wan_interfaces(id_remote_site, tenantid)[0]
        underlay_wan_id = storage_helper.get_underlay_wan_id(overlayid, tenantid)
        wan_intf_local_site = storage_helper.get_wan_interface(deviceid=id_local_site, tenantid=tenantid, underlay_wan_id=underlay_wan_id)
        wan_intf_remote_site = storage_helper.get_wan_interface(deviceid=id_remote_site, tenantid=tenantid, underlay_wan_id=underlay_wan_id)


        # transport protocol
        transport_proto = storage_helper.get_overlay(
            overlayid=overlayid, tenantid=tenantid
        )['transport_proto']
        # get external IP address for local site and remote site
        if transport_proto == 'ipv6':
            wan_ip_local_site = storage_helper.get_ext_ipv6_addresses(
                id_local_site, tenantid, wan_intf_local_site
            )
            wan_ip_remote_site = storage_helper.get_ext_ipv6_addresses(
                id_remote_site, tenantid, wan_intf_remote_site
            )
        elif transport_proto == 'ipv4':
            wan_ip_local_site = storage_helper.get_ext_ipv4_addresses(
                id_local_site, tenantid, wan_intf_local_site
            )
            wan_ip_remote_site = storage_helper.get_ext_ipv4_addresses(
                id_remote_site, tenantid, wan_intf_remote_site
            )
        else:
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        if wan_ip_local_site is not None and len(wan_ip_local_site) > 0:
            wan_ip_local_site = wan_ip_local_site[0].split("/")[0]
        if wan_ip_remote_site is not None and len(wan_ip_remote_site) > 0:
            wan_ip_remote_site = wan_ip_remote_site[0].split("/")[0]
        # get local and remote subnet
        lan_sub_local_sites = storage_helper.get_ip_subnets(
            id_local_site, tenantid, l_slice['interface_name']
        )
        lan_sub_remote_sites = storage_helper.get_ip_subnets(
            id_remote_site, tenantid, r_slice['interface_name']
        )
        # get table ID
        tableid = storage_helper.get_tableid(
            overlayid, tenantid
        )
        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        # get VTEP name
        vtep_name = 'vxlan-%s' % (vni)
        # DB key creation, one per tunnel direction
        key_local_to_remote = '%s__%s' % (id_local_site, id_remote_site)
        key_remote_to_local = '%s__%s' % (id_remote_site, id_local_site)
        # get tunnel dictionaries from DB
        #
        # local site
        tunnel_local = self.overlays.find_one(
            {
                '_id': ObjectId(overlayid),
                'tenantid': tenantid,
                'created_tunnel.tunnel_key': key_local_to_remote
            },
            {
                'created_tunnel.$.tunnel_key': 1
            }
        )['created_tunnel'][0]
        # remote site
        tunnel_remote = self.overlays.find_one(
            {
                '_id': ObjectId(overlayid),
                'tenantid': tenantid,
                'created_tunnel.tunnel_key': key_remote_to_local
            },
            {
                'created_tunnel.$.tunnel_key': 1
            }
        )['created_tunnel'][0]
        # Check if there is the fdb entry in remote site for local site
        if tunnel_remote.get('fdb_entry_config') is True:
            # Check if there is the route for the
            # local subnet in the remote device
            for lan_sub_local_site in lan_sub_local_sites:
                lan_sub_local_site = lan_sub_local_site['subnet']
                if lan_sub_local_site in tunnel_remote.get('reach_subnets'):
                    # remove route in remote site
                    if storage_helper.is_device_connected(
                        deviceid=id_remote_site, tenantid=tenantid
                    ):
                        response = self.srv6_manager.remove_iproute(
                            mgmt_ip_remote_site,
                            self.grpc_client_port,
                            destination=lan_sub_local_site,
                            table=tableid
                        )
                        if response != SbStatusCode.STATUS_SUCCESS:
                            # If the operation has failed, report an error
                            # message
                            logger.warning(
                                'Cannot remove route to %s in %s',
                                lan_sub_local_site,
                                mgmt_ip_remote_site
                            )
                            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                    else:
                        # Change device state to reboot required
                        success = storage_helper.change_device_state(
                            deviceid=id_remote_site,
                            tenantid=tenantid,
                            new_state=(
                                storage_helper.DeviceState.REBOOT_REQUIRED
                            )
                        )
                        if success is False or success is None:
                            logging.error('Error changing the device state')
                            return NbStatusCode.STATUS_INTERNAL_ERROR
                    # update local dictionary
                    tunnel_remote.get('reach_subnets').remove(
                        lan_sub_local_site
                    )
        # Check if the subnet removed is the last subnet
        # in the considered overlay in the local site
        if len(tunnel_remote.get('reach_subnets')) == 0:
            # Check if there is the route for remote subnet in the local site
            for lan_sub_remote_site in lan_sub_remote_sites:
                lan_sub_remote_site = lan_sub_remote_site['subnet']
                if lan_sub_remote_site in tunnel_local.get('reach_subnets'):
                    # remove route in remote site
                    if storage_helper.is_device_connected(
                        deviceid=id_local_site, tenantid=tenantid
                    ):
                        # remove route in local site
                        response = self.srv6_manager.remove_iproute(
                            mgmt_ip_local_site,
                            self.grpc_client_port,
                            destination=lan_sub_remote_site,
                            table=tableid
                        )
                        if response != SbStatusCode.STATUS_SUCCESS:
                            # If the operation has failed, report an error
                            # message
                            logger.warning(
                                'Cannot remove route to %s in %s',
                                lan_sub_remote_site,
                                mgmt_ip_local_site
                            )
                            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                    else:
                        # Change device state to reboot required
                        success = storage_helper.change_device_state(
                            deviceid=id_local_site,
                            tenantid=tenantid,
                            new_state=(
                                storage_helper.DeviceState.REBOOT_REQUIRED
                            )
                        )
                        if success is False or success is None:
                            logging.error('Error changing the device state')
                            return NbStatusCode.STATUS_INTERNAL_ERROR
                    # update local dictionary
                    tunnel_local.get('reach_subnets').remove(
                        lan_sub_remote_site
                    )
            # Check if there is the fdb entry in remote site for local site
            if tunnel_remote.get('fdb_entry_config') is True:
                # remove route in remote site
                if storage_helper.is_device_connected(
                    deviceid=id_remote_site, tenantid=tenantid
                ):
                    # remove FDB entry in remote site
                    response = self.srv6_manager.delfdbentries(
                        mgmt_ip_remote_site,
                        self.grpc_client_port,
                        ifindex=vtep_name,
                        dst=wan_ip_local_site
                    )
                    if response != SbStatusCode.STATUS_SUCCESS:
                        # If the operation has failed, report an error message
                        logger.warning(
                            'Cannot remove FDB entry %s in %s',
                            wan_ip_local_site,
                            mgmt_ip_remote_site
                        )
                        return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                else:
                    # Change device state to reboot required
                    success = storage_helper.change_device_state(
                        deviceid=id_remote_site,
                        tenantid=tenantid,
                        new_state=(
                            storage_helper.DeviceState.REBOOT_REQUIRED
                        )
                    )
                    if success is False or success is None:
                        logging.error('Error changing the device state')
                        return NbStatusCode.STATUS_INTERNAL_ERROR
                # update local dictionary
                tunnel_remote['fdb_entry_config'] = False
            # Check if there are no more remote subnets
            # reachable from the local site
            if len(tunnel_local.get('reach_subnets')) == 0:
                # Check if there is the fdb entry in local site for remote site
                if tunnel_local.get('fdb_entry_config') is True:
                    # remove FDB entry in local site
                    if storage_helper.is_device_connected(
                        deviceid=id_local_site, tenantid=tenantid
                    ):
                        response = self.srv6_manager.delfdbentries(
                            mgmt_ip_local_site,
                            self.grpc_client_port,
                            ifindex=vtep_name,
                            dst=wan_ip_remote_site
                        )
                        if response != SbStatusCode.STATUS_SUCCESS:
                            # If the operation has failed, report an error
                            # message
                            logger.warning(
                                'Cannot remove FDB entry %s in %s',
                                wan_ip_remote_site,
                                mgmt_ip_local_site
                            )
                            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                    else:
                        # Change device state to reboot required
                        success = storage_helper.change_device_state(
                            deviceid=id_local_site,
                            tenantid=tenantid,
                            new_state=(
                                storage_helper.DeviceState.REBOOT_REQUIRED
                            )
                        )
                        if success is False or success is None:
                            logging.error('Error changing the device state')
                            return NbStatusCode.STATUS_INTERNAL_ERROR
                    # update local dictionary
                    tunnel_local['fdb_entry_config'] = False
        # If there are no more overlay on the devices
        # and destroy data structure, else update it
        if tunnel_local.get('fdb_entry_config') is False and \
                tunnel_remote.get('fdb_entry_config') is False:
            # local site
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid
                },
                {
                    '$pull': {
                        'created_tunnel': {
                            'tunnel_key': tunnel_local.get('tunnel_key')
                        }
                    }
                }
            )
            # remote site
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid
                },
                {
                    '$pull': {
                        'created_tunnel': {
                            'tunnel_key': tunnel_remote.get('tunnel_key')
                        }
                    }
                }
            )
        else:
            # local site
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid,
                    'created_tunnel.tunnel_key': tunnel_local.get('tunnel_key')
                },
                {
                    '$set': {
                        'created_tunnel.$.reach_subnets': tunnel_local.get(
                            'reach_subnets'
                        ),
                        'created_tunnel.$.fdb_entry_config': tunnel_local.get(
                            'fdb_entry_config'
                        )
                    }
                }
            )
            # remote site
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid,
                    'created_tunnel.tunnel_key': tunnel_remote.get(
                        'tunnel_key'
                    )
                },
                {
                    '$set': {
                        'created_tunnel.$.reach_subnets': tunnel_remote.get(
                            'reach_subnets'
                        ),
                        'created_tunnel.$.fdb_entry_config': tunnel_remote.get(
                            'fdb_entry_config'
                        )
                    }
                }
            )

        # Success
        return NbStatusCode.STATUS_OK


    def remove_tunnel_2(self, overlayid, overlay_name, overlay_type,
                          l_slice, r_slice, tenantid, overlay_info,
                          ignore_errors=False):
        # get devices ID
        id_local_site = l_slice['deviceid']
        id_remote_site = r_slice['deviceid']
        # get VNI
        vni = storage_helper.get_vni(
            overlay_name, tenantid
        )
        # get management IP local and remote site
        mgmt_ip_remote_site = storage_helper.get_router_mgmtip(
            id_remote_site, tenantid
        )
        mgmt_ip_local_site = storage_helper.get_router_mgmtip(
            id_local_site, tenantid
        )
        # get WAN interface name for local site and remote site
        # TODO TERMIN* Add support for multiple WAN interfaces (hybrid WAN)
        # wan_intf_local_site = storage_helper.get_wan_interfaces(id_local_site, tenantid)[0]
        # wan_intf_remote_site = storage_helper.get_wan_interfaces(id_remote_site, tenantid)[0]
        underlay_wan_id = storage_helper.get_underlay_wan_id(overlayid, tenantid)
        wan_intf_local_site = storage_helper.get_wan_interface(deviceid=id_local_site, tenantid=tenantid, underlay_wan_id=underlay_wan_id)
        wan_intf_remote_site = storage_helper.get_wan_interface(deviceid=id_remote_site, tenantid=tenantid, underlay_wan_id=underlay_wan_id)
        # transport protocol
        transport_proto = storage_helper.get_overlay(
            overlayid=overlayid, tenantid=tenantid
        )['transport_proto']
        # get external IP address for local site and remote site
        if transport_proto == 'ipv6':
            wan_ip_local_site = storage_helper.get_ext_ipv6_addresses(
                id_local_site, tenantid, wan_intf_local_site
            )
            wan_ip_remote_site = storage_helper.get_ext_ipv6_addresses(
                id_remote_site, tenantid, wan_intf_remote_site
            )
        elif transport_proto == 'ipv4':
            wan_ip_local_site = storage_helper.get_ext_ipv4_addresses(
                id_local_site, tenantid, wan_intf_local_site
            )
            wan_ip_remote_site = storage_helper.get_ext_ipv4_addresses(
                id_remote_site, tenantid, wan_intf_remote_site
            )
        else:
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR


        # get VTEP IP remote site and local site
        if transport_proto == 'ipv6':
            vtep_ip_remote_site = storage_helper.get_vtep_ipv6(
                id_remote_site, tenantid
            )
            vtep_ip_local_site = storage_helper.get_vtep_ipv6(
                id_local_site, tenantid
            )
        elif transport_proto == 'ipv4':
            vtep_ip_remote_site = storage_helper.get_vtep_ip(
                id_remote_site, tenantid
            )
            vtep_ip_local_site = storage_helper.get_vtep_ip(
                id_local_site, tenantid
            )
        else:
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR

        if wan_ip_local_site is not None and len(wan_ip_local_site) > 0:
            wan_ip_local_site = wan_ip_local_site[0].split("/")[0]
        if wan_ip_remote_site is not None and len(wan_ip_remote_site) > 0:
            wan_ip_remote_site = wan_ip_remote_site[0].split("/")[0]
        # get local and remote subnet
        lan_sub_local_sites = storage_helper.get_ip_subnets(
            id_local_site, tenantid, l_slice['interface_name']
        )
        lan_sub_remote_sites = storage_helper.get_ip_subnets(
            id_remote_site, tenantid, r_slice['interface_name']
        )
        # get table ID
        tableid = storage_helper.get_tableid(
            overlayid, tenantid
        )
        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        # get VTEP name
        vtep_name = 'vxlan-%s' % (vni)
        # DB key creation, one per tunnel direction
        key_local_to_remote = '%s__%s' % (id_local_site, id_remote_site)
        key_remote_to_local = '%s__%s' % (id_remote_site, id_local_site)
        # get tunnel dictionaries from DB
        #
        # local site
        tunnel_local = self.overlays.find_one(
            {
                '_id': ObjectId(overlayid),
                'tenantid': tenantid,
                'created_tunnel.tunnel_key': key_local_to_remote
            },
            {
                'created_tunnel.$.tunnel_key': 1
            }
        )['created_tunnel'][0]
        # remote site
        tunnel_remote = self.overlays.find_one(
            {
                '_id': ObjectId(overlayid),
                'tenantid': tenantid,
                'created_tunnel.tunnel_key': key_remote_to_local
            },
            {
                'created_tunnel.$.tunnel_key': 1
            }
        )['created_tunnel'][0]
        # Check if there is the fdb entry in remote site for local site
        if tunnel_remote.get('fdb_entry_config') is True:
            # Check if there is the route for the
            # local subnet in the remote device
            for lan_sub_local_site in lan_sub_local_sites:
                lan_sub_local_site = lan_sub_local_site['subnet']
                if lan_sub_local_site in tunnel_remote.get('reach_subnets'):
                    # remove route in remote site
                    if storage_helper.is_device_connected(
                        deviceid=id_remote_site, tenantid=tenantid
                    ):
                        response = self.srv6_manager.remove_iproute(
                            mgmt_ip_remote_site,
                            self.grpc_client_port,
                            destination=lan_sub_local_site,
                            table=tableid
                        )
                        if response != SbStatusCode.STATUS_SUCCESS:
                            # If the operation has failed, report an error
                            # message
                            logger.warning(
                                'Cannot remove route to %s in %s',
                                lan_sub_local_site,
                                mgmt_ip_remote_site
                            )
                            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                    else:
                        # Change device state to reboot required
                        success = storage_helper.change_device_state(
                            deviceid=id_remote_site,
                            tenantid=tenantid,
                            new_state=(
                                storage_helper.DeviceState.REBOOT_REQUIRED
                            )
                        )
                        if success is False or success is None:
                            logging.error('Error changing the device state')
                            return NbStatusCode.STATUS_INTERNAL_ERROR
                    # update local dictionary
                    tunnel_remote.get('reach_subnets').remove(
                        lan_sub_local_site
                    )
        # Check if the subnet removed is the last subnet
        # in the considered overlay in the local site
        if len(tunnel_remote.get('reach_subnets')) == 0:
            # Check if there is the route for remote subnet in the local site
            for lan_sub_remote_site in lan_sub_remote_sites:
                lan_sub_remote_site = lan_sub_remote_site['subnet']
                if lan_sub_remote_site in tunnel_local.get('reach_subnets'):
                    # remove route in remote site
                    if storage_helper.is_device_connected(
                        deviceid=id_local_site, tenantid=tenantid
                    ):
                        # remove route in local site
                        response = self.srv6_manager.remove_iproute(
                            mgmt_ip_local_site,
                            self.grpc_client_port,
                            destination=lan_sub_remote_site,
                            table=tableid
                        )
                        if response != SbStatusCode.STATUS_SUCCESS:
                            # If the operation has failed, report an error
                            # message
                            logger.warning(
                                'Cannot remove route to %s in %s',
                                lan_sub_remote_site,
                                mgmt_ip_local_site
                            )
                            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                    else:
                        # Change device state to reboot required
                        success = storage_helper.change_device_state(
                            deviceid=id_local_site,
                            tenantid=tenantid,
                            new_state=(
                                storage_helper.DeviceState.REBOOT_REQUIRED
                            )
                        )
                        if success is False or success is None:
                            logging.error('Error changing the device state')
                            return NbStatusCode.STATUS_INTERNAL_ERROR
                    # update local dictionary
                    tunnel_local.get('reach_subnets').remove(
                        lan_sub_remote_site
                    )
            # Check if there is the fdb entry in remote site for local site
            if tunnel_remote.get('fdb_entry_config') is True:
                # remove route in remote site
                if storage_helper.is_device_connected(
                    deviceid=id_remote_site, tenantid=tenantid
                ):
                    # remove FDB entry in remote site
                    response = self.srv6_manager.delfdbentries(
                        mgmt_ip_remote_site,
                        self.grpc_client_port,
                        ifindex=vtep_name,
                        dst=wan_ip_local_site
                    )
                    if response != SbStatusCode.STATUS_SUCCESS:
                        # If the operation has failed, report an error message
                        logger.warning(
                            'Cannot remove FDB entry %s in %s',
                            wan_ip_local_site,
                            mgmt_ip_remote_site
                        )
                        return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                else:
                    # Change device state to reboot required
                    success = storage_helper.change_device_state(
                        deviceid=id_remote_site,
                        tenantid=tenantid,
                        new_state=(
                            storage_helper.DeviceState.REBOOT_REQUIRED
                        )
                    )
                    if success is False or success is None:
                        logging.error('Error changing the device state')
                        return NbStatusCode.STATUS_INTERNAL_ERROR
                # update local dictionary
                tunnel_remote['fdb_entry_config'] = False
            # Check if there are no more remote subnets
            # reachable from the local site
            if len(tunnel_local.get('reach_subnets')) == 0:
                # Check if there is the fdb entry in local site for remote site
                if tunnel_local.get('fdb_entry_config') is True:
                    # remove FDB entry in local site
                    if storage_helper.is_device_connected(
                        deviceid=id_local_site, tenantid=tenantid
                    ):
                        response = self.srv6_manager.delfdbentries(
                            mgmt_ip_local_site,
                            self.grpc_client_port,
                            ifindex=vtep_name,
                            dst=wan_ip_remote_site
                        )
                        if response != SbStatusCode.STATUS_SUCCESS:
                            # If the operation has failed, report an error
                            # message
                            logger.warning(
                                'Cannot remove FDB entry %s in %s',
                                wan_ip_remote_site,
                                mgmt_ip_local_site
                            )
                            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                    else:
                        # Change device state to reboot required
                        success = storage_helper.change_device_state(
                            deviceid=id_local_site,
                            tenantid=tenantid,
                            new_state=(
                                storage_helper.DeviceState.REBOOT_REQUIRED
                            )
                        )
                        if success is False or success is None:
                            logging.error('Error changing the device state')
                            return NbStatusCode.STATUS_INTERNAL_ERROR
                    # update local dictionary
                    tunnel_local['fdb_entry_config'] = False



        # reverse :
        #OK      default_ip_rules___lowest_priority_local_site = storage_helper.decrement_and_get_default_ip_rules___lowest_priority(deviceid=local_site_deviceid, tenantid=tenantid)
        #OK      default_ip_rules___lowest_priority_remote_site = storage_helper.decrement_and_get_default_ip_rules___lowest_priority(deviceid=remote_site_deviceid, tenantid=tenantid)   
        #OK    remote site : response = self.srv6_manager.create_iprule(
        #OK    local site : response = self.srv6_manager.create_iprule(

        #OK    local : response = self.srv6_manager.create_iptables_rule(
        #OK    remote : response = self.srv6_manager.create_iptables_rule(

        #OK    local : success = storage_helper.update_tunnel_mode_interfaces(
        #OK    remote : success = storage_helper.update_tunnel_mode_interfaces(


        # Get the default_iprules_lowest_priority_local_site
        default_iprules_lowest_priority_local_site = storage_helper.get_default_ip_rules___lowest_priority(
                                                    deviceid=id_local_site,tenantid=tenantid,)
        # FIXME Add checking for null default_iprules_lowest_priority_local_site


        # Get the default_iprules_lowest_priority_remote_site

        default_iprules_lowest_priority_remote_site = storage_helper.get_default_ip_rules___lowest_priority(
                                                    deviceid=id_remote_site,tenantid=tenantid,)
        # FIXME Add checking for null default_iprules_lowest_priority_remote_site




        # remove the ip rule in remote site 
        response = self.srv6_manager.remove_iprule(
                mgmt_ip_remote_site,
                self.grpc_client_port,
                table=tableid,
                priority=default_iprules_lowest_priority_remote_site,
                family=AF_INET)
        if response != SbStatusCode.STATUS_SUCCESS:
                logger.warning(
                    '[remote site] Cannot remove the default ip rule that looksUP for the tunnel table %s in %s',
                    tableid,
                    mgmt_ip_remote_site
                )
                return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # remove the ip rule in local site 
        response = self.srv6_manager.remove_iprule(
                mgmt_ip_local_site,
                self.grpc_client_port,
                table=tableid,
                priority=default_iprules_lowest_priority_local_site,
                family=AF_INET)
        if response != SbStatusCode.STATUS_SUCCESS:
                logger.warning(
                    '[local site] Cannot remove the default ip rule that looksUP for the tunnel table %s in %s',
                    tableid,
                    mgmt_ip_local_site
                )
                return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR


        # Removing the iptables rules
        # Remove iptables rule to FORWARD chain in mangle table - local site
        # Used for counting the traffic going through the tunnel
        response = self.srv6_manager.remove_iptables_rule(mgmt_ip_local_site, self.grpc_client_port, table= 'mangle',
                                            chain='FORWARD', target_name='ACCEPT', out_interface=vtep_name)
        if response != SbStatusCode.STATUS_SUCCESS:
            err = "Cannot remove iptables rule [local site]"
            logging.warning(err)
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR

        # Remove iptables rule to FORWARD chain in mangle table - remote site
        # Used for counting the traffic going through the tunnel
        response = self.srv6_manager.remove_iptables_rule(mgmt_ip_remote_site, self.grpc_client_port, table= 'mangle',
                                            chain='FORWARD', target_name='ACCEPT', out_interface=vtep_name)

        if response != SbStatusCode.STATUS_SUCCESS:
            err = "Cannot remove iptables rule [remote site]"
            logging.warning(err)
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR




        # Update the tunnel_mode virtual interfaces in the local site
        success = storage_helper.remove_tunnel_mode_interfaces(tenantid=tenantid, deviceid=id_local_site,
                                            tunnel_mode_name=self.name, tunnel_interface_name=vtep_name ,
                                            tunnel_dst_endpoint= vtep_ip_remote_site)
        if not success:
            err = "Cannot Remove the tunnel_mode virtual interfaces in the local site"
            logging.warning(err)
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR



        # Update the tunnel_mode virtual interfaces in the remote site
        success = storage_helper.remove_tunnel_mode_interfaces(tenantid=tenantid, deviceid=id_remote_site,
                                            tunnel_mode_name=self.name, tunnel_interface_name=vtep_name ,
                                            tunnel_dst_endpoint= vtep_ip_local_site)
        if not success:
            err = "Cannot Remove the tunnel_mode virtual interfaces in the remote site"
            logging.warning(err)
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR




        # Increment defualt_ip_rules lowest priority in the local site edge device
        succ = storage_helper.increment_default_ip_rules___lowest_priority(deviceid=id_local_site, tenantid=tenantid)
        # FIXME add checking for incrementing success.

        # Increment defualt_ip_rules lowest priority in the remote site edge device
        succ = storage_helper.increment_default_ip_rules___lowest_priority(deviceid=id_remote_site, tenantid=tenantid)
        # FIXME add checking for incrementing success.




        # If there are no more overlay on the devices
        # and destroy data structure, else update it
        if tunnel_local.get('fdb_entry_config') is False and \
                tunnel_remote.get('fdb_entry_config') is False:
            # local site
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid
                },
                {
                    '$pull': {
                        'created_tunnel': {
                            'tunnel_key': tunnel_local.get('tunnel_key')
                        }
                    }
                }
            )
            # remote site
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid
                },
                {
                    '$pull': {
                        'created_tunnel': {
                            'tunnel_key': tunnel_remote.get('tunnel_key')
                        }
                    }
                }
            )
        else:
            # local site
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid,
                    'created_tunnel.tunnel_key': tunnel_local.get('tunnel_key')
                },
                {
                    '$set': {
                        'created_tunnel.$.reach_subnets': tunnel_local.get(
                            'reach_subnets'
                        ),
                        'created_tunnel.$.fdb_entry_config': tunnel_local.get(
                            'fdb_entry_config'
                        )
                    }
                }
            )
            # remote site
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid,
                    'created_tunnel.tunnel_key': tunnel_remote.get(
                        'tunnel_key'
                    )
                },
                {
                    '$set': {
                        'created_tunnel.$.reach_subnets': tunnel_remote.get(
                            'reach_subnets'
                        ),
                        'created_tunnel.$.fdb_entry_config': tunnel_remote.get(
                            'fdb_entry_config'
                        )
                    }
                }
            )



        # Success
        return NbStatusCode.STATUS_OK

    def destroy_overlay(self, overlayid, overlay_name,
                        overlay_type, tenantid, deviceid, overlay_info,
                        ignore_errors=False):
        if not storage_helper.is_device_connected(
            deviceid=deviceid, tenantid=tenantid
        ):
            # The device is not connected, we skip it and we schedule a reboot
            #
            # Change device state to reboot required
            success = storage_helper.change_device_state(
                deviceid=deviceid,
                tenantid=tenantid,
                new_state=(
                    storage_helper.DeviceState.REBOOT_REQUIRED
                )
            )
            if success is False or success is None:
                logging.error('Error changing the device state')
                return NbStatusCode.STATUS_INTERNAL_ERROR
            return NbStatusCode.STATUS_OK
        # get device management IP address
        mgmt_ip_site = storage_helper.get_router_mgmtip(
            deviceid, tenantid
        )
        # get VNI
        vni = storage_helper.get_vni(overlay_name, tenantid)
        # get table ID
        tableid = storage_helper.get_tableid(
            overlayid, tenantid
        )
        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        # get VRF name
        vrf_name = 'vrf-%s' % (tableid)
        # get VTEP name
        vtep_name = 'vxlan-%s' % (vni)
        # get VTEP IP address
        if overlay_type == OverlayType.IPv6Overlay:
            vtep_ip_site = storage_helper.get_vtep_ipv6(
                deviceid, tenantid
            )
            vtep_ip_family = AF_INET6
        else:
            vtep_ip_site = storage_helper.get_vtep_ip(
                deviceid, tenantid
            )
            vtep_ip_family = AF_INET
        # get VTEP IP address
        response = self.srv6_manager.remove_ipaddr(
            mgmt_ip_site,
            self.grpc_client_port,
            ip_addr=vtep_ip_site,
            device=vtep_name,
            family=vtep_ip_family
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot remove the address %s of VTEP %s in %s',
                vtep_ip_site,
                vtep_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # remove VTEP
        response = self.srv6_manager.delVxLAN(
            mgmt_ip_site,
            self.grpc_client_port,
            ifname=vtep_name
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot remove VTEP %s in %s',
                vtep_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # remove VRF device
        response = self.srv6_manager.remove_vrf_device(
            mgmt_ip_site,
            self.grpc_client_port,
            name=vrf_name
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot remove VRF %s in %s',
                vrf_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # Success
        return NbStatusCode.STATUS_OK

    def destroy_overlay_2_0(self, overlayid, overlay_name,
                        overlay_type, tenantid, deviceid, overlay_info,
                        ignore_errors=False):
        if not storage_helper.is_device_connected(
            deviceid=deviceid, tenantid=tenantid
        ):
            # The device is not connected, we skip it and we schedule a reboot
            #
            # Change device state to reboot required
            success = storage_helper.change_device_state(
                deviceid=deviceid,
                tenantid=tenantid,
                new_state=(
                    storage_helper.DeviceState.REBOOT_REQUIRED
                )
            )
            if success is False or success is None:
                logging.error('Error changing the device state')
                return NbStatusCode.STATUS_INTERNAL_ERROR
            return NbStatusCode.STATUS_OK
        # get device management IP address
        mgmt_ip_site = storage_helper.get_router_mgmtip(
            deviceid, tenantid
        )
        # get VNI
        vni = storage_helper.get_vni(overlay_name, tenantid)
        # get table ID
        tableid = storage_helper.get_tableid(
            overlayid, tenantid
        )
        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        
        # get VTEP name
        vtep_name = 'vxlan-%s' % (vni)
        
        # get VTEP IP address
        if overlay_type == OverlayType.IPv6Overlay:
            vtep_ip_site = storage_helper.get_vtep_ipv6(
                deviceid, tenantid
            )
            vtep_ip_family = AF_INET6
        else:
            vtep_ip_site = storage_helper.get_vtep_ip(
                deviceid, tenantid
            )
            vtep_ip_family = AF_INET
        # get VTEP IP address
        response = self.srv6_manager.remove_ipaddr(
            mgmt_ip_site,
            self.grpc_client_port,
            ip_addr=vtep_ip_site,
            device=vtep_name,
            family=vtep_ip_family
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot remove the address %s of VTEP %s in %s',
                vtep_ip_site,
                vtep_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # remove VTEP
        response = self.srv6_manager.delVxLAN(
            mgmt_ip_site,
            self.grpc_client_port,
            ifname=vtep_name
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot remove VTEP %s in %s',
                vtep_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # Success
        return NbStatusCode.STATUS_OK

    def destroy_overlay_data(self, overlayid,
                             overlay_name, tenantid, overlay_info,
                             ignore_errors=False):
        # release VNI
        storage_helper.release_vni(overlay_name, tenantid)
        # release tableid
        success = storage_helper.release_tableid(
            overlayid, tenantid)
        if success is not True:
            logger.error(
                'Error while releasing table ID associated to the overlay %s '
                '(tenant %s)',
                overlayid,
                tenantid
            )
        # Success
        return NbStatusCode.STATUS_OK

    def destroy_tunnel_mode(self, deviceid, tenantid, overlay_info,
                            ignore_errors=False):
        # release VTEP IP address if no more VTEP on the EDGE device
        storage_helper.release_vtep_ip(deviceid, tenantid)
        storage_helper.release_vtep_ipv6(deviceid, tenantid)
        # Success
        return NbStatusCode.STATUS_OK



    def destroy_tunnel_mode_2(self, deviceid, tenantid, overlay_info, overlayid, ignore_errors=False):
        # release VTEP IP address on the EDGE device
        # release vtep_ip4
        suc = storage_helper.release_vtep_ip_unique_2(dev_id=deviceid, tenantid=tenantid, overlayid=overlayid)
        # release vtep_ip6
        # TODO release release_vtep_ipv6_unique
        # Success
        return NbStatusCode.STATUS_OK



    def get_overlays(self):
        raise NotImplementedError

    def add_slice_to_overlay_reconciliation(self, overlayid, overlay_name,
                                            deviceid, interface_name, tenantid,
                                            overlay_info):
        # Get device management IP address
        mgmt_ip_site = storage_helper.get_router_mgmtip(
            deviceid, tenantid
        )
        # get table ID
        tableid = storage_helper.get_tableid(
            overlayid, tenantid
        )
        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        # get VRF name
        vrf_name = 'vrf-%s' % (tableid)
        # add slice to the VRF
        response = self.srv6_manager.update_vrf_device(
            mgmt_ip_site,
            self.grpc_client_port,
            name=vrf_name,
            interfaces=[interface_name],
            op='add_interfaces'
        )
        if response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot add interface %s to the VRF %s in %s',
                interface_name,
                vrf_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # Create routes for subnets
        # get subnet for local and remote site
        subnets = storage_helper.get_ip_subnets(
            deviceid, tenantid, interface_name
        )
        for subnet in subnets:
            gateway = subnet['gateway']
            subnet = subnet['subnet']
            if gateway is not None and gateway != '':
                response = self.srv6_manager.create_iproute(
                    mgmt_ip_site,
                    self.grpc_client_port,
                    destination=subnet,
                    gateway=gateway,
                    out_interface=interface_name,
                    table=tableid
                )
                if response == SbStatusCode.STATUS_FILE_EXISTS:
                    logging.warning(
                        'Cannot set route. Route already exists. Skipping'
                    )
                elif response != SbStatusCode.STATUS_SUCCESS:
                    # If the operation has failed, report an error message
                    logger.warning(
                        'Cannot set route for %s (gateway %s) in %s ',
                        subnet,
                        gateway,
                        mgmt_ip_site
                    )
                    return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # Success
        return NbStatusCode.STATUS_OK

    def create_tunnel_reconciliation_l(self, overlayid, overlay_name,
                                       overlay_type, l_slice, r_slice,
                                       tenantid, overlay_info):
        # get devices ID
        id_remote_site = r_slice['deviceid']
        id_local_site = l_slice['deviceid']
        # get management IP address for local and remote site
        mgmt_ip_local_site = storage_helper.get_router_mgmtip(
            l_slice['deviceid'], tenantid
        )
        # get subnet for local and remote site
        lan_sub_remote_sites = storage_helper.get_ip_subnets(
            id_remote_site, tenantid, r_slice['interface_name']
        )
        # get table ID
        tableid = storage_helper.get_tableid(
            overlayid, tenantid
        )
        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        # get VTEP IP remote site and local site
        if overlay_type == OverlayType.IPv6Overlay:
            vtep_ip_remote_site = storage_helper.get_vtep_ipv6(
                id_remote_site, tenantid
            )
        else:
            vtep_ip_remote_site = storage_helper.get_vtep_ip(
                id_remote_site, tenantid
            )
        # get VNI
        vni = storage_helper.get_vni(overlay_name, tenantid)
        # get VTEP name
        vtep_name = 'vxlan-%s' % (vni)

        # get WAN interface name for local site and remote site
        # TODO TERMIN* Add support for multiple WAN interfaces (hybrid WAN)
        # wan_intf_remote_site = storage_helper.get_wan_interfaces(id_remote_site, tenantid)[0]
        underlay_wan_id = storage_helper.get_underlay_wan_id(overlayid, tenantid)
        wan_intf_remote_site = storage_helper.get_wan_interface(deviceid=id_remote_site, tenantid=tenantid, underlay_wan_id=underlay_wan_id)

        

        # transport protocol
        transport_proto = storage_helper.get_overlay(
            overlayid=overlayid, tenantid=tenantid
        )['transport_proto']
        # get external IP address for loal site and remote site
        if transport_proto == 'ipv6':
            wan_ip_remote_site = storage_helper.get_ext_ipv6_addresses(
                id_remote_site, tenantid, wan_intf_remote_site
            )[0].split("/")[0]
        elif transport_proto == 'ipv4':
            wan_ip_remote_site = storage_helper.get_ext_ipv4_addresses(
                id_remote_site, tenantid, wan_intf_remote_site
            )[0].split("/")[0]
        else:
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # DB key creation, one per tunnel direction
        key_local_to_remote = '%s__%s' % (id_local_site, id_remote_site)
        # get tunnel dictionaries from DB
        dictionary_local = self.overlays.find_one(
            {
                '_id': ObjectId(overlayid),
                'tenantid': tenantid,
                'created_tunnel.tunnel_key': key_local_to_remote
            },
            {
                'created_tunnel.$.tunnel_key': 1
            }
        )
        # If it's the first overlay for the devices, create dictionaries
        # else take tunnel info from DB dictionaries
        #
        # local site
        if dictionary_local is None:
            tunnel_local = {
                'tunnel_key': key_local_to_remote,
                'reach_subnets': [],
                'fdb_entry_config': False
            }
        else:
            tunnel_local = dictionary_local['created_tunnel'][0]
        # Check if there is the fdb entry in local site for remote site
        if tunnel_local.get('fdb_entry_config') is False:
            # add FDB entry in local site
            response = self.srv6_manager.addfdbentries(
                mgmt_ip_local_site,
                self.grpc_client_port,
                ifindex=vtep_name,
                dst=wan_ip_remote_site
            )
            if response == SbStatusCode.STATUS_FILE_EXISTS:
                logging.warning(
                    'Cannot set FDB entry. FDB entry already exists. Skipping'
                )
            elif response != SbStatusCode.STATUS_SUCCESS:
                # If the operation has failed, report an error message
                logger.warning(
                    'Cannot add FDB entry %s for VTEP %s in %s',
                    wan_ip_remote_site,
                    vtep_name,
                    mgmt_ip_local_site
                )
                return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
            # update local dictionary
            tunnel_local['fdb_entry_config'] = True
        # set route in local site for the remote subnet, if not present
        for lan_sub_remote_site in lan_sub_remote_sites:
            lan_sub_remote_site = lan_sub_remote_site['subnet']
            if lan_sub_remote_site not in tunnel_local.get('reach_subnets'):
                response = self.srv6_manager.create_iproute(
                    mgmt_ip_local_site,
                    self.grpc_client_port,
                    destination=lan_sub_remote_site,
                    gateway=vtep_ip_remote_site.split("/")[0],
                    table=tableid
                )
                if response == SbStatusCode.STATUS_FILE_EXISTS:
                    logging.warning(
                        'Cannot set route. Route already exists. Skipping'
                    )
                elif response != SbStatusCode.STATUS_SUCCESS:
                    # If the operation has failed, report an error message
                    logger.warning(
                        'Cannot set route for %s in %s ',
                        lan_sub_remote_site,
                        mgmt_ip_local_site
                    )
                    return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
                # update local dictionary with the new subnet in overlay
                tunnel_local.get('reach_subnets').append(lan_sub_remote_site)
        # Insert the device overlay state in DB,
        # if there is already a state update it
        #
        # local site
        new_doc_created = self.overlays.update_one(
            {
                '_id': ObjectId(overlayid),
                'tenantid': tenantid,
                'created_tunnel.tunnel_key': {
                    '$ne': tunnel_local.get('tunnel_key')
                }
            },
            {
                '$push': {
                    'created_tunnel': {
                        'tunnel_key': tunnel_local.get('tunnel_key'),
                        'reach_subnets': tunnel_local.get('reach_subnets'),
                        'fdb_entry_config': tunnel_local.get(
                            'fdb_entry_config'
                        )
                    }
                }
            }
        ).matched_count == 1
        if new_doc_created is False:
            self.overlays.update_one(
                {
                    '_id': ObjectId(overlayid),
                    'tenantid': tenantid,
                    'created_tunnel.tunnel_key': tunnel_local.get('tunnel_key')
                },
                {
                    '$set': {
                        'created_tunnel.$.reach_subnets': tunnel_local.get(
                            'reach_subnets'
                        ),
                        'created_tunnel.$.fdb_entry_config': tunnel_local.get(
                            'fdb_entry_config'
                        )
                    }
                },
                upsert=True)
        # Success
        return NbStatusCode.STATUS_OK

    def create_tunnel_reconciliation_r(self, overlayid, overlay_name,
                                       overlay_type, l_slice, r_slice,
                                       tenantid, overlay_info):
        # Nothing to do
        return NbStatusCode.STATUS_OK

    def init_overlay_reconciliation(self, overlayid, overlay_name,
                                    overlay_type, tenantid, deviceid,
                                    overlay_info):
        # get device management IP address
        mgmt_ip_site = storage_helper.get_router_mgmtip(
            deviceid, tenantid
        )
        # Get vxlan port set by user
        vxlan_port_site = storage_helper.get_tenant_vxlan_port(
            tenantid
        )
        # get table ID
        tableid = storage_helper.get_tableid(
            overlayid, tenantid
        )
        if tableid is None:
            logger.error(
                'Error while getting table ID assigned to the overlay %s',
                overlayid
            )
        # get VRF name
        vrf_name = 'vrf-%s' % (tableid)
        
        # get WAN interface
        # TODO TERMIN* Add support for multiple WAN interfaces (hybrid WAN)
        # wan_intf_site = storage_helper.get_wan_interfaces(deviceid, tenantid)[0]
        underlay_wan_id = storage_helper.get_underlay_wan_id(overlayid, tenantid)
        wan_intf_site = storage_helper.get_wan_interface(deviceid=deviceid, tenantid=tenantid, underlay_wan_id=underlay_wan_id)

        # get VNI for the overlay
        vni = storage_helper.get_vni(overlay_name, tenantid)
        # get VTEP name
        vtep_name = 'vxlan-%s' % (vni)
        # get VTEP IP address
        if overlay_type == OverlayType.IPv6Overlay:
            vtep_ip_site = storage_helper.get_vtep_ipv6(
                deviceid, tenantid
            )
            vtep_ip_family = AF_INET6
        else:
            vtep_ip_site = storage_helper.get_vtep_ip(
                deviceid, tenantid
            )
            vtep_ip_family = AF_INET
        # transport protocol
        transport_proto = storage_helper.get_overlay(
            overlayid=overlayid, tenantid=tenantid
        )['transport_proto']
        # crete VTEP interface
        response = self.srv6_manager.createVxLAN(
            mgmt_ip_site,
            self.grpc_client_port,
            ifname=vtep_name,
            vxlan_link=wan_intf_site,
            vxlan_id=vni,
            vxlan_port=vxlan_port_site,
            vxlan_group='::' if transport_proto == 'ipv6' else '0.0.0.0'
        )
        if response == SbStatusCode.STATUS_FILE_EXISTS:
            logging.warning('Cannot create VTEP. VTEP already exists.Skipping')
        elif response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot create VTEP %s in %s',
                vtep_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # set VTEP IP address
        response = self.srv6_manager.create_ipaddr(
            mgmt_ip_site,
            self.grpc_client_port,
            ip_addr=vtep_ip_site,
            device=vtep_name, net='',
            family=vtep_ip_family
        )
        if response == SbStatusCode.STATUS_FILE_EXISTS:
            logging.warning(
                'Cannot set IP for vtep. IP already exists. Skipping'
            )
        elif response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot set IP %s for VTEP %s in %s',
                vtep_ip_site,
                vtep_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # create VRF and add the VTEP interface
        response = self.srv6_manager.create_vrf_device(
            mgmt_ip_site,
            self.grpc_client_port,
            name=vrf_name,
            table=tableid,
            interfaces=[vtep_name]
        )
        if response == SbStatusCode.STATUS_FILE_EXISTS:
            logging.warning('Cannot create vrf. VRF already exists.Skipping')
        elif response != SbStatusCode.STATUS_SUCCESS:
            # If the operation has failed, report an error message
            logger.warning(
                'Cannot create VRF %s in %s',
                vrf_name,
                mgmt_ip_site
            )
            return NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
        # Success
        return NbStatusCode.STATUS_OK

    def init_overlay_data_reconciliation(self, overlayid,
                                         overlay_name, tenantid,
                                         overlay_info):
        # Success
        return NbStatusCode.STATUS_OK

    def init_tunnel_mode_reconciliation(self, deviceid, tenantid,
                                        overlay_info):
        # Success
        return NbStatusCode.STATUS_OK
