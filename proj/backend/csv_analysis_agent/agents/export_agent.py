"""
Export Agent
Worker agent for generating and formatting CSV exports
"""

from typing import Dict, Any, List, Optional
from ..utils.csv_processor import CSVProcessor
import os
from datetime import datetime


class ExportAgent:
    """Worker agent for CSV export operations"""
    
    def __init__(self):
        """Initialize Export Agent"""
        self.processor = CSVProcessor()
    
    def export_csv(
        self,
        data: List[Dict],
        export_format: str = 'csv',
        include_metadata: bool = True,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export CSV data with optional formatting
        
        Args:
            data: List of dictionaries to export
            export_format: Format type ('csv', 'filtered', 'summary')
            include_metadata: Whether to include metadata
            filename: Optional custom filename
            
        Returns:
            Export result with file path
        """
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"export_{timestamp}.csv"
            
            # Ensure .csv extension
            if not filename.endswith('.csv'):
                filename += '.csv'
            
            # Create temporary export path
            export_dir = 'data/csv_sessions/exports'
            os.makedirs(export_dir, exist_ok=True)
            export_path = os.path.join(export_dir, filename)
            
            # Handle different export formats
            if export_format == 'csv':
                # Standard CSV export
                result = self.processor.write_csv(export_path, data)
                
            elif export_format == 'filtered':
                # Export with filtering (data already filtered)
                result = self.processor.write_csv(export_path, data)
                
            elif export_format == 'summary':
                # Export summary statistics
                summary_data = self._generate_summary(data)
                result = self.processor.write_csv(export_path, summary_data)
            
            else:
                return {
                    'success': False,
                    'error': f'Unknown export format: {export_format}'
                }
            
            if result['success']:
                return {
                    'success': True,
                    'file_path': export_path,
                    'filename': filename,
                    'rows_exported': result['rows_written'],
                    'format': export_format
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Export failed')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Export error: {str(e)}'
            }
    
    def _generate_summary(self, data: List[Dict]) -> List[Dict]:
        """
        Generate summary statistics from data
        
        Args:
            data: Original data
            
        Returns:
            Summary data
        """
        import pandas as pd
        
        try:
            df = pd.DataFrame(data)
            
            summary_rows = []
            
            # For each numeric column, generate stats
            for col in df.select_dtypes(include=['number']).columns:
                summary_rows.append({
                    'Column': col,
                    'Count': int(df[col].count()),
                    'Mean': float(df[col].mean()),
                    'Median': float(df[col].median()),
                    'Min': float(df[col].min()),
                    'Max': float(df[col].max()),
                    'Sum': float(df[col].sum())
                })
            
            # For categorical columns
            for col in df.select_dtypes(include=['object']).columns:
                summary_rows.append({
                    'Column': col,
                    'Count': int(df[col].count()),
                    'Unique_Values': int(df[col].nunique()),
                    'Most_Common': df[col].mode()[0] if len(df[col].mode()) > 0 else 'N/A',
                    'Type': 'Categorical'
                })
            
            return summary_rows
            
        except Exception as e:
            print(f"Summary generation error: {e}")
            return [{'error': str(e)}]
    
    def prepare_download(self, file_path: str) -> Dict[str, Any]:
        """
        Prepare file for download
        
        Args:
            file_path: Path to file
            
        Returns:
            Download preparation result
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            return {
                'success': True,
                'file_path': file_path,
                'filename': filename,
                'file_size': file_size,
                'ready': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Download preparation error: {str(e)}'
            }

