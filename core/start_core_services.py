"""
Startup script for BHIV Core services
"""

import subprocess
import sys
import time
import requests
import threading

def start_core_events_service():
    """Start the Core Events API service"""
    print("Starting Core Events API service on port 8004...")
    try:
        process = subprocess.Popen([
            sys.executable, 
            "core/events/core_events.py", 
            "--port", "8004"
        ])
        print("Core Events API service started with PID:", process.pid)
        return process
    except Exception as e:
        print(f"Error starting Core Events API service: {e}")
        return None

def start_webhooks_service():
    """Start the Webhooks API service"""
    print("Starting Webhooks API service on port 8005...")
    try:
        process = subprocess.Popen([
            sys.executable, 
            "core/events/webhooks.py", 
            "--port", "8005"
        ])
        print("Webhooks API service started with PID:", process.pid)
        return process
    except Exception as e:
        print(f"Error starting Webhooks API service: {e}")
        return None

def check_service_health(base_url, service_name):
    """Check if a service is healthy"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"{service_name} is healthy")
            return True
        else:
            print(f"{service_name} health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"Error checking {service_name} health: {e}")
        return False

def monitor_services():
    """Monitor the health of all services"""
    print("\nMonitoring services...")
    print("Press Ctrl+C to stop monitoring")
    
    try:
        while True:
            check_service_health("http://localhost:8004", "Core Events API")
            check_service_health("http://localhost:8005", "Webhooks API")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nMonitoring stopped")

def main():
    """Main function to start all core services"""
    print("BHIV Core Services Startup")
    print("=" * 30)
    
    # Start the services
    core_events_process = start_core_events_service()
    webhooks_process = start_webhooks_service()
    
    # Wait a moment for services to start
    print("\nWaiting for services to start...")
    time.sleep(5)
    
    # Check initial health
    print("\nInitial health checks:")
    core_events_healthy = check_service_health("http://localhost:8004", "Core Events API")
    webhooks_healthy = check_service_health("http://localhost:8005", "Webhooks API")
    
    if core_events_healthy and webhooks_healthy:
        print("\n✅ All core services are running and healthy!")
        print("\nAPI Endpoints:")
        print("  Core Events API: http://localhost:8004")
        print("  Webhooks API: http://localhost:8005")
        print("\nDocumentation:")
        print("  Core Events API Docs: http://localhost:8004/docs")
        print("  Webhooks API Docs: http://localhost:8005/docs")
        
        # Ask user if they want to monitor services
        try:
            choice = input("\nDo you want to monitor the services? (y/n): ")
            if choice.lower() == 'y':
                monitor_services()
        except KeyboardInterrupt:
            print("\nStartup script terminated")
    else:
        print("\n❌ Some services failed to start properly")
        print("Check the console output for error details")
    
    # Keep services running
    try:
        if core_events_process:
            core_events_process.wait()
        if webhooks_process:
            webhooks_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down services...")
        if core_events_process:
            core_events_process.terminate()
        if webhooks_process:
            webhooks_process.terminate()
        print("Services stopped")

if __name__ == "__main__":
    main()