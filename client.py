import socket
import threading
import json
import time
from utils import Message, MessageType, MessageParser, Security, format_message

class EnhancedChatClient:
    def __init__(self, host='localhost', port=5500):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.running = False
        self.username = None
        self.connected = threading.Event()

    def connect_to_server(self):
        try:
            self.client_socket.connect((self.host, self.port))
            print("Connected to server")
            self.running = True
            
            # Start receive thread
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Wait for initial connection to be fully established
            time.sleep(0.1)
            
            # Handle authentication and user input
            self.handle_authentication()
            if self.running:
                self.handle_user_input()
                
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.disconnect_from_server()

    def handle_authentication(self):
        """Handle the authentication process with the server"""
        try:
            # Wait for welcome message
            self.connected.wait(timeout=5.0)  # Wait up to 5 seconds for welcome message
            
            # Get username from user
            while not self.username and self.running:
                username = input().strip()
                if MessageParser.validate_username(username):
                    self.username = username
                    self.client_socket.send(username.encode('utf-8'))
                else:
                    print("Invalid username format. Please use 3-16 characters, only letters, numbers, underscore, and hyphen.")
                    
        except Exception as e:
            print(f"Error during authentication: {e}")
            self.running = False

    def receive_messages(self):
        """Receive and process messages from the server"""
        while self.running:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data:
                    print("Lost connection to server")
                    self.running = False
                    break
                
                # Parse and format message
                msg = Message.from_json(data)
                
                # Set connected event when we receive the welcome message
                if msg.type == MessageType.SYSTEM and "Welcome!" in msg.content:
                    self.connected.set()
                
                formatted_msg = format_message(msg)
                print(formatted_msg)
                
                # If we receive an error during authentication, allow another username attempt
                if msg.type == MessageType.ERROR and not self.username:
                    continue
                
            except json.JSONDecodeError as e:
                print(f"Received invalid message format: {data}")
                print(f"Error: {e}")
            except Exception as e:
                print(f"Error receiving message: {e}")
                self.running = False
                break

    def handle_user_input(self):
        """Handle user input and commands"""
        print("\nChat commands:")
        print("\n".join([f"{cmd}: {desc}" for cmd, desc in MessageParser.COMMANDS.items()]))
        print("\nStart chatting (type '/quit' to exit):")
        
        while self.running:
            try:
                message = input()
                if message.lower() == '/quit':
                    self.disconnect_from_server()
                    break
                    
                if message:
                    self.send_message(message)
                    
            except KeyboardInterrupt:
                self.disconnect_from_server()
                break
            except Exception as e:
                print(f"Error sending message: {e}")
                self.disconnect_from_server()
                break

    def send_message(self, message):
        """Send a message to the server"""
        try:
            # Sanitize input
            message = Security.sanitize_input(message)
            self.client_socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending message: {e}")
            self.running = False

    def disconnect_from_server(self):
        """Disconnect from the server"""
        print("Disconnecting from server...")
        self.running = False
        try:
            self.client_socket.close()
        except Exception as e:
            print(f"Error disconnecting: {e}")

if __name__ == "__main__":
    client = EnhancedChatClient()
    client.connect_to_server()