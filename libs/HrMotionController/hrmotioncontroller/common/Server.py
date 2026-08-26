import socket
import json
import threading
from .Motion import MotionBase, AxisBase, MotionStatus
from .Client import ParseSocketJson
from .Controller import Controller

class MotionServerBase:
    def __init__(self, ip='127.0.0.1', port=8080, **kwargs):
        self.ip = ip
        self.port = port
        self.server_thread = None
        self.server_sockopt_value = kwargs.get('sockopt_value', 1)
        self.server_sockopt_backlog = kwargs.get('sockopt_backlog', 5)
        self.server_socket:socket.socket = None
        self.receive_buffer_size = kwargs.get('receive_buffer_size', 1024)
        self.client_sockets:list[socket.socket] = []
        self.client_socket_parses:dict[str, ParseSocketJson] = {}
        self.running = False
        self._debug = kwargs.get('debug', True)
        self.dataMap = {}
        self.dataLock = threading.Lock()

    def __del__(self):
        self.stop()

    def handle_client(self, client_socket:socket.socket, address):
        try:
            while True:
                data = client_socket.recv(self.receive_buffer_size)
                if not data:
                    break
                self.process_client_msg(client_socket, data)
        except Exception as e:
            if self._debug:
                print(f"Error with client {address}: {e}")
        finally:
            if self._debug:
                print(f"Closing connection with {address}")
            client_socket.close()
            self.client_sockets.remove(client_socket)
            self.client_socket_parses.pop(str(address), None)

    def _on_start(self):
        if self._debug:
            print(f"Server started on {self.ip}:{self.port}")
        try:
            self.running = True
            while self.running:
                client_socket, address = self.server_socket.accept()
                if self._debug:
                    print(f"Connection established with {address}")
                self.client_sockets.append(client_socket)
                self.client_socket_parses[str(address)] = ParseSocketJson(self._generate_receive_callback(client_socket))  # Initialize a parser for the client socket
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.start()
        except KeyboardInterrupt:
            if self._debug:
                print("Shutting down server...")
        except Exception as e:
            if self._debug:
                print(f"Server error: {e}")
        finally:
            self.server_socket = None
            self.running = False

    def is_running(self):
        return self.running

    def start(self):
        if self.server_socket is None and (self.server_thread is None or not self.server_thread.is_alive()):
            try:
                self.server_socket:socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, self.server_sockopt_value)
                self.server_socket.bind((self.ip, self.port))
                self.server_socket.listen(self.server_sockopt_backlog)
                
                self.server_thread = threading.Thread(target=self._on_start)
                self.server_thread.daemon = True
                self.server_thread.start()
                
                if self._debug:
                    print("Server thread started.")
            except Exception as e:
                if self._debug:
                    print(f"Failed to start server: {e}")
        else:
            if self._debug:
                print("Server is already running.")

    def stop(self):
        if self.running:
            self.running = False
            
            self.server_socket.close()
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join()
            self.server_socket = None
            
            if self._debug:
                print("Server stopped.")
        else:
            if self._debug:
                print("Server is not running.")
        
    def process_client_msg(self, client_socket:socket.socket, message:bytes):
        """Process a message received from a client."""
        parse_obj = self.client_socket_parses.get(str(client_socket.getpeername()), None)
        if parse_obj is not None:
            parse_obj.handle_received_msg(message)
        else:
            if self._debug:
                print(f"No parser found for client {client_socket.getpeername()}. Message: {message}")
            
    def handle_message(self, client_socket:socket.socket, message:dict):
        """Handle a message received from a client."""
        # This method should be overridden in subclasses to handle specific messages.
        pass
    
    def send_response(self, client_socket:socket.socket, response:dict):
        """Send a JSON response to the client."""
        try:
            json_response = json.dumps(response).encode('utf-8')
            client_socket.sendall(json_response)
            if self._debug:
                print(f"Sent response to {client_socket.getpeername()}: {response}")
        except Exception as e:
            if self._debug:
                print(f"Error sending response: {e}")
                
    def broadcast(self, message: dict):
        """Broadcast a JSON message to all connected clients."""
        try:
            json_message = json.dumps(message).encode('utf-8')
            for client_socket in self.client_sockets:
                try:
                    client_socket.sendall(json_message)
                    if self._debug:
                        print(f"Broadcasted message to {client_socket.getpeername()}: {message}")
                except Exception as e:
                    if self._debug:
                        print(f"Error sending broadcast to {client_socket.getpeername()}: {e}")
        except Exception as e:
            if self._debug:
                print(f"Error broadcasting message: {e}")
     
    def _generate_receive_callback(self, client_socket:socket.socket):
        """Generate a callback function for receiving messages from a client."""
        def receive_callback(message:dict):
            self.handle_message(client_socket, message)
        return receive_callback
        
class MotionServer(MotionServerBase):
    def __init__(self, ip='127.0.0.1', port=8080, **kwargs):
        super().__init__(ip, port, **kwargs)
        self._motion:MotionBase = kwargs.get('motion', None)
        self._motion_status:MotionStatus = kwargs.get('status', None)
        
        self.controller = Controller()
        self.controller.set_motion(self._motion)
        self.controller.status = self._motion_status
        
        self._events = {}
        self.handle_controller_event = None
        
        self.register_event_handler("motion_status", self.__motion_status)
        self.register_event_handler("set_output", self.__motion_set_output)
        self.register_event_handler("axis_init", self.__axis_init)
        self.register_event_handler("axis_enable", self.__axis_enable)
        self.register_event_handler("axis_disable", self.__axis_disable)
        self.register_event_handler("axis_setvalue", self.__axis_setvalue)
        self.register_event_handler("axis_getvalue", self.__axis_getvalue)
        self.register_event_handler("axis_home", self.__axis_home)
        self.register_event_handler("axis_move_absolute", self.__axis_move_absolute)
        self.register_event_handler("axis_move_relative", self.__axis_move_relative)
        self.register_event_handler("axis_continuous_move", self.__axis_continuous_move)
        self.register_event_handler("axis_stop", self.__axis_stop)
        self.register_event_handler("axis_set_mpos", self.__axis_set_mpos)
        self.register_event_handler("axis_set_velocity", self.__axis_set_velocity)
        self.register_event_handler("axis_set_soft_limit", self.__axis_set_soft_limit)
        self.register_event_handler("axis_get_soft_limit", self.__axis_get_soft_limit)
        self.register_event_handler("axis_get_alarm", self.__axis_get_alarm)
        self.register_event_handler("axis_get_stop_reason", self.__axis_get_stop_reason)
        self.register_event_handler("axis_get_hard_limit", self.__axis_get_hard_limit)
        self.register_event_handler("axis_pause", self.__axis_pause)
        self.register_event_handler("axis_resume", self.__axis_resume)
        self.register_event_handler("controller_event", self.__controller_event)
        self.register_event_handler("datamap_read", self.__datamap_read)
        self.register_event_handler("datamap_write", self.__datamap_write)
        self.register_event_handler("datamap_get", self.__datamap_get)
        self.register_event_handler("datamap_set", self.__datamap_set)
        
    def start_controller(self):
        """Start the controller thread."""
        self.controller.start()
        
    def stop_controller(self):
        """Stop the controller thread."""
        self.controller.stop()
        
    def set_motion(self, motion):
        """Set the motion controller instance."""
        self._motion = motion
        self.controller.set_motion(self._motion)
        
    @property
    def motion(self):
        """Get the motion controller instance."""
        return self._motion
    
    def set_controller_event(self, handler):
        """Set the controller event handler."""
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self.handle_controller_event = handler
    
    def set_motion_status(self, status:MotionStatus):
        """Set the current motion status."""
        self._motion_status = status
        self.controller.status = self._motion_status
        
    @property
    def motion_status(self):
        """Get the current motion status."""
        return self._motion_status

    def gen_failed_response(self, message:str):
        """Generate a failure response."""
        return json.dumps({
            "header": "error",
            "message": message
        })
    
    def handle_message(self, client_socket:socket.socket, message:dict):
        if self._motion is None:
            if self._debug:
                print("No motion controller set.")
            client_socket.sendall(self.gen_failed_response("No motion controller set.").encode('utf-8'))
        else:
            try:
                if 'header' in message and message['header'] in self._events:
                    event_handler = self._events[message['header']]
                    if callable(event_handler):
                        ret = event_handler(message)
                        if ret is not None:
                            response, success = ret
                            if response:
                                response['success'] = success
                                client_socket.sendall(json.dumps(response).encode('utf-8'))
                    else:
                        if self._debug:
                            print(f"No callable handler for event: {message['header']}")
                        client_socket.sendall(self.gen_failed_response(f"No handler for event: {message['header']}").encode('utf-8'))
            except Exception as e:
                if self._debug:
                    print(f"Error handling message: {e}")
                client_socket.sendall(self.gen_failed_response(str(e)).encode('utf-8'))
                
    def register_event_handler(self, event_name:str, handler):
        """Register an event handler for a specific event."""
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self._events[event_name] = handler
        
    def unregister_event_handler(self, event_name:str):
        """Unregister an event handler for a specific event."""
        if event_name in self._events:
            del self._events[event_name]
        else:
            if self._debug:
                print(f"No handler registered for event: {event_name}")
    
    def clear_event_handlers(self):
        """Clear all registered event handlers."""
        self._events.clear()
        if self._debug:
            print("All event handlers cleared.")
            
    def __motion_status(self, message:dict):
        """Get the current status of the motion controller."""
        success = False 
        if self._motion_status is not None:
            message['data'] = self._motion_status.to_dict()
            message['status'] = "Motion status retrieved successfully."
            success = True
        else:
            message['status'] = "No motion status available."
        return message, success
    
    def __motion_set_output(self, message:dict) -> tuple[dict, bool]:
        """Set the output of the motion controller."""
        success = False
        name = message.get('name', None)
        value = message.get('value', None)
        
        if self._motion is None:
            message['status'] = "No motion controller set."
            return message, success
        
        if name is None or value is None:
            message['status'] = "Output ID or value not provided."
            return message, success
        
        try:
            self._motion.set_output(name, value)
            message['status'] = f"Output {name} set to {value} successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def check_axis(self, message:dict) -> tuple[dict, AxisBase]:
        if self._motion is None:
            message['status'] = "No motion controller set."
            return message, None
        
        axis_name = message.get('axis_id', None)
        if axis_name is None:
            message['status'] = "Axis ID not provided."
            return message, None
        
        axis_id = self._motion_status.axis_table.get(axis_name, None)
        if axis_id is None:
            message['status'] = f"Axis {axis_name} not found in motion status."
            return message, None
        
        axis = self._motion.get_axis(axis_id)
        if axis is None:
            message['status'] = f"Axis {axis_id} not found."
            return message, None
        
        return message, axis
    
    def __axis_init(self, message:dict):
        """Initialize the axes of the motion controller."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success 
        
        params = message.get('params', {})
        try:
            axis.init(**params)
            message['status'] = "Axis initialized successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success

    def __axis_enable(self, message:dict):
        """Enable an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success 
        
        try:
            axis.enable()
            message['status'] = "Axis enabled successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success 
    
    def __axis_disable(self, message:dict):
        """Disable an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success 
        
        try:
            axis.disable()
            message['status'] = "Axis disabled successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __axis_setvalue(self, message:dict):
        """Set the value of an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success 
        
        params = message.get('params', {})
        
        try:
            axis.setvalue(**params)
            message['status'] = "Axis moved successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __axis_getvalue(self, message:dict):
        """Get the current value of an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success 
        
        key = message.get('key', None)
        if key is None:
            message['status'] = "Key not provided."
            return message, success
        
        params = message.get('params', {})
        
        try:
            value = axis.getvalue(key, **params)
            message['data'] = value
            message['status'] = "Axis value retrieved successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success

    def __axis_home(self, message:dict):
        """Home an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success 
        
        try:
            axis.home()
            message['status'] = "Axis homed successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __axis_move_absolute(self, message:dict):
        """Move an axis to an absolute position."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success 
        
        if not axis.is_enabled():
            message['status'] = "Axis is not enabled."
            return message, success

        # if not axis.is_homed():
        #     message['status'] = "Axis is not homed."
        #     return message, success
        
        if not axis.idle():
            message['status'] = "Axis is not idle."
            return message, success
        
        position = message.get('position', None)
        if position is None:
            message['status'] = "Position not provided."
            return message, success
        
        velocity = message.get('velocity', None)
        if velocity is None:
            message['status'] = "Velocity not provided."
            return message, success
        
        try:
            axis.move_absolute(position, velocity)
            message['status'] = "Axis moved to absolute position successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __axis_move_relative(self, message:dict):
        """Move an axis to a relative position."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success  
        
        if not axis.is_enabled():
            message['status'] = "Axis is not enabled."
            return message, success
        
        if not axis.idle():
            message['status'] = "Axis is not idle."
            return message, success
        
        distance = message.get('distance', None)
        if distance is None:
            message['status'] = "Distance not provided."
            return message, success
        
        velocity = message.get('velocity', None)
        if velocity is None:
            message['status'] = "Velocity not provided."
            return message, success
        
        try:
            axis.move_relative(distance, velocity)
            message['status'] = "Axis moved to relative position successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __axis_continuous_move(self, message:dict):
        """Move an axis continuously."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success 
        
        if not axis.is_enabled():
            message['status'] = "Axis is not enabled."
            return message, success
        
        if not axis.idle():
            message['status'] = "Axis is not idle."
            return message, success
        
        direction = message.get('direction', None)
        if direction is None:
            message['status'] = "Direction not provided."
            return message, success
        
        velocity = message.get('velocity', None)
        if velocity is None:
            message['status'] = "Velocity not provided."
            return message, success
        
        try:
            axis.continuous_move(direction, velocity)
            message['status'] = "Axis continuous move started successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success

    def __axis_stop(self, message:dict):
        """Stop an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success  
        
        try:
            axis.stop()
            message['status'] = "Axis stopped successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __axis_set_mpos(self, message:dict):
        """Set the machine position of an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success 
        
        position = message.get('position', None)
        if position is None:
            message['status'] = "Position not provided."
            return message, success
        
        try:
            axis.set_mpos(position)
            message['status'] = "Machine position set successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __axis_set_velocity(self, message:dict):
        """Set the velocity of an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success 
        
        velocity = message.get('velocity', None)
        if velocity is None:
            message['status'] = "Velocity not provided."
            return message, success
        
        try:
            axis.set_velocity(velocity)
            message['status'] = "Axis velocity set successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)

        return message, success

    def __axis_set_soft_limit(self, message:dict):
        """Set the soft limit of an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success

        min_position = message.get('min_position', None)
        max_position = message.get('max_position', None)
        if min_position is None and max_position is None:
            message['status'] = "Soft limit not provided."
            return message, success

        try:
            axis.set_soft_limit(min_position=min_position, max_position=max_position)
            message['status'] = "Axis soft limit set successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)

        return message, success

    def __axis_get_soft_limit(self, message:dict):
        """Get the soft limit of an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success

        try:
            min_position, max_position = axis.get_soft_limit()
            message['data'] = {'min_position': min_position, 'max_position': max_position}
            message['status'] = "Axis soft limit retrieved successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)

        return message, success

    def __axis_get_alarm(self, message:dict):
        """Get the alarm state of an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success

        try:
            message['data'] = axis.get_alarm()
            message['status'] = "Axis alarm state retrieved successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)

        return message, success

    def __axis_get_stop_reason(self, message:dict):
        """Get the stop reason of an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success

        try:
            message['data'] = axis.get_stop_reason()
            message['status'] = "Axis stop reason retrieved successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)

        return message, success

    def __axis_get_hard_limit(self, message:dict):
        """Get the hard limit configuration of an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success

        try:
            (fwd_port, fwd_level), (rev_port, rev_level) = axis.get_hard_limit()
            message['data'] = {
                'fwd': {'port': fwd_port, 'level': fwd_level},
                'rev': {'port': rev_port, 'level': rev_level}
            }
            message['status'] = "Axis hard limit retrieved successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)

        return message, success

    def __axis_pause(self, message:dict):
        """Pause an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success

        try:
            axis.pause()
            message['status'] = "Axis paused successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)

        return message, success

    def __axis_resume(self, message:dict):
        """Resume an axis."""
        success = False
        message, axis = self.check_axis(message)
        if axis is None:
            return message, success

        try:
            axis.resume()
            message['status'] = "Axis resumed successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)

        return message, success

    def __controller_event(self, message:dict):
        """Handle controller events."""
        success = False
        try:
            if not self.handle_controller_event:
                message['status'] = "No controller event handler set."
                return message, success
            
            success, message = self.handle_controller_event(self, message)
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __datamap_read(self, message:dict):
        """Read a value from the data map."""
        success = False
        key = message.get('key', None)
        if key is None:
            message['status'] = "Key not provided."
            return message, success
        
        try:
            with self.dataLock:
                value = self.dataMap.get(key, None)
            message['data'] = value
            message['status'] = "Data map value retrieved successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __datamap_write(self, message:dict):
        """Write a value to the data map."""
        success = False
        key = message.get('key', None)
        value = message.get('value', None)
        if key is None or value is None:
            message['status'] = "Key or value not provided."
            return message, success
        
        try:
            with self.dataLock:
                self.dataMap[key] = value
            self.datamap_write_handle(key, value)
            message['status'] = "Data map value set successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __datamap_get(self, message:dict):
        """Get the entire data map."""
        success = False
        try:
            message['data'] = self.dataMap
            message['status'] = "Data map retrieved successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def __datamap_set(self, message:dict):
        """Set the entire data map."""
        success = False
        data = message.get('data', None)
        if data is None or not isinstance(data, dict):
            message['status'] = "Data map not provided or invalid."
            return message, success
        
        try:
            with self.dataLock:
                for key, value in data.items():
                    self.dataMap[key] = value
            message['status'] = "Data map set successfully."
            success = True
        except Exception as e:
            message['status'] = str(e)
        
        return message, success
    
    def datamap_write_handle(self, key, value):
        pass
    
    def read_data(self, key):
        with self.dataLock:
            var = self.dataMap.get(key, None)
        return var
        
    def write_data(self, key, value):
        if self.dataMap[key] == value:
            return
        with self.dataLock:
            self.dataMap[key] = value
        message = {
            "header": "data_change",
            "key": key,
            "value": value
        }
        self.broadcast(message)
