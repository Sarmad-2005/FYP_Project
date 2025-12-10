"""
CSV Parser Agent
Worker agent for parsing and validating CSV files
"""

from typing import Dict, Any
from ..utils.csv_processor import CSVProcessor


class CSVParserAgent:
    """Worker agent for CSV parsing and validation"""
    
    def __init__(self):
        """Initialize CSV Parser Agent"""
        self.processor = CSVProcessor()
    
    def parse_and_validate(self, file_path: str) -> Dict[str, Any]:
        """
        Parse and validate CSV file
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Validation and parsing results
        """
        try:
            # Step 1: Validate CSV structure
            validation = self.processor.validate_csv(file_path)
            
            if not validation.get('valid'):
                return {
                    'success': False,
                    'errors': validation.get('errors', []),
                    'data': None
                }
            
            # Step 2: Read CSV data
            result = self.processor.read_csv(file_path)
            
            if not result.get('success'):
                return {
                    'success': False,
                    'errors': [result.get('error', 'Unknown error')],
                    'data': None
                }
            
            # Step 3: Analyze data types and patterns
            data_analysis = self._analyze_data(result['data'], result['headers'])
            
            return {
                'success': True,
                'data': result['data'],
                'headers': result['headers'],
                'metadata': result['metadata'],
                'analysis': data_analysis,
                'errors': []
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f'Parsing error: {str(e)}'],
                'data': None
            }
    
    def _analyze_data(self, data: list, headers: list) -> Dict[str, Any]:
        """
        Analyze CSV data to identify patterns and types
        
        Args:
            data: List of row dictionaries
            headers: List of column headers
            
        Returns:
            Analysis results
        """
        import pandas as pd
        
        try:
            df = pd.DataFrame(data)
            
            # Replace NaN with None for consistency
            df = df.where(pd.notna(df), None)
            
            analysis = {
                'total_rows': len(df),
                'total_columns': len(headers),
                'column_types': {},
                'numeric_columns': [],
                'text_columns': [],
                'date_columns': [],
                'has_nulls': {}
            }
            
            for col in headers:
                # Determine column type
                if pd.api.types.is_numeric_dtype(df[col]):
                    analysis['column_types'][col] = 'numeric'
                    analysis['numeric_columns'].append(col)
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    analysis['column_types'][col] = 'datetime'
                    analysis['date_columns'].append(col)
                else:
                    analysis['column_types'][col] = 'text'
                    analysis['text_columns'].append(col)
                
                # Check for null values
                null_count = df[col].isnull().sum()
                analysis['has_nulls'][col] = int(null_count)
            
            return analysis
            
        except Exception as e:
            return {
                'error': f'Analysis error: {str(e)}'
            }
    
    def get_preview(self, file_path: str, num_rows: int = 100) -> Dict[str, Any]:
        """
        Get preview of CSV file
        
        Args:
            file_path: Path to CSV file
            num_rows: Number of rows to preview
            
        Returns:
            Preview data
        """
        return self.processor.get_csv_preview(file_path, num_rows)

