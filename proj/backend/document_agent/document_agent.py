"""
Document Agent: generates PSDP Summary and Financial Brief using existing Performance and Finance data.
"""

from __future__ import annotations
from typing import Dict, Any, List
import json
import requests
import time
from backend.document_agent.chroma_manager import DocumentChromaManager


class DocumentAgent:
    def __init__(self, llm_manager, performance_agent, financial_agent, chroma_manager=None, orchestrator=None):
        self.llm_manager = llm_manager
        self.performance_agent = performance_agent
        self.financial_agent = financial_agent
        self.chroma_manager = chroma_manager or DocumentChromaManager()
        self.orchestrator = orchestrator  # For A2A protocol in microservice mode

    def _get_performance_snapshot(self, project_id: str) -> Dict[str, Any]:
        """Get performance data snapshot, using A2A protocol if orchestrator available"""
        snapshot = {}
        
        # Use orchestrator (A2A) if available (microservice mode), otherwise direct calls (monolith mode)
        if self.orchestrator:
            try:
                # Fetch milestones via A2A
                milestones = self.orchestrator.route_data_request(
                    query="Get all project milestones with their details and status",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["milestones"] = milestones or []
                
                # Fetch tasks via A2A
                tasks = self.orchestrator.route_data_request(
                    query="Get all project tasks with their details",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["tasks"] = tasks or []
                
                # Fetch bottlenecks via A2A
                bottlenecks = self.orchestrator.route_data_request(
                    query="Get all project bottlenecks and potential issues",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["bottlenecks"] = bottlenecks or []
                
                # Fetch requirements via A2A
                requirements = self.orchestrator.route_data_request(
                    query="Get all project requirements with categories and priorities",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["requirements"] = requirements or []
                
                # Fetch actors via A2A
                actors = self.orchestrator.route_data_request(
                    query="Get all project actors/stakeholders with type and role",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["actors"] = actors or []
                
                # Fetch suggestions via A2A
                suggestions_data = self.orchestrator.route_data_request(
                    query="Get all performance suggestions and recommendations",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["suggestions"] = suggestions_data if isinstance(suggestions_data, dict) else {}
                
            except Exception as e:
                print(f"⚠️  A2A data fetch failed, falling back to direct calls: {e}")
                # Fallback to direct calls
                snapshot = self._get_performance_snapshot_direct(project_id)
        else:
            # Monolith mode: direct calls
            snapshot = self._get_performance_snapshot_direct(project_id)
        
        return snapshot
    
    def _get_performance_snapshot_direct(self, project_id: str) -> Dict[str, Any]:
        """Direct calls to performance agent (monolith mode fallback)"""
        return {
            "milestones": self.performance_agent.milestone_agent.get_project_milestones(project_id),
            "tasks": self.performance_agent.task_agent.get_project_tasks(project_id),
            "bottlenecks": self.performance_agent.bottleneck_agent.get_project_bottlenecks(project_id),
            "requirements": self.performance_agent.chroma_manager.get_performance_data('requirements', project_id),
            "actors": self.performance_agent.chroma_manager.get_performance_data('actors', project_id),
            "suggestions": self.performance_agent._get_current_performance_data(project_id).get("suggestions", {})
        }

    def _get_financial_snapshot(self, project_id: str) -> Dict[str, Any]:
        """Get financial data snapshot, using A2A protocol if orchestrator available"""
        snapshot = {}
        
        # Use orchestrator (A2A) if available (microservice mode), otherwise direct calls (monolith mode)
        if self.orchestrator:
            try:
                # Fetch transactions via A2A
                txns = self.orchestrator.route_data_request(
                    query="Get all financial transactions for the project",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["transactions"] = txns or []
                
                # Fetch expense analysis via A2A
                expense = self.orchestrator.route_data_request(
                    query="Get expense analysis with task mappings",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["expense_analysis"] = expense if isinstance(expense, dict) else {}
                
                # Fetch revenue analysis via A2A
                revenue = self.orchestrator.route_data_request(
                    query="Get revenue analysis with milestone linkages",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["revenue_analysis"] = revenue if isinstance(revenue, dict) else {}
                
                # Fetch anomalies via A2A
                anomalies = self.orchestrator.route_data_request(
                    query="Get financial anomalies and irregularities",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["anomalies"] = anomalies if isinstance(anomalies, dict) else {}
                
                # Fetch actor-transaction mappings via A2A
                actor_map = self.orchestrator.route_data_request(
                    query="Get actor to transaction mappings",
                    requesting_agent="document_agent",
                    project_id=project_id
                )
                snapshot["actor_transaction_mappings"] = actor_map if isinstance(actor_map, list) else []
                
            except Exception as e:
                print(f"⚠️  A2A data fetch failed, falling back to direct calls: {e}")
                # Fallback to direct calls
                snapshot = self._get_financial_snapshot_direct(project_id)
        else:
            # Monolith mode: direct calls
            snapshot = self._get_financial_snapshot_direct(project_id)
        
        return snapshot
    
    def _get_financial_snapshot_direct(self, project_id: str) -> Dict[str, Any]:
        """Direct calls to financial agent (monolith mode fallback)"""
        txns = self.financial_agent.chroma_manager.get_financial_data('transactions', project_id)
        expense = self.financial_agent.expense_agent.get_expense_analysis(project_id)
        revenue = self.financial_agent.revenue_agent.analyze_revenue(project_id, txns)
        anomalies = self.financial_agent.anomaly_agent.get_anomalies(project_id, {})
        actor_map = self.financial_agent.get_actor_transaction_mappings(project_id)
        return {
            "transactions": txns,
            "expense_analysis": expense,
            "revenue_analysis": revenue,
            "anomalies": anomalies,
            "actor_transaction_mappings": actor_map
        }

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 characters per token"""
        return len(text) // 4
    
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
    
    def _split_data_into_chunks(self, data_snapshot: Dict[str, Any], max_tokens_per_chunk: int = 1500) -> List[Dict[str, Any]]:
        """Split data snapshot into chunks based on token count, not just number of keys"""
        # First, truncate large arrays aggressively to reduce size (keep only 10 items)
        truncated_data = self._truncate_large_array(data_snapshot.copy(), max_items=10)
        
        chunks = []
        current_chunk = {}
        current_tokens = 0
        
        for key, value in truncated_data.items():
            # Serialize this key-value pair to estimate tokens
            try:
                item_json = json.dumps({key: value}, indent=2, default=str)
                item_tokens = self._estimate_tokens(item_json)
            except:
                item_tokens = 1000  # Conservative estimate
            
            # If adding this item would exceed limit, start new chunk
            if current_tokens + item_tokens > max_tokens_per_chunk and current_chunk:
                chunks.append(current_chunk)
                current_chunk = {}
                current_tokens = 0
            
            # Add item to current chunk
            current_chunk[key] = value
            current_tokens += item_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        # Ensure at least 3 chunks for document structure
        if len(chunks) < 3:
            # Split the largest chunk further
            if chunks:
                largest_idx = max(range(len(chunks)), key=lambda i: len(str(chunks[i])))
                largest = chunks[largest_idx]
                keys = list(largest.keys())
                mid = len(keys) // 2
                chunks[largest_idx] = {k: largest[k] for k in keys[:mid]}
                chunks.insert(largest_idx + 1, {k: largest[k] for k in keys[mid:]})
        
        print(f"   📦 Split data into {len(chunks)} chunks (max {max_tokens_per_chunk} tokens each)")
        return chunks
    
    def _call_llm_with_lower_tokens(self, prompt: str, max_tokens: int = 2000) -> Dict[str, Any]:
        """Call LLM with custom max_tokens for document generation to avoid context limits"""
        # For Hugging Face, we need to call the API directly with lower max_tokens
        # This is a workaround since simple_chat doesn't accept max_tokens parameter
        if hasattr(self.llm_manager, 'current_llm') and self.llm_manager.current_llm == 'huggingface':
            try:
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
    
    def _call_llm_chunked(self, title: str, instructions: str, data_snapshot: Dict[str, Any], 
                          section_names: List[str]) -> str:
        """Generate document in multiple LLM calls: structure+beginning, middle sections, end"""
        # Split data into chunks based on token count (max 1500 tokens per chunk to leave room for prompt + response)
        # With 1500 data tokens + ~1000 prompt tokens + 2000 max_tokens = ~4500 total (well under 8192 limit)
        data_chunks = self._split_data_into_chunks(data_snapshot, max_tokens_per_chunk=1500)
        num_chunks = len(data_chunks)
        
        print(f"   📊 Generating document in {num_chunks} LLM calls...")
        
        # Serialize chunks
        chunk_jsons = []
        for i, chunk in enumerate(data_chunks):
            try:
                chunk_json = json.dumps(chunk, indent=2, default=str)
                chunk_tokens = self._estimate_tokens(chunk_json)
                print(f"   📦 Chunk {i+1}: ~{chunk_tokens} tokens")
                chunk_jsons.append(chunk_json)
            except Exception as e:
                print(f"⚠️  Error serializing chunk {i+1}: {e}")
                chunk_jsons.append(str(chunk))
        
        html_parts = []
        
        # Call 1: Generate document structure and beginning
        print(f"   📝 LLM Call 1/{num_chunks}: Generating document structure and beginning...")
        # Enhanced prompt with specific HTML formatting requirements
        prompt1 = f"""Create professional HTML document "{title}".

PART 1/{num_chunks}: Generate HEADER, OVERVIEW, BEGINNING SECTIONS.

Data (JSON):
{chunk_jsons[0]}

Instructions: {instructions}
Sections to include: {', '.join(section_names[:3])}

REQUIREMENTS:
1. Start with complete HTML structure: <html><head><title>{title}</title><style>...</style></head><body><div class="container">
2. Add professional CSS styling in <style> tag (fonts, colors, spacing, table styles)
3. Create header with <h1> for title and <p> for generation date (use actual current date like "2025-12-10", NOT PHP code like <?= date(...) ?>)
4. Generate Overview section with actual data from JSON (use real numbers, not placeholders)
5. Generate first 1-2 sections with proper HTML formatting (tables use <table>, <tr>, <td> tags)
6. Use actual data from the JSON provided - NO placeholders, NO PHP code, NO template syntax
7. For tables: Populate with REAL data from JSON. Each row should have actual values from the data array
8. Format tables properly with borders, padding, and alternating row colors
9. Do NOT include markdown code blocks (```html) - return ONLY raw HTML
10. Do NOT use PHP, JavaScript, or any server-side code - ONLY static HTML with actual data
11. Do NOT close </div></body></html> yet - this will be done in final part

CRITICAL: Extract actual values from the JSON data and write them directly into HTML. For example, if JSON has milestones array, write each milestone as a <tr><td>row with actual content, category, priority values.

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
            # Enhanced prompt for middle sections
            prompt_mid = f"""Continue professional HTML document "{title}".

PART {i+1}/{num_chunks}: Generate MIDDLE SECTIONS.

Data (JSON):
{chunk_jsons[i]}

Instructions: {instructions}
Sections to generate: {', '.join(section_names[2:5] if len(section_names) > 2 else section_names)}

REQUIREMENTS:
1. Generate 2-3 middle sections based on instructions and data
2. Use proper HTML structure: <h2> for section titles, <p> for paragraphs, <table> for tables
3. Use actual data from JSON - NO placeholders, NO PHP code, NO template syntax
4. For tables: Populate with REAL data from JSON. Each row should have actual values from the data array
5. Format tables with proper HTML table tags (<table>, <thead>, <tbody>, <tr>, <th>, <td>)
6. Apply consistent styling (use inline styles or assume CSS from part 1)
7. Return ONLY the HTML body content - NO <html>, <head>, <body> tags
8. Do NOT include markdown code blocks
9. Do NOT use PHP, JavaScript, or any server-side code - ONLY static HTML with actual data
10. Do NOT close </div></body></html> yet

CRITICAL: Extract actual values from the JSON data and write them directly into HTML table rows. For example, if JSON has tasks array, write each task as a <tr><td>row with actual task content and priority values.

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
        # Enhanced prompt for final sections
        prompt_final = f"""Complete professional HTML document "{title}".

PART {num_chunks}/{num_chunks}: Generate FINAL SECTIONS and CONCLUSION.

Data (JSON):
{chunk_jsons[-1]}

Instructions: {instructions}
Remaining sections: {', '.join(section_names[-3:] if len(section_names) > 3 else section_names)}

REQUIREMENTS:
1. Generate remaining sections based on instructions and data
2. Add a "Recommendations" or "Conclusion" section if specified
3. Add a professional footer with actual generation date (not placeholder)
4. Use actual data from JSON - NO placeholders like "[Current Date]" or example data
5. Use proper HTML formatting: <h2> for section titles, <p> for text, <table> for tables
6. Format tables properly with HTML table structure
7. Return ONLY the HTML body content - NO <html>, <head>, <body> opening tags
8. MUST end with </body></html> to close the document
9. Do NOT include markdown code blocks

Return ONLY the HTML content that continues the document body, ending with </body></html>.
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
        
        # Ensure proper table formatting - fix any malformed tables
        # Add proper table structure if missing
        html = re.sub(r'<table([^>]*)>', r'<table\1><tbody>', html)
        html = re.sub(r'</table>', r'</tbody></table>', html)
        
        # Remove empty table rows that might have been generated with PHP loops
        # Look for patterns like <tr><td></td></tr> or empty table cells
        html = re.sub(r'<tr>\s*<td[^>]*>\s*</td>\s*</tr>', '', html, flags=re.IGNORECASE)
        
        # Fix "Generated on" with no date - add actual date
        html = re.sub(r'<p>Generated on\s*</p>', f'<p>Generated on {current_date}</p>', html, flags=re.IGNORECASE)
        html = re.sub(r'Generated on\s*</p>', f'Generated on {current_date}</p>', html, flags=re.IGNORECASE)
        
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
    
    def _call_llm(self, title: str, instructions: str, data_snapshot: Dict[str, Any]) -> str:
        """Legacy method - now uses chunked generation"""
        # This method is kept for compatibility but will use chunked generation
        section_names = ["Overview", "Key Sections", "Details", "Recommendations"]
        return self._call_llm_chunked(title, instructions, data_snapshot, section_names)

    def generate_psdp_summary(self, project_id: str) -> Dict[str, Any]:
        try:
            print(f"📄 Generating PSDP Summary for project {project_id[:8]}...")
            perf = self._get_performance_snapshot(project_id)
            print(f"   ✅ Retrieved performance snapshot: {len(perf)} sections")
            
            instructions = """Produce a PSDP-style project summary with sections:
- Project Overview (with actual milestone/task counts from data)
- Key Milestones (table with actual milestone data: category, content, priority)
- Tasks/Action Items (table with actual task data: task content, priority)
- Bottlenecks/Risks (table with actual bottleneck data: content, priority)
- Requirements (table with actual requirement data: content, category, priority)
- Actors/Stakeholders (table with actual actor data: name, role, type)
- Recommendations

CRITICAL: Use ACTUAL data from the JSON provided. Populate tables with real values from the data arrays. Do NOT use PHP, template code, or placeholders. Write static HTML with actual data values.
Keep it concise and formal."""
            
            section_names = ["Project Overview", "Key Milestones", "Tasks/Action Items", 
                           "Bottlenecks/Risks", "Requirements", "Actors/Stakeholders", "Recommendations"]
            
            html = self._call_llm_chunked("PSDP Summary", instructions, perf, section_names)
            print(f"   ✅ Generated HTML document ({len(html)} chars)")
            
            doc_id = self.chroma_manager.store_document(
                doc_type="psdp_summary",
                project_id=project_id,
                title="PSDP Summary",
                html_content=html,
                source_snapshot=perf,
                collection=self.chroma_manager.collections["doc_agent_documents"]
            )
            
            if not doc_id:
                return {"success": False, "error": "Failed to store document"}
            
            print(f"   ✅ Stored document with ID: {doc_id}")
            return {"success": True, "doc_id": doc_id, "html": html}
        except Exception as e:
            print(f"❌ Error generating PSDP summary: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def generate_financial_brief(self, project_id: str) -> Dict[str, Any]:
        try:
            print(f"💰 Generating Financial Brief for project {project_id[:8]}...")
            fin = self._get_financial_snapshot(project_id)
            print(f"   ✅ Retrieved financial snapshot: {len(fin)} sections")
            
            instructions = """Produce a Financial Brief with sections:
- Financial Overview (expenses, revenue)
- Transactions summary
- Expense/Revenue analysis
- Actor ↔ Transaction mappings
- Anomalies (if any)
- Recommendations
Keep it concise and professional."""
            
            section_names = ["Financial Overview", "Transactions Summary", "Expense/Revenue Analysis",
                           "Actor ↔ Transaction Mappings", "Anomalies", "Recommendations"]
            
            html = self._call_llm_chunked("Financial Brief", instructions, fin, section_names)
            print(f"   ✅ Generated HTML document ({len(html)} chars)")
            
            doc_id = self.chroma_manager.store_document(
                doc_type="financial_brief",
                project_id=project_id,
                title="Financial Brief",
                html_content=html,
                source_snapshot=fin,
                collection=self.chroma_manager.collections["doc_agent_documents"]
            )
            
            if not doc_id:
                return {"success": False, "error": "Failed to store document"}
            
            print(f"   ✅ Stored document with ID: {doc_id}")
            return {"success": True, "doc_id": doc_id, "html": html}
        except Exception as e:
            print(f"❌ Error generating financial brief: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
