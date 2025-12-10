"""
Financial Details Agent - Extracts financial details from documents
"""

import json
import re
from typing import Dict, List, Any
from datetime import datetime


class FinancialDetailsAgent:
    """Worker agent for extracting financial details"""
    
    def __init__(self, chroma_manager):
        """
        Initialize Financial Details Agent
        
        Args:
            chroma_manager: FinancialChromaManager instance
        """
        self.chroma_manager = chroma_manager
    
    def extract_financial_details(self, project_id: str, document_id: str,
                                  llm_manager, embeddings_manager) -> Dict[str, Any]:
        """
        Extract financial details from a document
        
        Args:
            project_id: Project identifier
            document_id: Document identifier
            llm_manager: LLM manager for extraction
            embeddings_manager: Embeddings manager for context
            
        Returns:
            Dict with extraction results
        """
        try:
            print(f"💰 Extracting financial details from document {document_id[:8]}...")
            
            # Get document embeddings
            document_embeddings = embeddings_manager.get_document_embeddings(project_id, document_id)
            
            if not document_embeddings or len(document_embeddings) == 0:
                return {'success': False, 'error': 'No document embeddings found', 'details': []}
            
            # Extract text from embeddings to create context
            context = "\n".join([
                emb.get('content', '') for emb in document_embeddings 
                if emb.get('content')
            ])
            
            if not context:
                return {'success': False, 'error': 'No text content found in embeddings', 'details': []}
            
            print(f"   - Using {len(document_embeddings)} embedding chunks ({len(context)} characters)")
            
            # Create extraction prompt
            prompt = self._create_extraction_prompt(context)
            
            # Get LLM response
            llm_response = llm_manager.simple_chat(prompt)
            
            if not llm_response.get('success'):
                print(f"   ❌ LLM error: {llm_response.get('error', 'Unknown error')}")
                return {
                    'success': False, 
                    'error': f"LLM error: {llm_response.get('error', 'Unknown error')}", 
                    'details': []
                }
            
            # Parse response - extract the actual text from the response dict
            response_text = llm_response.get('response', '')
            print(f"   ✅ LLM response received: {len(response_text)} characters")
            print(f"   📄 Response preview (first 500 chars): {response_text[:500]}...")
            
            details = self._parse_financial_details(response_text, llm_manager, context)
            
            # Store in ChromaDB
            if details:
                self._store_details(project_id, document_id, details)
                print(f"   ✅ Stored {len(details)} financial detail items")
            else:
                print(f"   ⚠️  No financial details extracted! LLM returned empty or invalid data.")
            
            return {
                'success': True,
                'details': details,
                'count': len(details)
            }
            
        except Exception as e:
            print(f"Error extracting financial details: {e}")
            return {'success': False, 'error': str(e), 'details': []}
    
    def _create_extraction_prompt(self, context: str) -> str:
        """Create LLM prompt for financial details extraction"""
        return f"""You are a financial analyst AI. Extract ALL financial planning information from the following project document.

CONTEXT:
{context}

TASK: Extract financial PLANNING and BUDGET details (NOT operational transactions):

1. **Budget Allocations** - Initial project funding, capital investment, grants
   - Total project cost/budget
   - Government funding and grants
   - Private investment and contributions
   - Capital expenditure budgets
   - Funding sources and amounts

2. **Cost Estimates** - Planned costs and expenditure
   - Estimated costs for project phases
   - Labor cost estimates
   - Material cost estimates
   - Contingency funds

3. **Financial Constraints** - Limits and restrictions
   - Budget limits per category
   - Spending restrictions
   - Approval requirements

4. **Payment Schedules** - Planned payment milestones
   - Milestone-based payments (NOT actual paid transactions)
   - Due dates for payments
   - Payment terms

5. **Financial Milestones** - Financial targets and goals
   - Revenue targets
   - Cost thresholds
   - Financial checkpoints

IMPORTANT: Extract PLANNING/BUDGET information, not operational transactions.
- ✅ "Government of Punjab provided PKR 720M" → budget_allocation
- ✅ "Total project cost PKR 1.2 billion" → budget_allocation
- ✅ "Labor costs estimated at PKR 250M" → cost_estimate
- ❌ "Ticket sales generated PKR 2.5M" → Skip (operational, not budget)

OUTPUT FORMAT (JSON):
{{
  "budget_allocations": [
    {{"category": "string", "amount": float, "currency": "PKR", "source": "string"}}
  ],
  "cost_estimates": [
    {{"item": "string", "estimated_cost": float, "currency": "PKR", "contingency": float}}
  ],
  "constraints": [
    {{"type": "string", "description": "string", "limit": float}}
  ],
  "payment_schedules": [
    {{"milestone": "string", "amount": float, "due_date": "string"}}
  ],
  "financial_milestones": [
    {{"milestone": "string", "target": float, "deadline": "string"}}
  ]
}}

EXAMPLES:
1. "Total project budget is Rs. 50 lakh from government funds"
   → budget_allocations: [{{"category": "total", "amount": 5000000, "currency": "PKR", "source": "government"}}]

2. "Construction phase estimated at Rs. 20 lakh with 10% contingency"
   → cost_estimates: [{{"item": "construction", "estimated_cost": 2000000, "currency": "PKR", "contingency": 0.10}}]

3. "Payment 1: Rs. 15 lakh upon project commencement"
   → payment_schedules: [{{"milestone": "commencement", "amount": 1500000, "due_date": "start"}}]

CONSTRAINTS:
- Extract ALL monetary amounts
- Identify currencies (default PKR if not specified)
- Capture both confirmed and estimated figures
- Return ONLY valid JSON object, no markdown, no explanations, no additional text
- Start your response with {{ and end with }}
- Do NOT include any text before or after the JSON object
- If no financial details found, return empty arrays: {{"budget_allocations": [], "cost_estimates": [], "constraints": [], "payment_schedules": [], "financial_milestones": []}}

CRITICAL: Your response must be ONLY the JSON object, nothing else. No explanations, no markdown code blocks, no additional text.

JSON OUTPUT:"""
    
    def _parse_financial_details(self, response: str, llm_manager=None, context: str = None) -> List[Dict]:
        """Parse financial details from LLM response with robust JSON extraction"""
        try:
            # Clean and parse JSON
            response_text = response.strip()
            original_length = len(response_text)
            
            # Remove markdown code blocks (handle various formats)
            if response_text.startswith('```json'):
                response_text = response_text[7:].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:].strip()
            if response_text.endswith('```'):
                response_text = response_text[:-3].strip()
            
            # Try to find the first complete JSON object in the response
            # This handles cases where LLM adds explanation text before/after JSON
            import re
            
            # First, try to find a JSON object that starts with { and ends with }
            # Use non-greedy match but ensure it's a complete object
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text)
            if not json_match:
                # Fallback: try to find any JSON object (greedy)
                json_match = re.search(r'\{[\s\S]*?\}(?=\s*(?:\n|$|Explanation|In the above|For |The |This |Note|Note that))', response_text)
            if not json_match:
                # Last resort: find the largest JSON object
                json_match = re.search(r'\{[\s\S]*\}', response_text)
            
            if json_match:
                response_text = json_match.group(0)
                print(f"   🔍 Extracted JSON object (original: {original_length} chars, extracted: {len(response_text)} chars)")
            else:
                print(f"   ⚠️  No JSON object found in response, trying full text")
            
            print(f"   📝 First 300 chars: {response_text[:300]}")
            
            # Try to parse JSON
            try:
                data = json.loads(response_text)
                print(f"   ✅ JSON parsed successfully")
            except json.JSONDecodeError as json_err:
                # If parsing fails, try to fix common issues
                print(f"   ⚠️  Initial JSON parse failed: {json_err}")
                
                # Try to fix trailing commas
                response_text = re.sub(r',\s*}', '}', response_text)
                response_text = re.sub(r',\s*]', ']', response_text)
                
                # Try to fix unclosed strings
                response_text = re.sub(r'("(?:[^"\\]|\\.)*)"?$', r'\1"', response_text, flags=re.MULTILINE)
                
                try:
                    data = json.loads(response_text)
                    print(f"   ✅ JSON parsed after fixing common issues")
                except json.JSONDecodeError:
                    # If still fails, try to extract just the structure
                    print(f"   ⚠️  JSON parsing failed after fixes, attempting structure extraction")
                    raise json_err
            
            # Process the parsed data
            return self._process_parsed_data(data)
            
        except json.JSONDecodeError as e:
            # Try retry with simpler prompt if LLM manager and context available
            if llm_manager and context:
                print(f"   ⚠️  JSON parsing failed: {e}")
                print(f"   🔄 Retrying with simpler, more direct prompt...")
                return self._retry_with_simple_prompt(llm_manager, context)
            else:
                print(f"   ⚠️  JSON parsing failed: {e}")
                print(f"   📄 Response (first 500 chars): {response[:500]}")
                print(f"   🔄 Using fallback regex extraction")
                return self._fallback_extraction(response)
        except Exception as e:
            print(f"   ❌ Error parsing financial details: {e}")
            import traceback
            traceback.print_exc()
            # Try retry if possible
            if llm_manager and context:
                print(f"   🔄 Retrying with simpler prompt...")
                return self._retry_with_simple_prompt(llm_manager, context)
            return self._fallback_extraction(response)
    
    def _process_parsed_data(self, data: Dict) -> List[Dict]:
        """Process parsed JSON data into detail items"""
        # Flatten into list of detail items
        details = []
        
        if 'budget_allocations' in data:
                for item in data['budget_allocations']:
                    category = item.get('category', 'general')
                    source = item.get('source', 'unknown')
                    amount = item.get('amount', 0)
                    
                    # Ensure no None values
                    if category is None or not str(category).strip():
                        category = 'general'
                    if source is None:
                        source = 'unknown'
                    if amount is None:
                        amount = 0
                    
                    details.append({
                        'type': 'budget_allocation',
                        'category': str(category),
                        'amount': float(amount),
                        'currency': str(item.get('currency', 'PKR')),
                        'description': f"Budget allocation for {category}: {source}"
                    })
        
        if 'cost_estimates' in data:
                for item in data['cost_estimates']:
                    item_name = item.get('item', 'general')
                    amount = item.get('estimated_cost', 0)
                    
                    # Ensure no None values
                    if item_name is None or not str(item_name).strip():
                        item_name = 'general'
                    if amount is None:
                        amount = 0
                    
                    details.append({
                        'type': 'cost_estimate',
                        'category': str(item_name),
                        'amount': float(amount),
                        'currency': str(item.get('currency', 'PKR')),
                        'description': f"Estimated cost for {item_name}"
                    })
        
        if 'constraints' in data:
                for item in data['constraints']:
                    constraint_type = item.get('type', 'general')
                    limit = item.get('limit', 0)
                    description = item.get('description', 'Financial constraint')
                    
                    # Ensure no None values
                    if constraint_type is None or not str(constraint_type).strip():
                        constraint_type = 'general'
                    if limit is None:
                        limit = 0
                    if description is None or not str(description).strip():
                        description = 'Financial constraint'
                    
                    details.append({
                        'type': 'financial_constraint',
                        'category': str(constraint_type),
                        'amount': float(limit),
                        'currency': 'PKR',
                        'description': str(description)
                    })
        
        if 'payment_schedules' in data:
                for item in data['payment_schedules']:
                    milestone = item.get('milestone', 'general')
                    amount = item.get('amount', 0)
                    
                    # Ensure no None values
                    if milestone is None or not str(milestone).strip():
                        milestone = 'general'
                    if amount is None:
                        amount = 0
                    
                    details.append({
                        'type': 'payment_schedule',
                        'category': str(milestone),
                        'amount': float(amount),
                        'currency': 'PKR',
                        'description': f"Payment for {milestone}"
                    })
        
        if 'financial_milestones' in data:
                for item in data['financial_milestones']:
                    milestone = item.get('milestone', 'general')
                    target = item.get('target', 0)
                    
                    # Ensure no None values
                    if milestone is None or not str(milestone).strip():
                        milestone = 'general'
                    if target is None:
                        target = 0
                    
                    details.append({
                        'type': 'financial_milestone',
                        'category': str(milestone),
                        'amount': float(target),
                        'currency': 'PKR',
                        'description': f"Financial milestone: {milestone}"
                    })
            
        print(f"   📊 Extracted: {len([d for d in details if d.get('type') == 'budget_allocation'])} budgets, " +
              f"{len([d for d in details if d.get('type') == 'cost_estimate'])} costs, " +
              f"{len([d for d in details if d.get('type') == 'financial_constraint'])} constraints, " +
              f"{len([d for d in details if d.get('type') == 'payment_schedule'])} payments, " +
              f"{len([d for d in details if d.get('type') == 'financial_milestone'])} milestones")
        
        return details
            
    def _retry_with_simple_prompt(self, llm_manager, context: str) -> List[Dict]:
        """Retry extraction with a simpler, more direct prompt"""
        try:
            simple_prompt = f"""Extract financial budget and planning information from this document. Return ONLY a JSON object, no other text.

Document:
{context[:3000]}

Return JSON in this exact format:
{{
  "budget_allocations": [{{"category": "string", "amount": number, "currency": "PKR", "source": "string"}}],
  "cost_estimates": [{{"item": "string", "estimated_cost": number, "currency": "PKR"}}],
  "constraints": [{{"type": "string", "description": "string", "limit": number}}],
  "payment_schedules": [{{"milestone": "string", "amount": number}}],
  "financial_milestones": [{{"milestone": "string", "target": number}}]
}}

Start with {{ and end with }}. No markdown, no explanations, just JSON:"""
            
            llm_response = llm_manager.simple_chat(simple_prompt)
            if llm_response.get('success'):
                response_text = llm_response.get('response', '').strip()
                print(f"   🔄 Retry response received: {len(response_text)} chars")
                # Parse directly without recursion
                try:
                    # Clean response
                    if response_text.startswith('```json'):
                        response_text = response_text[7:].strip()
                    elif response_text.startswith('```'):
                        response_text = response_text[3:].strip()
                    if response_text.endswith('```'):
                        response_text = response_text[:-3].strip()
                    
                    # Extract JSON object
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', response_text)
                    if json_match:
                        response_text = json_match.group(0)
                    
                    data = json.loads(response_text)
                    print(f"   ✅ Retry JSON parsed successfully")
                    # Process data using same logic as main parser
                    return self._process_parsed_data(data)
                except Exception as parse_err:
                    print(f"   ⚠️  Retry parsing also failed: {parse_err}")
                    return self._fallback_extraction(response_text)
            else:
                print(f"   ⚠️  Retry LLM call failed: {llm_response.get('error')}")
                return []
        except Exception as e:
            print(f"   ❌ Error in retry: {e}")
            return []
    
    def _fallback_extraction(self, response: str) -> List[Dict]:
        """Fallback extraction using regex with intelligent categorization"""
        details = []
        seen_amounts = set()  # Deduplicate by amount
        print(f"   🔄 Using fallback regex extraction for financial details")
        
        def extract_amount_and_unit(match):
            """Helper to extract amount and unit from regex match"""
            if isinstance(match, tuple):
                amount_str = match[0].replace(',', '') if len(match) > 0 else ''
                unit = match[1] if len(match) > 1 else ''
            else:
                amount_str = str(match).replace(',', '')
                unit = ''
            
            multiplier = 1
            if unit:
                unit_lower = unit.lower()
                if unit_lower in ['lakh', 'l']:
                    multiplier = 100000
                elif unit_lower in ['crore', 'cr']:
                    multiplier = 10000000
                elif unit_lower in ['million', 'm']:
                    multiplier = 1000000
                elif unit_lower in ['billion', 'b']:
                    multiplier = 1000000000
                elif unit_lower in ['thousand', 'k']:
                    multiplier = 1000
            
            try:
                amount = float(amount_str) * multiplier
                return amount, amount_str, unit
            except (ValueError, TypeError):
                return None, None, None
        
        # Pattern 1: Budget allocations (highest priority)
        budget_patterns = [
            r'(?:budget|total\s+project\s+cost|total\s+cost|allocated|allocation|funding|capital|project\s+budget)\s+(?:of\s+)?(?:Rs\.?|PKR|PKR\.?)\s*([0-9,]+(?:\.[0-9]+)?)\s*(lakh|crore|million|billion|thousand|M|B)?',
            r'(?:Rs\.?|PKR|PKR\.?)\s*([0-9,]+(?:\.[0-9]+)?)\s*(lakh|crore|million|billion|thousand|M|B)?\s+(?:budget|total\s+project\s+cost|allocated|allocation|funding)',
            r'([0-9,]+(?:\.[0-9]+)?)\s*(lakh|crore|million|billion|thousand|M|B)?\s*(?:Rs\.?|PKR|PKR\.?)\s+(?:budget|total\s+cost|project\s+cost)'
        ]
        
        for pattern in budget_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                amount, amount_str, unit = extract_amount_and_unit(match)
                if amount and amount > 0 and amount not in seen_amounts:
                    seen_amounts.add(amount)
                    details.append({
                        'type': 'budget_allocation',
                        'category': 'total',
                        'amount': amount,
                        'currency': 'PKR',
                        'description': f"Total project budget: PKR {amount:,.0f}"
                    })
                    print(f"   ✅ Extracted budget: PKR {amount:,.2f}")
        
        # Pattern 2: Cost estimates
        cost_patterns = [
            r'(?:estimated\s+cost|cost\s+estimate|estimated|estimation)\s+(?:of\s+)?(?:Rs\.?|PKR|PKR\.?)\s*([0-9,]+(?:\.[0-9]+)?)\s*(lakh|crore|million|billion|thousand|M|B)?',
            r'(?:Rs\.?|PKR|PKR\.?)\s*([0-9,]+(?:\.[0-9]+)?)\s*(lakh|crore|million|billion|thousand|M|B)?\s+(?:estimated|cost\s+estimate)'
        ]
        
        for pattern in cost_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                amount, amount_str, unit = extract_amount_and_unit(match)
                if amount and amount > 0 and amount not in seen_amounts:
                    seen_amounts.add(amount)
                    details.append({
                        'type': 'cost_estimate',
                        'category': 'general',
                        'amount': amount,
                        'currency': 'PKR',
                        'description': f"Estimated cost: PKR {amount:,.0f}"
                    })
                    print(f"   ✅ Extracted cost estimate: PKR {amount:,.2f}")
        
        # Pattern 3: Payment schedules
        payment_patterns = [
            r'(?:payment|installment|milestone\s+payment)\s+(?:of\s+)?(?:Rs\.?|PKR|PKR\.?)\s*([0-9,]+(?:\.[0-9]+)?)\s*(lakh|crore|million|billion|thousand|M|B)?',
            r'(?:Rs\.?|PKR|PKR\.?)\s*([0-9,]+(?:\.[0-9]+)?)\s*(lakh|crore|million|billion|thousand|M|B)?\s+(?:payment|installment)'
        ]
        
        for pattern in payment_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                amount, amount_str, unit = extract_amount_and_unit(match)
                if amount and amount > 0 and amount not in seen_amounts:
                    seen_amounts.add(amount)
                    details.append({
                        'type': 'payment_schedule',
                        'category': 'milestone',
                        'amount': amount,
                        'currency': 'PKR',
                        'description': f"Payment schedule: PKR {amount:,.0f}"
                    })
                    print(f"   ✅ Extracted payment: PKR {amount:,.2f}")
        
        # Pattern 4: Large amounts (only if no other details found, and only very large ones)
        if not details:
            amount_pattern = r'(?:Rs\.?|PKR|PKR\.?)\s*([0-9,]+(?:\.[0-9]+)?)\s*(lakh|crore|million|billion|thousand|M|B)?'
            matches = re.findall(amount_pattern, response, re.IGNORECASE)
            print(f"   🔍 General amount pattern found {len(matches)} matches")
            
            for match in matches[:3]:  # Limit to first 3 largest
                amount, amount_str, unit = extract_amount_and_unit(match)
                # Only extract very large amounts (>= 10 million) as potential budget
                if amount and amount >= 10000000 and amount not in seen_amounts:
                    seen_amounts.add(amount)
                    details.append({
                        'type': 'budget_allocation',
                        'category': 'general',
                        'amount': amount,
                        'currency': 'PKR',
                        'description': f"Large project amount: PKR {amount:,.0f}"
                    })
                    print(f"   ✅ Extracted large amount (potential budget): PKR {amount:,.2f}")
        
        print(f"   ✅ Fallback extraction found {len(details)} unique financial details")
        return details
    
    def _store_details(self, project_id: str, document_id: str, details: List[Dict]):
        """Store financial details in ChromaDB"""
        try:
            data_items = []
            for detail in details:
                # Ensure all metadata values are not None (ChromaDB requirement)
                category = detail.get('category', '')
                if category is None:
                    category = 'general'
                elif not category or category.strip() == '':
                    category = 'general'
                    
                detail_type = detail.get('type', 'unknown')
                if detail_type is None:
                    detail_type = 'unknown'
                    
                amount = detail.get('amount', 0)
                if amount is None:
                    amount = 0
                    
                currency = detail.get('currency', 'PKR')
                if currency is None or not currency:
                    currency = 'PKR'
                    
                description = detail.get('description', str(detail))
                if description is None or not description:
                    description = f"{detail_type}: {category}"
                
                data_items.append({
                    'text': description,
                    'metadata': {
                        'project_id': str(project_id),
                        'document_id': str(document_id),
                        'detail_type': str(detail_type),
                        'category': str(category),
                        'amount': float(amount),
                        'currency': str(currency),
                        'created_at': datetime.now().isoformat()
                    }
                })
            
            self.chroma_manager.store_financial_data(
                'financial_details', data_items, project_id, 'detail'
            )
            
        except Exception as e:
            print(f"Error storing financial details: {e}")

