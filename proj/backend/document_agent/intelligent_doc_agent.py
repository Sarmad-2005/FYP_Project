"""
Intelligent Document Creator: user-driven document generation with reasoning over available data.
"""

from typing import Dict, Any, List
import json
import requests
import time
from backend.document_agent.chroma_manager import DocumentChromaManager


class IntelligentDocAgent:
    def __init__(self, llm_manager, performance_agent, financial_agent, chroma_manager=None, orchestrator=None):
        self.llm_manager = llm_manager
        self.performance_agent = performance_agent
        self.financial_agent = financial_agent
        self.chroma_manager = chroma_manager or DocumentChromaManager()
        self.orchestrator = orchestrator  # For A2A protocol in microservice mode

    def _reason_intent(self, user_instructions: str) -> str:
        prompt = f"""
You are an intent classifier. Given the user's request, identify which data sources to use:
- performance: milestones, tasks, bottlenecks, requirements, actors
- finance: transactions, expense/revenue analyses, actor-transaction mappings, anomalies

User request:
{user_instructions}

Return a JSON object with two arrays: "performance_fields" and "finance_fields" listing which to use. If none, return empty arrays. No extra text.
"""
        resp = self.llm_manager.simple_chat(prompt)
        if not resp.get("success"):
            return '{"performance_fields": [], "finance_fields": []}'
        return resp.get("response", '{"performance_fields": [], "finance_fields": []}')

    def _fetch_data(self, project_id: str, perf_fields: List[str], fin_fields: List[str]) -> Dict[str, Any]:
        """Fetch data using A2A protocol if orchestrator available, otherwise direct calls"""
        data = {}
        
        # Use orchestrator (A2A) if available (microservice mode), otherwise direct calls (monolith mode)
        if self.orchestrator:
            try:
                # Performance data via A2A
                if "milestones" in perf_fields:
                    milestones = self.orchestrator.route_data_request(
                        query="Get all project milestones with their details and status",
                        requesting_agent="intelligent_doc_agent",
                        project_id=project_id
                    )
                    data["milestones"] = milestones or []
                
                if "tasks" in perf_fields:
                    tasks = self.orchestrator.route_data_request(
                        query="Get all project tasks with their details",
                        requesting_agent="intelligent_doc_agent",
                        project_id=project_id
                    )
                    data["tasks"] = tasks or []
                
                if "bottlenecks" in perf_fields:
                    bottlenecks = self.orchestrator.route_data_request(
                        query="Get all project bottlenecks and potential issues",
                        requesting_agent="intelligent_doc_agent",
                        project_id=project_id
                    )
                    data["bottlenecks"] = bottlenecks or []
                
                if "requirements" in perf_fields:
                    requirements = self.orchestrator.route_data_request(
                        query="Get all project requirements with categories and priorities",
                        requesting_agent="intelligent_doc_agent",
                        project_id=project_id
                    )
                    data["requirements"] = requirements or []
                
                if "actors" in perf_fields:
                    actors = self.orchestrator.route_data_request(
                        query="Get all project actors/stakeholders with type and role",
                        requesting_agent="intelligent_doc_agent",
                        project_id=project_id
                    )
                    data["actors"] = actors or []
                
                # Financial data via A2A
                if "transactions" in fin_fields:
                    txns = self.orchestrator.route_data_request(
                        query="Get all financial transactions for the project",
                        requesting_agent="intelligent_doc_agent",
                        project_id=project_id
                    )
                    data["transactions"] = txns or []
                
                if "expense_analysis" in fin_fields:
                    expense = self.orchestrator.route_data_request(
                        query="Get expense analysis with task mappings",
                        requesting_agent="intelligent_doc_agent",
                        project_id=project_id
                    )
                    data["expense_analysis"] = expense if isinstance(expense, dict) else {}
                
                if "revenue_analysis" in fin_fields:
                    revenue = self.orchestrator.route_data_request(
                        query="Get revenue analysis with milestone linkages",
                        requesting_agent="intelligent_doc_agent",
                        project_id=project_id
                    )
                    data["revenue_analysis"] = revenue if isinstance(revenue, dict) else {}
                
                if "actor_transaction_mappings" in fin_fields:
                    actor_map = self.orchestrator.route_data_request(
                        query="Get actor to transaction mappings",
                        requesting_agent="intelligent_doc_agent",
                        project_id=project_id
                    )
                    data["actor_transaction_mappings"] = actor_map if isinstance(actor_map, list) else []
                
                if "anomalies" in fin_fields:
                    anomalies = self.orchestrator.route_data_request(
                        query="Get financial anomalies and irregularities",
                        requesting_agent="intelligent_doc_agent",
                        project_id=project_id
                    )
                    data["anomalies"] = anomalies if isinstance(anomalies, dict) else {}
                    
            except Exception as e:
                print(f"⚠️  A2A data fetch failed, falling back to direct calls: {e}")
                # Fallback to direct calls
                data = self._fetch_data_direct(project_id, perf_fields, fin_fields)
        else:
            # Monolith mode: direct calls
            data = self._fetch_data_direct(project_id, perf_fields, fin_fields)
        
        return data
    
    def _fetch_data_direct(self, project_id: str, perf_fields: List[str], fin_fields: List[str]) -> Dict[str, Any]:
        """Direct calls to agents (monolith mode fallback)"""
        data = {}
        if "milestones" in perf_fields:
            data["milestones"] = self.performance_agent.milestone_agent.get_project_milestones(project_id)
        if "tasks" in perf_fields:
            data["tasks"] = self.performance_agent.task_agent.get_project_tasks(project_id)
        if "bottlenecks" in perf_fields:
            data["bottlenecks"] = self.performance_agent.bottleneck_agent.get_project_bottlenecks(project_id)
        if "requirements" in perf_fields:
            data["requirements"] = self.performance_agent.chroma_manager.get_performance_data('requirements', project_id)
        if "actors" in perf_fields:
            data["actors"] = self.performance_agent.chroma_manager.get_performance_data('actors', project_id)

        if "transactions" in fin_fields:
            data["transactions"] = self.financial_agent.chroma_manager.get_financial_data('transactions', project_id)
        if "expense_analysis" in fin_fields:
            data["expense_analysis"] = self.financial_agent.expense_agent.get_expense_analysis(project_id)
        if "revenue_analysis" in fin_fields:
            txns = data.get("transactions") or self.financial_agent.chroma_manager.get_financial_data('transactions', project_id)
            data["revenue_analysis"] = self.financial_agent.revenue_agent.analyze_revenue(project_id, txns)
        if "actor_transaction_mappings" in fin_fields:
            data["actor_transaction_mappings"] = self.financial_agent.get_actor_transaction_mappings(project_id)
        if "anomalies" in fin_fields:
            data["anomalies"] = self.financial_agent.anomaly_agent.get_anomalies(project_id, {})

        return data

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 characters per token"""
        return len(text) // 4
    
    def _call_llm_with_lower_tokens(self, prompt: str, max_tokens: int = 2000) -> Dict[str, Any]:
        """Call LLM with custom max_tokens for document generation to avoid context limits"""
        # For Hugging Face, we need to call the API directly with lower max_tokens
        if hasattr(self.llm_manager, 'current_llm') and self.llm_manager.current_llm == 'huggingface':
            try:
                import requests
                import time
                
                # Rate limiting
                time_since_last_call = time.time() - self.llm_manager.last_huggingface_call_time
                if time_since_last_call < 2:
                    delay_needed = 2 - time_since_last_call
                    time.sleep(delay_needed)
                
                self.llm_manager.last_huggingface_call_time = time.time()
                
                headers = {
                    "Authorization": f"Bearer {self.llm_manager.huggingface_api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.llm_manager.huggingface_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": max_tokens  # Use custom lower max_tokens
                }
                
                response = requests.post(
                    self.llm_manager.huggingface_api_url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        generated_text = result["choices"][0].get("message", {}).get("content", "")
                        if generated_text:
                            return {
                                "response": generated_text,
                                "model": self.llm_manager.huggingface_model,
                                "success": True
                            }
                
                return {
                    "error": f"Hugging Face API error ({response.status_code}): {response.text}",
                    "success": False
                }
            except Exception as e:
                return {
                    "error": f"Hugging Face API error: {str(e)}",
                    "success": False
                }
        else:
            # For other LLMs, use regular simple_chat
            return self.llm_manager.simple_chat(prompt)
    
    def _truncate_large_array(self, data: Any, max_items: int = 10) -> Any:
        """Truncate large arrays to summaries to reduce token count"""
        if isinstance(data, list):
            if len(data) > max_items:
                # Keep first few and last few, summarize the middle
                kept = data[:max_items//2] + data[-max_items//2:]
                summary = {
                    "total_count": len(data),
                    "items_shown": len(kept),
                    "note": f"Showing first {max_items//2} and last {max_items//2} of {len(data)} total items"
                }
                return kept + [summary]
            return data
        elif isinstance(data, dict):
            # Recursively truncate arrays in dict
            return {k: self._truncate_large_array(v, max_items) for k, v in data.items()}
        return data
    
    def _split_data_into_chunks(self, data: Dict[str, Any], max_tokens_per_chunk: int = 1500) -> List[Dict[str, Any]]:
        """Split data into chunks based on token count, intelligently handling arrays"""
        # First, truncate large arrays to reasonable size (keep up to 20 items per array for better coverage)
        truncated_data = self._truncate_large_array(data.copy(), max_items=20)
        
        chunks = []
        
        # Strategy: Group related data together, split large arrays across chunks
        for key, value in truncated_data.items():
            # If value is a list/array, split it across multiple chunks if needed
            if isinstance(value, list) and len(value) > 0:
                # Estimate tokens per item
                try:
                    sample_item = json.dumps({key: [value[0]]}, indent=2, default=str)
                    tokens_per_item = self._estimate_tokens(sample_item)
                except:
                    tokens_per_item = 200  # Conservative estimate
                
                # Calculate how many items per chunk
                items_per_chunk = max(1, max_tokens_per_chunk // max(tokens_per_item, 1))
                
                # Split array into sub-arrays
                for i in range(0, len(value), items_per_chunk):
                    chunk_data = {key: value[i:i + items_per_chunk]}
                    chunks.append(chunk_data)
            else:
                # Non-array data - add to current chunk or create new one
                try:
                    item_json = json.dumps({key: value}, indent=2, default=str)
                    item_tokens = self._estimate_tokens(item_json)
                except:
                    item_tokens = 500  # Conservative estimate
                
                # If this single item is too large, it goes in its own chunk
                if item_tokens > max_tokens_per_chunk:
                    chunks.append({key: value})
                else:
                    # Try to add to last chunk if it fits, otherwise create new chunk
                    if chunks:
                        last_chunk = chunks[-1]
                        last_chunk_json = json.dumps(last_chunk, indent=2, default=str)
                        last_chunk_tokens = self._estimate_tokens(last_chunk_json)
                        
                        if last_chunk_tokens + item_tokens <= max_tokens_per_chunk:
                            last_chunk[key] = value
                            continue
                    
                    # Create new chunk
                    chunks.append({key: value})
        
        # Filter out empty chunks
        chunks = [chunk for chunk in chunks if chunk and len(str(chunk)) > 50]
        
        # Ensure we have at least one chunk
        if not chunks:
            chunks = [truncated_data] if truncated_data else [{}]
        
        # If we have one very large chunk, split it further
        if len(chunks) == 1:
            single_chunk = chunks[0]
            single_chunk_json = json.dumps(single_chunk, indent=2, default=str)
            single_chunk_tokens = self._estimate_tokens(single_chunk_json)
            
            # If chunk is too large, split it
            if single_chunk_tokens > max_tokens_per_chunk:
                keys = list(single_chunk.keys())
                if len(keys) > 1:
                    # Split keys in half
                    mid = len(keys) // 2
                    chunks = [
                        {k: single_chunk[k] for k in keys[:mid]},
                        {k: single_chunk[k] for k in keys[mid:]}
                    ]
                elif len(keys) == 1 and isinstance(single_chunk[keys[0]], list):
                    # Split the array
                    arr = single_chunk[keys[0]]
                    mid = len(arr) // 2
                    chunks = [
                        {keys[0]: arr[:mid]},
                        {keys[0]: arr[mid:]}
                    ]
        
        print(f"   📦 Split data into {len(chunks)} chunks (max {max_tokens_per_chunk} tokens each)")
        return chunks
    
    def _generate_empty_document(self, title: str, user_instructions: str) -> str:
        """Generate a basic HTML document when no data is available"""
        from datetime import datetime
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        .meta {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}
        .no-data {{
            background: #ecf0f1;
            border-left: 4px solid #e74c3c;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .no-data h2 {{
            color: #e74c3c;
            margin-bottom: 10px;
        }}
        .instructions {{
            background: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .instructions h3 {{
            color: #2e7d32;
            margin-bottom: 10px;
        }}
        .no-data ul {{
            margin-left: 20px;
            margin-top: 10px;
        }}
        .no-data ul li {{
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p class="meta">Generated on: {current_date}</p>
        
        <div class="instructions">
            <h3>User Instructions</h3>
            <p>{user_instructions if user_instructions else 'No specific instructions provided.'}</p>
        </div>
        
        <div class="no-data">
            <h2>⚠️ No Data Available</h2>
            <p>This document was generated but no project data was available at the time of generation. Please ensure that:</p>
            <ul>
                <li>The project has been analyzed by the Performance Agent</li>
                <li>The project has financial data from the Financial Agent</li>
                <li>Relevant data has been stored in the system</li>
            </ul>
            <p style="margin-top: 15px;">You can regenerate this document after the project data has been processed.</p>
        </div>
    </div>
</body>
</html>"""
        return html
    
    def _generate_document_chunked(self, title: str, user_instructions: str, data: Dict[str, Any]) -> str:
        """Generate document in multiple LLM calls: structure+beginning, middle sections, end"""
        # Split data into chunks based on token count (max 1500 tokens per chunk to leave room for prompt + response)
        # With 1500 data tokens + ~1000 prompt tokens + 2000 max_tokens = ~4500 total (well under 8192 limit)
        data_chunks = self._split_data_into_chunks(data, max_tokens_per_chunk=1500)
        num_chunks = len(data_chunks)
        
        print(f"   📊 Generating document in {num_chunks} LLM calls...")
        
        # Handle empty data case
        if num_chunks == 0:
            print("   ⚠️  No data available - generating basic document structure...")
            # Generate a basic document with no data
            return self._generate_empty_document(title, user_instructions)
        
        # Serialize chunks and filter out empty ones
        chunk_jsons = []
        for i, chunk in enumerate(data_chunks):
            try:
                chunk_json = json.dumps(chunk, indent=2, default=str)
                chunk_tokens = self._estimate_tokens(chunk_json)
                # Only add non-empty chunks (at least 50 tokens to be meaningful)
                if chunk_tokens > 50:
                    print(f"   📦 Chunk {i+1}: ~{chunk_tokens} tokens")
                    chunk_jsons.append(chunk_json)
                else:
                    print(f"   ⚠️  Chunk {i+1} too small ({chunk_tokens} tokens) - skipping")
            except Exception as e:
                print(f"⚠️  Error serializing chunk {i+1}: {e}")
                # Only add if it's not empty
                chunk_str = str(chunk)
                if len(chunk_str) > 100:  # Meaningful content
                    chunk_jsons.append(chunk_str)
        
        # Update num_chunks based on actual valid chunks
        num_chunks = len(chunk_jsons)
        
        # Ensure we have at least one chunk
        if not chunk_jsons:
            print("   ⚠️  No valid chunks created - generating basic document structure...")
            return self._generate_empty_document(title, user_instructions)
        
        print(f"   📊 Processing {num_chunks} valid chunks for document generation...")
        
        html_parts = []
        
        # Call 1: Generate document structure and beginning
        print(f"   📝 LLM Call 1/{num_chunks}: Generating document structure and beginning...")
        # Enhanced prompt with strict data requirements
        prompt1 = f"""Create professional HTML document "{title}".

PART 1/{num_chunks}: Generate HEADER, OVERVIEW, BEGINNING SECTIONS.

User Instructions: {user_instructions}

Data (JSON) - USE ONLY THIS DATA, DO NOT INVENT OR HALLUCINATE:
{chunk_jsons[0]}

CRITICAL RULES:
1. Start with complete HTML structure: <html><head><title>{title}</title><style>...</style></head><body><div class="container">
2. Add professional CSS styling in <style> tag (fonts, colors, spacing, table styles)
3. Create header with <h1> for title and <p> for generation date (use actual current date like "2025-12-10")
4. ONLY use data that exists in the JSON above - DO NOT create fake requirements, milestones, or any data
5. If JSON is empty or has no meaningful data, create a simple header and state "No data available for this section"
6. For Overview: ONLY include metrics that exist in the JSON data. If no metrics exist, skip the overview or state "Overview data not available"
7. Generate first 1-2 sections using ONLY the actual data from JSON
8. For tables: Extract REAL data from JSON arrays. Each row = one item from the array with actual field values
9. Format tables properly: <table><thead><tr><th>Column1</th>...</tr></thead><tbody><tr><td>Actual Value</td>...</tr></tbody></table>
10. Do NOT include markdown code blocks (```html) - return ONLY raw HTML
11. Do NOT close </div></body></html> yet - this will be done in final part
12. DO NOT INVENT DATA - if a field doesn't exist in JSON, don't create it

ANTI-HALLUCINATION: If the JSON data is empty, minimal, or doesn't contain the information needed, explicitly state that in the document rather than making up data.

Return ONLY valid HTML starting with <html> tag. Do NOT wrap in code blocks.
"""
        resp1 = self._call_llm_with_lower_tokens(prompt1, max_tokens=2000)
        if not resp1.get("success"):
            raise RuntimeError(resp1.get("error", "LLM error in part 1"))
        part1 = resp1.get("response", "").strip()
        
        # Clean up markdown code blocks if present
        if part1.startswith("```html"):
            part1 = part1[7:]
        if part1.startswith("```"):
            part1 = part1[3:]
        if part1.endswith("```"):
            part1 = part1[:-3]
        part1 = part1.strip()
        
        # Ensure proper HTML structure with professional styling
        if not part1.startswith("<html"):
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            professional_css = """<style>
body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 30px; line-height: 1.8; background: #f5f5f5; }
.container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
h1 { color: #2c3e50; border-bottom: 4px solid #3498db; padding-bottom: 15px; margin-bottom: 30px; font-size: 2.2em; }
h2 { color: #34495e; margin-top: 40px; margin-bottom: 20px; font-size: 1.6em; border-left: 4px solid #3498db; padding-left: 15px; }
h3 { color: #7f8c8d; margin-top: 25px; margin-bottom: 15px; }
p { margin: 15px 0; color: #555; }
table { width: 100%; border-collapse: collapse; margin: 20px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
th { background: #3498db; color: white; padding: 12px; text-align: left; font-weight: 600; }
td { padding: 10px 12px; border-bottom: 1px solid #ddd; }
tr:nth-child(even) { background: #f8f9fa; }
tr:hover { background: #e8f4f8; }
ul, ol { margin: 15px 0; padding-left: 30px; }
li { margin: 8px 0; color: #555; }
.footer { margin-top: 50px; padding-top: 20px; border-top: 2px solid #ddd; color: #7f8c8d; text-align: center; font-size: 0.9em; }
</style>"""
            part1 = f"""<html><head><title>{title}</title>{professional_css}</head><body><div class="container"><h1>{title}</h1><p style="color: #7f8c8d; margin-bottom: 30px;">Generated on {current_date}</p>{part1}"""
        elif "<style>" not in part1 and "<head>" in part1:
            # Add professional CSS if missing
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            professional_css = """<style>
body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 30px; line-height: 1.8; background: #f5f5f5; }
.container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
h1 { color: #2c3e50; border-bottom: 4px solid #3498db; padding-bottom: 15px; margin-bottom: 30px; font-size: 2.2em; }
h2 { color: #34495e; margin-top: 40px; margin-bottom: 20px; font-size: 1.6em; border-left: 4px solid #3498db; padding-left: 15px; }
h3 { color: #7f8c8d; margin-top: 25px; margin-bottom: 15px; }
p { margin: 15px 0; color: #555; }
table { width: 100%; border-collapse: collapse; margin: 20px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
th { background: #3498db; color: white; padding: 12px; text-align: left; font-weight: 600; }
td { padding: 10px 12px; border-bottom: 1px solid #ddd; }
tr:nth-child(even) { background: #f8f9fa; }
tr:hover { background: #e8f4f8; }
ul, ol { margin: 15px 0; padding-left: 30px; }
li { margin: 8px 0; color: #555; }
.footer { margin-top: 50px; padding-top: 20px; border-top: 2px solid #ddd; color: #7f8c8d; text-align: center; font-size: 0.9em; }
</style>"""
            part1 = part1.replace("</head>", f"{professional_css}</head>")
            if "<div class=\"container\">" not in part1:
                part1 = part1.replace("<body>", "<body><div class=\"container\">")
        html_parts.append(part1)
        print(f"   ✅ Part 1 generated: {len(part1)} chars")
        
        # Middle calls: Generate sections for chunks 2 to n-1
        for i in range(1, num_chunks - 1):
            print(f"   📝 LLM Call {i+1}/{num_chunks}: Generating middle sections...")
            # Enhanced prompt for middle sections with strict data requirements
            prompt_mid = f"""Continue professional HTML document "{title}".

PART {i+1}/{num_chunks}: Generate MIDDLE SECTIONS.

User Instructions: {user_instructions}

Data (JSON) - USE ONLY THIS DATA, DO NOT INVENT:
{chunk_jsons[i]}

CRITICAL RULES:
1. Generate 2-3 middle sections based on instructions and ACTUAL data from JSON
2. Use proper HTML structure: <h2> for section titles, <p> for paragraphs, <table> for tables
3. ONLY use data that exists in the JSON above - DO NOT create fake or example data
4. Format tables with proper HTML structure:
   <table>
     <thead>
       <tr>
         <th>Column Header 1</th>
         <th>Column Header 2</th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td>Actual Value 1</td>
         <td>Actual Value 2</td>
       </tr>
     </tbody>
   </table>
5. Extract data from JSON arrays: For each item in an array, create one table row with actual field values
6. If JSON is empty or has no data, create a section stating "No data available for this section"
7. Apply consistent styling (assume CSS from part 1)
8. Return ONLY the HTML body content - NO <html>, <head>, <body> tags
9. Do NOT include markdown code blocks
10. Do NOT close </div></body></html> yet
11. DO NOT INVENT DATA - use only what's in the JSON

ANTI-HALLUCINATION: Extract actual field names and values from the JSON. If a field is missing, don't create it.

Return ONLY the HTML content that continues the document body.
"""
            resp_mid = self._call_llm_with_lower_tokens(prompt_mid, max_tokens=2000)
            if not resp_mid.get("success"):
                raise RuntimeError(resp_mid.get("error", f"LLM error in part {i+1}"))
            part_mid = resp_mid.get("response", "").strip()
            
            # Clean up markdown code blocks if present
            if part_mid.startswith("```html"):
                part_mid = part_mid[7:]
            if part_mid.startswith("```"):
                part_mid = part_mid[3:]
            if part_mid.endswith("```"):
                part_mid = part_mid[:-3]
            part_mid = part_mid.strip()
            
            # Remove any HTML document structure tags (should only be body content)
            part_mid = part_mid.replace("<html>", "").replace("</html>", "").replace("<head>", "").replace("</head>", "").replace("<body>", "").replace("</body>", "").strip()
            html_parts.append(part_mid)
            print(f"   ✅ Part {i+1} generated: {len(part_mid)} chars")
        
        # Final call: Generate conclusion
        print(f"   📝 LLM Call {num_chunks}/{num_chunks}: Generating final sections and conclusion...")
        # Enhanced prompt for final sections with strict data requirements
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt_final = f"""Complete professional HTML document "{title}".

PART {num_chunks}/{num_chunks}: Generate FINAL SECTIONS and CONCLUSION.

User Instructions: {user_instructions}

Data (JSON) - USE ONLY THIS DATA, DO NOT INVENT:
{chunk_jsons[-1]}

CRITICAL RULES:
1. Generate remaining sections based on instructions and ACTUAL data from JSON
2. Add a "Recommendations" or "Conclusion" section based on the actual data (not generic recommendations)
3. Add a professional footer with generation date: {current_date} (use this exact date)
4. ONLY use data that exists in the JSON above - DO NOT create fake data
5. Use proper HTML formatting: <h2> for section titles, <p> for text, <table> for tables
6. Format tables properly with complete HTML structure:
   <table>
     <thead>
       <tr>
         <th>Column Header</th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td>Actual Value from JSON</td>
       </tr>
     </tbody>
   </table>
7. Extract data from JSON arrays: For each item, create table rows with actual field values
8. If JSON is empty, create sections stating "No data available" rather than inventing data
9. Return ONLY the HTML body content - NO <html>, <head>, <body> opening tags
10. MUST end with </div></body></html> to close the document
11. Do NOT include markdown code blocks
12. DO NOT INVENT DATA - use only what's in the JSON

ANTI-HALLUCINATION: Recommendations should be based on actual data patterns found in the JSON, not generic suggestions.

Return ONLY the HTML content that continues the document body, ending with </div></body></html>.
"""
        resp_final = self._call_llm_with_lower_tokens(prompt_final, max_tokens=2000)
        if not resp_final.get("success"):
            raise RuntimeError(resp_final.get("error", f"LLM error in part {num_chunks}"))
        part_final = resp_final.get("response", "").strip()
        
        # Clean up markdown code blocks if present
        if part_final.startswith("```html"):
            part_final = part_final[7:]
        if part_final.startswith("```"):
            part_final = part_final[3:]
        if part_final.endswith("```"):
            part_final = part_final[:-3]
        part_final = part_final.strip()
        
        # Remove any HTML document structure tags (should only be body content)
        part_final = part_final.replace("<html>", "").replace("<head>", "").replace("</head>", "").replace("<body>", "").strip()
        
        # Ensure proper closing with container div and body/html tags
        if not part_final.endswith("</div></body></html>"):
            if not part_final.endswith("</div>"):
                part_final = part_final + "</div>"
            if not part_final.endswith("</body></html>"):
                part_final = part_final + "</body></html>"
        html_parts.append(part_final)
        print(f"   ✅ Part {num_chunks} generated: {len(part_final)} chars")
        
        # Combine all parts
        full_html = "\n".join(html_parts)
        
        # Post-process to clean up formatting issues
        full_html = self._cleanup_html(full_html, title)
        
        print(f"   ✅ Complete document: {len(full_html)} chars")
        return full_html
    
    def _cleanup_html(self, html: str, title: str) -> str:
        """Post-process HTML to fix formatting issues, remove duplicates, and ensure proper structure"""
        import re
        from datetime import datetime
        
        # Remove any markdown code blocks that might have slipped through
        html = re.sub(r'```html\s*', '', html)
        html = re.sub(r'```\s*', '', html)
        
        # Remove duplicate document structures (multiple <html> tags)
        # Keep only the first complete HTML structure
        html_parts = html.split('<html>')
        if len(html_parts) > 2:
            # Multiple HTML documents detected, keep only the first one
            first_html = '<html>' + html_parts[1]
            # Find the last </html> tag in the first document
            last_closing = first_html.rfind('</html>')
            if last_closing > 0:
                html = first_html[:last_closing + 7]
        
        # Remove duplicate titles/headers
        # Count occurrences of the title in h1 tags
        title_pattern = re.compile(rf'<h1[^>]*>{re.escape(title)}</h1>', re.IGNORECASE)
        matches = list(title_pattern.finditer(html))
        if len(matches) > 1:
            # Keep only the first h1, remove others
            for match in matches[1:]:
                html = html[:match.start()] + html[match.end():]
        
        # Replace placeholder dates with actual dates
        current_date = datetime.now().strftime("%Y-%m-%d")
        html = re.sub(r'\[Current Date\]', current_date, html, flags=re.IGNORECASE)
        html = re.sub(r'\[Your Name\]', 'Document Agent', html, flags=re.IGNORECASE)
        html = re.sub(r'Generated on \[Current Date\]', f'Generated on {current_date}', html, flags=re.IGNORECASE)
        
        # Remove PHP code (common mistake by LLM)
        html = re.sub(r'<\?php.*?\?>', '', html, flags=re.DOTALL)
        html = re.sub(r'<\?=.*?\?>', '', html, flags=re.DOTALL)
        html = re.sub(r'<\?.*?\?>', '', html, flags=re.DOTALL)
        
        # Fix empty date fields - replace PHP date() calls with actual date
        html = re.sub(r'<\?=\s*date\([^)]+\)\s*\?>', current_date, html, flags=re.IGNORECASE)
        html = re.sub(r'Generated on\s*$', f'Generated on {current_date}', html, flags=re.MULTILINE)
        html = re.sub(r'Generated on\s*<p>', f'Generated on {current_date}</p>', html, flags=re.IGNORECASE)
        
        # Fix "Generated on" with no date - add actual date
        html = re.sub(r'<p>Generated on\s*</p>', f'<p>Generated on {current_date}</p>', html, flags=re.IGNORECASE)
        html = re.sub(r'Generated on\s*</p>', f'Generated on {current_date}</p>', html, flags=re.IGNORECASE)
        
        # Ensure proper table formatting - fix any malformed tables
        # Add proper table structure if missing
        html = re.sub(r'<table([^>]*)>', r'<table\1><tbody>', html)
        html = re.sub(r'</table>', r'</tbody></table>', html)
        
        # Remove any standalone table rows outside of tables
        # (This is a safety measure)
        
        # Ensure container div is properly closed
        if '<div class="container">' in html and '</div>' not in html.split('</body>')[0]:
            # Add closing div before </body>
            html = html.replace('</body>', '</div></body>')
        
        # Ensure proper closing tags
        if not html.rstrip().endswith('</html>'):
            if '</body>' not in html:
                html += '</body>'
            if '</html>' not in html:
                html += '</html>'
        
        return html
    
    def _build_prompt(self, title: str, user_instructions: str, data: Dict[str, Any]) -> str:
        """Legacy method - now uses chunked generation"""
        # This method is kept for compatibility but chunked generation is used directly
        return self._generate_document_chunked(title, user_instructions, data)

    def create_document(self, project_id: str, title: str, user_instructions: str) -> Dict[str, Any]:
        try:
            print(f"📝 Creating intelligent document '{title}' for project {project_id[:8]}...")
            intent_json = self._reason_intent(user_instructions)
            try:
                intent = json.loads(intent_json)
                perf_fields = intent.get("performance_fields", [])
                fin_fields = intent.get("finance_fields", [])
            except Exception as e:
                print(f"   ⚠️  Error parsing intent JSON: {e}")
                perf_fields, fin_fields = ([], [])
                intent = {"performance_fields": [], "finance_fields": []}

            print(f"   📊 Intent: {len(perf_fields)} performance fields, {len(fin_fields)} finance fields")
            data = self._fetch_data(project_id, perf_fields, fin_fields)
            print(f"   ✅ Fetched data: {len(data)} sections")
            
            # Use chunked generation to avoid context length issues
            html = self._generate_document_chunked(title, user_instructions, data)
            print(f"   ✅ Generated HTML document ({len(html)} chars)")
            
            doc_id = self.chroma_manager.store_document(
                doc_type="custom_doc",
                project_id=project_id,
                title=title,
                html_content=html,
                source_snapshot={"intent": intent, "data": data},
                collection=self.chroma_manager.collections["doc_gen_documents"]
            )
            
            if not doc_id:
                return {"success": False, "error": "Failed to store document"}
            
            print(f"   ✅ Stored document with ID: {doc_id}")
            return {"success": True, "doc_id": doc_id, "html": html, "intent": intent}
        except Exception as e:
            print(f"❌ Error creating intelligent document: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
