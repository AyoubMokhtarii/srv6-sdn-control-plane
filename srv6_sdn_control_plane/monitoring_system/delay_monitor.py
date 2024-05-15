from srv6_sdn_controller_state import (
    srv6_sdn_controller_state as storage_helper
)



import logging
import threading
import time

from srv6_sdn_proto.status_codes_pb2 import Status, NbStatusCode, SbStatusCode

from srv6_sdn_proto.srv6_vpn_pb2 import TenantReply, OverlayServiceReply

STATUS_INTERNAL_SERVER_ERROR = NbStatusCode.STATUS_INTERNAL_SERVER_ERROR
STATUS_OK = NbStatusCode.STATUS_OK


DEFAULT_GRPC_CLIENT_PORT = 12345

DEFAULT_DELAY_MEASUREMENT_INTERVAL = 0.1 # seconds


# class DelayMonitor():
#     def __init__(self, 
#                  srv6_manager=None,
#                  grpc_client_port=DEFAULT_GRPC_CLIENT_PORT
#                  ) :
#         self.srv6_manager = srv6_manager
#         self.grpc_client_port = grpc_client_port

#     def start(self):
#         tenantid = "1"
        
#         self.measure_overlay_network_tunnels_delay(tenantid)
        

#         return OverlayServiceReply(
#             status=Status(code=STATUS_OK, reason='OK')
#         )

#     def stop(self) -> None:
#         pass


#     def _measure_device_tunnels_delay(self, tenantid, device,srv6_manager):
#         # check if the device is configured and connected and enabled
#         if device['configured'] == False \
#             or device['connected'] == False \
#             or device['enabled'] == False:
#             return

#         # Check if there is at least one overlay tunnel configured
#         if len(device['stats']['counters']['tunnels']) == 0:
#             return
        
        
#         tunnels = []
#         for device_tunnel in device['stats']['counters']['tunnels']:
            
#             # TODO add other overlay tunnel mode (e.g. GRE, SRV6)
#             # Currently only VXLAN is supported
#             if device_tunnel['tunnel_mode'] == 'VXLAN':
#                 for interf in device_tunnel['tunnel_mode_interfaces']:
#                     tunnel = dict()
#                     tunnel['tunnel_interface_name'] = interf['tunnel_interface_name']
#                     tunnel['tunnel_dst_endpoint'] = interf['tunnel_dst_endpoint'].split('/')[0]   
#                     tunnels.append(tunnel) 

#         response, stats = srv6_manager.get_tunnel_delay(
#                         server_ip=device['mgmtip'],
#                         server_port =self.grpc_client_port,
#                         tunnels =tunnels
#                         )
#         if response != SbStatusCode.STATUS_SUCCESS:
#             err = "Cannot get tunnel delay for device: " + device['name']
#             logging.warning(err)
#             return
        
#         for stat in stats:
#             storage_helper.insert_delay_to_delayHistoryStats(
#                 tenantid=tenantid,
#                 deviceid=device['deviceid'],
#                 device_name=device['name'],
#                 tunnel_name=stat['tunnel_interface_name'],
#                 instant_tunnel_delay=stat['tunnel_delay']
#             )


            
#     def measure_overlay_network_tunnels_delay(self, tenantid):
#         devices = storage_helper.get_devices_by_tenantid(tenantid)
#         threads = []
#         for device in devices:
#             thread = threading.Thread(target=self._measure_device_tunnels_delay, args=(device, tenantid, self.srv6_manager))
#             threads.append(thread)
#             thread.start()
        


    

#     def measure_overlay_network_tunnels_delay_x(self, tenantid):
#         """
#         Measure the delay of the overlay network tunnels,
#         and add the measurements to delay history in database. 
#         """
#         # Get all registered devices
#         devices = storage_helper.get_devices_by_tenantid(tenantid)
#         for device in devices:
#             # check if the device is configured and connected and enabled
#             if device['configured'] == False \
#                     or device['connected'] == False \
#                     or device['enabled'] == False:
#                 continue

#             # Check if there is at least one overlay tunnel configured
#             if len(device['stats']['counters']['tunnels']) == 0:
#                 continue

#             # TODO add other overlay tunnel mode (e.g. GRE, SRV6)
#             # Currently only VXLAN is supported
#             tunnels = []
#             for device_tunnel in device['stats']['counters']['tunnels']:
                
#                 if device_tunnel['tunnel_mode'] != 'VXLAN':
#                     continue 
#                 else: # VXLAN
#                     for interf in device_tunnel['tunnel_mode_interfaces']:
                    
#                         tunnel = dict()
#                         tunnel['tunnel_interface_name'] = interf['tunnel_interface_name']
#                         tunnel['tunnel_dst_endpoint'] = interf['tunnel_dst_endpoint'].split('/')[0]   
#                         tunnels.append(tunnel)

#                         # # FIXME remove this just for testing -----------------------
#                         # logging.info("\n\n\nNnNnNnNnNnNnNnNnNnNnNnNnNnNnNnNn")
#                         # logging.info(device['name'])
#                         # logging.info(tunnel['tunnel_interface_name'])
#                         # logging.info(tunnel['tunnel_dst_endpoint'])
#                         # logging.info("NnNnNnNnNnNnNnNnNnNnNnNnNnNnNnNn\n\n\n")
#                         # # FIXME remove this just for testing -----------------------

#             response, stats = self.srv6_manager.get_tunnel_delay(
#                         server_ip=device['mgmtip'],
#                         server_port =self.grpc_client_port,
#                         tunnels =tunnels
#                         )
            

#             if response != SbStatusCode.STATUS_SUCCESS:
#                 err = "Cannot get tunnel delay for device: " + device['name']
#                 logging.warning(err)
#                 return OverlayServiceReply(
#                         status=Status(code=STATUS_INTERNAL_SERVER_ERROR, reason=err)
#                     )
            
#             for stat in stats:

#                 storage_helper.insert_delay_to_delayHistoryStats(
#                 tenantid=tenantid,
#                 deviceid=device['deviceid'],
#                 device_name=device['name'],
#                 tunnel_name=stat['tunnel_interface_name'],
#                 instant_tunnel_delay=stat['tunnel_delay'] 
#             )
            


# ======================================================================================================

class NetworkDelayMonitoring:
    """
    This class is responsible for monitoring the overlay network delay.
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
                 delay_measurement_interval=DEFAULT_DELAY_MEASUREMENT_INTERVAL
                 ):
        # FIXME add support for multiple tenants.
        self.tenantid = "1"
        self.delay_measurement_interval = DEFAULT_DELAY_MEASUREMENT_INTERVAL # FIXME this should take value from init parameters.
        self.srv6_manager = srv6_manager
        self.grpc_client_port = grpc_client_port

        # FIXME add the support for multiple tenants (NB: class is singleton).
        
        self._thread = None
        self.measurementThreads= {}
        self._stop_event = threading.Event()
        self._running_flag = False

    def start(self):
        success = False
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                    target=self._start_devices_delay_monitoring, 
                    kwargs={'tenantid': self.tenantid},
                    daemon=True)
            self.measurementThreads= {}
            self._thread.start()
            self._running_flag = True
            success = True
        return success

    def stop(self):
        success = False
        # if self._thread is not None and self._thread.is_alive():
        self._running_flag = False
        self._stop_event.set()
        for thread in self.measurementThreads.values():
            thread.join()
        self.measurementThreads= {}
        success = True
        return success


    def _start_devices_delay_monitoring(self, tenantid):
        UPDATE_RATE = 10
        try:
            # check if new device added each UPDATE_RATE seconds.
            while self._running_flag:
                devices={}
                devices = get_devices(tenantid=tenantid, return_dict=True)

                for dev_id in devices:
                    _device=devices[dev_id]
                    if not self._check_device_thread(deviceid=_device["deviceid"]):
                        thread = threading.Thread(
                            target=self._measure_device_tunnels_2,
                            kwargs=({'tenantid': tenantid,'device': _device,}))

                        thread.daemon = True
                        #Update the mapping 
                        self.measurementThreads[_device["deviceid"]] = thread
                        thread.start()



                time.sleep(UPDATE_RATE)

        except KeyboardInterrupt:
            self.stop()

    def _check_device_thread(self, deviceid):
        device_measurement_thread = self.measurementThreads.get(deviceid)
        if device_measurement_thread is not None:
            if device_measurement_thread.is_alive():
                # The tread is still alive
                return True
        return False

    def _measure_device_tunnels_2(self, tenantid, device):
        UPDATE_RATE = 10
        checking_overlay_updates_counter = 0
        while self._running_flag:
            device_tunnels=[]
            if checking_overlay_updates_counter % UPDATE_RATE == 0:
                overlay_intf_name_map = {}
                overlays =  storage_helper.get_overlays(tenantid=tenantid)
                for overlay in overlays :
                    tunnels_hashes=[]
                    for created_tunnel in overlay["created_tunnel"]:
                        # Get only the one direction of an overlay tunnel.
                        tunnel_key = created_tunnel["tunnel_key"]
                        tunnel_hash = tunnel_key_hash(tunnel_key) 
                        key1, key2 = tunnel_key.split('__')
                        if tunnel_hash in tunnels_hashes:
                            continue
                        tunnels_hashes.append(tunnel_hash)
                        if key1 == device['deviceid']:
                            device_tunnels.append(
                                {
                                    "tunnel_interface_name": created_tunnel["tunnel_interface_name"],
                                    "tunnel_dst_endpoint": created_tunnel["tunnel_dst_endpoint"].split('/')[0],
                                }
                            )
                            overlay_intf_name_map[created_tunnel["tunnel_interface_name"]] = {
                                "tunnel_intf_name" : created_tunnel["tunnel_interface_name"],
                                "overlay_id": overlay["_id"], 
                                "tunnel_key" : tunnel_key
                            }
                checking_overlay_updates_counter = 0 
            if len(device_tunnels)>0:
                devicename= device["name"]
                msg = f'Requesting device <{devicename}> tunnels delay.'
                logging.debug(msg)
                logging.debug("device_tunnels")
                logging.debug(device_tunnels)


                response, stats = self.srv6_manager.get_tunnel_delay(
                                server_ip=device['mgmtip'],
                                server_port =self.grpc_client_port,
                                tunnels=device_tunnels
                                )
                if response != SbStatusCode.STATUS_SUCCESS:
                    err = "Cannot get device tunnels delay  (device : " + device['name'] + " )"
                    logging.warning(err)
                    continue
                else:
                    for stat in stats:
                        storage_helper.insert_delay_to_delayHistoryStats_2(
                            tenantid=tenantid,
                            deviceid=device['deviceid'],
                            device_name=device['name'],
                            tunnel_name=stat['tunnel_interface_name'],
                            instant_tunnel_delay=stat['tunnel_delay'],
                            tunnel_dst_endpoint= stat['tunnel_dst_endpoint'],
                            overlay_id= overlay_intf_name_map[str(stat['tunnel_interface_name'])]["overlay_id"],
                            tunnel_key= overlay_intf_name_map[str(stat['tunnel_interface_name'])]["tunnel_key"]
                            )

            time.sleep(self.delay_measurement_interval)
            checking_overlay_updates_counter +=1
        

    # def _check_device_delay_monitor_thread(self, deviceid):
    #     device_measurement_thread = self.measurementThreads.get(deviceid)
    #     if device_measurement_thread is not None:
    #         if device_measurement_thread.is_alive():
    #             # The tread is still alive
    #             return True
      
    #     return False

    # def _check_device_configuration(self, device):
    #     # Check if the device is configured and connected and enabled.
    #     # Check if there is at least one overlay tunnel configured.
    #     return device['configured'] and device['connected'] and device['enabled'] \
    #         and (len(device['stats']['counters']['tunnels']) > 0)
    
    # def _measure_device_tunnels_delay(self, tenantid, device):

    #     device_vxlan_tunnels = []
            
    #     # TODO add other overlay tunnel mode (e.g. GRE, SRV6) \
    #     # Currently only VXLAN is supported.
    #     for device_tunnel in device['stats']['counters']['tunnels']:
    #         if device_tunnel['tunnel_mode'] == 'VXLAN':
    #             for interf in device_tunnel['tunnel_mode_interfaces']:
    #                 tunnel = dict()
    #                 tunnel['tunnel_interface_name'] = interf['tunnel_interface_name']
    #                 tunnel['tunnel_dst_endpoint'] = interf['tunnel_dst_endpoint'].split('/')[0]   
    #                 device_vxlan_tunnels.append(tunnel)

    #     while self._running_flag:

    #         response, stats = self.srv6_manager.get_tunnel_delay(
    #                         server_ip=device['mgmtip'],
    #                         server_port =self.grpc_client_port,
    #                         tunnels =device_vxlan_tunnels
    #                         )
    #         if response != SbStatusCode.STATUS_SUCCESS:
    #             err = "Cannot get device tunnels delay  (device : " + device['name'] + " )"
    #             logging.warning(err)
    #             continue

    #         else:

    #             for stat in stats:
    #                 storage_helper.insert_delay_to_delayHistoryStats(
    #                     tenantid=tenantid,
    #                     deviceid=device['deviceid'],
    #                     device_name=device['name'],
    #                     tunnel_name=stat['tunnel_interface_name'],
    #                     instant_tunnel_delay=stat['tunnel_delay']
    #                     )
                    
    #         time.sleep(self.delay_measurement_interval)
        
    # def _run_overlay_network_tunnels_delay_measurements(self, tenantid):

    #     # FIXME the devices list not updated in the while loop. 
    #     # => Update the devices list or Restart the measurement each time a device is connected.
    #     # Get the devices of the tenant.
    #     devices = storage_helper.get_devices_by_tenantid(tenantid)
    #     configured_devices = []

    #     # Get only configured devices.
    #     for device in devices:
    #         # check if the device is configured and connected and enabled \
    #         # and has at least one overlay tunnel configured.
    #         if self._check_device_configuration(device):
    #             configured_devices.append(device)

            

    #     try:
    #         while self._running_flag:
    #             for device in configured_devices:
                   
    #                 # Check if the measurement thread is not running, and start it if not running.
    #                 if not self._check_device_delay_monitor_thread(deviceid=device['deviceid']):

    #                     thread = threading.Thread(
    #                         target=self._measure_device_tunnels_delay,
    #                         kwargs=({
    #                             'tenantid': tenantid,
    #                             'device': device,

    #                                 })
    #                             )
                        
    #                     thread.daemon = True
    #                     #Update the mapping 
    #                     self.measurementThreads[device['deviceid']] = thread
    #                     thread.start()

    #             time.sleep(5)

    #     except KeyboardInterrupt:
            
    #         self.stop()


