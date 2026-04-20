"""
Test script for BHIV Core functionality
"""

import json
import requests
import time

# Base URLs for the services
CORE_EVENTS_URL = "http://localhost:8004"
WEBHOOKS_URL = "http://localhost:8005"

def test_core_events_api():
    """Test the core events API functionality"""
    print("Testing Core Events API...")
    
    # Test event payload
    event_payload = {
        "caseId": "test-case-123",
        "evidenceId": "test-evidence-456",
        "riskScore": 85.5,
        "actionSuggested": "escalate",
        "txHash": "0x123456789abcdef",
        "source": "test-script",
        "metadata": {
            "walletAddress": "0xabcdef123456789",
            "amount": 15000,
            "currency": "USD"
        }
    }
    
    # Accept an event
    print("1. Accepting event...")
    response = requests.post(f"{CORE_EVENTS_URL}/core/events", json=event_payload)
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 202:
        event_response = response.json()
        core_event_id = event_response["coreEventId"]
        print(f"   Core Event ID: {core_event_id}")
        
        # Wait a moment for processing
        time.sleep(1)
        
        # Get event status
        print("2. Getting event status...")
        response = requests.get(f"{CORE_EVENTS_URL}/core/events/{core_event_id}")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            status_response = response.json()
            print(f"   Event Status: {status_response}")
        
        # Get case status
        print("3. Getting case status...")
        response = requests.get(f"{CORE_EVENTS_URL}/core/case/{event_payload['caseId']}/status")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            case_response = response.json()
            print(f"   Case Status: {case_response}")
        
        return core_event_id
    else:
        print(f"   Error: {response.text}")
        return None

def test_webhooks_api(core_event_id):
    """Test the webhooks API functionality"""
    print("\nTesting Webhooks API...")
    
    # Send escalation result callback
    print("1. Sending escalation result callback...")
    callback_payload = {
        "outcomeId": "test-outcome-123",
        "caseId": "test-case-123",
        "eventType": "escalation_completed",
        "result": {
            "status": "approved",
            "decision": "Escalation approved by test script",
            "assignedTo": "test-analyst",
            "nextSteps": ["investigate_further", "contact_customer"]
        },
        "timestamp": "2025-10-06T10:30:00Z"
    }
    
    response = requests.post(f"{WEBHOOKS_URL}/callbacks/escalation-result", json=callback_payload)
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        webhook_response = response.json()
        message_id = webhook_response["messageId"]
        print(f"   Message ID: {message_id}")
        
        # Log a monitoring event
        print("2. Logging monitoring event...")
        monitoring_payload = {
            "eventId": "test-monitoring-event-123",
            "eventType": "test_event",
            "status": "success",
            "timestamp": "2025-10-06T12:00:00Z",
            "details": "Test monitoring event from test script"
        }
        
        response = requests.post(f"{WEBHOOKS_URL}/monitoring/events", json=monitoring_payload)
        print(f"   Status Code: {response.status_code}")
        
        # Get monitoring events
        print("3. Getting monitoring events...")
        response = requests.get(f"{WEBHOOKS_URL}/monitoring/events")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            monitoring_events = response.json()
            print(f"   Monitoring Events Count: {len(monitoring_events)}")
        
        return message_id
    else:
        print(f"   Error: {response.text}")
        return None

def test_health_checks():
    """Test health check endpoints"""
    print("\nTesting Health Checks...")
    
    # Core Events API health check
    print("1. Core Events API health check...")
    response = requests.get(f"{CORE_EVENTS_URL}/health")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        health_response = response.json()
        print(f"   Health Status: {health_response}")
    
    # Webhooks API health check
    print("2. Webhooks API health check...")
    response = requests.get(f"{WEBHOOKS_URL}/health")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        health_response = response.json()
        print(f"   Health Status: {health_response}")

def main():
    """Main test function"""
    print("BHIV Core Functionality Test")
    print("=" * 40)
    
    # Test health checks first
    test_health_checks()
    
    # Test core events API
    core_event_id = test_core_events_api()
    
    # Test webhooks API if core events test was successful
    if core_event_id:
        test_webhooks_api(core_event_id)
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()