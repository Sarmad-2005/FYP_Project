"""
CSV Processor Utility
Handles CSV file reading, writing, validation, and transformations
"""

import csv
import os
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime


class CSVProcessor:
    """Utility class for CSV file operations"""
    
    @staticmethod
    def read_csv(file_path: str) -> Dict[str, Any]:
        """
        Read CSV file and return structured data
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Dict with headers, data, and metadata
        """
        try:
            # Normalize path for Windows compatibility
            file_path = os.path.normpath(file_path)
            
            # Read CSV using pandas for better handling
            df = pd.read_csv(file_path)
            
            # Replace NaN with None (null in JSON) for JSON compatibility
            df = df.where(pd.notna(df), None)
            
            # Convert to list of dictionaries
            data = df.to_dict('records')
            headers = df.columns.tolist()
            
            # Get metadata
            metadata = {
                'rows': len(df),
                'columns': len(headers),
                'headers': headers,
                'file_size': os.path.getsize(file_path),
                'last_modified': datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).isoformat()
            }
            
            return {
                'success': True,
                'data': data,
                'headers': headers,
                'metadata': metadata
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'headers': [],
                'metadata': {}
            }
    
    @staticmethod
    def write_csv(file_path: str, data: List[Dict], headers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Write data to CSV file
        
        Args:
            file_path: Path to output CSV file
            data: List of dictionaries to write
            headers: Optional custom headers (auto-detected if None)
            
        Returns:
            Success status and metadata
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Use custom headers if provided
            if headers and len(headers) == len(df.columns):
                df.columns = headers
            
            # Write to CSV
            df.to_csv(file_path, index=False)
            
            return {
                'success': True,
                'file_path': file_path,
                'rows_written': len(df),
                'columns_written': len(df.columns)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def validate_csv(file_path: str) -> Dict[str, Any]:
        """
        Validate CSV file structure and content
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Validation results
        """
        try:
            # Check file exists
            if not os.path.exists(file_path):
                return {
                    'valid': False,
                    'errors': ['File does not exist']
                }
            
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            file_size = os.path.getsize(file_path)
            
            if file_size > max_size:
                return {
                    'valid': False,
                    'errors': [f'File too large ({file_size} bytes). Maximum: {max_size} bytes']
                }
            
            # Try reading CSV
            df = pd.read_csv(file_path)
            
            # Check for empty file
            if len(df) == 0:
                return {
                    'valid': False,
                    'errors': ['CSV file is empty']
                }
            
            # Check for duplicate column names
            if len(df.columns) != len(set(df.columns)):
                return {
                    'valid': False,
                    'errors': ['Duplicate column names detected']
                }
            
            # All validations passed
            return {
                'valid': True,
                'rows': len(df),
                'columns': len(df.columns),
                'headers': df.columns.tolist(),
                'errors': []
            }
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f'Validation error: {str(e)}']
            }
    
    @staticmethod
    def get_csv_preview(file_path: str, num_rows: int = 100) -> Dict[str, Any]:
        """
        Get preview of CSV file (first N rows)
        
        Args:
            file_path: Path to CSV file
            num_rows: Number of rows to preview
            
        Returns:
            Preview data
        """
        try:
            df = pd.read_csv(file_path, nrows=num_rows)
            
            # Replace NaN with None for JSON compatibility
            df = df.where(pd.notna(df), None)
            
            return {
                'success': True,
                'preview': df.to_dict('records'),
                'total_rows': len(df),
                'headers': df.columns.tolist()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'preview': []
            }
    
    @staticmethod
    def transform_data(data: List[Dict], operation: str, **kwargs) -> List[Dict]:
        """
        Apply transformations to CSV data
        
        Args:
            data: List of dictionaries (CSV data)
            operation: Type of operation (filter, sort, aggregate)
            **kwargs: Operation-specific parameters
            
        Returns:
            Transformed data
        """
        try:
            df = pd.DataFrame(data)
            
            if operation == 'filter':
                # Filter rows based on condition
                column = kwargs.get('column')
                value = kwargs.get('value')
                operator = kwargs.get('operator', '==')
                
                if operator == '==':
                    df = df[df[column] == value]
                elif operator == '>':
                    df = df[df[column] > value]
                elif operator == '<':
                    df = df[df[column] < value]
                elif operator == 'contains':
                    df = df[df[column].astype(str).str.contains(str(value), case=False)]
            
            elif operation == 'sort':
                # Sort by column
                column = kwargs.get('column')
                ascending = kwargs.get('ascending', True)
                df = df.sort_values(by=column, ascending=ascending)
            
            elif operation == 'aggregate':
                # Group and aggregate
                group_by = kwargs.get('group_by')
                agg_column = kwargs.get('agg_column')
                agg_func = kwargs.get('agg_func', 'sum')
                
                df = df.groupby(group_by).agg({agg_column: agg_func}).reset_index()
            
            # Replace NaN with None for JSON compatibility
            df = df.where(pd.notna(df), None)
            
            return df.to_dict('records')
            
        except Exception as e:
            print(f"Transform error: {e}")
            return data
    
    @staticmethod
    def get_column_stats(data: List[Dict], column: str) -> Dict[str, Any]:
        """
        Get statistics for a specific column
        
        Args:
            data: List of dictionaries (CSV data)
            column: Column name
            
        Returns:
            Column statistics
        """
        try:
            df = pd.DataFrame(data)
            
            if column not in df.columns:
                return {'error': f'Column {column} not found'}
            
            # Check if numeric
            if pd.api.types.is_numeric_dtype(df[column]):
                return {
                    'type': 'numeric',
                    'count': int(df[column].count()),
                    'min': float(df[column].min()),
                    'max': float(df[column].max()),
                    'mean': float(df[column].mean()),
                    'median': float(df[column].median()),
                    'sum': float(df[column].sum()),
                    'std': float(df[column].std())
                }
            else:
                # For categorical/text columns
                return {
                    'type': 'categorical',
                    'count': int(df[column].count()),
                    'unique': int(df[column].nunique()),
                    'top_values': df[column].value_counts().head(10).to_dict()
                }
                
        except Exception as e:
            return {'error': str(e)}

