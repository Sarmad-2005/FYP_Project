"""
LangChain Tools for CSV Operations
"""

from langchain.tools import BaseTool
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from ..utils.csv_processor import CSVProcessor


class CSVReadInput(BaseModel):
    """Input for CSV Read Tool"""
    session_csv_path: str = Field(description="Path to the session CSV file")
    operation: str = Field(description="Type of read operation: 'full', 'preview', 'columns', 'stats'", default="full")
    column_name: Optional[str] = Field(description="Column name for stats operation", default=None)


class CSVReadTool(BaseTool):
    """Tool for reading CSV data"""
    
    name: str = "csv_read"
    description: str = """
    Read and analyze CSV file data.
    Operations:
    - 'full': Read all data from CSV
    - 'preview': Get first 100 rows
    - 'columns': Get column names and types
    - 'stats': Get statistics for a specific column (requires column_name)
    
    Input should be a JSON with 'session_csv_path', 'operation', and optional 'column_name'.
    """
    args_schema: type[BaseModel] = CSVReadInput
    
    def _run(self, session_csv_path: str, operation: str = "full", column_name: Optional[str] = None) -> str:
        """Execute CSV read operation"""
        try:
            # Normalize path for OS compatibility
            import os
            session_csv_path = os.path.normpath(session_csv_path)
            print(f"🔍 CSV Read Tool: Attempting to read: {session_csv_path}")
            
            processor = CSVProcessor()
            
            if operation == "full":
                result = processor.read_csv(session_csv_path)
                if result['success']:
                    data_preview = result['data'][:10] if len(result['data']) > 10 else result['data']
                    return f"CSV data loaded successfully. {result['metadata']['rows']} rows, {result['metadata']['columns']} columns. Headers: {result['headers']}. Sample data (first 10 rows): {data_preview}"
                print(f"❌ CSV Read Error: {result.get('error', 'Unknown error')}")
                return f"Error reading CSV: {result.get('error', 'Unable to read file')}"
            
            elif operation == "preview":
                result = processor.get_csv_preview(session_csv_path, 100)
                if result['success']:
                    return f"Preview loaded: {len(result['preview'])} rows. Headers: {result['headers']}. Sample data: {result['preview'][:5]}"
                return f"Error: {result.get('error', 'Unable to preview file')}"
            
            elif operation == "columns":
                result = processor.read_csv(session_csv_path)
                if result['success']:
                    column_info = [{"name": h, "type": "TEXT"} for h in result['headers']]
                    return f"{{'columns': {column_info}}}"
                return f"Error: {result.get('error', 'Unable to read columns')}"
            
            elif operation == "stats" and column_name:
                result = processor.read_csv(session_csv_path)
                if result['success']:
                    stats = processor.get_column_stats(result['data'], column_name)
                    return f"Statistics for column '{column_name}': {stats}"
                return f"Error: {result['error']}"
            
            return "Invalid operation or missing parameters"
            
        except Exception as e:
            return f"CSV Read Error: {str(e)}"
    
    async def _arun(self, session_csv_path: str, operation: str = "full", column_name: Optional[str] = None) -> str:
        """Async version - not implemented, calls sync version"""
        return self._run(session_csv_path, operation, column_name)


class CSVWriteInput(BaseModel):
    """Input for CSV Write Tool"""
    session_csv_path: str = Field(description="Path to save the CSV file")
    data: str = Field(description="JSON string of data to write (list of dictionaries)")
    headers: Optional[str] = Field(description="Optional comma-separated list of header names", default=None)


class CSVWriteTool(BaseTool):
    """Tool for writing CSV data"""
    
    name: str = "csv_write"
    description: str = """
    Write data to CSV file. Useful for saving modified or filtered CSV data.
    
    Input should be a JSON with:
    - 'session_csv_path': Path to save CSV file
    - 'data': JSON string of list of dictionaries to write
    - 'headers': Optional comma-separated header names
    """
    args_schema: type[BaseModel] = CSVWriteInput
    
    def _run(self, session_csv_path: str, data: str, headers: Optional[str] = None) -> str:
        """Execute CSV write operation"""
        try:
            import json
            
            # Parse data from JSON string
            data_list = json.loads(data) if isinstance(data, str) else data
            
            # Parse headers if provided
            headers_list = headers.split(',') if headers else None
            
            processor = CSVProcessor()
            result = processor.write_csv(session_csv_path, data_list, headers_list)
            
            if result['success']:
                return f"CSV written successfully to {result['file_path']}. {result['rows_written']} rows, {result['columns_written']} columns saved."
            else:
                return f"Error writing CSV: {result['error']}"
                
        except Exception as e:
            return f"CSV Write Error: {str(e)}"
    
    async def _arun(self, session_csv_path: str, data: str, headers: Optional[str] = None) -> str:
        """Async version - not implemented, calls sync version"""
        return self._run(session_csv_path, data, headers)

