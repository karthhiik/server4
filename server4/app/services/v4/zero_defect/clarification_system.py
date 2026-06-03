"""
Clarification System - Manages clarification requests and user responses
Stores pending clarifications and handles user responses
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.services.v4.zero_defect.models import Ambiguity
from app.config import settings


class ClarificationSystem:
    """Manages clarification requests and user responses"""
    
    def __init__(self):
        self.pending_clarifications: Dict[str, List[Ambiguity]] = {}
        self.clarification_responses: Dict[str, Dict[str, str]] = {}
        self.clarification_timeout = timedelta(minutes=30)
    
    async def request_clarification(self, session_id: str, ambiguities: List[Ambiguity]) -> Dict[str, any]:
        """
        Request clarification from user for ambiguous statements
        
        Args:
            session_id: Unique session identifier
            ambiguities: List of ambiguities that need clarification
            
        Returns:
            Dictionary with clarification request details
        """
        # Store pending clarifications
        self.pending_clarifications[session_id] = ambiguities
        
        # Generate clarification questions
        clarification_questions = []
        for ambiguity in ambiguities:
            clarification_questions.append({
                "statement": ambiguity.statement,
                "question": ambiguity.clarification_question,
                "suggested": ambiguity.suggested_clarification,
                "type": ambiguity.ambiguity_type
            })
        
        return {
            "clarification_needed": True,
            "session_id": session_id,
            "questions": clarification_questions,
            "timeout_minutes": int(self.clarification_timeout.total_seconds() / 60)
        }
    
    async def receive_clarification(
        self,
        session_id: str,
        responses: Dict[str, str]
    ) -> Dict[str, any]:
        """
        Receive clarification responses from user
        
        Args:
            session_id: Unique session identifier
            responses: Dictionary mapping statement to user's clarification
            
        Returns:
            Dictionary with processed clarifications
        """
        if session_id not in self.pending_clarifications:
            return {
                "success": False,
                "error": "No pending clarifications for this session"
            }
        
        # Store responses
        self.clarification_responses[session_id] = responses
        
        # Clear pending clarifications
        del self.pending_clarifications[session_id]
        
        return {
            "success": True,
            "session_id": session_id,
            "responses_received": len(responses)
        }
    
    def get_pending_clarifications(self, session_id: str) -> Optional[List[Ambiguity]]:
        """
        Get pending clarifications for a session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            List of pending ambiguities or None if no pending clarifications
        """
        return self.pending_clarifications.get(session_id)
    
    def get_clarification_responses(self, session_id: str) -> Optional[Dict[str, str]]:
        """
        Get clarification responses for a session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Dictionary of responses or None if no responses
        """
        return self.clarification_responses.get(session_id)
    
    def has_pending_clarifications(self, session_id: str) -> bool:
        """
        Check if session has pending clarifications
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if session has pending clarifications
        """
        return session_id in self.pending_clarifications
    
    def cleanup_expired_sessions(self):
        """Clean up expired clarification sessions"""
        # This would be called periodically to clean up old sessions
        # For now, just pass - implement with Redis/DB in production
        pass
