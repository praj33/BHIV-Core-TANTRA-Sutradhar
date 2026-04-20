"""
Main Core Orchestrator for BHIV System

This module integrates event handling, orchestration rules, and webhook callbacks
for the BHIV Core system.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

# Import local modules
from core.orchestration.rules import (
    check_auto_escalation,
    detect_duplicate_wallets,
    should_trigger_multisig,
    generate_cross_case_alerts
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoreOrchestrator:
    """Main orchestrator for the BHIV Core system."""
    
    def __init__(self):
        self.events_storage = {}
        self.webhook_events = []
        self.monitoring_events = []
        logger.info("CoreOrchestrator initialized")
    
    def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming event through the orchestration pipeline.
        
        Args:
            event_data: Event data to process
            
        Returns:
            Processing result with any triggered actions
        """
        try:
            # Generate core event ID if not present
            if "coreEventId" not in event_data:
                event_data["coreEventId"] = str(uuid.uuid4())
            
            # Store the event
            core_event_id = event_data["coreEventId"]
            event_data["processedAt"] = datetime.now().isoformat()
            self.events_storage[core_event_id] = event_data
            
            logger.info(f"Processing event {core_event_id}")
            
            # Apply orchestration rules
            actions_triggered = []
            
            # Check for auto-escalation
            if check_auto_escalation(event_data):
                actions_triggered.append({
                    "action": "auto_escalation",
                    "reason": "Risk score or transaction value threshold exceeded",
                    "timestamp": datetime.now().isoformat()
                })
                logger.info("Auto-escalation triggered")
            
            # Check for multisig trigger
            if should_trigger_multisig(event_data):
                actions_triggered.append({
                    "action": "multisig_trigger",
                    "reason": "Freeze action with high risk score",
                    "timestamp": datetime.now().isoformat()
                })
                logger.info("Multisig trigger activated")
            
            # Generate cross-case alerts
            all_events = list(self.events_storage.values())
            cross_case_alerts = generate_cross_case_alerts(all_events)
            
            if cross_case_alerts:
                actions_triggered.append({
                    "action": "cross_case_alerts",
                    "alerts": cross_case_alerts,
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"Generated {len(cross_case_alerts)} cross-case alerts")
            
            # Store monitoring event
            monitoring_event = {
                "eventId": str(uuid.uuid4()),
                "eventType": "event_processed",
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "details": f"Processed event {core_event_id} with {len(actions_triggered)} actions triggered"
            }
            self.monitoring_events.append(monitoring_event)
            
            return {
                "coreEventId": core_event_id,
                "status": "processed",
                "actionsTriggered": actions_triggered,
                "crossCaseAlerts": cross_case_alerts,
                "processedAt": event_data["processedAt"]
            }
            
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
            
            # Store error monitoring event
            monitoring_event = {
                "eventId": str(uuid.uuid4()),
                "eventType": "event_processing_error",
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "details": str(e)
            }
            self.monitoring_events.append(monitoring_event)
            
            return {
                "coreEventId": event_data.get("coreEventId", "unknown"),
                "status": "error",
                "error": str(e),
                "processedAt": datetime.now().isoformat()
            }
    
    def handle_webhook_callback(self, callback_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming webhook callbacks.
        
        Args:
            callback_type: Type of callback
            payload: Callback payload
            
        Returns:
            Handling result
        """
        try:
            # Generate message ID
            message_id = str(uuid.uuid4())
            
            # Store the webhook event
            event_data = {
                "messageId": message_id,
                "callbackType": callback_type,
                "payload": payload,
                "receivedAt": datetime.now().isoformat()
            }
            self.webhook_events.append(event_data)
            
            logger.info(f"Received {callback_type} webhook callback")
            
            # Store monitoring event
            monitoring_event = {
                "eventId": str(uuid.uuid4()),
                "eventType": f"webhook_{callback_type}",
                "status": "received",
                "timestamp": datetime.now().isoformat(),
                "details": f"Webhook {callback_type} received with message ID {message_id}"
            }
            self.monitoring_events.append(monitoring_event)
            
            return {
                "status": "received",
                "messageId": message_id,
                "receivedAt": event_data["receivedAt"]
            }
            
        except Exception as e:
            logger.error(f"Error handling webhook callback: {str(e)}")
            
            # Store error monitoring event
            monitoring_event = {
                "eventId": str(uuid.uuid4()),
                "eventType": f"webhook_{callback_type}_error",
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "details": str(e)
            }
            self.monitoring_events.append(monitoring_event)
            
            return {
                "status": "error",
                "error": str(e),
                "receivedAt": datetime.now().isoformat()
            }
    
    def get_event_status(self, core_event_id: str) -> Dict[str, Any]:
        """
        Get the status of a specific event.
        
        Args:
            core_event_id: Core event ID
            
        Returns:
            Event status information
        """
        if core_event_id not in self.events_storage:
            return {
                "coreEventId": core_event_id,
                "status": "not_found",
                "error": "Event not found"
            }
        
        event_data = self.events_storage[core_event_id]
        return {
            "coreEventId": core_event_id,
            "status": "processed",
            "eventData": event_data,
            "processedAt": event_data.get("processedAt")
        }
    
    def get_monitoring_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get monitoring events, optionally filtered by event type.
        
        Args:
            event_type: Optional event type to filter by
            
        Returns:
            List of monitoring events
        """
        if event_type:
            return [event for event in self.monitoring_events if event.get("eventType") == event_type]
        return self.monitoring_events
    
    def replay_failed_event(self, event_id: str) -> Dict[str, Any]:
        """
        Replay a failed event delivery.
        
        Args:
            event_id: Event ID to replay
            
        Returns:
            Replay result
        """
        # Find the event in webhook events
        event_to_replay = None
        for event in self.webhook_events:
            if event.get("messageId") == event_id:
                event_to_replay = event
                break
        
        if not event_to_replay:
            return {
                "status": "error",
                "error": "Event not found"
            }
        
        # Log this as a monitoring event
        monitoring_event = {
            "eventId": str(uuid.uuid4()),
            "eventType": "replay",
            "status": "initiated",
            "timestamp": datetime.now().isoformat(),
            "details": f"Replay initiated for event {event_id}"
        }
        self.monitoring_events.append(monitoring_event)
        
        logger.info(f"Replay initiated for event {event_id}")
        
        return {
            "status": "replay_initiated",
            "eventId": event_id,
            "monitoringEventId": monitoring_event["eventId"]
        }

# Global orchestrator instance
core_orchestrator = CoreOrchestrator()

def process_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to process an event."""
    return core_orchestrator.process_event(event_data)

def handle_webhook_callback(callback_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to handle webhook callbacks."""
    return core_orchestrator.handle_webhook_callback(callback_type, payload)

def get_event_status(core_event_id: str) -> Dict[str, Any]:
    """Convenience function to get event status."""
    return core_orchestrator.get_event_status(core_event_id)

def get_monitoring_events(event_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function to get monitoring events."""
    return core_orchestrator.get_monitoring_events(event_type)

def replay_failed_event(event_id: str) -> Dict[str, Any]:
    """Convenience function to replay failed events."""
    return core_orchestrator.replay_failed_event(event_id)