import json
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
import re
import hashlib
import logging  # noqa: F401
from dataclasses import dataclass, asdict  # noqa: F401
from colorama import Fore, Style, init  # type: ignore # noqa: F401

class MessageType(Enum):
    CHAT = "chat"
    SYSTEM = "system"
    PRIVATE = "private"
    JOIN = "join"
    LEAVE = "leave"
    STATUS = "status"
    ERROR = "error"
    COMMAND = "command"
    CHANGE = "change"

class UserStatus(Enum):
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"

@dataclass
class Message:
    type: MessageType
    content: str
    sender: Optional[str] = None
    receiver: Optional[str] = None
    timestamp: str = None
    room: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "content": self.content,
            "sender": self.sender,
            "receiver": self.receiver,
            "timestamp": self.timestamp,
            "room": self.room
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        data = json.loads(json_str)
        data['type'] = MessageType(data['type'])
        return cls(**data)

class MessageParser:
    COMMAND_PREFIX = '/'
    COMMANDS = {
        'help': 'Show available commands',
        'change': 'Change your username',
        'join': 'Join a room: /join room_name',
        'leave': 'Leave current room',
        'list': 'List all available rooms',
        'users': 'List all online users',
        'msg': 'Send private message: /msg username message'
    }

    @staticmethod
    def is_command(message: str) -> bool:
        return message.startswith(MessageParser.COMMAND_PREFIX)

    @staticmethod
    def parse_command(message: str) -> tuple[str, list[str]]:
        parts = message[1:].split()  # Remove prefix and split
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        return command, args

    @staticmethod
    def validate_username(username: str) -> bool:
        pattern = r'^[a-zA-Z0-9_-]{3,16}$'
        return bool(re.match(pattern, username))

    @staticmethod
    def validate_room_name(room: str) -> bool:
        pattern = r'^[a-zA-Z0-9_-]{1,32}$'
        return bool(re.match(pattern, room))

class Security: 
    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def sanitize_input(text: str) -> str:
        # Remove HTML tags
        text = re.sub(r'<[^>]*>', '', text)
        return text

class RateLimiter:
    def __init__(self, max_messages: int = 10, window_seconds: int = 60):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.message_times: Dict[str, list[datetime]] = {}

    def can_send_message(self, user_id: str) -> bool:
        now = datetime.now()
        
        # Initialize or clean old messages
        if user_id not in self.message_times:
            self.message_times[user_id] = []
        
        # Remove messages outside the time window
        self.message_times[user_id] = [
            t for t in self.message_times[user_id]
            if (now - t).total_seconds() < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.message_times[user_id]) < self.max_messages:
            self.message_times[user_id].append(now)
            return True
            
        return False

class ChatRoom:
    def __init__(self, name: str, description: str = "", max_users: int = 100):
        self.name = name
        self.description = description
        self.max_users = max_users
        self.users: set = set()
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "user_count": len(self.users),
            "max_users": self.max_users,
            "created_at": self.created_at.isoformat()
        }

def format_message(message: Message) -> str:
    timestamp = datetime.fromisoformat(message.timestamp).strftime("%H:%M:%S")
    if message.type == MessageType.SYSTEM:
        return Fore.YELLOW +f"[{timestamp}] System: {message.content}"+Style.RESET_ALL
    elif message.type == MessageType.PRIVATE:
        return Fore.BLUE +f"[{timestamp}] (Private) {message.sender} → {message.receiver}: {message.content}"+Style.RESET_ALL
    elif message.type == MessageType.JOIN:
        return Fore.GREEN +f"[{timestamp}] → {message.sender} joined the chat"+Style.RESET_ALL
    elif message.type == MessageType.LEAVE:
        return Fore.RED +f"[{timestamp}] ← {message.sender} left the chat"+Style.RESET_ALL
    elif message.type == MessageType.CHANGE:
        return Fore.RED +f"[{timestamp}] {message.content}"+Style.RESET_ALL
    else:
        return f"[{timestamp}] {message.sender}: {message.content}"

def create_error_message(error_text: str) -> Message:
    return Message(
        type=MessageType.ERROR,
        content=error_text,
        sender="System"
    )

def create_system_message(content: str) -> Message:
    return Message(
        type=MessageType.SYSTEM,
        content=content,
        sender="System"
    )