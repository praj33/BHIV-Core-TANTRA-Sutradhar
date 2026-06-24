"""
Participant Lifecycle Manager

Defines participant lifecycle states and manages transitions.
States: INITIALIZING → READY → DEGRADED → MAINTENANCE → READ_ONLY → DRAINING → STOPPED

Usage:
    manager = LifecycleManager()
    manager.set_state("bridge", LifecycleState.READY)
    if manager.can_accept_requests("bridge"):
        # route to bridge
"""

from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class LifecycleState(str, Enum):
    """Participant lifecycle states."""
    INITIALIZING = "initializing"   # Service starting up, not ready
    READY = "ready"                 # Fully operational, accepting requests
    DEGRADED = "degraded"           # Operational but with reduced capability
    MAINTENANCE = "maintenance"     # Planned downtime, reject new requests
    READ_ONLY = "read_only"         # Accepts reads, rejects writes
    DRAINING = "draining"           # No new requests, finishing in-flight
    STOPPED = "stopped"             # Offline

    @property
    def accepts_new_requests(self) -> bool:
        """Whether this state allows new incoming requests."""
        return self in (LifecycleState.READY, LifecycleState.DEGRADED, LifecycleState.READ_ONLY)

    @property
    def is_healthy(self) -> bool:
        """Whether this state is considered healthy."""
        return self in (LifecycleState.READY,)

    @property
    def is_operational(self) -> bool:
        """Whether the service is doing any work (including draining)."""
        return self in (
            LifecycleState.READY,
            LifecycleState.DEGRADED,
            LifecycleState.READ_ONLY,
            LifecycleState.DRAINING,
        )


# Valid transitions: from_state -> set of allowed to_states
VALID_TRANSITIONS = {
    LifecycleState.INITIALIZING: {LifecycleState.READY, LifecycleState.STOPPED},
    LifecycleState.READY: {LifecycleState.DEGRADED, LifecycleState.MAINTENANCE, LifecycleState.DRAINING, LifecycleState.STOPPED},
    LifecycleState.DEGRADED: {LifecycleState.READY, LifecycleState.MAINTENANCE, LifecycleState.DRAINING, LifecycleState.STOPPED},
    LifecycleState.MAINTENANCE: {LifecycleState.INITIALIZING, LifecycleState.READY, LifecycleState.STOPPED},
    LifecycleState.READ_ONLY: {LifecycleState.READY, LifecycleState.MAINTENANCE, LifecycleState.DRAINING, LifecycleState.STOPPED},
    LifecycleState.DRAINING: {LifecycleState.STOPPED, LifecycleState.READY},
    LifecycleState.STOPPED: {LifecycleState.INITIALIZING},
}


class ParticipantLifecycle:
    """Tracks lifecycle state for a single participant."""

    def __init__(self, name: str, initial_state: LifecycleState = LifecycleState.INITIALIZING):
        self.name = name
        self.state = initial_state
        self.last_transition = datetime.now(timezone.utc)
        self.transition_history: list = []
        self._record_transition(None, initial_state)

    def _record_transition(self, from_state: Optional[LifecycleState], to_state: LifecycleState):
        self.transition_history.append({
            "from": from_state.value if from_state else None,
            "to": to_state.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep last 50 transitions
        if len(self.transition_history) > 50:
            self.transition_history = self.transition_history[-50:]

    def transition_to(self, new_state: LifecycleState) -> bool:
        """Attempt state transition. Returns True if successful."""
        if new_state == self.state:
            return True

        allowed = VALID_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            logger.warning(
                f"[lifecycle] Invalid transition for {self.name}: "
                f"{self.state.value} → {new_state.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
            return False

        old_state = self.state
        self.state = new_state
        self.last_transition = datetime.now(timezone.utc)
        self._record_transition(old_state, new_state)
        logger.info(f"[lifecycle] {self.name}: {old_state.value} → {new_state.value}")
        return True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "accepts_requests": self.state.accepts_new_requests,
            "is_healthy": self.state.is_healthy,
            "is_operational": self.state.is_operational,
            "last_transition": self.last_transition.isoformat(),
            "recent_transitions": self.transition_history[-5:],
        }


class LifecycleManager:
    """Manages lifecycle states for all participants."""

    def __init__(self):
        self._participants: Dict[str, ParticipantLifecycle] = {}

    def register(self, name: str, initial_state: LifecycleState = LifecycleState.INITIALIZING) -> ParticipantLifecycle:
        """Register a participant with initial lifecycle state."""
        participant = ParticipantLifecycle(name, initial_state)
        self._participants[name] = participant
        return participant

    def set_state(self, name: str, state: LifecycleState) -> bool:
        """Set lifecycle state for a participant."""
        if name not in self._participants:
            self.register(name, state)
            return True
        return self._participants[name].transition_to(state)

    def get_state(self, name: str) -> Optional[LifecycleState]:
        """Get current lifecycle state."""
        p = self._participants.get(name)
        return p.state if p else None

    def can_accept_requests(self, name: str) -> bool:
        """Check if participant can accept new requests."""
        p = self._participants.get(name)
        if not p:
            return False
        return p.state.accepts_new_requests

    def get_ready_participants(self) -> list:
        """Get names of all participants in READY state."""
        return [name for name, p in self._participants.items() if p.state == LifecycleState.READY]

    def get_degraded_participants(self) -> list:
        """Get names of all participants in DEGRADED state."""
        return [name for name, p in self._participants.items() if p.state == LifecycleState.DEGRADED]

    def get_all_states(self) -> dict:
        """Get states of all participants."""
        return {name: p.to_dict() for name, p in self._participants.items()}

    def summary(self) -> dict:
        """Summary of all participant states."""
        states = {}
        for name, p in self._participants.items():
            state_name = p.state.value
            states.setdefault(state_name, []).append(name)
        return {
            "total_participants": len(self._participants),
            "by_state": states,
            "accepting_requests": [n for n, p in self._participants.items() if p.state.accepts_new_requests],
            "not_accepting": [n for n, p in self._participants.items() if not p.state.accepts_new_requests],
        }
