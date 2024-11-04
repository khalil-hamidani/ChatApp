import socket # This one to creat and manage sockets
import threading # This one to creat a thread to handle multi users

# Now we creat our chat server class
class ChatServer:
    def __init__(self, host='localhost', port=5000): #? Let the Port be 5000 on the localhost
        # Initialize server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        # Here we store connected clients {client_socket: client_address}
        self.clients = {}

    def start_server(self):
        try:
            # Bind the socket to host and port
            self.server_socket.bind((self.host, self.port))
            
            # Start listening for connections
            self.server_socket.listen(5) # The argument 5 specifies the maximum number of queued connections
            
            print(f"Chat App Server started on {self.host}:{self.port}")
            
            while True: # infinty loop to never stop listning
                # Accept client connection
                client_socket, client_address = self.server_socket.accept()
                print(f"New connection from {client_address}")
                
                # Add client to clients dictionary
                self.clients[client_socket] = client_address
                
                # Create a new thread to handle this client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.start()
                
        except Exception as e:
            print(f"Error starting server: {e}")
        finally:
            self.server_socket.close()

    def handle_client(self, client_socket, client_address):
        try:
            while True:
                # Receive message from client
                message = client_socket.recv(1024).decode('utf-8')
                if not message:
                    # If no message, client has disconnected
                    break
                
                print(f"Message from {client_address}: {message}")
                
                # Here you'll later implement message handling logic
                # For now, we'll just broadcast the message to all clients
                self.broadcast_message(f"{client_address}: {message}", client_socket)
                
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            # Clean up when client disconnects
            self.handle_client_disconnect(client_socket)

    def broadcast_message(self, message, sender_socket=None):
        """Send message to all clients except the sender"""
        for client_socket in self.clients:
            if client_socket != sender_socket:
                try:
                    client_socket.send(message.encode('utf-8'))
                except Exception as e:
                    print(f"Error broadcasting to {self.clients[client_socket]}: {e}")

    def handle_client_disconnect(self, client_socket):
        """Clean up when a client disconnects"""
        if client_socket in self.clients:
            address = self.clients[client_socket]
            print(f"Client {address} disconnected")
            client_socket.close()
            del self.clients[client_socket]

# Create and start the server
if __name__ == "__main__":
    server = ChatServer()
    server.start_server()