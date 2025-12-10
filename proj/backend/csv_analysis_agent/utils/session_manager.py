"""
Session Manager
Manages CSV analysis sessions per project
"""

import os
import uuid
import json
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List


class SessionManager:
    """Manages CSV analysis sessions"""
    
    def __init__(self, base_dir: str = 'data/csv_sessions'):
        """
        Initialize Session Manager
        
        Args:
            base_dir: Base directory for session storage
        """
        self.base_dir = base_dir
        self._ensure_base_directory()
    
    def _ensure_base_directory(self):
        """Create base directory if it doesn't exist"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
    
    def create_session(self, project_id: str, csv_file_path: str, metadata: Optional[Dict] = None) -> str:
        """
        Create a new CSV analysis session
        
        Args:
            project_id: Project identifier
            csv_file_path: Path to uploaded CSV file
            metadata: Optional session metadata
            
        Returns:
            Session ID
        """
        # Generate unique session ID
        session_id = str(uuid.uuid4())[:8]
        
        # Create project directory if not exists
        project_dir = os.path.join(self.base_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        # Create session directory
        session_dir = os.path.join(project_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Copy CSV file to session directory
        session_csv_path = os.path.join(session_dir, 'data.csv')
        shutil.copy2(csv_file_path, session_csv_path)
        
        # Create session metadata file
        session_meta = {
            'session_id': session_id,
            'project_id': project_id,
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'csv_file': 'data.csv',
            'metadata': metadata or {}
        }
        
        meta_path = os.path.join(session_dir, 'session.json')
        with open(meta_path, 'w') as f:
            json.dump(session_meta, f, indent=2)
        
        return session_id
    
    def get_session_path(self, project_id: str, session_id: str) -> Optional[str]:
        """
        Get path to session CSV file
        
        Args:
            project_id: Project identifier
            session_id: Session identifier
            
        Returns:
            Path to CSV file or None if not found
        """
        session_dir = os.path.join(self.base_dir, project_id, session_id)
        csv_path = os.path.join(session_dir, 'data.csv')
        
        if os.path.exists(csv_path):
            # Update last accessed time
            self._update_last_accessed(project_id, session_id)
            return csv_path
        
        return None
    
    def update_session_data(self, project_id: str, session_id: str, new_csv_path: str) -> bool:
        """
        Update CSV data for a session
        
        Args:
            project_id: Project identifier
            session_id: Session identifier
            new_csv_path: Path to new CSV file
            
        Returns:
            Success status
        """
        try:
            session_dir = os.path.join(self.base_dir, project_id, session_id)
            
            if not os.path.exists(session_dir):
                return False
            
            # Replace CSV file
            session_csv_path = os.path.join(session_dir, 'data.csv')
            shutil.copy2(new_csv_path, session_csv_path)
            
            # Update last accessed time
            self._update_last_accessed(project_id, session_id)
            
            return True
            
        except Exception as e:
            print(f"Error updating session: {e}")
            return False
    
    def get_session_metadata(self, project_id: str, session_id: str) -> Optional[Dict]:
        """
        Get session metadata
        
        Args:
            project_id: Project identifier
            session_id: Session identifier
            
        Returns:
            Session metadata or None
        """
        try:
            session_dir = os.path.join(self.base_dir, project_id, session_id)
            meta_path = os.path.join(session_dir, 'session.json')
            
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            print(f"Error getting metadata: {e}")
            return None
    
    def _update_last_accessed(self, project_id: str, session_id: str):
        """Update last accessed timestamp"""
        try:
            session_dir = os.path.join(self.base_dir, project_id, session_id)
            meta_path = os.path.join(session_dir, 'session.json')
            
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                
                metadata['last_accessed'] = datetime.now().isoformat()
                
                with open(meta_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                    
        except Exception as e:
            print(f"Error updating last accessed: {e}")
    
    def delete_session(self, project_id: str, session_id: str) -> bool:
        """
        Delete a session
        
        Args:
            project_id: Project identifier
            session_id: Session identifier
            
        Returns:
            Success status
        """
        try:
            session_dir = os.path.join(self.base_dir, project_id, session_id)
            
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def list_project_sessions(self, project_id: str) -> List[Dict]:
        """
        List all sessions for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of session metadata
        """
        sessions = []
        project_dir = os.path.join(self.base_dir, project_id)
        
        if not os.path.exists(project_dir):
            return sessions
        
        try:
            for session_id in os.listdir(project_dir):
                metadata = self.get_session_metadata(project_id, session_id)
                if metadata:
                    sessions.append(metadata)
            
            # Sort by created_at (newest first)
            sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
        except Exception as e:
            print(f"Error listing sessions: {e}")
        
        return sessions
    
    def cleanup_old_sessions(self, days: int = 1):
        """
        Delete sessions older than specified days
        
        Args:
            days: Number of days to keep sessions
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for project_id in os.listdir(self.base_dir):
                project_dir = os.path.join(self.base_dir, project_id)
                
                if not os.path.isdir(project_dir):
                    continue
                
                for session_id in os.listdir(project_dir):
                    metadata = self.get_session_metadata(project_id, session_id)
                    
                    if metadata:
                        last_accessed = datetime.fromisoformat(metadata['last_accessed'])
                        
                        if last_accessed < cutoff_date:
                            print(f"Cleaning up old session: {project_id}/{session_id}")
                            self.delete_session(project_id, session_id)
                            
        except Exception as e:
            print(f"Error during cleanup: {e}")

