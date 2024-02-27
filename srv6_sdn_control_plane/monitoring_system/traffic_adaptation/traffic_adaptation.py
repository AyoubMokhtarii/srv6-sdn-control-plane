from srv6_sdn_controller_state import (
    srv6_sdn_controller_state as storage_helper
)


import logging
import threading
import time
import sys 
import os

# import torch
# import torch.nn as nn
# import torch.nn.functional as F
import numpy as np

from srv6_sdn_proto.status_codes_pb2 import Status, NbStatusCode, SbStatusCode
from srv6_sdn_proto.srv6_vpn_pb2 import TenantReply, OverlayServiceReply



from socket import AF_INET

# THIS_FILE_PATH = os.path.abspath(__file__)
# CONTAINING_FOLDER = os.path.dirname(THIS_FILE_PATH)

sys.path.insert(0, '/home/ayoub/Desktop/_EVERY-WAN_workspace/ew_controller/src/srv6-sdn-control-plane/srv6_sdn_control_plane/monitoring_system/traffic_adaptation/DQN_agent/utils')
from utils import load_trained_model, DQN





# Status codes
STATUS_OK = NbStatusCode.STATUS_OK
STATUS_BAD_REQUEST = NbStatusCode.STATUS_BAD_REQUEST
STATUS_INTERNAL_SERVER_ERROR = NbStatusCode.STATUS_INTERNAL_SERVER_ERROR


DEFAULT_GRPC_CLIENT_PORT = 12345

DEFAULT_ADAPT_INTERVAL = 1 # seconds


# if GPU is to be used
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")



SIZE=6
td=[None for _ in range(SIZE)]
MANGLETABLE = "mangle"
PREROUTINGCHAIN = "PREROUTING"









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
        
        self.tenantid = "1"
        self.adapt_frequency = adapt_frequency
        self.srv6_manager = srv6_manager
        self.grpc_client_port = grpc_client_port

        
        
        self._thread = None
        self._stop_event = threading.Event()
        self._running_flag = False

        self._choosen_tunnel = 1


    def start(self):
        # success = False
        # if self._thread is None or not self._thread.is_alive():
            
        #     self._thread = threading.Thread(
        #             target=self._run_traffic_adaptation_algorithm, 
        #             kwargs={'tenantid': self.tenantid},
        #             daemon=True)
            
        #     self._running_flag = True
        #     self._thread.start()
        #     success = True
        # return success
        logging.debug("NOT Implemented Yet.")
        return False


    def stop(self):
        # success = False

        # logging.info("Stopping the traffic adaptation algorithm ...")

        # # if self._thread is not None and self._thread.is_alive():
        # self._running_flag = False
        # self._stop_event.set()
        
        # success = True
        # return success
        logging.debug("NOT Implemented Yet.")
        return False
    

    # def _run_traffic_adaptation_algorithm(self, tenantid):

    #     logging.info("Starting the traffic adaptation algorithm ...")

    #     client = storage_helper.get_mongodb_session()

    #     ewED1 = storage_helper.get_device_by_name(name='ewED1', tenantid=tenantid)
    #     deviceid = ewED1['deviceid']

    #     tunnels_cost = [1, 2]
        

    #     policy_model_net = load_trained_model()
      
    #     while self._running_flag:
    #         time.sleep(0.1)

    #         application_identifiers = storage_helper.get_application_identifiers(client=client,tenantid='1', mode='dynamic')

    #         threshold, rules = get_app_rules(application_identifiers)

    #         if threshold is None:
    #             logging.error("Application SLA Threshold is None. At least one application with delay Threshold should be defined.")
    #             raise Exception()



    #         state = self.get_state(client, tenantid, deviceid, threshold, tunnels_cost)

    #         state = torch.tensor(state, dtype=torch.float32, device=device).unsqueeze(0)

    #         tunnel_update = policy_model_net(state).max(1)[1].view(1, 1)


            
    #         if self._choosen_tunnel != tunnel_update.item():
    #             logging.debug("\n\n ===========> changing tunnel ...")
    #             logging.debug("old tunnel : %s", self._choosen_tunnel)
    #             logging.debug("new tunnel : %s", tunnel_update.item())
                

    #             self._choosen_tunnel = tunnel_update.item()


    #             self.change_tunnel(choosentunnel=self._choosen_tunnel, tenantid=tenantid, deviceid=deviceid,
    #                                device=ewED1, table=MANGLETABLE, chain=PREROUTINGCHAIN, rules=rules)

    
#     def _create_application_traffic_identifier(self, tenantid, deviceid, device, paths, table, chain, protocol, 
#                                                 source_ip, destination_ip, source_port, destination_port):

#         if len(paths) == 1:
#             # Add the Traffic identifier rule to route the traffic through the overlay (the overlay over the underlay_wan_id== path[0])
#             # Get the table id of the specific overlay
#             underlay_wan_id = paths[0]
#             table_id = storage_helper.get_tableid_of_overlay_in_device(tenantid, deviceid, underlay_wan_id)
            
#             # Check if the overlay exists
#             if table_id == None:
#                 err = ('There is no overlay created over the underlay %s in device %s (tenantid %s)',underlay_wan_id, deviceid, tenantid)
#                 logging.warning(err)
#                 return OverlayServiceReply(
#                     status=Status(code=STATUS_BAD_REQUEST, reason=err)
#                 )
            
#             # The target is "MARK" in the mangle table
#             # target value to mark packets with the overlay tableid to route traffic matching the rule to the overlay
#             target_name = "MARK"
#             target_value = str(table_id)


#             response = self.srv6_manager.create_iptables_rule(device['mgmtip'],self.grpc_client_port,table=table ,
#                                                 chain=chain, target_name=target_name,target_value=target_value,
#                                                 protocol=protocol, source_ip=source_ip, destination_ip=destination_ip, 
#                                                 source_port=source_port, destination_port=destination_port, rule_match = {}
#                                                 )
            
        
#             if response != SbStatusCode.STATUS_SUCCESS:
#                 err = "Cannot create iptables rule [1]"
#                 logging.warning(err)
#                 return OverlayServiceReply(
#                         status=Status(code=STATUS_INTERNAL_SERVER_ERROR, reason=err)
#                     )
            

            
#             specific_ip_rules___lowest_priority = storage_helper.decrement_and_get_specific_ip_rules___lowest_priority(deviceid= device["deviceid"], tenantid=tenantid)

#             # Create ip rule to route the traffic marked with target_value to the overlay
#             response = self.srv6_manager.create_iprule(
#                 device['mgmtip'],
#                 self.grpc_client_port,
#                 table=target_value,
#                 fwmark=target_value,
#                 priority=specific_ip_rules___lowest_priority,
#                 family=AF_INET
#                 )
            
#             if response != SbStatusCode.STATUS_SUCCESS:
#                 # If the operation has failed, report an error message
#                 err = (
#                     'Cannot Create ip rule to route the traffic marked with target_value to the overlay fwmark %s ; table %s',
#                     target_value,
#                     target_value
#                 )
#                 logging.warning(err)
#                 return OverlayServiceReply(
#                         status=Status(code=NbStatusCode.STATUS_INTERNAL_SERVER_ERROR, reason=err)
#                     )


#         else :
#             raise NotImplementedError("The implementation of load balancing for more than 2 paths is not implemented yet.")
        

#         logging.info('All the intents have been processed successfully\n\n')
#         # Create the response
#         return OverlayServiceReply(
#             status=Status(code=STATUS_OK, reason='OK')
#         )


#     def change_tunnel(self, choosentunnel, tenantid, deviceid, device, table, chain, rules):
#         assert type(choosentunnel) == int
#         if choosentunnel == 0 :
#             paths = ['WAN-1']
#         elif choosentunnel == 1 :
#             paths = ['WAN-2']

#         protocol = rules['protocol']
#         source_ip = rules['source_ip']
#         destination_ip = rules['destination_ip']
#         source_port = rules['source_port']
#         destination_port = rules['destination_port']

#         self._create_application_traffic_identifier(tenantid=tenantid, deviceid=deviceid, device=device, 
#                                         paths=paths, table=table, chain=chain, protocol=protocol, 
#                                         source_ip=source_ip, destination_ip=destination_ip, source_port=source_port, destination_port=destination_port)


#     def get_state(self, client, tenantid, deviceid, threshold, tunnels_cost):
    
#         tunnels_delay = storage_helper.get_device_delay_history_stats(tenantid=tenantid, deviceid=deviceid, client=client, max_history=3)
    
#         tunnels_delay_vector = get_tunnels_delay_vector(tunnels_delay)
    
#         if tunnels_delay_vector is None:
#             logging.error("Cant get current tunnels delay vector. You should start delay monitoring first.")
#             raise Exception()
        

#         current_tunnels_delay_threshold_diff = np.array(tunnels_delay_vector) - threshold
#         current_tunnels_delay_threshold_diff = current_tunnels_delay_threshold_diff.astype(np.float32)
    
#         tmp_tunnels_cost = np.array(tunnels_cost)
#         max_cost = np.max(tmp_tunnels_cost)
#         normal_tunnels_cost = tmp_tunnels_cost / max_cost
#         normal_tunnels_cost = normal_tunnels_cost.astype(np.float32)
    
#         choosen_tunnel_float = np.float32([self._choosen_tunnel])

#         state = np.concatenate((choosen_tunnel_float, current_tunnels_delay_threshold_diff, normal_tunnels_cost), axis=0, dtype=np.float32)
        
    
#         return state
    



# def get_tunnels_delay_vector(tunnels_delay):
#     td = [None, None, None, None, None, None]
    
#     if tunnels_delay is None :
#         return None
    
#     for t in tunnels_delay:
#         if t['tunnel_name'] == 'vxlan-2':
#             td[0]= np.float32(t['tunnel_delay_history_stats'][0])
#             td[1]= np.float32(t['tunnel_delay_history_stats'][-2])
#             td[2]= np.float32(t['tunnel_delay_history_stats'][-1])
#         elif t['tunnel_name'] == 'vxlan-3':
#             td[3]= np.float32(t['tunnel_delay_history_stats'][-3])
#             td[4]= np.float32(t['tunnel_delay_history_stats'][-2])
#             td[5]= np.float32(t['tunnel_delay_history_stats'][-1])
#         else: 
#             raise NotImplementedError()
        

#     return td
            

# def get_app_rules(application_identifiers):
#     threshold = None
#     rules = None    
#     if application_identifiers:
#         for application_identifier in application_identifiers:

#             threshold = application_identifier['path']['delay_threshold']
#             rules = application_identifier['rules']
#             break
    

#     return np.float32(threshold), rules




