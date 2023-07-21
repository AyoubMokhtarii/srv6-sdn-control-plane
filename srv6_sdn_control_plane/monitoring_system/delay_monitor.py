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
                    target=self._run_overlay_network_tunnels_delay_measurements, 
                    kwargs={'tenantid': self.tenantid},
                    daemon=True)
            
            self.measurementThreads= {}
            self._running_flag = True
            self._thread.start()
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


    def _check_device_delay_monitor_thread(self, deviceid):
        device_measurement_thread = self.measurementThreads.get(deviceid)
        if device_measurement_thread is not None:
            if device_measurement_thread.is_alive():
                # The tread is still alive
                return True
      
        return False
    
    def _check_device_configuration(self, device):
        # Check if the device is configured and connected and enabled.
        # Check if there is at least one overlay tunnel configured.
        return device['configured'] and device['connected'] and device['enabled'] \
            and (len(device['stats']['counters']['tunnels']) > 0)

    
    def _measure_device_tunnels_delay(self, tenantid, device):

        device_vxlan_tunnels = []
            
        # TODO add other overlay tunnel mode (e.g. GRE, SRV6) \
        # Currently only VXLAN is supported.
        for device_tunnel in device['stats']['counters']['tunnels']:
            if device_tunnel['tunnel_mode'] == 'VXLAN':
                for interf in device_tunnel['tunnel_mode_interfaces']:
                    tunnel = dict()
                    tunnel['tunnel_interface_name'] = interf['tunnel_interface_name']
                    tunnel['tunnel_dst_endpoint'] = interf['tunnel_dst_endpoint'].split('/')[0]   
                    device_vxlan_tunnels.append(tunnel)

        





        while self._running_flag:

            

            response, stats = self.srv6_manager.get_tunnel_delay(
                            server_ip=device['mgmtip'],
                            server_port =self.grpc_client_port,
                            tunnels =device_vxlan_tunnels
                            )
            if response != SbStatusCode.STATUS_SUCCESS:
                err = "Cannot get device tunnels delay  (device : " + device['name'] + " )"
                logging.warning(err)
                continue

            else:
                

                for stat in stats:
                    storage_helper.insert_delay_to_delayHistoryStats(
                        tenantid=tenantid,
                        deviceid=device['deviceid'],
                        device_name=device['name'],
                        tunnel_name=stat['tunnel_interface_name'],
                        instant_tunnel_delay=stat['tunnel_delay']
                        )
                    
            time.sleep(self.delay_measurement_interval)
        




    def _run_overlay_network_tunnels_delay_measurements(self, tenantid):

        # FIXME the devices list not updated in the while loop. 
        # => Update the devices list or Restart the measurement each time a device is connected.
        # Get the devices of the tenant.
        devices = storage_helper.get_devices_by_tenantid(tenantid)
        configured_devices = []

        # Get only configured devices.
        for device in devices:
            # check if the device is configured and connected and enabled \
            # and has at least one overlay tunnel configured.
            if self._check_device_configuration(device):
                configured_devices.append(device)

            

        try:
            while self._running_flag:
                for device in configured_devices:
                   
                    # Check if the measurement thread is not running, and start it if not running.
                    if not self._check_device_delay_monitor_thread(deviceid=device['deviceid']):

                        thread = threading.Thread(
                            target=self._measure_device_tunnels_delay,
                            kwargs=({
                                'tenantid': tenantid,
                                'device': device,

                                    })
                                )
                        
                        thread.daemon = True
                        #Update the mapping 
                        self.measurementThreads[device['deviceid']] = thread
                        thread.start()

                time.sleep(5)

        except KeyboardInterrupt:
            
            self.stop()