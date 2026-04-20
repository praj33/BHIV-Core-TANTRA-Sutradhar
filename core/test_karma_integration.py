"""
Test script for Karma Tracker integration with BHIV Core.

This script simulates 3 user actions to validate Karma updates and event propagation.
"""

import sys
import os
import time
from datetime import datetime

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.karma_client import get_karma, update_karma

def test_karma_integration():
    """Test karma integration with 3 simulated user actions."""
    
    print("=" * 60)
    print("BHIV Core - Karma Tracker Integration Test")
    print("=" * 60)
    
    # Test user ID
    user_id = "test_user_001"
    
    print(f"\nTesting with user ID: {user_id}")
    print("-" * 40)
    
    # Test 1: Initial karma check
    print("\n1. Checking initial karma...")
    initial_karma = get_karma(user_id)
    print(f"   Initial karma: {initial_karma}")
    
    # Test 2: Simulate learning task completion
    print("\n2. Simulating learning task completion...")
    task_result = update_karma(user_id, "learning_task_completed", 10.0)
    print(f"   After task completion: {task_result}")
    time.sleep(1)  # Small delay to ensure timestamp difference
    
    # Test 3: Simulate agent suggestion provided
    print("\n3. Simulating agent suggestion...")
    suggestion_result = update_karma(user_id, "suggestion_provided", 5.0)
    print(f"   After suggestion: {suggestion_result}")
    time.sleep(1)  # Small delay to ensure timestamp difference
    
    # Test 4: Simulate negative action (e.g., skipped task)
    print("\n4. Simulating skipped task (negative karma)...")
    negative_result = update_karma(user_id, "task_skipped", -2.0)
    print(f"   After negative action: {negative_result}")
    
    # Final check
    print("\n5. Final karma check...")
    final_karma = get_karma(user_id)
    print(f"   Final karma: {final_karma}")
    
    # Validate results
    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    
    # Check that we got responses
    tests_passed = 0
    total_tests = 4
    
    if "karma_score" in initial_karma:
        print("✓ Initial karma check successful")
        tests_passed += 1
    else:
        print("✗ Initial karma check failed")
    
    if "karma_score" in task_result and task_result["karma_score"] >= 0:
        print("✓ Learning task completion successful")
        tests_passed += 1
    else:
        print("✗ Learning task completion failed")
    
    if "karma_score" in suggestion_result and suggestion_result["karma_score"] >= 0:
        print("✓ Agent suggestion successful")
        tests_passed += 1
    else:
        print("✗ Agent suggestion failed")
    
    if "karma_score" in negative_result and "karma_score" in final_karma:
        expected_final = task_result["karma_score"] + 5.0 - 2.0
        if abs(final_karma["karma_score"] - expected_final) < 0.001:
            print("✓ Negative action and final calculation successful")
            tests_passed += 1
        else:
            print(f"✗ Final calculation mismatch. Expected: {expected_final}, Got: {final_karma['karma_score']}")
    else:
        print("✗ Negative action test failed")
    
    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {tests_passed}/{total_tests} tests passed")
    if tests_passed == total_tests:
        print("🎉 All tests passed! Karma integration is working correctly.")
    else:
        print("❌ Some tests failed. Please check the Karma Tracker service.")
    print("=" * 60)
    
    return tests_passed == total_tests

def simulate_agentic_workflows():
    """Simulate karma calls being injected into agentic workflows."""
    
    print("\n" + "=" * 60)
    print("AGENTIC WORKFLOW SIMULATION")
    print("=" * 60)
    
    user_id = "workflow_user_001"
    
    # Simulate workflow 1: User completes a learning task
    print("\nWorkflow 1: User completes a learning task")
    print("-" * 40)
    print("1. Text Agent processing user input...")
    print("2. Task completed successfully...")
    print("3. Injecting karma update...")
    
    result = update_karma(user_id, "learning_task_completed", 15.0)
    print(f"   Karma update result: {result}")
    
    # Simulate workflow 2: Agent provides a suggestion
    print("\nWorkflow 2: Agent provides a suggestion")
    print("-" * 40)
    print("1. Knowledge Agent analyzing user query...")
    print("2. Generating personalized suggestion...")
    print("3. Injecting karma effect...")
    
    result = update_karma(user_id, "agent_suggestion_provided", 7.0)
    print(f"   Karma update result: {result}")
    
    # Simulate workflow 3: User interacts with voice interface
    print("\nWorkflow 3: User interacts with voice interface")
    print("-" * 40)
    print("1. Audio Agent processing voice input...")
    print("2. Voice Persona Agent generating response...")
    print("3. Logging karma effect...")
    
    result = update_karma(user_id, "voice_interaction", 3.0)
    print(f"   Karma update result: {result}")
    
    print("\n✅ Agentic workflow simulations completed!")
    return True

if __name__ == "__main__":
    print("Starting Karma Tracker integration tests...")
    
    # Run integration tests
    integration_success = test_karma_integration()
    
    # Run workflow simulations
    workflow_success = simulate_agentic_workflows()
    
    if integration_success and workflow_success:
        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("Karma Tracker is properly integrated with BHIV Core.")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Please check the Karma Tracker service and integration.")
        
    sys.exit(0 if integration_success and workflow_success else 1)