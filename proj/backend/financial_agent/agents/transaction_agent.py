"""
Transaction Agent - Extracts and tracks financial transactions
"""

import json
import re
from typing import Dict, List, Any
from datetime import datetime


class TransactionAgent:
    """Worker agent for extracting financial transactions"""
    
    def __init__(self, chroma_manager):
        """
        Initialize Transaction Agent
        
        Args:
            chroma_manager: FinancialChromaManager instance
        """
        self.chroma_manager = chroma_manager
    
    def extract_transactions(self, project_id: str, document_id: str,
                            llm_manager, embeddings_manager) -> Dict[str, Any]:
        """
        Extract transactions from a document
        
        Args:
            project_id: Project identifier
            document_id: Document identifier
            llm_manager: LLM manager for extraction
            embeddings_manager: Embeddings manager for context
            
        Returns:
            Dict with extraction results
        """
        try:
            print(f"💳 Extracting transactions from document {document_id[:8]}...")
            
            # Get document embeddings
            document_embeddings = embeddings_manager.get_document_embeddings(project_id, document_id)
            
            if not document_embeddings or len(document_embeddings) == 0:
                return {'success': False, 'error': 'No document embeddings found', 'transactions': []}
            
            # Extract text from embeddings to create context
            context = "\n".join([
                emb.get('content', '') for emb in document_embeddings 
                if emb.get('content')
            ])
            
            if not context:
                return {'success': False, 'error': 'No text content found in embeddings', 'transactions': []}
            
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
                    'transactions': []
                }
            
            response_text = llm_response.get('response', '')
            print(f"   ✅ LLM response received: {len(response_text)} characters")
            print(f"   📝 LLM response (first 500 chars): {response_text[:500]}")
            
            # Parse response - extract the actual text from the response dict
            transactions = self._parse_transactions(response_text, llm_manager)
            
            # Store in ChromaDB
            if transactions:
                self._store_transactions(project_id, document_id, transactions)
            
            return {
                'success': True,
                'transactions': transactions,
                'count': len(transactions)
            }
            
        except Exception as e:
            print(f"Error extracting transactions: {e}")
            return {'success': False, 'error': str(e), 'transactions': []}
    
    def _create_extraction_prompt(self, context: str) -> str:
        """Create LLM prompt for transaction extraction"""
        return f"""You are a financial transaction analyst. Extract ONLY ACTUAL financial transactions from this document.

CONTEXT:
{context}

⚠️ CRITICAL INSTRUCTIONS - READ CAREFULLY:

DO NOT EXTRACT (These are BUDGET/CAPITAL, not operational transactions):
❌ Initial project funding/grants (e.g., "Government provided PKR 720M", "Private investment PKR 480M")
❌ Total project cost/budget (e.g., "Total project cost: PKR 1.2 billion")
❌ Budget allocations (e.g., "Budget of PKR X allocated for Y")
❌ Cost estimates (e.g., "Estimated cost of PKR X")
❌ Planned expenses (future intentions, not actual payments)
❌ Financial targets or goals
❌ Maintenance funds set aside (e.g., "Reserve fund of PKR 25M")
❌ Initial fund transfers from funding sources (e.g., "Initial transfer of PKR 150M from Punjab Board")
❌ Hypothetical amounts

ONLY EXTRACT OPERATIONAL TRANSACTIONS:
✅ Operational revenue from facility (ticket sales, memberships, sponsorships, event fees, rental income)
✅ Recurring operational expenses (monthly payments, staff salaries, utilities, maintenance contracts)
✅ Actual payments made with dates (e.g., "Paid PKR X to vendor Y on [date]")
✅ Money received from operations (e.g., "Ticket sales generated PKR X")
✅ Completed or pending invoices with specific vendors
✅ Refunds processed
✅ Service-related transfers (NOT initial capital transfers)

TRANSACTION TYPES:
1. Expenses - Money going out (ACTUAL PAYMENTS ONLY)
2. Revenue - Money coming in (ACTUAL RECEIPTS ONLY)
3. Transfers - Money moved between accounts
4. Refunds - Money returned
5. Advances - Advance payments

OUTPUT FORMAT (JSON Array):
[
  {{
    "date": "YYYY-MM-DD or relative description (e.g., 'monthly', 'annual', 'first six months', 'quarterly')",
    "amount": float,
    "currency": "PKR",
    "type": "expense/revenue/transfer/refund/advance",
    "category": "string",
    "vendor_recipient": "string",
    "payment_method": "cash/bank_transfer/check/unknown",
    "status": "completed/pending",
    "reference_number": "string or empty",
    "description": "string",
    "time_period": "exact date OR relative time description from document"
  }}
]

EXAMPLES OF ACTUAL TRANSACTIONS (EXTRACT THESE):

1. ✅ "Paid Rs. 50,000 to ABC Construction on Jan 15th via bank transfer for foundation work (Invoice #1234)"
   → {{
       "date": "2024-01-15",
       "amount": 50000,
       "currency": "PKR",
       "type": "expense",
       "category": "construction",
       "vendor_recipient": "ABC Construction",
       "payment_method": "bank_transfer",
       "status": "completed",
       "reference_number": "1234",
       "description": "Payment for foundation work",
       "time_period": "2024-01-15"
     }}

2. ✅ "Average monthly cafeteria revenue during active tournaments is Rs. 500,000"
   → {{
       "date": "monthly",
       "amount": 500000,
       "currency": "PKR",
       "type": "revenue",
       "category": "cafeteria",
       "vendor_recipient": "cafeteria",
       "payment_method": "unknown",
       "status": "completed",
       "reference_number": "",
       "description": "Average monthly cafeteria revenue during active tournaments",
       "time_period": "monthly"
     }}

3. ✅ "Annual membership registrations revenue within the first six months: Rs. 10M"
   → {{
       "date": "first six months",
       "amount": 10000000,
       "currency": "PKR",
       "type": "revenue",
       "category": "membership",
       "vendor_recipient": "unknown",
       "payment_method": "unknown",
       "status": "completed",
       "reference_number": "",
       "description": "Annual membership registrations revenue within the first six months",
       "time_period": "first six months"
     }}

4. ✅ "Invoice from XYZ Suppliers for Rs. 25,000 for electrical materials (pending payment)"
   → {{
       "date": "pending",
       "amount": 25000,
       "currency": "PKR",
       "type": "expense",
       "category": "materials_electrical",
       "vendor_recipient": "XYZ Suppliers",
       "payment_method": "unknown",
       "status": "pending",
       "reference_number": "",
       "description": "Electrical materials purchase",
       "time_period": "pending"
     }}

EXAMPLES OF NON-TRANSACTIONS (DO NOT EXTRACT THESE):

1. ❌ "Budget allocated for equipment: Rs. 150,000,000"
   → SKIP (This is a budget allocation, not a transaction)

2. ❌ "Total estimated cost of the project: Rs. 1,200,000,000"
   → SKIP (This is an estimate, not a transaction)

3. ❌ "Maintenance fund of Rs. 25,000,000 will be set aside"
   → SKIP (This is a planned allocation, not a transaction)

4. ❌ "Government of Punjab to provide 60% funding (Rs. 720,000,000)"
   → SKIP (This is a funding plan, not a completed transaction)

5. ❌ "Labor expenses: PKR 250,000,000"
   → SKIP (This is a budget category total, not individual transactions)

6. ❌ "Materials expenses estimated at PKR 400,000,000"
   → SKIP (This is a cost estimate, not actual transactions)

7. ❌ "Technology imports: PKR 120,000,000"
   → SKIP (This is a budget line item, not a specific transaction)

CONSTRAINTS:
- Extract ALL transactions, even partial information
- Infer transaction type from context
- Use standardized categories
- For dates: Use exact date (YYYY-MM-DD) if available, otherwise capture relative time description from document (e.g., "monthly", "annual", "quarterly", "first six months", "during tournaments")
- NEVER use "unknown" for dates - always extract the time description from context
- Return ONLY valid JSON array
- If no transactions found, return empty array []
- Always include the "time_period" field with the time description from the document

JSON OUTPUT:"""
    
    def _parse_transactions(self, response: str, llm_manager) -> List[Dict]:
        """Parse transactions from LLM response"""
        try:
            # Remove markdown code blocks if present
            response_text = response.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            elif response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Try to find JSON array in the response
            import re
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                response_text = json_match.group(0)
            
            print(f"   🔍 Attempting to parse JSON (length: {len(response_text)} chars)")
            print(f"   📝 First 200 chars: {response_text[:200]}")
            
            transactions = json.loads(response_text)
            
            # If it's a dict, try to extract a list from it
            if isinstance(transactions, dict):
                # Check common keys that might contain the list
                for key in ['transactions', 'data', 'results', 'items', 'financial_transactions']:
                    if key in transactions and isinstance(transactions[key], list):
                        transactions = transactions[key]
                        print(f"   ✅ Found transactions list in key: {key}")
                        break
                else:
                    print(f"   ⚠️  Response is a dict but no transactions list found. Keys: {list(transactions.keys())}")
                    return self._fallback_extraction(response)
            
            if isinstance(transactions, list):
                print(f"   ✅ Parsed {len(transactions)} transaction candidates")
                # Use LLM to validate transactions (filter out budget allocations)
                valid_transactions = self._llm_validate_transactions(transactions, llm_manager)
                
                # Add IDs and ensure required fields
                for i, txn in enumerate(valid_transactions):
                    txn['id'] = f"txn_{datetime.now().timestamp()}_{i}"
                    
                    # Use time_period for date if available, otherwise use date field
                    if 'time_period' in txn and txn['time_period']:
                        txn['date'] = txn['time_period']
                    
                    # Ensure required fields
                    txn.setdefault('date', 'not specified')
                    txn.setdefault('time_period', txn.get('date', 'not specified'))
                    txn.setdefault('currency', 'PKR')
                    txn.setdefault('type', 'expense')
                    txn.setdefault('category', 'general')
                    txn.setdefault('vendor_recipient', 'unknown')
                    txn.setdefault('status', 'unknown')
                    txn.setdefault('amount', 0)
                
                print(f"   ✅ Validated {len(valid_transactions)} transactions (filtered out {len(transactions) - len(valid_transactions)} invalid items)")
                return valid_transactions
            
            print(f"   ⚠️  Parsed data is not a list (type: {type(transactions).__name__})")
            return self._fallback_extraction(response)
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing failed for transactions: {e}")
            print(f"   📄 Response (first 500 chars): {response[:500]}")
            return self._fallback_extraction(response)
        except Exception as e:
            print(f"⚠️ Error parsing transactions: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_extraction(response)
    
    def _llm_validate_transactions(self, transactions: List[Dict], llm_manager) -> List[Dict]:
        """
        Use LLM to validate if extracted items are real transactions or budget allocations
        
        Args:
            transactions: List of extracted transaction candidates
            llm_manager: LLM manager instance
            
        Returns:
            List of validated actual transactions
        """
        if not transactions:
            return []
        
        try:
            # Create validation prompt
            transactions_summary = "\n".join([
                f"{i+1}. Description: {txn.get('description', 'N/A')}, "
                f"Amount: {txn.get('amount', 0)}, "
                f"Date: {txn.get('date', 'unknown')}, "
                f"Vendor: {txn.get('vendor_recipient', 'unknown')}"
                for i, txn in enumerate(transactions)
            ])
            
            validation_prompt = f"""You are a financial analyst. Review these extracted transactions and determine which are OPERATIONAL transactions versus INITIAL FUNDING/BUDGET allocations.

EXTRACTED ITEMS:
{transactions_summary}

RULES FOR OPERATIONAL TRANSACTIONS (KEEP):
- ✅ Operational revenue: ticket sales, memberships, sponsorships, rental income, event revenue
- ✅ Recurring expenses: monthly contractor payments, staff salaries, utilities, maintenance
- ✅ Has specific operational context (e.g., "during tournament", "monthly rent", "cafeteria revenue")
- ✅ Ongoing facility operations and services
- ✅ Specific vendor/recipient names (not "unknown")
- ✅ Specific dates or recurring periods (not just "unknown")

RULES FOR BUDGET/ESTIMATES (REJECT):
- ❌ Initial project funding from government or private investors
- ❌ Large capital amounts for project setup (e.g., PKR 720M, PKR 480M, PKR 150M)
- ❌ Descriptions mentioning "Government of Punjab provided", "Private investors contributed", "Initial fund transfer"
- ❌ Words like "funding", "capital", "investment", "total project cost", "budget allocation", "estimated", "expenses" (as category label)
- ❌ Budget category labels: "Labor expenses", "Materials expenses", "Technology imports", "Equipment costs"
- ❌ Maintenance funds "set aside" or "established" (not actual payments)
- ❌ If date AND vendor are both "unknown" AND amount > PKR 10M, likely budget item
- ❌ If description is just a category name (e.g., "Labor expenses", "Materials"), not a specific transaction

TASK: For each item, decide: KEEP (operational transaction) or REJECT (initial funding/budget)

OUTPUT FORMAT: Return ONLY a JSON array of indices (1-based) to KEEP.
Example: [1, 3, 5] means keep items 1, 3, and 5, reject others.

JSON OUTPUT:"""

            # Get LLM validation
            llm_response = llm_manager.simple_chat(validation_prompt)
            
            if llm_response.get('success'):
                response_text = llm_response.get('response', '').strip()
                print(f"   🔍 LLM validation response (first 200 chars): {response_text[:200]}")
                
                # Clean and parse indices to keep
                # Remove markdown code blocks
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                elif response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                # Try to find JSON array in the response
                json_match = re.search(r'\[[\s\S]*\]', response_text)
                if json_match:
                    response_text = json_match.group(0)
                
                try:
                    indices_to_keep = json.loads(response_text)
                    if not isinstance(indices_to_keep, list):
                        print(f"   ⚠️  LLM returned non-list, using all transactions")
                        return self._basic_validate_transactions(transactions)
                except json.JSONDecodeError as e:
                    print(f"   ⚠️  Failed to parse LLM validation indices: {e}")
                    print(f"   📄 Response was: {response_text[:300]}")
                    # Fallback: use all transactions with basic validation
                    return self._basic_validate_transactions(transactions)
                
                # Filter transactions
                valid_transactions = []
                for idx in indices_to_keep:
                    if 1 <= idx <= len(transactions):
                        txn = transactions[idx - 1]
                        # Additional check: amount must be positive
                        if float(txn.get('amount', 0)) > 0:
                            valid_transactions.append(txn)
                        else:
                            print(f"   ⚠️ Skipping item {idx}: invalid amount")
                    else:
                        print(f"   ⚠️ Invalid index from LLM: {idx}")
                
                rejected_count = len(transactions) - len(valid_transactions)
                if rejected_count > 0:
                    print(f"   🤖 LLM filtered out {rejected_count} non-transactions")
                
                return valid_transactions
            else:
                print(f"   ⚠️ LLM validation failed, using basic validation")
                # Fallback to basic validation
                return self._basic_validate_transactions(transactions)
                
        except Exception as e:
            print(f"   ⚠️ LLM validation error: {e}, using basic validation")
            return self._basic_validate_transactions(transactions)
    
    def _basic_validate_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Basic validation fallback (keyword-based)"""
        valid = []
        for txn in transactions:
            amount = float(txn.get('amount', 0))
            if amount <= 0:
                continue
            
            description = str(txn.get('description', '')).lower()
            category = str(txn.get('category', '')).lower()
            
            # Reject obvious budget keywords
            if any(kw in description or kw in category for kw in [
                'budget', 'allocation', 'estimated', 'planned', 'fund for', 'set aside'
            ]):
                continue
            
            valid.append(txn)
        
        return valid
    
    def _fallback_extraction(self, response: str) -> List[Dict]:
        """Fallback transaction extraction using regex"""
        transactions = []
        print(f"   🔄 Using fallback regex extraction")
        print(f"   📄 Response length: {len(response)} chars")
        
        # Pattern for payments - more flexible
        payment_pattern = r'(?:paid|payment|expense|cost|spent|disbursed|transferred)\s+(?:of\s+)?(?:Rs\.?|PKR|PKR\.?)\s*([0-9,]+(?:\.[0-9]+)?)\s*(lakh|crore|million|billion|M|B)?'
        matches = re.findall(payment_pattern, response, re.IGNORECASE)
        print(f"   🔍 Found {len(matches)} payment matches")
        
        for match in matches:
            try:
                # Handle different match structures
                if isinstance(match, tuple):
                    amount_str = match[1].replace(',', '') if len(match) > 1 else match[0].replace(',', '')
                    unit = match[2] if len(match) > 2 else ''
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
                
                amount = float(amount_str) * multiplier
                if amount > 0:  # Only add positive amounts
                    transactions.append({
                        'id': f"txn_fallback_{len(transactions)}",
                        'date': 'not specified',
                        'time_period': 'not specified',
                        'amount': amount,
                        'currency': 'PKR',
                        'type': 'expense',
                    'category': 'general',
                    'vendor_recipient': 'unknown',
                    'payment_method': 'unknown',
                    'status': 'unknown',
                    'reference_number': '',
                    'description': 'Extracted payment from document'
                })
            except (ValueError, IndexError, TypeError) as e:
                print(f"   ⚠️  Error processing payment match: {e}")
                continue
        
        # Pattern for revenue - more flexible
        revenue_pattern = r'(?:received|revenue|income|earned|generated)\s+(?:of\s+)?(?:Rs\.?|PKR|PKR\.?)\s*([0-9,]+(?:\.[0-9]+)?)\s*(lakh|crore|million|billion|M|B)?'
        matches = re.findall(revenue_pattern, response, re.IGNORECASE)
        print(f"   🔍 Found {len(matches)} revenue matches")
        
        for match in matches:
            try:
                # Handle different match structures
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
                
                amount = float(amount_str) * multiplier
                if amount > 0:  # Only add positive amounts
                    transactions.append({
                        'id': f"txn_fallback_{len(transactions)}",
                        'date': 'not specified',
                        'time_period': 'not specified',
                        'amount': amount,
                        'currency': 'PKR',
                        'type': 'revenue',
                    'category': 'general',
                    'vendor_recipient': 'unknown',
                    'payment_method': 'unknown',
                    'status': 'unknown',
                    'reference_number': '',
                    'description': 'Extracted revenue from document'
                })
            except (ValueError, IndexError, TypeError) as e:
                print(f"   ⚠️  Error processing revenue match: {e}")
                continue
        
        print(f"   ✅ Fallback extraction found {len(transactions)} transactions")
        return transactions
    
    def _store_transactions(self, project_id: str, document_id: str, transactions: List[Dict]):
        """Store transactions in ChromaDB"""
        try:
            data_items = []
            for txn in transactions:
                data_items.append({
                    'id': txn.get('id'),
                    'text': txn.get('description', str(txn)),
                    'metadata': {
                        'project_id': project_id,
                        'document_id': document_id,
                        'transaction_type': txn.get('type', 'expense'),
                        'amount': txn.get('amount', 0),
                        'currency': txn.get('currency', 'PKR'),
                        'date': txn.get('date', 'not specified'),
                        'time_period': txn.get('time_period', txn.get('date', 'not specified')),
                        'vendor_recipient': txn.get('vendor_recipient', ''),
                        'category': txn.get('category', 'general'),
                        'status': txn.get('status', 'unknown'),
                        'payment_method': txn.get('payment_method', 'unknown'),
                        'reference_number': txn.get('reference_number', ''),
                        'created_at': datetime.now().isoformat()
                    }
                })
            
            self.chroma_manager.store_financial_data(
                'transactions', data_items, project_id, 'transaction'
            )
            
        except Exception as e:
            print(f"Error storing transactions: {e}")
    
    def get_all_transactions(self, project_id: str, filters: Dict = None) -> List[Dict]:
        """Get all transactions for a project"""
        try:
            return self.chroma_manager.get_financial_data(
                'transactions', project_id, filters
            )
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []

