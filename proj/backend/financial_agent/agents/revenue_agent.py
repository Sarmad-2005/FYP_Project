"""
Revenue Agent - Tracks and projects project revenue
"""

from typing import Dict, List, Any
from datetime import datetime


class RevenueAgent:
    """Worker agent for revenue tracking with orchestrator integration"""
    
    def __init__(self, chroma_manager, orchestrator=None, llm_manager=None):
        """
        Initialize Revenue Agent
        
        Args:
            chroma_manager: FinancialChromaManager instance
            orchestrator: OrchestratorAgent instance for inter-agent communication
            llm_manager: LLMManager instance for LLM-based mapping
        """
        self.chroma_manager = chroma_manager
        self.orchestrator = orchestrator
        self.llm_manager = llm_manager
    
    def analyze_revenue(self, project_id: str, transactions: List[Dict]) -> Dict[str, Any]:
        """
        Analyze project revenue
        
        Args:
            project_id: Project identifier
            transactions: List of transaction dictionaries
            
        Returns:
            Dict with revenue analysis results
        """
        try:
            print(f"💵 Analyzing revenue for project {project_id[:8]}...")
            
            # Filter revenue transactions
            revenue_txns = [t for t in transactions 
                           if t.get('metadata', {}).get('transaction_type') == 'revenue']
            
            if not revenue_txns:
                return {
                    'total_revenue': 0,
                    'by_source': {},
                    'milestone_linked': {},
                    'count': 0
                }
            
            # Calculate totals
            total = sum(float(r.get('metadata', {}).get('amount', 0)) for r in revenue_txns)
            
            # Group by source/category
            by_source = {}
            for rev in revenue_txns:
                source = rev.get('metadata', {}).get('category', 'unknown')
                amount = float(rev.get('metadata', {}).get('amount', 0))
                by_source[source] = by_source.get(source, 0) + amount
            
            # Get milestone linking if orchestrator available
            milestone_linked = {}
            if self.orchestrator:
                milestone_linked = self._link_revenue_to_milestones(project_id, revenue_txns)
            
            analysis = {
                'total_revenue': total,
                'by_source': by_source,
                'milestone_linked': milestone_linked,
                'count': len(revenue_txns),
                'currency': 'PKR'
            }
            
            # Store analysis
            self._store_analysis(project_id, analysis)
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing revenue: {e}")
            return {'total_revenue': 0, 'by_source': {}, 'milestone_linked': {}, 'count': 0}
    
    def _link_revenue_to_milestones(self, project_id: str, revenue_txns: List[Dict]) -> Dict[str, float]:
        """
        Link revenue to milestones using LLM with orchestrator data
        
        Args:
            project_id: Project identifier
            revenue_txns: List of revenue transactions
            
        Returns:
            Dict mapping milestone IDs to revenue amounts
        """
        try:
            if not self.orchestrator or not self.llm_manager:
                return {}
            
            # Get milestones from Performance Agent via orchestrator
            milestones = self.orchestrator.route_data_request(
                query="Get all project milestones with completion status",
                requesting_agent="financial_agent",
                project_id=project_id
            )
            
            if not milestones:
                print("   ℹ️  No milestones found from Performance Agent (run Performance Agent analysis first)")
                return {}
            
            # Use LLM to link revenue to milestones
            print(f"   🤖 Using LLM to link {len(revenue_txns)} revenue transactions to {len(milestones)} milestones...")
            
            # Prepare context
            milestones_context = self._format_milestones_for_llm(milestones)
            revenue_context = self._format_revenue_for_llm(revenue_txns)
            
            prompt = f"""
You are a financial analyst linking revenue payments to project milestones.

MILESTONES:
{milestones_context}

REVENUE TRANSACTIONS:
{revenue_context}

TASK:
For each revenue transaction, determine which milestone it is most closely related to based on:
- Transaction description and payment terms
- Milestone description and completion status
- Payment timing and milestone dates
- Phase-based payments (e.g., "Payment upon Phase 1 completion")

Output Format: JSON object mapping revenue transaction IDs to milestone IDs
{{
  "revenue_id_1": "milestone_id_X",
  "revenue_id_2": "milestone_id_Y",
  "revenue_id_3": "general_revenue"
}}

CRITICAL REQUIREMENTS:
- Return ONLY a JSON object (dictionary), NOT an array
- The object keys are revenue transaction IDs
- The object values are milestone IDs (or "general_revenue")
- Do NOT return milestone objects or arrays
- Start with {{ and end with }}
- No markdown, no explanations, no additional text

Rules:
- Link each revenue transaction to the MOST relevant milestone
- If no clear milestone link exists, use "general_revenue"
- Look for explicit mentions of milestone completion or phase payments
- Use exact IDs from the provided lists
"""
            
            llm_response = self.llm_manager.simple_chat(prompt)
            
            # Parse LLM response
            import json
            import re
            try:
                # Check for LLM errors
                if isinstance(llm_response, dict):
                    if not llm_response.get('success', False):
                        print(f"   ⚠️  LLM error: {llm_response.get('error', 'Unknown error')}")
                        return {}
                    # Extract the actual response text
                    response_text = llm_response.get('response', '')
                else:
                    response_text = str(llm_response)
                
                # Clean response - remove markdown code blocks if present
                response_text = response_text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                elif response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                # Extract JSON (could be object or array)
                # First try to find JSON object
                json_match = re.search(r'\{[\s\S]*?\}(?=\s*(?:\n|$|Explanation|In the above|For |The |This|python|import))', response_text)
                if not json_match:
                    # Try to find JSON array
                    json_match = re.search(r'\[[\s\S]*?\](?=\s*(?:\n|$|Explanation|In the above|For |The |This|python|import))', response_text)
                if not json_match:
                    # Last resort: find any JSON structure
                    json_match = re.search(r'[\{\[][\s\S]*?[\}\]]', response_text)
                
                if json_match:
                    response_text = json_match.group(0)
                
                print(f"   🔍 Extracted JSON (length: {len(response_text)} chars)")
                print(f"   📝 First 200 chars: {response_text[:200]}")
                
                # Parse JSON
                parsed = json.loads(response_text)
                
                # Handle different response formats
                mapping = {}
                
                if isinstance(parsed, dict):
                    # Expected format: {"revenue_id": "milestone_id"}
                    mapping = parsed
                elif isinstance(parsed, list):
                    # LLM returned array - try to extract mapping from it
                    print(f"   ⚠️  LLM returned array instead of mapping dict, attempting to extract mapping...")
                    # If it's an array of milestone objects, we can't map revenue to them
                    # Return empty mapping and log warning
                    if parsed and isinstance(parsed[0], dict) and 'id' in parsed[0]:
                        print(f"   ⚠️  LLM returned milestone objects array, not a revenue-to-milestone mapping")
                        print(f"   💡 This suggests the prompt needs improvement or LLM misunderstood the task")
                        return {}
                    else:
                        # Try to interpret as mapping array
                        for item in parsed:
                            if isinstance(item, dict):
                                # Look for revenue_id and milestone_id keys
                                rev_id = item.get('revenue_id') or item.get('transaction_id')
                                mil_id = item.get('milestone_id') or item.get('milestone')
                                if rev_id and mil_id:
                                    mapping[rev_id] = mil_id
                
                if not mapping:
                    print(f"   ⚠️  Could not extract revenue-to-milestone mapping from LLM response")
                    return {}
                
                # Aggregate revenue by milestone
                milestone_revenue = {}
                for revenue_id, milestone_id in mapping.items():
                    # Find revenue amount
                    revenue = next((r for r in revenue_txns if r.get('id') == revenue_id), None)
                    if revenue:
                        amount = float(revenue.get('metadata', {}).get('amount', 0))
                        milestone_revenue[milestone_id] = milestone_revenue.get(milestone_id, 0) + amount
                
                print(f"   ✅ Linked revenue to {len(milestone_revenue)} milestones")                
                return milestone_revenue
                
            except json.JSONDecodeError as e:
                print(f"   ⚠️  Failed to parse LLM response as JSON: {e}")
                print(f"   📄 Response text (first 500 chars): {response_text[:500]}...")
                return {}
            
        except Exception as e:
            print(f"   ❌ Error linking revenue to milestones: {e}")
            return {}
    
    def _format_milestones_for_llm(self, milestones: List[Dict]) -> str:
        """Format milestones for LLM context"""
        formatted = []
        for i, milestone in enumerate(milestones[:20], 1):  # Limit to 20 milestones
            milestone_id = milestone.get('id', milestone.get('metadata', {}).get('milestone_id', f'milestone_{i}'))
            milestone_text = milestone.get('text', milestone.get('metadata', {}).get('milestone_text', 'No description'))
            status = milestone.get('metadata', {}).get('status', 'unknown')
            priority = milestone.get('metadata', {}).get('priority', 'unknown')
            formatted.append(f"{i}. ID: {milestone_id}\n   Description: {milestone_text}\n   Status: {status}\n   Priority: {priority}")
        return "\n".join(formatted)
    
    def _format_revenue_for_llm(self, revenue_txns: List[Dict]) -> str:
        """Format revenue transactions for LLM context"""
        formatted = []
        for i, rev in enumerate(revenue_txns[:50], 1):  # Limit to 50 revenues
            rev_id = rev.get('id', f'rev_{i}')
            amount = rev.get('metadata', {}).get('amount', 0)
            date = rev.get('metadata', {}).get('date', 'unknown')
            source = rev.get('metadata', {}).get('vendor_recipient', 'unknown')
            category = rev.get('metadata', {}).get('category', 'unknown')
            desc = rev.get('text', rev.get('metadata', {}).get('description', 'No description'))
            formatted.append(f"{i}. ID: {rev_id}\n   Amount: PKR {amount:,.2f}\n   Date: {date}\n   Source: {source}\n   Category: {category}\n   Description: {desc}")
        return "\n".join(formatted)

    
    def _store_analysis(self, project_id: str, analysis: Dict):
        """Store revenue analysis in ChromaDB"""
        try:
            data_item = {
                'text': f"Revenue analysis: Total {analysis['total_revenue']} PKR from {analysis['count']} transactions",
                'metadata': {
                    'project_id': project_id,
                    'analysis_type': 'revenue',
                    'total_revenue': analysis['total_revenue'],
                    'transaction_count': analysis['count'],
                    'sources': len(analysis['by_source']),
                    'created_at': datetime.now().isoformat()
                }
            }
            
            self.chroma_manager.store_financial_data(
                'revenue_analysis', [data_item], project_id, 'analysis'
            )
            
        except Exception as e:
            print(f"Error storing revenue analysis: {e}")
    
    def get_revenue_analysis(self, project_id: str) -> Dict:
        """Get revenue analysis for a project (recalculated from current transactions)"""
        try:
            # Get all transactions
            transactions = self.chroma_manager.get_financial_data('transactions', project_id)
            
            # Analyze current transactions
            analysis = self.analyze_revenue(project_id, transactions)
            
            return analysis
            
        except Exception as e:
            print(f"Error getting revenue analysis: {e}")
            return {'total_revenue': 0, 'by_source': {}, 'count': 0}

