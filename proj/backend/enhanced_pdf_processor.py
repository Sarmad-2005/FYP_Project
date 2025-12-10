"""
Enhanced PDF processor using PyMuPDF for better table extraction and spatial awareness.
Uses PyMuPDF for extraction, L6 model for embeddings, ChromaDB for storage.
"""

import fitz  # PyMuPDF
import pandas as pd
from sentence_transformers import SentenceTransformer
import re
from typing import List, Dict, Tuple
import json

class EnhancedPDFProcessor:
    """Enhanced processor: PyMuPDF for extraction, L6 for embeddings, ChromaDB for storage."""
    
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
    
    def process_pdf(self, pdf_path: str) -> Tuple[List[str], List[Dict]]:
        """
        Main method to process PDF and return sentences and tables
        """
        try:
            # Extract content from PDF
            tables, text_content = self._extract_content(pdf_path)
            
            # Process tables (each table as one chunk)
            table_chunks = self._process_tables(tables)
            
            # Process non-tabular text (sentence-level chunks)
            text_chunks = self._process_text(text_content)
            
            # Convert to the format expected by your existing system
            sentences = [chunk['content'] for chunk in text_chunks]
            tables = table_chunks
            
            return sentences, tables
            
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return [], []
    
    def _extract_content(self, pdf_path: str) -> Tuple[List[Dict], str]:
        """
        Extract tables and text separately from PDF
        """
        doc = fitz.open(pdf_path)
        all_tables = []
        all_text = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text (excluding tables)
            text = self._extract_text_excluding_tables(page)
            all_text.append(f"--- Page {page_num + 1} ---\n{text}")
            
            # Extract tables
            page_tables = self._extract_tables(page, page_num)
            all_tables.extend(page_tables)
        
        doc.close()
        return all_tables, '\n'.join(all_text)
    
    def _extract_text_excluding_tables(self, page) -> str:
        """
        Extract text while trying to exclude table content
        """
        # Get the page dimensions
        rect = page.rect
        
        # First, identify table areas
        table_areas = self._identify_table_areas(page)
        
        # Extract text blocks that are not in table areas
        text_blocks = []
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" in block:  # Text block
                block_rect = fitz.Rect(block["bbox"])
                
                # Check if this block overlaps with any table area
                is_table_content = False
                for table_area in table_areas:
                    if self._rectangles_overlap(block_rect, table_area):
                        is_table_content = True
                        break
                
                if not is_table_content:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_blocks.append(span["text"])
        
        return ' '.join(text_blocks)
    
    def _identify_table_areas(self, page) -> List[fitz.Rect]:
        """
        Identify potential table areas on the page using PyMuPDF's table detection
        """
        table_areas = []
        
        try:
            # Use PyMuPDF's built-in table detection
            page_tables = page.find_tables()
            
            if page_tables.tables:
                for table in page_tables.tables:
                    # Get table bounding box
                    bbox = table.bbox
                    table_areas.append(fitz.Rect(bbox))
        
        except Exception as e:
            print(f"Error identifying table areas: {e}")
        
        return table_areas
    
    def _extract_tables(self, page, page_num: int) -> List[Dict]:
        """
        Extract tables from PDF page using PyMuPDF's native table extraction
        """
        tables = []
        
        try:
            # Use PyMuPDF's built-in table extraction
            page_tables = page.find_tables()
            
            if page_tables.tables:
                for table_num, table in enumerate(page_tables.tables):
                    df = table.to_pandas()
                    table_text = self._dataframe_to_text(df)
                    
                    tables.append({
                        'content': table_text,
                        'type': 'table',
                        'page': page_num + 1,
                        'table_num': table_num,
                        'headers': list(df.columns) if not df.empty else [],
                        'rows': df.values.tolist() if not df.empty else [],
                        'row_count': len(df),
                        'column_count': len(df.columns),
                        'dataframe': df.to_dict(),  # Store structured data
                        'metadata': {
                            'rows': len(df),
                            'columns': len(df.columns),
                            'headers': list(df.columns)
                        }
                    })
        
        except Exception as e:
            print(f"Error extracting tables from page {page_num}: {e}")
        
        return tables
    
    def _dataframe_to_text(self, df: pd.DataFrame) -> str:
        """
        Convert DataFrame to readable text representation
        """
        try:
            if df.empty:
                return "Empty table"
            
            # Create a text representation of the table
            text_representation = "TABLE:\n"
            
            # Add headers
            headers = " | ".join(str(col) for col in df.columns)
            text_representation += headers + "\n"
            text_representation += "-" * len(headers) + "\n"
            
            # Add rows
            for _, row in df.iterrows():
                row_text = " | ".join(str(cell) for cell in row)
                text_representation += row_text + "\n"
            
            return text_representation.strip()
        
        except Exception as e:
            # Fallback: simple string representation
            return f"Table with {len(df)} rows and {len(df.columns)} columns: " + str(df.to_dict())
    
    def _process_tables(self, tables: List[Dict]) -> List[Dict]:
        """
        Process tables - each table becomes one chunk
        """
        table_chunks = []
        
        for i, table in enumerate(tables):
            chunk = {
                'content': table['content'],
                'type': 'table',
                'page': table['page'],
                'table_id': i,
                'headers': table.get('headers', []),
                'rows': table.get('rows', []),
                'row_count': table.get('row_count', 0),
                'column_count': table.get('column_count', 0),
                'metadata': table.get('metadata', {}),
                'original_data': table.get('dataframe', {})
            }
            table_chunks.append(chunk)
        
        return table_chunks
    
    def _process_text(self, text_content: str) -> List[Dict]:
        """
        Process non-tabular text - split into sentence-level chunks
        """
        # First, split into sentences
        sentences = self._split_into_sentences(text_content)
        
        text_chunks = []
        chunk_id = 0
        
        for sentence in sentences:
            if len(sentence.strip()) > 10:  # Ignore very short sentences
                chunk = {
                    'content': sentence.strip(),
                    'type': 'text',
                    'chunk_id': chunk_id,
                    'metadata': {
                        'length': len(sentence),
                        'words': len(sentence.split())
                    }
                }
                text_chunks.append(chunk)
                chunk_id += 1
        
        return text_chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Robust sentence splitting
        """
        # Basic sentence splitting with regex
        sentence_endings = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(sentence_endings, text)
        
        # Clean up sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.replace('\n', ' ').strip()
            sentence = re.sub(r'\s+', ' ', sentence)  # Normalize whitespace
            
            if sentence and len(sentence) > 10:  # Meaningful sentences only
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _rectangles_overlap(self, rect1: fitz.Rect, rect2: fitz.Rect) -> bool:
        """
        Check if two rectangles overlap
        """
        return not (rect1.x1 < rect2.x0 or 
                   rect1.x0 > rect2.x1 or 
                   rect1.y1 < rect2.y0 or 
                   rect1.y0 > rect2.y1)
    
    def table_to_text(self, table: Dict) -> str:
        """
        Convert table to text representation for embedding.
        Compatible with existing system.
        """
        try:
            # Support both dict-shaped tables and pre-rendered text tables
            if not isinstance(table, dict):
                return str(table)

            # If it already has a content field, use it
            if 'content' in table:
                return table['content']

            text_parts = []

            if table.get('headers'):
                text_parts.append("Headers: " + " | ".join(table['headers']))

            if table.get('rows'):
                text_parts.append("Data:")
                for row in table['rows']:
                    text_parts.append(" | ".join(str(cell) for cell in row))

            return "\n".join(text_parts)
            
        except Exception as e:
            print(f"Error converting table to text: {e}")
            return str(table)
