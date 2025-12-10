"""
A2A Message Implementation
Defines the message structure for Agent-to-Agent communication.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum
import uuid
import json


class MessageType(Enum):
    """Message types for A2A communication."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class Priority(Enum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class A2AMessage:
    """
    A2A Protocol Message structure for inter-agent communication.
    
    Attributes:
        message_id: Unique identifier for the message
        sender_agent: Name/ID of the sending agent
        recipient_agent: Name/ID of the receiving agent
        message_type: Type of message (request, response, notification, error)
        timestamp: When the message was created
        payload: The actual message data
        priority: Message priority level
        requires_response: Whether this message expects a response
        correlation_id: ID to correlate request/response pairs
        metadata: Additional metadata dictionary
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_agent: str = ""
    recipient_agent: str = ""
    message_type: MessageType = MessageType.REQUEST
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    requires_response: bool = False
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate message after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate message structure and required fields.
        
        Raises:
            ValueError: If message is invalid
        """
        if not self.sender_agent:
            raise ValueError("sender_agent is required")
        if not self.recipient_agent and self.message_type != MessageType.NOTIFICATION:
            raise ValueError("recipient_agent is required for non-notification messages")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be a dictionary")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary")

    @classmethod
    def create_request(
        cls,
        sender_agent: str,
        recipient_agent: str,
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        requires_response: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "A2AMessage":
        """
        Create a request message.
        
        Args:
            sender_agent: Name/ID of the sending agent
            recipient_agent: Name/ID of the receiving agent
            payload: Request data
            priority: Message priority
            requires_response: Whether response is required
            metadata: Additional metadata
            
        Returns:
            A2AMessage instance configured as a request
        """
        return cls(
            sender_agent=sender_agent,
            recipient_agent=recipient_agent,
            message_type=MessageType.REQUEST,
            payload=payload,
            priority=priority,
            requires_response=requires_response,
            metadata=metadata or {}
        )

    @classmethod
    def create_response(
        cls,
        sender_agent: str,
        recipient_agent: str,
        payload: Dict[str, Any],
        correlation_id: str,
        priority: Priority = Priority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "A2AMessage":
        """
        Create a response message.
        
        Args:
            sender_agent: Name/ID of the responding agent
            recipient_agent: Name/ID of the original requester
            payload: Response data
            correlation_id: ID of the original request
            priority: Message priority
            metadata: Additional metadata
            
        Returns:
            A2AMessage instance configured as a response
        """
        return cls(
            sender_agent=sender_agent,
            recipient_agent=recipient_agent,
            message_type=MessageType.RESPONSE,
            payload=payload,
            correlation_id=correlation_id,
            priority=priority,
            requires_response=False,
            metadata=metadata or {}
        )

    @classmethod
    def create_notification(
        cls,
        sender_agent: str,
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "A2AMessage":
        """
        Create a notification message (broadcast, no specific recipient).
        
        Args:
            sender_agent: Name/ID of the sending agent
            payload: Notification data
            priority: Message priority
            metadata: Additional metadata
            
        Returns:
            A2AMessage instance configured as a notification
        """
        return cls(
            sender_agent=sender_agent,
            recipient_agent="",  # Notifications don't need recipients
            message_type=MessageType.NOTIFICATION,
            payload=payload,
            priority=priority,
            requires_response=False,
            metadata=metadata or {}
        )

    @classmethod
    def create_error(
        cls,
        sender_agent: str,
        recipient_agent: str,
        error_message: str,
        error_code: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "A2AMessage":
        """
        Create an error message.
        
        Args:
            sender_agent: Name/ID of the agent reporting the error
            recipient_agent: Name/ID of the agent that should receive the error
            error_message: Error description
            error_code: Optional error code
            correlation_id: ID of the related request if applicable
            metadata: Additional metadata
            
        Returns:
            A2AMessage instance configured as an error
        """
        payload = {
            "error": error_message,
            "error_code": error_code
        }
        return cls(
            sender_agent=sender_agent,
            recipient_agent=recipient_agent,
            message_type=MessageType.ERROR,
            payload=payload,
            priority=Priority.HIGH,
            requires_response=False,
            correlation_id=correlation_id,
            metadata=metadata or {}
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert message to dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        result = asdict(self)
        result['message_type'] = self.message_type.value
        result['priority'] = self.priority.value
        return result

    def to_json(self) -> str:
        """
        Serialize message to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        """
        Create A2AMessage from dictionary.
        
        Args:
            data: Dictionary containing message data
            
        Returns:
            A2AMessage instance
        """
        # Convert string enums back to Enum types
        if isinstance(data.get('message_type'), str):
            data['message_type'] = MessageType(data['message_type'])
        if isinstance(data.get('priority'), str):
            data['priority'] = Priority(data['priority'])
        
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "A2AMessage":
        """
        Deserialize message from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            A2AMessage instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __repr__(self) -> str:
        """String representation of the message."""
        return (
            f"A2AMessage(id={self.message_id[:8]}..., "
            f"type={self.message_type.value}, "
            f"{self.sender_agent} -> {self.recipient_agent})"
        )
