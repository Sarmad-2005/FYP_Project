"""
LangChain Tools for Q&A Operations
"""

from langchain.tools import BaseTool
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import json
import pandas as pd
import numpy as np


class CalculationInput(BaseModel):
    """Input for Calculation Tool"""
    operation: str = Field(description="Type of calculation: 'sum', 'average', 'count', 'max', 'min', 'std'")
    values: str = Field(description="JSON string of numeric values or column data")
    column_name: Optional[str] = Field(description="Optional column name for context", default=None)


class CalculationTool(BaseTool):
    """Tool for performing calculations on CSV data"""
    
    name: str = "calculate"
    description: str = """
    Perform mathematical calculations on CSV data.
    
    Operations:
    - 'sum': Sum of all values
    - 'average' or 'mean': Average of values
    - 'count': Count of values
    - 'max': Maximum value
    - 'min': Minimum value
    - 'std': Standard deviation
    - 'median': Median value
    - 'percentage': Calculate percentage (requires two values: part and total)
    
    Input should be a JSON with 'operation' and 'values' (JSON array of numbers).
    """
    args_schema: type[BaseModel] = CalculationInput
    
    def _run(self, operation: str, values: str, column_name: Optional[str] = None) -> str:
        """Execute calculation"""
        try:
            # Parse values from JSON string
            values_list = json.loads(values) if isinstance(values, str) else values
            
            # Convert to numpy array for calculations
            values_array = np.array([float(v) for v in values_list if v is not None])
            
            if len(values_array) == 0:
                return "Error: No valid numeric values provided"
            
            column_context = f" for column '{column_name}'" if column_name else ""
            
            if operation in ['sum', 'total']:
                result = np.sum(values_array)
                return f"Sum{column_context}: {result:,.2f} (calculated from {len(values_array)} values)"
            
            elif operation in ['average', 'mean', 'avg']:
                result = np.mean(values_array)
                return f"Average{column_context}: {result:,.2f} (calculated from {len(values_array)} values)"
            
            elif operation == 'count':
                result = len(values_array)
                return f"Count{column_context}: {result} values"
            
            elif operation == 'max':
                result = np.max(values_array)
                return f"Maximum{column_context}: {result:,.2f}"
            
            elif operation == 'min':
                result = np.min(values_array)
                return f"Minimum{column_context}: {result:,.2f}"
            
            elif operation in ['std', 'stdev', 'standard_deviation']:
                result = np.std(values_array)
                return f"Standard Deviation{column_context}: {result:,.2f}"
            
            elif operation == 'median':
                result = np.median(values_array)
                return f"Median{column_context}: {result:,.2f}"
            
            elif operation == 'percentage':
                if len(values_array) >= 2:
                    part = values_array[0]
                    total = values_array[1]
                    if total != 0:
                        result = (part / total) * 100
                        return f"Percentage{column_context}: {result:.2f}% ({part:,.2f} out of {total:,.2f})"
                    return "Error: Cannot calculate percentage with total = 0"
                return "Error: Percentage calculation requires two values (part and total)"
            
            return f"Unknown operation: {operation}"
            
        except Exception as e:
            return f"Calculation Error: {str(e)}"
    
    async def _arun(self, operation: str, values: str, column_name: Optional[str] = None) -> str:
        """Async version - not implemented, calls sync version"""
        return self._run(operation, values, column_name)


class ContextInput(BaseModel):
    """Input for Context Tool"""
    selected_cells: str = Field(description="JSON string of selected cell data (list of {row, column, value})")
    csv_data: Optional[str] = Field(description="Optional full CSV data as JSON string", default=None)
    context_type: str = Field(description="Type of context needed: 'selection', 'full', 'summary'", default="selection")


class ContextTool(BaseTool):
    """Tool for building context from CSV selections"""
    
    name: str = "build_context"
    description: str = """
    Build context from selected CSV cells and data for answering questions.
    
    Context types:
    - 'selection': Focus only on selected cells
    - 'full': Include full CSV data context
    - 'summary': Provide statistical summary of data
    
    Input should be a JSON with 'selected_cells' (JSON array) and optional 'csv_data' and 'context_type'.
    """
    args_schema: type[BaseModel] = ContextInput
    
    def _run(self, selected_cells: str, csv_data: Optional[str] = None, context_type: str = "selection") -> str:
        """Build context from selections"""
        try:
            # Parse selected cells - handle Python None values
            if isinstance(selected_cells, str):
                # Replace Python 'None' with JSON 'null' before parsing
                selected_cells_clean = selected_cells.replace(': None', ': null').replace(':None', ':null')
                cells = json.loads(selected_cells_clean)
            else:
                cells = selected_cells
            
            if not cells:
                return "No cells selected"
            
            # Extract information from selected cells
            num_cells = len(cells)
            context_parts = []
            
            # For row-based selections, extract all data from each row
            if isinstance(cells, list) and len(cells) > 0 and isinstance(cells[0], dict):
                # Build a readable context with row data
                context_parts.append(f"The user selected {num_cells} rows with the following data:\n")
                
                for i, row in enumerate(cells[:10], 1):  # Limit to first 10 rows for context
                    row_data = []
                    for key, value in row.items():
                        if value is not None and key != '__rowNum':
                            row_data.append(f"{key}: {value}")
                    if row_data:
                        context_parts.append(f"- Row {i}: {', '.join(row_data)}")
                
                if num_cells > 10:
                    context_parts.append(f"... and {num_cells - 10} more rows")
            else:
                # Fallback for cell-based selections
                columns = list(set(cell.get('column', '') for cell in cells if 'column' in cell))
                context_parts.append(f"Selected {num_cells} cells from columns: {columns}")
            
            # Try to extract numeric values for quick stats (optional)
            numeric_values = []
            for cell in cells:
                if isinstance(cell, dict):
                    for key, value in cell.items():
                        # Skip ID fields and row numbers
                        if key not in ['__rowNum', 'NewGSNo', 'SchemeNo', 'ProjectID', 'Latitude', 'Longitude']:
                            try:
                                numeric_values.append(float(value))
                            except (ValueError, TypeError, AttributeError):
                                pass
            
            # Add numeric stats if available (optional - keep it brief)
            if numeric_values and len(numeric_values) > 0:
                context_parts.append(f"\nNumeric statistics: {len(numeric_values)} values, Range: {min(numeric_values):,.2f} to {max(numeric_values):,.2f}, Average: {np.mean(numeric_values):,.2f}")
            
            # If full CSV data is provided
            if csv_data and context_type == 'full':
                try:
                    full_data = json.loads(csv_data) if isinstance(csv_data, str) else csv_data
                    df = pd.DataFrame(full_data)
                    context_parts.append(f"Full CSV context: {len(df)} rows, {len(df.columns)} columns")
                    context_parts.append(f"Available columns: {df.columns.tolist()}")
                except:
                    pass
            
            # Return as a clean context string
            return "\n".join(context_parts)
            
        except json.JSONDecodeError as e:
            return f"JSON Parse Error: {str(e)}. Unable to parse selected cells data."
        except Exception as e:
            return f"Context Building Error: {str(e)}"
    
    async def _arun(self, selected_cells: str, csv_data: Optional[str] = None, context_type: str = "selection") -> str:
        """Async version - not implemented, calls sync version"""
        return self._run(selected_cells, csv_data, context_type)

