"""
Financial Agent - Main Coordinator
Manages financial analysis, transactions, expenses, and revenue tracking
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .agents.financial_details_agent import FinancialDetailsAgent
from .agents.transaction_agent import TransactionAgent
from .agents.expense_agent import ExpenseAgent
from .agents.revenue_agent import RevenueAgent
from .agents.anomaly_detection_agent import AnomalyDetectionAgent
from .chroma_manager import FinancialChromaManager


class FinancialAgent:
    """Main Financial Agent coordinator"""
    
    def __init__(self, llm_manager, embeddings_manager, db_manager, orchestrator=None):
        self.llm_manager = llm_manager
        self.embeddings_manager = embeddings_manager
        self.db_manager = db_manager
        self.orchestrator = orchestrator
        
        # Initialize centralized ChromaDB manager
        self.chroma_manager = FinancialChromaManager()
        
        # Initialize worker agents (pass llm_manager for LLM-based mapping)
        self.details_agent = FinancialDetailsAgent(self.chroma_manager)
        self.transaction_agent = TransactionAgent(self.chroma_manager)
        self.expense_agent = ExpenseAgent(self.chroma_manager, orchestrator, llm_manager)
        self.revenue_agent = RevenueAgent(self.chroma_manager, orchestrator, llm_manager)
        self.anomaly_agent = AnomalyDetectionAgent(self.chroma_manager)
        self.actor_mapper = None
        try:
            from backend.financial_agent.agents.actor_transaction_mapper import ActorTransactionMapper
            self.actor_mapper = ActorTransactionMapper(self.chroma_manager, orchestrator, llm_manager)
        except Exception as e:
            print(f"⚠️ Failed to initialize ActorTransactionMapper: {e}")
        
        # Financial data storage
        self.financial_data_dir = 'data/financial'
        self._ensure_financial_data_directory()
    
    def _ensure_financial_data_directory(self):
        """Create financial data directory if it doesn't exist"""
        if not os.path.exists(self.financial_data_dir):
            os.makedirs(self.financial_data_dir)

    # ------------------------------------------------------------------ #
    # Actor ↔ Transaction Mapping
    # ------------------------------------------------------------------ #
    def map_actor_transactions(self, project_id: str, actors: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Map actors (from Performance) to financial transactions.
        
        actors: optional pre-fetched list (for A2A/gateway usage)
        """
        if not self.actor_mapper:
            return {"success": False, "error": "Actor mapper not initialized"}
        return self.actor_mapper.map_actors_to_transactions(project_id, actors_override=actors)

    def get_actor_transaction_mappings(self, project_id: str) -> List[Dict[str, Any]]:
        """Retrieve stored actor → transaction mappings with enriched transaction details."""
        mappings = self.chroma_manager.get_financial_data('actor_transaction_mappings', project_id)
        print(f"🔗 Actor-Transaction Mappings retrieved: {len(mappings)} items")
        
        if not mappings:
            return []
        
        # Get all transactions to enrich mapping data
        all_transactions = self.chroma_manager.get_financial_data('transactions', project_id)
        transaction_lookup = {t.get('id'): t for t in all_transactions}
        
        # Enrich mappings with transaction details
        enriched_mappings = []
        for mapping in mappings:
            meta = mapping.get('metadata', {})
            transactions = meta.get('transactions', [])
            
            # Enrich each transaction with full details
            enriched_transactions = []
            for tx in transactions:
                tx_id = tx.get('transaction_id') or tx.get('id')
                if tx_id and tx_id in transaction_lookup:
                    full_tx = transaction_lookup[tx_id]
                    tx_meta = full_tx.get('metadata', {})
                    enriched_transactions.append({
                        **tx,  # Keep original mapping data (reason, confidence)
                        'transaction_details': {
                            'id': tx_id,
                            'amount': tx_meta.get('amount', 0),
                            'currency': tx_meta.get('currency', 'PKR'),
                            'type': tx_meta.get('transaction_type') or tx_meta.get('type', 'unknown'),
                            'category': tx_meta.get('category', ''),
                            'vendor_recipient': tx_meta.get('vendor_recipient', ''),
                            'description': full_tx.get('text') or full_tx.get('content', ''),
                            'date': tx_meta.get('date', ''),
                            'status': tx_meta.get('status', '')
                        }
                    })
                else:
                    # Keep original if transaction not found
                    enriched_transactions.append(tx)
            
            # Create enriched mapping
            enriched_mapping = {
                **mapping,
                'metadata': {
                    **meta,
                    'transactions': enriched_transactions
                }
            }
            enriched_mappings.append(enriched_mapping)
        
        if enriched_mappings:
            print(f"   Sample enriched mapping structure: {enriched_mappings[0] if enriched_mappings else 'None'}")
        return enriched_mappings
    
    def first_time_generation(self, project_id: str, document_id: str) -> Dict[str, Any]:
        """
        First time generation of all financial metrics for a project
        
        Args:
            project_id: Project identifier
            document_id: Document identifier
            
        Returns:
            Dict with results of first time generation
        """
        results = {
            'project_id': project_id,
            'document_id': document_id,
            'timestamp': datetime.now().isoformat(),
            'financial_details': {'success': False, 'count': 0},
            'transactions': {'success': False, 'count': 0},
            'expenses': {'total': 0, 'count': 0},
            'revenue': {'total': 0, 'count': 0},
            'financial_health': 0.0,
            'overall_success': False
        }
        
        try:
            print(f"\n{'='*80}")
            print(f"💰 STARTING FIRST-TIME FINANCIAL ANALYSIS")
            print(f"📁 Project ID: {project_id}")
            print(f"📄 Document ID: {document_id}")
            print(f"{'='*80}\n")
            
            # Debug: Show current LLM selection
            current_llm = self.llm_manager.get_current_llm()
            print(f"🤖 Using LLM: {current_llm.upper() if current_llm else 'NONE'}")
            if current_llm:
                print(f"   ✅ LLM is set and ready")
            else:
                print(f"   ⚠️ WARNING: No LLM selected!")
            print()
            
            # Step 1: Extract financial details
            print("💵 STEP 1/5: Extracting Financial Details...")
            details_result = self.details_agent.extract_financial_details(
                project_id, document_id, self.llm_manager, self.embeddings_manager
            )
            results['financial_details']['success'] = details_result['success']
            results['financial_details']['count'] = details_result.get('count', 0)
            print(f"   ✅ Financial Details: {results['financial_details']['count']} found")
            
            # Step 2: Extract transactions
            print("\n💳 STEP 2/5: Extracting Transactions...")
            txn_result = self.transaction_agent.extract_transactions(
                project_id, document_id, self.llm_manager, self.embeddings_manager
            )
            results['transactions']['success'] = txn_result['success']
            results['transactions']['count'] = txn_result.get('count', 0)
            print(f"   ✅ Transactions: {results['transactions']['count']} found")
            
            # Step 3: Analyze expenses
            print("\n📊 STEP 3/5: Analyzing Expenses...")
            transactions = self.chroma_manager.get_financial_data('transactions', project_id)
            expense_analysis = self.expense_agent.analyze_expenses(project_id, transactions)
            results['expenses']['total'] = expense_analysis.get('total_expenses', 0)
            results['expenses']['count'] = expense_analysis.get('count', 0)
            print(f"   ✅ Total Expenses: PKR {results['expenses']['total']:,.2f}")
            
            # Step 4: Analyze revenue
            print("\n💵 STEP 4/5: Analyzing Revenue...")
            revenue_analysis = self.revenue_agent.analyze_revenue(project_id, transactions)
            results['revenue']['total'] = revenue_analysis.get('total_revenue', 0)
            results['revenue']['count'] = revenue_analysis.get('count', 0)
            print(f"   ✅ Total Revenue: PKR {results['revenue']['total']:,.2f}")
            
            # Step 5: Calculate financial health
            print("\n🏥 STEP 5/6: Calculating Financial Health Score...")
            health_score = self._calculate_financial_health(
                results['expenses']['total'],
                results['revenue']['total'],
                expense_analysis.get('by_category', {})
            )
            results['financial_health'] = health_score
            print(f"   ✅ Financial Health: {health_score:.1f}%")
            
            # Step 6: Detect anomalies using Isolation Forest
            print("\n🔍 STEP 6/6: Running Anomaly Detection...")
            anomaly_result = self.anomaly_agent.detect_anomalies(project_id, transactions)
            results['anomaly_detection'] = {
                'success': anomaly_result.get('success', False),
                'anomalies_detected': anomaly_result.get('anomalies_detected', 0),
                'anomaly_rate': anomaly_result.get('anomaly_rate', 0)
            }
            if anomaly_result.get('success'):
                print(f"   ✅ Detected {anomaly_result.get('anomalies_detected', 0)} anomalies")
            else:
                print(f"   ⚠️ {anomaly_result.get('message', 'Anomaly detection skipped')}")
            
            # Determine overall success
            results['overall_success'] = (
                results['financial_details']['success'] and
                results['transactions']['success']
            )
            
            print(f"\n{'='*80}")
            print(f"✅ FINANCIAL ANALYSIS COMPLETE!")
            print(f"   Expenses: PKR {results['expenses']['total']:,.2f}")
            print(f"   Revenue: PKR {results['revenue']['total']:,.2f}")
            print(f"   Health: {results['financial_health']:.1f}%")
            print(f"   Anomalies: {results['anomaly_detection']['anomalies_detected']}")
            print(f"{'='*80}\n")
            
            # Save results
            self._save_financial_results(project_id, results)
            
            return results
            
        except Exception as e:
            print(f"❌ Error in first-time generation: {e}")
            results['error'] = str(e)
            return results
    
    def refresh_financial_data(self, project_id: str) -> Dict[str, Any]:
        """
        Refresh financial data (processes new documents)
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with updated financial data
        """
        try:
            print(f"\n{'='*80}")
            print(f"🔄 REFRESHING FINANCIAL DATA - Project: {project_id}")
            print(f"{'='*80}\n")
            
            # Debug: Show current LLM selection
            current_llm = self.llm_manager.get_current_llm()
            print(f"🤖 Using LLM: {current_llm.upper() if current_llm else 'NONE'}")
            if current_llm:
                print(f"   ✅ LLM is set and ready")
            else:
                print(f"   ⚠️ WARNING: No LLM selected!")
            print()
            
            # Get project documents
            documents = self.db_manager.get_project_documents(project_id)
            
            if not documents:
                return {
                    'success': False,
                    'error': 'No documents found',
                    'project_id': project_id
                }
            
            # Check for new documents
            last_update = self._get_last_financial_update(project_id)
            
            new_documents = []
            if last_update:
                for document in documents:
                    if document.get('created_at', '') > last_update:
                        new_documents.append(document)
            else:
                new_documents = documents
            
            if not new_documents:
                print("✅ No new documents - financial data is up to date")
                return self._get_current_financial_data(project_id)
            
            print(f"📄 Found {len(new_documents)} new document(s) to process")
            
            # Process new documents
            for document in new_documents:
                doc_name = document.get('filename', document['id'][:8])
                print(f"\n📄 Processing: {doc_name}")
                
                # Extract from new document
                self.details_agent.extract_financial_details(
                    project_id, document['id'], self.llm_manager, self.embeddings_manager
                )
                self.transaction_agent.extract_transactions(
                    project_id, document['id'], self.llm_manager, self.embeddings_manager
                )
            
            # Recalculate aggregations
            transactions = self.chroma_manager.get_financial_data('transactions', project_id)
            self.expense_agent.analyze_expenses(project_id, transactions)
            self.revenue_agent.analyze_revenue(project_id, transactions)
            
            # Step 6: Detect anomalies using Isolation Forest
            print("\n🔍 STEP 6/6: Running Anomaly Detection...")
            anomaly_result = self.anomaly_agent.detect_anomalies(project_id, transactions)
            if anomaly_result.get('success'):
                print(f"   ✅ Detected {anomaly_result.get('anomalies_detected', 0)} anomalies")
            
            # Update timestamp
            self._update_last_financial_update(project_id)
            
            # Get updated data
            updated_data = self._get_current_financial_data(project_id)
            
            print(f"\n{'='*80}")
            print(f"✅ REFRESH COMPLETE")
            print(f"{'='*80}\n")
            
            return updated_data
            
        except Exception as e:
            print(f"❌ Error refreshing financial data: {e}")
            return {'success': False, 'error': str(e), 'project_id': project_id}
    
    def schedule_financial_updates(self):
        """
        Scheduled function to update financial metrics every 12 hours
        """
        try:
            print("\n🕐 Running scheduled financial updates...")
            
            # Get all projects
            all_projects = self.db_manager.get_all_projects()
            
            for project in all_projects:
                project_id = project['id']
                print(f"\n📊 Processing project: {project.get('name', project_id[:8])}")
                
                # Refresh financial data for this project
                self.refresh_financial_data(project_id)
            
            print("\n✅ Scheduled updates complete")
            
        except Exception as e:
            print(f"❌ Error in scheduled financial updates: {e}")
    
    def _calculate_financial_health(self, expenses: float, revenue: float, 
                                    expense_categories: Dict) -> float:
        """
        Calculate financial health score (0-100%)
        
        Args:
            expenses: Total expenses
            revenue: Total revenue
            expense_categories: Dict containing 'budget' and expense breakdown
            
        Returns:
            Health score percentage
        """
        try:
            budget = expense_categories.get('budget', 0) if isinstance(expense_categories, dict) else 0
            
            # Check if there's ANY financial data - if not, return 0
            if budget == 0 and expenses == 0 and revenue == 0:
                return 0.0
            
            score = 0.0
            
            # Factor 1: Budget Utilization (30%)
            if budget > 0:
                utilization = (expenses / budget) * 100
                if utilization < 50:  # Under 50% - early stage or under-spending
                    score += 20
                elif utilization < 80:  # 50-80% - good progress
                    score += 30
                elif utilization < 100:  # 80-100% - nearing budget
                    score += 25
                elif utilization < 110:  # 100-110% - slightly over
                    score += 15
                else:  # > 110% - significantly over budget
                    score += 5
            else:
                score += 15  # No budget data
            
            # Factor 2: Revenue vs Expenses ratio (40%)
            if revenue > 0:
                ratio = expenses / revenue
                if ratio < 0.7:  # Expenses < 70% of revenue - excellent
                    score += 40
                elif ratio < 1.0:  # Expenses < 100% of revenue - good
                    score += 30
                elif ratio < 1.2:  # Expenses < 120% of revenue - acceptable
                    score += 20
                else:  # Expenses >= 120% of revenue - concerning
                    score += 10
            else:
                score += 20  # Neutral if no revenue data yet
            
            # Factor 3: Cash Flow Status (30%)
            net_balance = revenue - expenses
            if net_balance > 0:  # Positive cash flow
                if budget > 0 and net_balance > (budget * 0.1):  # 10%+ net margin
                    score += 30
                else:
                    score += 20
            elif net_balance == 0:  # Break-even
                score += 15
            else:  # Negative cash flow
                if budget > 0 and abs(net_balance) < (budget * 0.1):  # Small deficit
                    score += 10
                else:
                    score += 5
            
            return min(100.0, max(0.0, score))
            
        except Exception as e:
            print(f"Error calculating financial health: {e}")
            return 0.0  # No hardcoding - return 0 if calculation fails
    
    def _get_current_financial_data(self, project_id: str) -> Dict[str, Any]:
        """Get current financial data without processing"""
        try:
            # Get all current data
            financial_details = self.chroma_manager.get_financial_data('financial_details', project_id)
            transactions = self.chroma_manager.get_financial_data('transactions', project_id)
            expense_analysis = self.expense_agent.get_expense_analysis(project_id)
            revenue_analysis = self.revenue_agent.get_revenue_analysis(project_id)
            
            # Calculate BUDGET from financial_details (NOT from transactions!)
            total_budget = 0
            for detail in financial_details:
                metadata = detail.get('metadata', {})
                detail_type = metadata.get('detail_type', metadata.get('type', ''))
                
                # Count ALL budget allocations (removed category restriction)
                if detail_type in ['budget_allocation', 'budget']:
                    amount = float(metadata.get('amount', 0))
                    if amount > 0:
                        total_budget += amount
            
            # Calculate EXPENSES from transactions (only actual expense transactions with positive amounts)
            expense_transactions = [
                t for t in transactions 
                if t.get('metadata', {}).get('transaction_type') == 'expense'
                and float(t.get('metadata', {}).get('amount', 0)) > 0
            ]
            
            total_expenses = sum(
                float(t.get('metadata', {}).get('amount', 0))
                for t in expense_transactions
            )
            
            # Calculate REVENUE from transactions (only actual revenue transactions with positive amounts)
            revenue_transactions = [
                t for t in transactions 
                if t.get('metadata', {}).get('transaction_type') == 'revenue'
                and float(t.get('metadata', {}).get('amount', 0)) > 0
            ]
            
            total_revenue = sum(
                float(t.get('metadata', {}).get('amount', 0))
                for t in revenue_transactions
            )
            
            # Calculate budget utilization percentage
            budget_utilization = (total_expenses / total_budget * 100) if total_budget > 0 else 0
            
            return {
                'success': True,
                'project_id': project_id,
                'financial_details_count': len(financial_details),
                'transactions_count': len(transactions),
                'budget': total_budget,
                'total_expenses': total_expenses,
                'total_revenue': total_revenue,
                'expense_count': len(expense_transactions),
                'revenue_count': len(revenue_transactions),
                'budget_utilization': round(budget_utilization, 2),
                'expense_analysis': expense_analysis,
                'revenue_analysis': revenue_analysis,
                'financial_health': self._calculate_financial_health(
                    total_expenses, total_revenue, {'budget': total_budget}
                )
            }
            
        except Exception as e:
            print(f"Error getting current financial data: {e}")
            return {
                'success': False, 
                'error': str(e), 
                'project_id': project_id,
                'budget': 0,
                'total_expenses': 0,
                'total_revenue': 0,
                'expense_count': 0,
                'revenue_count': 0,
                'financial_health': 0.0  # No hardcoding - 0 when no data
            }
    
    def _get_last_financial_update(self, project_id: str) -> Optional[str]:
        """Get last financial update timestamp"""
        try:
            update_file = os.path.join(self.financial_data_dir, f"{project_id}_last_update.json")
            
            if os.path.exists(update_file):
                with open(update_file, 'r') as f:
                    data = json.load(f)
                    return data.get('last_update')
            
            return None
            
        except Exception as e:
            print(f"Error getting last update: {e}")
            return None
    
    def _update_last_financial_update(self, project_id: str):
        """Update last financial update timestamp"""
        try:
            update_file = os.path.join(self.financial_data_dir, f"{project_id}_last_update.json")
            
            data = {
                'project_id': project_id,
                'last_update': datetime.now().isoformat()
            }
            
            with open(update_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error updating last update: {e}")
    
    def _save_financial_results(self, project_id: str, results: Dict):
        """Save financial results to file"""
        try:
            results_file = os.path.join(
                self.financial_data_dir,
                f"{project_id}_financial_analysis.json"
            )
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            print(f"Error saving financial results: {e}")

