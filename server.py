import socket
import threading
from colorama import Fore, Style # type: ignore
from utils import Message, MessageType, MessageParser, logging, Security, RateLimiter, ChatRoom, format_message  # noqa: F401

class EnhancedChatServer:
    def __init__(self, host='localhost', port=3000):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.host = host
        self.port = port
        self.clients = {}  # {client_socket: (address, username)}
        self.rooms = {}    # {room_name: ChatRoom}
        self.rate_limiter = RateLimiter()
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler('chat_server.log'),  # Creates/opens chat_server.log file
                logging.StreamHandler()                  # Handles console output
            ]
        )
        # Create and assign logger to instance
        self.logger = logging.getLogger(__name__)
        
        # Create default room
        self.rooms['main'] = ChatRoom('main', "Main chat room")

    def start_server(self):
            try:
                self.logger.info("Starting The [ChatApp] Server.....")
                self.server_socket.bind((self.host, self.port))
                self.server_socket.listen(5)
                print(f"Chat Server started on {self.host}:{self.port}")

                while True:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"New connection from {client_address}")

                    # Send welcome message immediately after connection
                    welcome_msg = Message(
                        type=MessageType.SYSTEM,
                        content="Welcome to the server! Please enter your username:",
                        sender="System"
                    )
                    try:
                        client_socket.send(welcome_msg.to_json().encode('utf-8'))
                    except Exception as e:
                        print(f"Error sending welcome message: {e}")
                        client_socket.close()
                        continue

                    # Start authentication process
                    auth_thread = threading.Thread(
                        target=self.handle_client_authentication,
                        args=(client_socket, client_address)
                    )
                    auth_thread.daemon = True
                    auth_thread.start()

            except Exception as e:
                print(f"Error starting server: {e}")
            finally:
                self.server_socket.close()

    def handle_client_authentication(self, client_socket, client_address):
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                self.logger.info(f"Client {client_address} disconnected during authentication")
                client_socket.close()
                return

            username = Security.sanitize_input(data.strip())
            
            if not MessageParser.validate_username(username):
                self.logger.warning(f"Invalid username attempt: {username} from {client_address}")
                error_msg = Message(
                    type=MessageType.ERROR,
                    content="Invalid username format. Connection rejected.",
                    sender="System"
                )
                client_socket.send(error_msg.to_json().encode('utf-8'))
                client_socket.close()
                return
            
            if any(username == client_data[1] for client_data in self.clients.values()):
                self.logger.warning(f"Duplicate username attempt: {username} from {client_address}")
                error_msg = Message(
                    type=MessageType.ERROR,
                    content="Username already taken. Please try another one.",
                    sender="System"
                )
                client_socket.send(error_msg.to_json().encode('utf-8'))
                client_socket.close()
                return

            self.clients[client_socket] = (client_address, username)
            self.rooms['main'].users.add(username)
            
            self.logger.info(f"User {username} ({client_address}) authenticated successfully")
            
            success_msg = Message(
                type=MessageType.SYSTEM,
                content=f"Welcome {username}! You have joined the chat.",
                sender="System"
            )
            client_socket.send(success_msg.to_json().encode('utf-8'))

            join_msg = Message(
                type=MessageType.JOIN,
                content=f"{username} joined the chat",
                sender=username,
                room="main"
            )
            self.broadcast_message(join_msg, exclude_socket=client_socket)
            
            self.handle_client(client_socket)
                
        except Exception as e:
            self.logger.error(f"Authentication error for {client_address}: {e}")
            if client_socket:
                client_socket.close()
    #foncton ta3 zebi
    def change_username(self, client_socket, new_username):
        current_username = self.clients[client_socket][1]
        new_username = Security.sanitize_input(new_username.strip())

        # Check if the new username is valid
        if not MessageParser.validate_username(new_username):
            error_msg = Message(
                type=MessageType.ERROR,
                content=Fore.RED+"Invalid username format. Please try again."+Style.RESET_ALL,
                sender="System"
            )
            client_socket.send(error_msg.to_json().encode('UTF-8'))
            return

        # Check if the new username is already in use
        if any(new_username == client_data[1] for client_data in self.clients.values()):
            error_msg = Message(
                type=MessageType.ERROR,
                content="Username already taken. Please choose another one.",
                sender="System"
            )
            client_socket.send(error_msg.to_json().encode('UTF-8'))
            return

        # Update the username in the clients dictionary
        self.clients[client_socket] = (self.clients[client_socket][0], new_username)

        # Find the current room of the user and update the username
        current_room = next((room for room in self.rooms.values() if current_username in room.users), None)
        if current_room:
            current_room.users.remove(current_username)
            current_room.users.add(new_username)

        # Send confirmation message to the client
        success_msg = Message(
            type=MessageType.CHANGE,
            content=f"Your username has been changed to {new_username}.",
            sender="System",
            room=current_room.name if current_room else "main"
        )
        client_socket.send(success_msg.to_json().encode('utf-8'))

        # Notify other users about the username change
        change_msg = Message(
            type=MessageType.CHANGE,
            content=f"{current_username} has changed their username to {new_username}.",
            sender="System",
            room="main"
        )
        self.broadcast_to_room(change_msg, room_name="main", exclude_socket=client_socket)

        self.logger.info(f"User {current_username} changed username to {new_username}")

    def list_room_users(self, client_socket: socket.socket) -> None:
        username = self.clients[client_socket][1]
        current_room = None
        
        # Find user's current room
        for room in self.rooms.values():
            if username in room.users:
                current_room = room
                break
                
        if current_room:
            user_list = sorted(current_room.users)
            msg = Message(
                type=MessageType.SYSTEM,
                content=f"Users in {current_room.name}:\n" + "\n".join(user_list),
                sender="System"
            )
            client_socket.send(msg.to_json().encode('utf-8'))
            
    def join_room(self, client_socket: socket.socket, room_name: str) -> None:
        if not MessageParser.validate_room_name(room_name):
            error_msg = Message(
                type=MessageType.ERROR,
                content=f"Invalid room name: {room_name}",
                sender="System"
            )
            client_socket.send(error_msg.to_json().encode('utf-8'))
            return
            
        username = self.clients[client_socket][1]
        self.logger.info(f"User {username} attempting to join room {room_name}")
        
        if not MessageParser.validate_room_name(room_name):
            self.logger.warning(f"Invalid room name attempt from {username}: {room_name}")
            error_msg = Message(
                type=MessageType.ERROR,
                content=f"Invalid room name: {room_name}",
                sender="System"
            )
            client_socket.send(error_msg.to_json().encode('utf-8'))
            return
        
        # Create room if it doesn't exist
        if room_name not in self.rooms:
            self.rooms[room_name] = ChatRoom(room_name, f"Room {room_name}")
            
        room = self.rooms[room_name]
        
        # Check room capacity
        if len(room.users) >= room.max_users:
            error_msg = Message(
                type=MessageType.ERROR,
                content=f"Room {room_name} is full",
                sender="System"
            )
            client_socket.send(error_msg.to_json().encode('utf-8'))
            return
            
        # Remove user from current room
        for r in self.rooms.values():
            if username in r.users:
                r.users.remove(username)
                leave_msg = Message(
                    type=MessageType.LEAVE,
                    content=f"{username} left the room",
                    sender=username,
                    room=r.name
                )
                self.broadcast_to_room(leave_msg, r.name)
        
        # Add user to new room
        room.users.add(username)
        
        # Notify user of successful join
        success_msg = Message(
            type=MessageType.SYSTEM,
            content=f"You joined room: {room_name}",
            sender="System",
            room=room_name
        )
        client_socket.send(success_msg.to_json().encode('utf-8'))
        
        # Notify others in the room
        join_msg = Message(
            type=MessageType.JOIN,
            content=f"{username} joined the room",
            sender=username,
            room=room_name
        )
        self.broadcast_to_room(join_msg, room_name, exclude_socket=client_socket)

    def leave_room(self, client_socket: socket.socket) -> None:
        username = self.clients[client_socket][1]
        current_room = None
        
        # Find user's current room
        for room in self.rooms.values():
            if username in room.users:
                current_room = room
                break
        
        if current_room:
            # Remove user from room
            current_room.users.remove(username)
            
            # Notify user
            msg = Message(
                type=MessageType.SYSTEM,
                content=f"You left room: {current_room.name}",
                sender="System"
            )
            client_socket.send(msg.to_json().encode('utf-8'))
            
            # Notify others
            leave_msg = Message(
                type=MessageType.LEAVE,
                content=f"{username} left the room",
                sender=username,
                room=current_room.name
            )
            self.broadcast_to_room(leave_msg, current_room.name)
            
            # Join main room
            self.join_room(client_socket, "main")

    def broadcast_to_room(self, message: Message, room_name: str, exclude_socket=None) -> None:
        if room_name not in self.rooms:
            self.logger.warning(f"Attempt to broadcast to non-existent room: {room_name}")
            return
            
        room = self.rooms[room_name]
        message_json = message.to_json()
        
        recipients = 0
        for client_socket, (_, username) in self.clients.items():
            if client_socket != exclude_socket and username in room.users:
                try:
                    client_socket.send(message_json.encode('utf-8'))
                    recipients += 1
                except Exception as e:
                    self.logger.error(f"Error broadcasting to {username}: {e}")
                    self.handle_client_disconnect(client_socket)
                    
        self.logger.debug(f"Message broadcast to {recipients} users in room {room_name}")

    def list_rooms(self, client_socket: socket.socket) -> None:
        room_list = []
        for room in self.rooms.values():
            room_list.append(f"{room.name} ({len(room.users)}/{room.max_users} users)")
            
        msg = Message(
            type=MessageType.SYSTEM,
            content="Available rooms:\n" + "\n".join(room_list),
            sender="System"
        )
        client_socket.send(msg.to_json().encode('utf-8'))

    def handle_client(self, client_socket):
        try:
            username = self.clients[client_socket][1]
            
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                if not self.rate_limiter.can_send_message(username):
                    self.logger.warning(f"Rate limit exceeded for user {username}")
                    error_msg = Message(
                        type=MessageType.ERROR,
                        content="Rate limit exceeded. Please wait before sending more messages.",
                        sender="System"
                    )
                    client_socket.send(error_msg.to_json().encode('utf-8'))
                    continue
                username = self.clients[client_socket][1]
                if MessageParser.is_command(data):
                    self.logger.info(f"Command from {username}: {data}")
                    self.handle_command(client_socket, data)
                else:
                    current_room = next((room.name for room in self.rooms.values() 
                                      if username in room.users), 'main')
                    self.logger.info(f"Message from {username} in room {current_room}: {data}")
                    msg = Message(
                        type=MessageType.CHAT,
                        content=Security.sanitize_input(data),
                        sender=username,
                        room=current_room
                    )
                    self.broadcast_to_room(msg, current_room)
                    
        except Exception as e:
            self.logger.error(f"Error handling client {username}: {e}")
        finally:
            self.handle_client_disconnect(client_socket)

    def broadcast_message(self, message: Message, exclude_socket=None, room=None):
        message_json = message.to_json()
        
        for client_socket, client_data in self.clients.items():  # Iterate over both socket and client data
            if room and client_data[1] not in self.rooms[room].users:
                continue
            if client_socket != exclude_socket:
                try:
                    client_socket.send(message_json.encode('utf-8'))
                except Exception as e:
                    print(f"Error broadcasting to {self.clients[client_socket]}: {e}")
                    self.handle_client_disconnect(client_socket)

    def handle_client_disconnect(self, client_socket):
        if client_socket in self.clients:
            address, username = self.clients[client_socket]
            
            # Remove from all rooms
            for room in self.rooms.values():
                if username in room.users:
                    room.users.discard(username)
                    self.logger.info(f"User {username} removed from room {room.name}")
            
            leave_msg = Message(
                type=MessageType.LEAVE,
                content=f"{username} left the chat",
                sender=username
            )
            self.broadcast_message(leave_msg, exclude_socket=client_socket)
            #yroh ya3ti l client
            self.logger.info(f"User {username} ({address}) disconnected")
            
            del self.clients[client_socket]
            try:
                client_socket.close()
            except Exception as e:
                self.logger.error(f"Error closing socket for {username}: {e}")

    def handle_command(self, client_socket, command_str):
        username = self.clients[client_socket][1]
        command, args = MessageParser.parse_command(command_str)
        
        if command == 'help':
            help_text = "\n".join([f"{cmd}: {desc}" for cmd, desc in MessageParser.COMMANDS.items()])
            msg = Message(
                type=MessageType.SYSTEM,
                content=help_text,
                sender="System"
            )
            client_socket.send(msg.to_json().encode('utf-8'))
            
        elif command == 'join' and len(args) == 1:
            self.join_room(client_socket, args[0])
            
        elif command == 'leave':
            self.leave_room(client_socket)
            
        elif command == 'list':
            self.list_rooms(client_socket)
            
        elif command == 'users':
            self.list_room_users(client_socket)
            
        elif command == 'change' and len(args) == 1:
            self.change_username(client_socket,args[0])
            
        elif command == 'msg' and len(args) >= 2:
            target_user = args[0]
            content = " ".join(args[1:])
            self.send_private_message(username, target_user, content)
            
    def send_private_message(self, sender, receiver, content):
        msg = Message(
            type=MessageType.PRIVATE,
            content=Security.sanitize_input(content),
            sender=sender,
            receiver=receiver
        )
        
        # Find receiver's socket
        for client_socket, (_, username) in self.clients.items():
            if username == receiver:
                try:
                    client_socket.send(msg.to_json().encode('utf-8'))
                    return
                except Exception as e:
                    print(f"Error sending private message: {e}")
                    break

if __name__ == "__main__":
    server = EnhancedChatServer()
    server.start_server()
    