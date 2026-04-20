"""
Karma Event Propagation Module

This module handles event propagation for karma updates to be consumed by the Bucket service.
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

class KarmaEventEmitter:
    """Handles emission of karma-related events for consumption by other services."""
    
    def __init__(self):
        """Initialize the event emitter."""
        pass
    
    def emit_karma_updated(self, user_id: str, karma_score: float, source_action: str) -> bool:
        """
        Emit a karma_updated event for the Bucket to consume.
        
        Args:
            user_id: Unique identifier for the user
            karma_score: Current karma score
            source_action: Action that triggered the karma update
            
        Returns:
            Boolean indicating success of event emission
        """
        try:
            # Create event data
            event_data = {
                "event_id": str(uuid.uuid4()),
                "event_type": "karma_updated",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "user_id": user_id,
                    "karma_score": karma_score,
                    "source_action": source_action,
                    "updated_at": datetime.now().isoformat()
                }
            }
            
            # In a real implementation, this would send the event to a message queue
            # or event bus that the Bucket service can consume
            
            # For now, we'll log the event and save it to a file
            logger.info(f"Karma event emitted: {json.dumps(event_data, indent=2)}")
            
            # Save to a log file for demonstration
            try:
                with open("logs/karma_events.log", "a") as f:
                    f.write(f"{json.dumps(event_data)}\n")
            except Exception as e:
                logger.warning(f"Failed to write event to log file: {str(e)}")
            
            return True
        except Exception as e:
            logger.error(f"Error emitting karma event for user {user_id}: {str(e)}")
            return False
    
    def emit_karma_reset(self, user_id: str, reason: str) -> bool:
        """
        Emit a karma_reset event.
        
        Args:
            user_id: Unique identifier for the user
            reason: Reason for the karma reset
            
        Returns:
            Boolean indicating success of event emission
        """
        try:
            event_data = {
                "event_id": str(uuid.uuid4()),
                "event_type": "karma_reset",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "user_id": user_id,
                    "reason": reason,
                    "reset_at": datetime.now().isoformat()
                }
            }
            
            logger.info(f"Karma reset event emitted: {json.dumps(event_data, indent=2)}")
            
            # Save to a log file for demonstration
            try:
                with open("logs/karma_events.log", "a") as f:
                    f.write(f"{json.dumps(event_data)}\n")
            except Exception as e:
                logger.warning(f"Failed to write event to log file: {str(e)}")
            
            return True
        except Exception as e:
            logger.error(f"Error emitting karma reset event for user {user_id}: {str(e)}")
            return False

# Global event emitter instance
karma_event_emitter = KarmaEventEmitter()

def emit_karma_updated(user_id: str, karma_score: float, source_action: str) -> bool:
    """
    Emit a karma_updated event for the Bucket to consume.
    
    Args:
        user_id: Unique identifier for the user
        karma_score: Current karma score
        source_action: Action that triggered the karma update
        
    Returns:
        Boolean indicating success of event emission
    """
    return karma_event_emitter.emit_karma_updated(user_id, karma_score, source_action)

def emit_karma_reset(user_id: str, reason: str) -> bool:
    """
    Emit a karma_reset event.
    
    Args:
        user_id: Unique identifier for the user
        reason: Reason for the karma reset
        
    Returns:
        Boolean indicating success of event emission
    """
    return karma_event_emitter.emit_karma_reset(user_id, reason)