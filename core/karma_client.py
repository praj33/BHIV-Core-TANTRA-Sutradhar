"""
Karma Client for BHIV Core Integration

This module handles communication with the Karma Tracker service for
real-time behavioral updates based on user actions and events.
"""

import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class KarmaClient:
    """Client for interacting with Karma Tracker API."""
    
    def __init__(self, base_url: str = "http://localhost:8005"):
        """
        Initialize Karma Client.
        
        Args:
            base_url: Base URL for the Karma Tracker API
        """
        self.base_url = base_url
        self.session = requests.Session()
        
    def get_karma(self, user_id: str) -> Dict[str, Any]:
        """
        Get current karma score for a user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing user karma information:
            {
                "user_id": str,
                "karma_score": float,
                "last_update": str (ISO format),
                "source_action": str
            }
        """
        try:
            response = self.session.get(
                f"{self.base_url}/get_karma",
                params={"user_id": user_id},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error getting karma for user {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "karma_score": 0.0,
                "last_update": datetime.now().isoformat(),
                "source_action": "error",
                "error": str(e)
            }
    
    def update_karma(self, user_id: str, action_type: str, value: float) -> Dict[str, Any]:
        """
        Update karma for a user based on an action.
        
        Args:
            user_id: Unique identifier for the user
            action_type: Type of action performed (e.g., "learning_task_completed", "suggestion_provided")
            value: Karma value to add/subtract
            
        Returns:
            Dictionary containing updated karma information:
            {
                "user_id": str,
                "karma_score": float,
                "last_update": str (ISO format),
                "source_action": str
            }
        """
        try:
            payload = {
                "user_id": user_id,
                "action_type": action_type,
                "value": value
            }
            
            response = self.session.post(
                f"{self.base_url}/update_karma",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error updating karma for user {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "karma_score": 0.0,
                "last_update": datetime.now().isoformat(),
                "source_action": action_type,
                "error": str(e)
            }
    
    def emit_karma_event(self, user_id: str, karma_score: float, action_type: str) -> bool:
        """
        Emit karma_updated event for the Bucket to consume.
        
        Args:
            user_id: Unique identifier for the user
            karma_score: Current karma score
            action_type: Type of action that triggered the update
            
        Returns:
            Boolean indicating success of event emission
        """
        try:
            # In a real implementation, this would send an event to a message queue
            # or event bus that the Bucket service can consume
            event_data = {
                "event_id": str(uuid.uuid4()),
                "event_type": "karma_updated",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "user_id": user_id,
                    "karma_score": karma_score,
                    "source_action": action_type
                }
            }
            
            # Log the event emission
            logger.info(f"Karma event emitted: {event_data}")
            
            # In a real implementation, we would send this to an event system
            # For now, we'll just log it and return success
            return True
        except Exception as e:
            logger.error(f"Error emitting karma event for user {user_id}: {str(e)}")
            return False

# Global karma client instance
karma_client = KarmaClient()

def get_karma(user_id: str) -> Dict[str, Any]:
    """
    Get current karma score for a user.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Dictionary containing user karma information
    """
    return karma_client.get_karma(user_id)

def update_karma(user_id: str, action_type: str, value: float) -> Dict[str, Any]:
    """
    Update karma for a user based on an action.
    
    Args:
        user_id: Unique identifier for the user
        action_type: Type of action performed
        value: Karma value to add/subtract
        
    Returns:
        Dictionary containing updated karma information
    """
    result = karma_client.update_karma(user_id, action_type, value)
    
    # Emit event if update was successful
    if "error" not in result:
        karma_client.emit_karma_event(user_id, result["karma_score"], action_type)
    
    return result