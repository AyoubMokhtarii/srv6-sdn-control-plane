from srv6_sdn_controller_state import (
    srv6_sdn_controller_state as storage_helper
)



import logging
import threading
import time

from srv6_sdn_proto.status_codes_pb2 import Status, NbStatusCode, SbStatusCode

from srv6_sdn_proto.srv6_vpn_pb2 import TenantReply, OverlayServiceReply

# Status codes
STATUS_OK = NbStatusCode.STATUS_OK
STATUS_BAD_REQUEST = NbStatusCode.STATUS_BAD_REQUEST
STATUS_INTERNAL_SERVER_ERROR = NbStatusCode.STATUS_INTERNAL_SERVER_ERROR

from socket import AF_INET



DEFAULT_GRPC_CLIENT_PORT = 12345

DEFAULT_ADAPT_INTERVAL = 1 # seconds



# FIXME : tunnel cost is global for now.
tunnel_1_cost = 1
tunnel_2_cost = 2
SIZE=6
td=[None for _ in range(SIZE)]
MANGLETABLE = "mangle"
PREROUTINGCHAIN = "PREROUTING"


# ======================================================================================================

class TrafficAdaptation:
    """
    This class is responsible for automaticaly adapting the traffic acording to the defined applications requirements and SLA.
    It is a Singleton class.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, 
                 
                 srv6_manager=None,
                 grpc_client_port=DEFAULT_GRPC_CLIENT_PORT,
                 adapt_frequency=DEFAULT_ADAPT_INTERVAL
                 ):
        # FIXME add the support for multiple tenants (NB: class is singleton).
        self.tenantid = "1"
        self.adapt_frequency = adapt_frequency
        self.srv6_manager = srv6_manager
        self.grpc_client_port = grpc_client_port

        
        
        self._thread = None
        self._stop_event = threading.Event()
        self._running_flag = False


    def start(self):
        success = False
        if self._thread is None or not self._thread.is_alive():
            
            self._thread = threading.Thread(
                    target=self._run_traffic_adaptation_algorithm, 
                    kwargs={'tenantid': self.tenantid},
                    daemon=True)
            
            self._running_flag = True
            self._thread.start()
            success = True
        return success


    def stop(self):
        success = False

        logging.info("Stopping the traffic adaptation algorithm ...")

        # if self._thread is not None and self._thread.is_alive():
        self._running_flag = False
        self._stop_event.set()
        
        success = True
        return success
    

    def _run_traffic_adaptation_algorithm(self, tenantid):

        logging.info("Starting the traffic adaptation algorithm ...")

        client = storage_helper.get_mongodb_session()

        # FIXME for testing purpose only, get the device 1
        ewED1 = storage_helper.get_device_by_name(name='ewED1', tenantid=tenantid)
        deviceid = ewED1['deviceid']
      
        one_time = False
        while self._running_flag:
            time.sleep(0.1)

            application_identifiers = storage_helper.get_application_identifiers(client=client,tenantid='1', mode='dynamic')

            threshold, rules = get_app_rules(application_identifiers)



            tunnels_delay_vector, threshold = get_state(client, tenantid, deviceid, threshold)

            

            if tunnels_delay_vector is None or threshold is None or tunnels_delay_vector[5] is None:
                111/0
                


            # if not one_time:
            #     logging.info("tunnels_delay_vector")
            #     logging.info(tunnels_delay_vector)

            #     logging.info("threshold")
            #     logging.info(threshold)

            # logging.info("type(tunnels_delay_vector[5])")
            # logging.info(type(tunnels_delay_vector[5]))


            

            if float(tunnels_delay_vector[5]) >= float(threshold) and not one_time:
                logging.info("type(threshold)")
                logging.info(type(threshold))

                logging.info("threshold")
                logging.info(threshold)

                logging.info("changing tunnel ...")

                tunnel_name = 'vxlan-2'
                self.change_tunnel(choosentunnel=tunnel_name, tenantid=tenantid, deviceid=deviceid,
                                   device=ewED1, table=MANGLETABLE, chain=PREROUTINGCHAIN, rules=rules)
                
                one_time = True

            



    
    def _create_application_traffic_identifier(self, tenantid, deviceid, device, paths, table, chain, protocol, 
                                                source_ip, destination_ip, source_port, destination_port):

        if len(paths) == 1:
            # Add the Traffic identifier rule to route the traffic through the overlay (the overlay over the underlay_wan_id== path[0])
            # Get the table id of the specific overlay
            underlay_wan_id = paths[0]
            table_id = storage_helper.get_tableid_of_overlay_in_device(tenantid, deviceid, underlay_wan_id)
            
            # Check if the overlay exists
            if table_id == None:
                err = ('There is no overlay created over the underlay %s in device %s (tenantid %s)',underlay_wan_id, deviceid, tenantid)
                logging.warning(err)
                return OverlayServiceReply(
                    status=Status(code=STATUS_BAD_REQUEST, reason=err)
                )
            
            # The target is "MARK" in the mangle table
            # target value to mark packets with the overlay tableid to route traffic matching the rule to the overlay
            target_name = "MARK"
            target_value = str(table_id)


            logging.info("\n\ntarget_value")
            logging.info(target_value)

            logging.info("device['mgmtip']")
            logging.info(device['mgmtip'])

            logging.info("self.grpc_client_port")
            logging.info(self.grpc_client_port)

            logging.info("table")
            logging.info(table)

            logging.info("chain")
            logging.info(chain)

            logging.info("target_name")
            logging.info(target_name)

            logging.info("target_value")
            logging.info(target_value)

            logging.info("protocol")
            logging.info(protocol)

            logging.info("source_ip")
            logging.info(source_ip)

            logging.info("destination_ip")
            logging.info(destination_ip)

            logging.info("source_port")
            logging.info(source_port)




            response = self.srv6_manager.create_iptables_rule(device['mgmtip'],self.grpc_client_port,table=table ,
                                                chain=chain, target_name=target_name,target_value=target_value,
                                                protocol=protocol, source_ip=source_ip, destination_ip=destination_ip, 
                                                source_port=source_port, destination_port=destination_port, rule_match = {}
                                                )
            
            logging.info("response")
            logging.info(response)
        
            if response != SbStatusCode.STATUS_SUCCESS:
                err = "Cannot create iptables rule [1]"
                logging.warning(err)
                return OverlayServiceReply(
                        status=Status(code=STATUS_INTERNAL_SERVER_ERROR, reason=err)
                    )
            

            
            specific_ip_rules___lowest_priority = storage_helper.decrement_and_get_specific_ip_rules___lowest_priority(deviceid= device["deviceid"], tenantid=tenantid)

            # Create ip rule to route the traffic marked with target_value to the overlay
            response = self.srv6_manager.create_iprule(
                device['mgmtip'],
                self.grpc_client_port,
                table=target_value,
                fwmark=target_value,
                priority=specific_ip_rules___lowest_priority,
                family=AF_INET
                )
            
            if response != SbStatusCode.STATUS_SUCCESS:
                # If the operation has failed, report an error message
                err = (
                    'Cannot Create ip rule to route the traffic marked with target_value to the overlay fwmark %s ; table %s',
                    target_value,
                    target_value
                )
                logging.warning(err)
                return OverlayServiceReply(
                        status=Status(code=NbStatusCode.STATUS_INTERNAL_SERVER_ERROR, reason=err)
                    )


        else :
            raise NotImplementedError("The implementation of load balancing for more than 2 paths is not implemented yet.")
        

        logging.info('All the intents have been processed successfully\n\n')
        # Create the response
        return OverlayServiceReply(
            status=Status(code=STATUS_OK, reason='OK')
        )


    def change_tunnel(self, choosentunnel, tenantid, deviceid, device, table, chain, rules):

    
        # tunnel_name = 'vxlan-2'
        tunnel_name=choosentunnel

        protocol = rules['protocol']
        source_ip = rules['source_ip']
        destination_ip = rules['destination_ip']
        source_port = rules['source_port']
        destination_port = rules['destination_port']

        



        paths = [get_underlay_wan_id_from_tunnel_name(tunnel_name)]

        # logging.info("protocol")
        # logging.info(protocol)
        # logging.info("source_ip")
        # logging.info(source_ip)
        # logging.info("destination_ip")
        # logging.info(destination_ip)
        # logging.info("source_port")
        # logging.info(source_port)
        # logging.info("destination_port")
        # logging.info(destination_port)
        # logging.info("paths")
        # logging.info(paths)
        # logging.info("table")
        # logging.info(table)
        # logging.info("chain")
        # logging.info(chain)



        self._create_application_traffic_identifier(tenantid=tenantid, deviceid=deviceid, device=device, 
                                        paths=paths, table=table, chain=chain, protocol=protocol, 
                                        source_ip=source_ip, destination_ip=destination_ip, source_port=source_port, destination_port=destination_port)




def get_underlay_wan_id_from_tunnel_name(tunnel_name):
    # FIXME this function is just for testing purpose
    # this underlay_wan_id should be retrieved from the database
    return 'WAN-1'

    if tunnel_name == 'vxlan-2':
        return 'WAN-1'
    elif tunnel_name == 'vxlan-3':
        return 'WAN-2'
    else :
        return None



def get_state(client, tenantid, deviceid, threshold):

    tunnels_delay = storage_helper.get_device_delay_history_stats(tenantid=tenantid, deviceid=deviceid, client=client, max_history=3)

    # logging.info('\n\ntunnels_delay')
    # logging.info(tunnels_delay)
    

    tunnels_delay_vector = __get_tunnels_delay_vector(tunnels_delay)

    # logging.info("\n\ntunnels_delay_vector")
    # logging.info(tunnels_delay_vector)
    
    

    # logging.info("\n\nthreshold")
    # logging.info(threshold)

    # if tunnels_delay_vector is not None:
    #     pass

    return tunnels_delay_vector, threshold

    # logging.info("\n\napplication_identifiers")
    # logging.info(application_identifiers)



def __get_tunnels_delay_vector(tunnels_delay):
    td = [None, None, None, None, None, None]
    
    if tunnels_delay is not None :
        for t in tunnels_delay:
            if t['tunnel_name'] == 'vxlan-2':
                td[0]= t['tunnel_delay_history_stats'][0]
                td[1]= t['tunnel_delay_history_stats'][-2]
                td[2]= t['tunnel_delay_history_stats'][-1]

            elif t['tunnel_name'] == 'vxlan-3':
                td[3]= t['tunnel_delay_history_stats'][-3]
                td[4]= t['tunnel_delay_history_stats'][-2]
                td[5]= t['tunnel_delay_history_stats'][-1]
            else: 
                # FIXME for test purpose, we use only 2 FIXED tunnels.
                raise NotImplementedError()
    else : 
        return None
    return td
            


def get_app_rules(application_identifiers):
    threshold = None
    rules = None    
    if application_identifiers:
        for application_identifier in application_identifiers:


            # logging.info(application_identifier)


            threshold = application_identifier['path']['delay_threshold']
            rules = application_identifier['rules']

            # FIXME : for testing purpose we are taking only the first appIdentifier
            break
    

    return threshold, rules
