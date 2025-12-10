"""
CSV Analysis Agent - Main Coordinator
LangChain-based agent system for CSV financial data analysis
"""

from typing import Dict, Any, Optional, List
from .agents.csv_parser_agent import CSVParserAgent
from .agents.data_context_agent import DataContextAgent
from .agents.qa_agent import QAAgent
from .agents.export_agent import ExportAgent
from .tools.csv_tools import CSVReadTool, CSVWriteTool
from .tools.financial_tools import FinancialDataTool, TransactionTool, AnomalyTool
from .tools.qa_tools import CalculationTool, ContextTool
from .utils.session_manager import SessionManager
from .utils.csv_processor import CSVProcessor
import time


class CSVAnalysisAgent:
    """Main coordinator for CSV analysis operations"""
    
    def __init__(self, llm_manager, a2a_router, anomaly_agent=None):
        """
        Initialize CSV Analysis Agent
        
        Args:
            llm_manager: LLM Manager instance
            a2a_router: A2ARouter instance for inter-service communication
            anomaly_agent: AnomalyDetectionAgent instance (optional, for backward compatibility)
        """
        self.llm_manager = llm_manager
        self.a2a_router = a2a_router
        self.anomaly_agent = anomaly_agent
        
        # Initialize session manager
        self.session_manager = SessionManager()
        self.csv_processor = CSVProcessor()
        
        # Initialize worker agents
        self.parser_agent = CSVParserAgent()
        self.context_agent = DataContextAgent(a2a_router, anomaly_agent)
        self.export_agent = ExportAgent()
        
        # Initialize LangChain tools
        self.tools = self._initialize_tools()
        
        # Initialize QA agent with tools and llm_manager
        self.qa_agent = QAAgent(llm_manager, self.tools)
    
    def _initialize_tools(self) -> List:
        """Initialize all LangChain tools"""
        tools = [
            CSVReadTool(),
            CSVWriteTool(),
            FinancialDataTool(self.a2a_router),
            TransactionTool(self.a2a_router),
            AnomalyTool(a2a_router=self.a2a_router, anomaly_agent=self.anomaly_agent),
            CalculationTool(),
            ContextTool()
        ]
        return tools
    
    def upload_csv(self, project_id: str, csv_file_path: str) -> Dict[str, Any]:
        """
        Upload and process CSV file
        
        Args:
            project_id: Project identifier
            csv_file_path: Path to uploaded CSV file
            
        Returns:
            Upload result with session ID and preview
        """
        try:
            # Step 1: Parse and validate CSV
            parse_result = self.parser_agent.parse_and_validate(csv_file_path)
            
            if not parse_result['success']:
                return {
                    'success': False,
                    'errors': parse_result['errors']
                }
            
            # Step 2: Create session
            metadata = {
                'headers': parse_result['headers'],
                'rows': parse_result['metadata']['rows'],
                'columns': parse_result['metadata']['columns'],
                'analysis': parse_result['analysis']
            }
            
            session_id = self.session_manager.create_session(
                project_id,
                csv_file_path,
                metadata
            )
            
            # Step 3: Get preview
            preview = self.parser_agent.get_preview(csv_file_path, 100)
            
            # Clean the preview data - convert NaN to None
            import pandas as pd
            import numpy as np
            preview_data = preview.get('preview', [])
            
            # Sanitize each row in preview
            clean_preview = []
            for row in preview_data:
                clean_row = {}
                for key, value in row.items():
                    # Handle various NaN types
                    if pd.isna(value) or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
                        clean_row[key] = None
                    else:
                        clean_row[key] = value
                clean_preview.append(clean_row)
            
            return {
                'success': True,
                'session_id': session_id,
                'rows': parse_result['metadata']['rows'],
                'columns': parse_result['metadata']['columns'],
                'headers': parse_result['headers'],
                'preview': clean_preview,
                'analysis': parse_result['analysis']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload error: {str(e)}'
            }
    
    def get_csv_data(self, project_id: str, session_id: str) -> Dict[str, Any]:
        """
        Get CSV data for a session
        
        Args:
            project_id: Project identifier
            session_id: Session identifier
            
        Returns:
            CSV data and metadata
        """
        try:
            # Get session path
            csv_path = self.session_manager.get_session_path(project_id, session_id)
            
            if not csv_path:
                return {
                    'success': False,
                    'error': 'Session not found'
                }
            
            # Read CSV
            result = self.csv_processor.read_csv(csv_path)
            
            if result['success']:
                return {
                    'success': True,
                    'data': result['data'],
                    'headers': result['headers'],
                    'metadata': result['metadata']
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Data retrieval error: {str(e)}'
            }
    
    def update_csv_data(
        self,
        project_id: str,
        session_id: str,
        updated_data: List[Dict],
        operation: str = 'edit'
    ) -> Dict[str, Any]:
        """
        Update CSV data in session
        
        Args:
            project_id: Project identifier
            session_id: Session identifier
            updated_data: New data to save
            operation: Type of operation performed
            
        Returns:
            Update result
        """
        try:
            # Get current session path
            csv_path = self.session_manager.get_session_path(project_id, session_id)
            
            if not csv_path:
                return {
                    'success': False,
                    'error': 'Session not found'
                }
            
            # Write updated data
            result = self.csv_processor.write_csv(csv_path, updated_data)
            
            if result['success']:
                return {
                    'success': True,
                    'message': f'Data updated successfully ({operation})',
                    'rows': result['rows_written'],
                    'columns': result['columns_written']
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Update error: {str(e)}'
            }
    
    def ask_question(
        self,
        project_id: str,
        session_id: str,
        question: str,
        selected_cells: Optional[List[Dict]] = None,
        include_project_context: bool = True
    ) -> Dict[str, Any]:
        """
        Answer question about CSV data using LangChain agent
        
        Args:
            project_id: Project identifier
            session_id: Session identifier
            question: User's question
            selected_cells: Optional selected cell data
            include_project_context: Whether to include financial context
            
        Returns:
            Answer with sources and reasoning
        """
        try:
            start_time = time.time()
            
            # Get CSV path
            csv_path = self.session_manager.get_session_path(project_id, session_id)
            
            if not csv_path:
                return {
                    'success': False,
                    'error': 'Session not found'
                }
            
            # Build financial context if requested
            financial_context = None
            if include_project_context:
                financial_context = self.context_agent.build_context_summary(project_id)
            
            # Use QA agent to answer question
            result = self.qa_agent.answer_question(
                question,
                csv_path,
                selected_cells,
                financial_context,
                project_id  # Pass project_id for financial tools
            )
            
            execution_time = time.time() - start_time
            
            # Build sources list
            sources = []
            
            if selected_cells:
                sources.append({
                    'type': 'csv_selection',
                    'description': f'{len(selected_cells)} selected cells',
                    'data': selected_cells[:5]  # Sample
                })
            
            sources.append({
                'type': 'csv_file',
                'description': 'Full CSV data',
                'path': csv_path
            })
            
            if include_project_context:
                sources.append({
                    'type': 'project_context',
                    'description': 'Project financial data',
                    'summary': financial_context[:200] + '...' if financial_context else ''
                })
            
            if result['success']:
                return {
                    'success': True,
                    'answer': result['answer'],
                    'question': question,
                    'sources': sources,
                    'agent_chain': [
                        f"QA Agent processed question",
                        f"Tools used: {', '.join(result.get('tools_used', []))}",
                        f"Reasoning: {result.get('reasoning', 'N/A')[:100]}..."
                    ],
                    'execution_time': round(execution_time, 2)
                }
            else:
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Q&A error: {str(e)}',
                'answer': f'An error occurred: {str(e)}'
            }
    
    def export_csv(
        self,
        project_id: str,
        session_id: str,
        export_format: str = 'csv',
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export CSV data
        
        Args:
            project_id: Project identifier
            session_id: Session identifier
            export_format: Export format type
            filename: Optional custom filename
            
        Returns:
            Export result with file path
        """
        try:
            # Get CSV data
            data_result = self.get_csv_data(project_id, session_id)
            
            if not data_result['success']:
                return data_result
            
            # Export using export agent
            export_result = self.export_agent.export_csv(
                data_result['data'],
                export_format,
                include_metadata=True,
                filename=filename
            )
            
            return export_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Export error: {str(e)}'
            }
    
    def get_financial_context(self, project_id: str) -> Dict[str, Any]:
        """
        Get complete financial context for project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Financial context data
        """
        try:
            context = self.context_agent.get_full_context(project_id)
            return context
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Context retrieval error: {str(e)}'
            }
    
    def cleanup_old_sessions(self, days: int = 1):
        """
        Cleanup old sessions
        
        Args:
            days: Number of days to keep sessions
        """
        self.session_manager.cleanup_old_sessions(days)

