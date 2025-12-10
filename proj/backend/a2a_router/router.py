"""
A2A Router Implementation
Routes messages between registered agents with history logging and error handling.
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, List, Any
from datetime import datetime
from collections import deque
import threading

from ..a2a_protocol.a2a_message import A2AMessage, MessageType

logger = logging.getLogger(__name__)


class A2ARouter:
    """
    Router for A2A protocol messages.
    
    Manages agent registration, message routing, history logging,
    and error handling with retry logic.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize the A2A Router.
        
        Args:
            max_history: Maximum number of messages to keep in history
        """
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._message_history: deque = deque(maxlen=max_history)
        self._lock = threading.RLock()
        self._async_handlers: Dict[str, Callable] = {}
        self._sync_handlers: Dict[str, Callable] = {}

    def register_agent(
        self,
        agent_id: str,
        agent_url: Optional[str] = None,
        handler: Optional[Callable] = None,
        async_handler: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register an agent with the router.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_url: Optional URL for HTTP-based communication
            handler: Synchronous message handler function
            async_handler: Asynchronous message handler function
            metadata: Additional agent metadata
        """
        with self._lock:
            if agent_id in self._agents:
                logger.warning(f"Agent {agent_id} is already registered, updating...")
            
            self._agents[agent_id] = {
                "agent_id": agent_id,
                "url": agent_url,
                "handler": handler,
                "async_handler": async_handler,
                "metadata": metadata or {},
                "registered_at": datetime.utcnow().isoformat(),
                "message_count": 0
            }
            
            if handler:
                self._sync_handlers[agent_id] = handler
            if async_handler:
                self._async_handlers[agent_id] = async_handler
            
            logger.info(f"Agent {agent_id} registered successfully")

    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent from the router.
        
        Args:
            agent_id: Identifier of the agent to unregister
        """
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                self._sync_handlers.pop(agent_id, None)
                self._async_handlers.pop(agent_id, None)
                logger.info(f"Agent {agent_id} unregistered")
            else:
                logger.warning(f"Attempted to unregister unknown agent: {agent_id}")

    def is_agent_registered(self, agent_id: str) -> bool:
        """
        Check if an agent is registered.
        
        Args:
            agent_id: Agent identifier to check
            
        Returns:
            True if agent is registered, False otherwise
        """
        return agent_id in self._agents

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent information dictionary or None if not found
        """
        return self._agents.get(agent_id)

    def list_agents(self) -> List[str]:
        """
        Get list of all registered agent IDs.
        
        Returns:
            List of agent identifiers
        """
        return list(self._agents.keys())

    def send_message(
        self,
        message: A2AMessage,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[A2AMessage]:
        """
        Send a message synchronously.
        
        Args:
            message: A2A message to send
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Response message if requires_response is True, None otherwise
        """
        # Log message
        self._log_message(message, "outgoing")
        
        # Validate recipient
        if not self.is_agent_registered(message.recipient_agent):
            error_msg = A2AMessage.create_error(
                sender_agent="router",
                recipient_agent=message.sender_agent,
                error_message=f"Recipient agent '{message.recipient_agent}' not registered",
                correlation_id=message.message_id
            )
            self._log_message(error_msg, "error")
            return error_msg
        
        # Get handler
        handler = self._sync_handlers.get(message.recipient_agent)
        agent_info = self._agents.get(message.recipient_agent)
        
        if not handler and not agent_info.get("url"):
            error_msg = A2AMessage.create_error(
                sender_agent="router",
                recipient_agent=message.sender_agent,
                error_message=f"No handler or URL available for agent '{message.recipient_agent}'",
                correlation_id=message.message_id
            )
            self._log_message(error_msg, "error")
            return error_msg
        
        # Try to deliver message
        for attempt in range(max_retries):
            try:
                if handler:
                    response = handler(message)
                    if response:
                        self._log_message(response, "incoming")
                        self._agents[message.recipient_agent]["message_count"] += 1
                    return response
                else:
                    # HTTP-based delivery would go here
                    logger.warning(f"HTTP delivery not yet implemented for {message.recipient_agent}")
                    return None
            except Exception as e:
                logger.error(f"Error delivering message (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    error_msg = A2AMessage.create_error(
                        sender_agent="router",
                        recipient_agent=message.sender_agent,
                        error_message=f"Failed to deliver message after {max_retries} attempts: {str(e)}",
                        correlation_id=message.message_id
                    )
                    self._log_message(error_msg, "error")
                    return error_msg
        
        return None

    async def send_message_async(
        self,
        message: A2AMessage,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[A2AMessage]:
        """
        Send a message asynchronously.
        
        Args:
            message: A2A message to send
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Response message if requires_response is True, None otherwise
        """
        # Log message
        self._log_message(message, "outgoing")
        
        # Validate recipient
        if not self.is_agent_registered(message.recipient_agent):
            error_msg = A2AMessage.create_error(
                sender_agent="router",
                recipient_agent=message.sender_agent,
                error_message=f"Recipient agent '{message.recipient_agent}' not registered",
                correlation_id=message.message_id
            )
            self._log_message(error_msg, "error")
            return error_msg
        
        # Get async handler
        handler = self._async_handlers.get(message.recipient_agent)
        agent_info = self._agents.get(message.recipient_agent)
        
        if not handler and not agent_info.get("url"):
            error_msg = A2AMessage.create_error(
                sender_agent="router",
                recipient_agent=message.sender_agent,
                error_message=f"No async handler or URL available for agent '{message.recipient_agent}'",
                correlation_id=message.message_id
            )
            self._log_message(error_msg, "error")
            return error_msg
        
        # Try to deliver message
        for attempt in range(max_retries):
            try:
                if handler:
                    response = await handler(message)
                    if response:
                        self._log_message(response, "incoming")
                        self._agents[message.recipient_agent]["message_count"] += 1
                    return response
                else:
                    # HTTP-based delivery would go here
                    logger.warning(f"HTTP delivery not yet implemented for {message.recipient_agent}")
                    return None
            except Exception as e:
                logger.error(f"Error delivering message (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    error_msg = A2AMessage.create_error(
                        sender_agent="router",
                        recipient_agent=message.sender_agent,
                        error_message=f"Failed to deliver message after {max_retries} attempts: {str(e)}",
                        correlation_id=message.message_id
                    )
                    self._log_message(error_msg, "error")
                    return error_msg
        
        return None

    def _log_message(self, message: A2AMessage, direction: str) -> None:
        """
        Log a message to history.
        
        Args:
            message: Message to log
            direction: Direction of message (incoming, outgoing, error)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "direction": direction,
            "message": message.to_dict()
        }
        self._message_history.append(log_entry)
        logger.debug(f"Message logged: {direction} - {message.message_id[:8]}")

    def get_message_history(
        self,
        limit: Optional[int] = None,
        agent_id: Optional[str] = None,
        message_type: Optional[MessageType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get message history with optional filtering.
        
        Args:
            limit: Maximum number of messages to return
            agent_id: Filter by agent ID (sender or recipient)
            message_type: Filter by message type
            
        Returns:
            List of message log entries
        """
        history = list(self._message_history)
        
        # Apply filters
        if agent_id:
            history = [
                entry for entry in history
                if (entry["message"].get("sender_agent") == agent_id or
                    entry["message"].get("recipient_agent") == agent_id)
            ]
        
        if message_type:
            history = [
                entry for entry in history
                if entry["message"].get("message_type") == message_type.value
            ]
        
        # Apply limit
        if limit:
            history = history[-limit:]
        
        return history

    def clear_history(self) -> None:
        """Clear message history."""
        self._message_history.clear()
        logger.info("Message history cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get router statistics.
        
        Returns:
            Dictionary with router statistics
        """
        total_messages = sum(agent["message_count"] for agent in self._agents.values())
        
        return {
            "total_agents": len(self._agents),
            "total_messages": total_messages,
            "history_size": len(self._message_history),
            "agents": {
                agent_id: {
                    "message_count": agent["message_count"],
                    "registered_at": agent["registered_at"]
                }
                for agent_id, agent in self._agents.items()
            }
        }
