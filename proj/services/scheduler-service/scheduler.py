"""
Refresh Scheduler
Handles scheduled refresh operations for financial and performance services.
"""

from typing import List, Dict, Any
from backend.a2a_router.router import A2ARouter
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType
from backend.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)


class RefreshScheduler:
    """Scheduler for triggering refresh operations via A2A protocol"""
    
    def __init__(self, a2a_router: A2ARouter, db_manager: DatabaseManager):
        """
        Initialize Refresh Scheduler
        
        Args:
            a2a_router: A2ARouter instance for sending messages
            db_manager: DatabaseManager instance for getting projects
        """
        self.a2a_router = a2a_router
        self.db_manager = db_manager
    
    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        Get all projects from database.
        
        Returns:
            List of project dictionaries
        """
        try:
            projects = self.db_manager.get_all_projects()
            return projects
        except Exception as e:
            logger.error(f"Error getting all projects: {e}")
            return []
    
    def trigger_financial_refresh_all(self) -> Dict[str, Any]:
        """
        Trigger financial refresh for all projects via A2A.
        
        Returns:
            Dictionary with refresh results
        """
        results = {
            'success': True,
            'total_projects': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            logger.info("Starting financial refresh for all projects...")
            
            # Get all projects
            projects = self.get_all_projects()
            results['total_projects'] = len(projects)
            
            if not projects:
                logger.info("No projects found for financial refresh")
                return results
            
            # Check if financial-service is registered
            if not self.a2a_router.is_agent_registered("financial-service"):
                logger.warning("financial-service not registered with A2A router")
                results['success'] = False
                results['errors'].append("financial-service not registered")
                return results
            
            # Send refresh request for each project
            for project in projects:
                project_id = project.get('id')
                if not project_id:
                    continue
                
                try:
                    # Create A2A refresh request
                    request_msg = A2AMessage.create_request(
                        sender_agent="scheduler-service",
                        recipient_agent="financial-service",
                        payload={
                            "action": "refresh",
                            "project_id": project_id
                        }
                    )
                    
                    # Send message
                    response = self.a2a_router.send_message(request_msg)
                    
                    if response and response.message_type == MessageType.RESPONSE:
                        if response.payload.get("success", False):
                            results['successful'] += 1
                            logger.info(f"Financial refresh successful for project {project_id[:8]}")
                        else:
                            results['failed'] += 1
                            error_msg = response.payload.get("error", "Unknown error")
                            results['errors'].append(f"Project {project_id[:8]}: {error_msg}")
                            logger.warning(f"Financial refresh failed for project {project_id[:8]}: {error_msg}")
                    else:
                        results['failed'] += 1
                        error_msg = "No response or error response from financial-service"
                        results['errors'].append(f"Project {project_id[:8]}: {error_msg}")
                        logger.error(f"Financial refresh error for project {project_id[:8]}: {error_msg}")
                
                except Exception as e:
                    results['failed'] += 1
                    error_msg = str(e)
                    results['errors'].append(f"Project {project_id[:8]}: {error_msg}")
                    logger.error(f"Exception during financial refresh for project {project_id[:8]}: {e}")
            
            logger.info(f"Financial refresh complete: {results['successful']}/{results['total_projects']} successful")
            results['success'] = results['failed'] == 0
            
            return results
            
        except Exception as e:
            logger.error(f"Error in trigger_financial_refresh_all: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
            return results
    
    def trigger_performance_refresh_all(self) -> Dict[str, Any]:
        """
        Trigger performance refresh for all projects via A2A.
        
        Returns:
            Dictionary with refresh results
        """
        results = {
            'success': True,
            'total_projects': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            logger.info("Starting performance refresh for all projects...")
            
            # Get all projects
            projects = self.get_all_projects()
            results['total_projects'] = len(projects)
            
            if not projects:
                logger.info("No projects found for performance refresh")
                return results
            
            # Check if performance-service is registered
            if not self.a2a_router.is_agent_registered("performance-service"):
                logger.warning("performance-service not registered with A2A router")
                results['success'] = False
                results['errors'].append("performance-service not registered")
                return results
            
            # Send refresh request for each project
            for project in projects:
                project_id = project.get('id')
                if not project_id:
                    continue
                
                try:
                    # Create A2A refresh request
                    request_msg = A2AMessage.create_request(
                        sender_agent="scheduler-service",
                        recipient_agent="performance-service",
                        payload={
                            "action": "refresh",
                            "project_id": project_id
                        }
                    )
                    
                    # Send message
                    response = self.a2a_router.send_message(request_msg)
                    
                    if response and response.message_type == MessageType.RESPONSE:
                        if response.payload.get("success", False):
                            results['successful'] += 1
                            logger.info(f"Performance refresh successful for project {project_id[:8]}")
                        else:
                            results['failed'] += 1
                            error_msg = response.payload.get("error", "Unknown error")
                            results['errors'].append(f"Project {project_id[:8]}: {error_msg}")
                            logger.warning(f"Performance refresh failed for project {project_id[:8]}: {error_msg}")
                    else:
                        results['failed'] += 1
                        error_msg = "No response or error response from performance-service"
                        results['errors'].append(f"Project {project_id[:8]}: {error_msg}")
                        logger.error(f"Performance refresh error for project {project_id[:8]}: {error_msg}")
                
                except Exception as e:
                    results['failed'] += 1
                    error_msg = str(e)
                    results['errors'].append(f"Project {project_id[:8]}: {error_msg}")
                    logger.error(f"Exception during performance refresh for project {project_id[:8]}: {e}")
            
            logger.info(f"Performance refresh complete: {results['successful']}/{results['total_projects']} successful")
            results['success'] = results['failed'] == 0
            
            return results
            
        except Exception as e:
            logger.error(f"Error in trigger_performance_refresh_all: {e}")
            results['success'] = False
            results['errors'].append(f"Fatal error: {str(e)}")
            return results
