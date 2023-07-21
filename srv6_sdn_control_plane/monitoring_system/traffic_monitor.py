
from srv6_sdn_controller_state import (
    srv6_sdn_controller_state as storage_helper
)

DEFAULT_GRPC_CLIENT_PORT = 12345

class TrafficMonitor():
    def __init__(self, 
                 srv6_manager=None,
                 grpc_client_port=DEFAULT_GRPC_CLIENT_PORT
                 ) :
        self.srv6_manager = srv6_manager
        self.grpc_client_port = grpc_client_port

    def start(self):
        pass 

    def stop(self):
        pass

