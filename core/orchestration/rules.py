"""
Orchestration Rules for BHIV Core System

This module implements the orchestration primitives for the BHIV Core system,
including auto-escalation rules, duplicate wallet detection, and multisig triggers.
"""

from typing import Dict, Any, List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrchestrationRules:
    """Class to manage orchestration rules for the BHIV Core system."""
    
    def __init__(self):
        # Threshold for auto-escalation
        self.risk_threshold = 80.0
        
        # Minimum transaction value for high-value transfer flagging (in USD)
        self.high_value_threshold = 10000.0
        
        # Multisig configuration (3/5 signers required)
        self.multisig_signers = 5
        self.multisig_required = 3
    
    def check_auto_escalation(self, event: Dict[str, Any]) -> bool:
        """
        Check if an event should be auto-escalated based on risk score and transaction value.
        
        Args:
            event: Event data containing riskScore and metadata
            
        Returns:
            True if event should be escalated, False otherwise
        """
        risk_score = event.get("riskScore", 0)
        metadata = event.get("metadata", {})
        amount = metadata.get("amount", 0)
        currency = metadata.get("currency", "USD")
        
        # Check if risk score exceeds threshold
        if risk_score >= self.risk_threshold:
            logger.info(f"Auto-escalation triggered: risk score {risk_score} >= threshold {self.risk_threshold}")
            return True
            
        # Check if high-value transfer
        if amount >= self.high_value_threshold:
            logger.info(f"Auto-escalation triggered: high-value transfer {amount} {currency} >= threshold {self.high_value_threshold}")
            return True
            
        return False
    
    def detect_duplicate_wallets(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect duplicate wallets across multiple cases.
        
        Args:
            events: List of event data
            
        Returns:
            List of alerts for duplicate wallets
        """
        wallet_cases = {}
        alerts = []
        
        # Group cases by wallet address
        for event in events:
            metadata = event.get("metadata", {})
            wallet_address = metadata.get("walletAddress")
            
            if wallet_address:
                if wallet_address not in wallet_cases:
                    wallet_cases[wallet_address] = []
                wallet_cases[wallet_address].append(event)
        
        # Generate alerts for wallets involved in multiple cases
        for wallet, cases in wallet_cases.items():
            if len(cases) > 1:
                alert = {
                    "type": "duplicate_wallet",
                    "walletAddress": wallet,
                    "caseIds": [case["caseId"] for case in cases],
                    "count": len(cases),
                    "details": f"Wallet {wallet} appears in {len(cases)} cases"
                }
                alerts.append(alert)
                logger.info(f"Duplicate wallet detected: {alert}")
        
        return alerts
    
    def should_trigger_multisig(self, event: Dict[str, Any]) -> bool:
        """
        Determine if a multisig freeze action should be triggered.
        
        Args:
            event: Event data
            
        Returns:
            True if multisig should be triggered, False otherwise
        """
        action_suggested = event.get("actionSuggested")
        risk_score = event.get("riskScore", 0)
        
        # Trigger multisig for freeze actions with high risk
        if action_suggested == "freeze" and risk_score >= 70:
            logger.info("Multisig freeze trigger activated")
            return True
            
        return False
    
    def generate_cross_case_alerts(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate cross-case alerts based on patterns across multiple events.
        
        Args:
            events: List of event data
            
        Returns:
            List of cross-case alerts
        """
        alerts = []
        
        # Detect duplicate wallets
        duplicate_alerts = self.detect_duplicate_wallets(events)
        alerts.extend(duplicate_alerts)
        
        # Additional cross-case analysis could be added here
        # For example, detecting patterns in transaction times, amounts, etc.
        
        return alerts

# Global instance
orchestration_rules = OrchestrationRules()

def check_auto_escalation(event: Dict[str, Any]) -> bool:
    """Convenience function to check auto-escalation."""
    return orchestration_rules.check_auto_escalation(event)

def detect_duplicate_wallets(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function to detect duplicate wallets."""
    return orchestration_rules.detect_duplicate_wallets(events)

def should_trigger_multisig(event: Dict[str, Any]) -> bool:
    """Convenience function to check if multisig should be triggered."""
    return orchestration_rules.should_trigger_multisig(event)

def generate_cross_case_alerts(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function to generate cross-case alerts."""
    return orchestration_rules.generate_cross_case_alerts(events)