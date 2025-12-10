"""
Risk Mitigation Agent - Main Coordinator
Manages risk analysis, prediction, and mitigation strategies for projects
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from .agents.what_if_simulator_agent import WhatIfSimulatorAgent
from .chroma_manager import RiskChromaManager


class RiskMitigationAgent:
    """Main Risk Mitigation Agent coordinator"""
    
    def __init__(self, llm_manager, embeddings_manager, db_manager, orchestrator=None, 
                 performance_agent=None, performance_chroma_manager=None):
        """
        Initialize Risk Mitigation Agent
        
        Args:
            llm_manager: LLM manager instance
            embeddings_manager: Embeddings manager instance
            db_manager: Database manager instance
            orchestrator: Orchestrator for A2A protocol (optional)
            performance_agent: PerformanceAgent instance for direct access (optional)
            performance_chroma_manager: PerformanceChromaManager for direct ChromaDB access (optional)
        """
        self.llm_manager = llm_manager
        self.embeddings_manager = embeddings_manager
        self.db_manager = db_manager
        self.orchestrator = orchestrator
        
        # Initialize centralized ChromaDB manager
        self.chroma_manager = RiskChromaManager()
        
        # Initialize worker agent
        self.what_if_simulator = WhatIfSimulatorAgent(
            self.chroma_manager,
            performance_chroma_manager=performance_chroma_manager
        )
        
        # Store references for direct access
        self.performance_agent = performance_agent
        
        # Risk data storage
        self.risk_data_dir = 'data/risk_mitigation'
        self._ensure_risk_data_directory()
    
    def _ensure_risk_data_directory(self):
        """Create risk data directory if it doesn't exist"""
        if not os.path.exists(self.risk_data_dir):
            os.makedirs(self.risk_data_dir)
    
    def initialize_risk_analysis(self, project_id: str) -> Dict[str, Any]:
        """
        First-time initialization routine for Risk Mitigation Dashboard
        
        This method:
        1. Fetches bottlenecks from Performance Agent
        2. Enhances impacts for bottlenecks with "Unknown impact" using LLM
        3. Orders bottlenecks by priority (which will occur first)
        4. Generates ALL mitigation suggestions for all bottlenecks
        5. Generates ALL consequences for all bottlenecks
        6. Stores everything in ChromaDB
        
        Note: Risk Mitigation Agent doesn't extract data itself - it reads from Performance Agent.
        This initialization ensures bottlenecks have proper impacts, are ordered, and all suggestions/consequences are pre-generated.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with initialization results
        """
        try:
            print(f"\n{'='*80}")
            print(f"🔮 RISK MITIGATION FIRST-TIME GENERATION - Project: {project_id}")
            print(f"{'='*80}\n")
            
            # Step 1: Fetch bottlenecks (this also enhances impacts automatically)
            print("📍 STEP 1/5: Fetching & Enhancing Bottlenecks...")
            bottlenecks = self.what_if_simulator.fetch_project_bottlenecks(
                project_id,
                orchestrator=self.orchestrator,
                performance_agent=self.performance_agent,
                llm_manager=self.llm_manager,
                use_cache=False  # Force fresh fetch during first-time generation
            )
            
            if not bottlenecks:
                return {
                    'success': False,
                    'error': 'No bottlenecks found. Run Performance Agent first to extract bottlenecks.',
                    'bottlenecks_count': 0
                }
            
            print(f"   ✅ Found {len(bottlenecks)} bottlenecks")
            
            # Step 2: Order bottlenecks by priority
            print("\n📍 STEP 2/5: Ordering Bottlenecks by Priority...")
            ordered_bottlenecks = self.what_if_simulator.order_bottlenecks_by_priority(
                bottlenecks,
                self.llm_manager
            )
            print(f"   ✅ Ordered {len(ordered_bottlenecks)} bottlenecks")
            
            # Step 3: Store ordering for future use
            print("\n📍 STEP 3/5: Storing Bottleneck Ordering...")
            self.chroma_manager.store_risk_data(
                'ordering',
                [{
                    'id': f"ordering_{project_id}",
                    'text': json.dumps([b['id'] for b in ordered_bottlenecks]),
                    'metadata': {
                        'project_id': project_id,
                        'ordered_count': len(ordered_bottlenecks)
                    }
                }],
                project_id
            )
            print(f"   ✅ Stored ordering data")
            
            # Step 4: Generate ALL mitigation suggestions
            print("\n📍 STEP 4/5: Generating Mitigation Suggestions for All Bottlenecks...")
            all_bottleneck_titles = [b['bottleneck'] for b in bottlenecks]
            suggestions_generated = 0
            for i, bottleneck in enumerate(ordered_bottlenecks, 1):
                try:
                    print(f"   [{i}/{len(ordered_bottlenecks)}] Generating suggestions for: {bottleneck['bottleneck'][:50]}...")
                    self.what_if_simulator.generate_mitigation_suggestions(
                        bottleneck['id'],
                        bottleneck['bottleneck'],
                        all_bottleneck_titles,
                        self.llm_manager,
                        project_id=project_id,
                        force_regenerate=True  # Force generation during first-time
                    )
                    suggestions_generated += 1
                except Exception as e:
                    print(f"   ⚠️ Error generating suggestions for {bottleneck['id']}: {e}")
            print(f"   ✅ Generated {suggestions_generated}/{len(ordered_bottlenecks)} mitigation suggestions")
            
            # Step 5: Generate ALL consequences
            print("\n📍 STEP 5/5: Generating Consequences for All Bottlenecks...")
            consequences_generated = 0
            for i, bottleneck in enumerate(ordered_bottlenecks, 1):
                try:
                    print(f"   [{i}/{len(ordered_bottlenecks)}] Analyzing consequences for: {bottleneck['bottleneck'][:50]}...")
                    self.what_if_simulator.analyze_consequences(
                        bottleneck['id'],
                        bottleneck['bottleneck'],
                        all_bottleneck_titles,
                        self.llm_manager,
                        project_id=project_id,
                        force_regenerate=True  # Force generation during first-time
                    )
                    consequences_generated += 1
                except Exception as e:
                    print(f"   ⚠️ Error analyzing consequences for {bottleneck['id']}: {e}")
            print(f"   ✅ Generated {consequences_generated}/{len(ordered_bottlenecks)} consequence analyses")
            
            print(f"\n{'='*80}")
            print(f"✅ RISK MITIGATION FIRST-TIME GENERATION COMPLETE")
            print(f"   Bottlenecks: {len(bottlenecks)}")
            print(f"   High Severity: {sum(1 for b in bottlenecks if b.get('severity') in ['High', 'Critical'])}")
            print(f"   Mitigation Suggestions: {suggestions_generated}")
            print(f"   Consequences: {consequences_generated}")
            print(f"{'='*80}\n")
            
            return {
                'success': True,
                'project_id': project_id,
                'bottlenecks_count': len(bottlenecks),
                'ordered_bottlenecks_count': len(ordered_bottlenecks),
                'high_severity_count': sum(1 for b in bottlenecks if b.get('severity') in ['High', 'Critical']),
                'suggestions_generated': suggestions_generated,
                'consequences_generated': consequences_generated,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error in initialize_risk_analysis: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'bottlenecks_count': 0
            }
    
    def check_generation_status(self, project_id: str) -> Dict[str, Any]:
        """
        Check if first-time generation has been run for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with has_data boolean
        """
        try:
            ordering_data = self.chroma_manager.get_risk_data('ordering', project_id)
            cached_bottlenecks = self.what_if_simulator._get_cached_bottlenecks(project_id)
            
            has_data = bool(ordering_data and cached_bottlenecks)
            
            return {
                'success': True,
                'has_data': has_data,
                'project_id': project_id
            }
        except Exception as e:
            print(f"❌ Error checking generation status: {e}")
            return {
                'success': False,
                'has_data': False,
                'error': str(e)
            }
    
    def get_what_if_simulator_data(self, project_id: str) -> Dict[str, Any]:
        """
        Get What If Simulator data (bottlenecks + graph)
        Retrieves from DB if available, otherwise generates on-demand
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with bottlenecks, ordered_bottlenecks, and graph_data
        """
        try:
            print(f"\n{'='*80}")
            print(f"🔮 WHAT IF SIMULATOR - Project: {project_id}")
            print(f"{'='*80}\n")
            
            # Retrieve cached bottlenecks ONLY (no generation)
            print("📍 STEP 1/3: Retrieving Cached Bottlenecks...")
            cached_bottlenecks = self.what_if_simulator._get_cached_bottlenecks(project_id)
            
            if not cached_bottlenecks:
                print("   ⚠️ No cached bottlenecks found. User must run first-time generation.")
                return {
                    'success': False,
                    'error': 'No data available. Please run first-time generation.',
                    'bottlenecks': [],
                    'ordered_bottlenecks': [],
                    'graph_data': {'nodes': [], 'edges': []}
                }
            
            bottlenecks = cached_bottlenecks
            print(f"   ✅ Retrieved {len(bottlenecks)} cached bottlenecks")
            
            # Check if ordering exists in DB
            print("\n📍 STEP 2/3: Checking for Existing Ordering...")
            ordering_data = self.chroma_manager.get_risk_data('ordering', project_id)
            ordered_bottlenecks = None
            
            if ordering_data:
                try:
                    # Get the ordering entry
                    ordering_entry = ordering_data[0]  # Should only be one per project
                    ordered_ids = json.loads(ordering_entry.get('content', '[]'))
                    
                    # Create a map of bottleneck IDs to bottleneck objects
                    bottleneck_map = {b['id']: b for b in bottlenecks}
                    
                    # Reorder bottlenecks according to stored ordering
                    ordered_bottlenecks = []
                    for bid in ordered_ids:
                        if bid in bottleneck_map:
                            ordered_bottlenecks.append(bottleneck_map[bid])
                    
                    # Add any bottlenecks not in the ordering (new ones)
                    for b in bottlenecks:
                        if b['id'] not in ordered_ids:
                            ordered_bottlenecks.append(b)
                    
                    print(f"   ✅ Retrieved ordering from DB ({len(ordered_bottlenecks)} bottlenecks)")
                except Exception as e:
                    print(f"   ⚠️ Error retrieving ordering from DB: {e}, generating new ordering...")
                    ordered_bottlenecks = None
            
            # If no ordering in DB, return error (user must run first-time generation)
            if not ordered_bottlenecks:
                print("   ⚠️ No ordering found in DB. User must run first-time generation.")
                return {
                    'success': False,
                    'error': 'No ordering data. Please run first-time generation.',
                    'bottlenecks': [],
                    'ordered_bottlenecks': [],
                    'graph_data': {'nodes': [], 'edges': []}
                }
            
            # Generate graph data
            print("\n📍 STEP 3/3: Generating Graph Data...")
            graph_data = self.what_if_simulator.generate_graph_data(ordered_bottlenecks)
            print(f"   ✅ Generated graph with {len(graph_data['nodes'])} nodes")
            
            print(f"\n{'='*80}")
            print(f"✅ WHAT IF SIMULATOR DATA READY")
            print(f"{'='*80}\n")
            
            return {
                'success': True,
                'project_id': project_id,
                'bottlenecks': bottlenecks,
                'ordered_bottlenecks': ordered_bottlenecks,
                'graph_data': graph_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error in get_what_if_simulator_data: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'bottlenecks': [],
                'ordered_bottlenecks': [],
                'graph_data': {'nodes': [], 'edges': []}
            }
    
    def get_mitigation_suggestions(self, project_id: str, bottleneck_id: str) -> Dict[str, Any]:
        """
        Get mitigation suggestions for a bottleneck
        Retrieves from DB if available, otherwise generates on-demand
        
        Args:
            project_id: Project identifier
            bottleneck_id: Bottleneck identifier
            
        Returns:
            Dict with mitigation_points
        """
        try:
            # Try to get from DB first
            cached = self.what_if_simulator.get_mitigation_suggestions_from_db(bottleneck_id, project_id)
            if cached:
                print(f"✅ Retrieved mitigation suggestions from DB for {bottleneck_id[:20]}...")
                return {
                    'success': True,
                    'project_id': project_id,
                    'bottleneck_id': bottleneck_id,
                    **cached
                }
            
            # If not in DB, generate it (shouldn't happen if first-time generation was run)
            print(f"⚠️ Mitigation suggestions not found in DB, generating on-demand...")
            
            # Get bottleneck details
            bottlenecks = self.what_if_simulator.fetch_project_bottlenecks(
                project_id,
                orchestrator=self.orchestrator,
                performance_agent=self.performance_agent,
                llm_manager=self.llm_manager
            )
            
            # Find the specific bottleneck
            bottleneck = next((b for b in bottlenecks if b['id'] == bottleneck_id), None)
            if not bottleneck:
                return {
                    'success': False,
                    'error': 'Bottleneck not found',
                    'mitigation_points': []
                }
            
            # Get all bottleneck titles for context
            all_bottleneck_titles = [b['bottleneck'] for b in bottlenecks]
            
            # Generate mitigation suggestions
            result = self.what_if_simulator.generate_mitigation_suggestions(
                bottleneck_id,
                bottleneck['bottleneck'],
                all_bottleneck_titles,
                self.llm_manager,
                project_id=project_id
            )
            
            return {
                'success': True,
                'project_id': project_id,
                'bottleneck_id': bottleneck_id,
                **result
            }
            
        except Exception as e:
            print(f"Error getting mitigation suggestions: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'mitigation_points': []
            }
    
    def get_consequences(self, project_id: str, bottleneck_id: str) -> Dict[str, Any]:
        """
        Get consequences for a bottleneck
        Retrieves from DB if available, otherwise generates on-demand
        
        Args:
            project_id: Project identifier
            bottleneck_id: Bottleneck identifier
            
        Returns:
            Dict with consequence_points
        """
        try:
            # Try to get from DB first
            cached = self.what_if_simulator.get_consequences_from_db(bottleneck_id, project_id)
            if cached:
                print(f"✅ Retrieved consequences from DB for {bottleneck_id[:20]}...")
                return {
                    'success': True,
                    'project_id': project_id,
                    'bottleneck_id': bottleneck_id,
                    **cached
                }
            
            # If not in DB, generate it (shouldn't happen if first-time generation was run)
            print(f"⚠️ Consequences not found in DB, generating on-demand...")
            
            # Get bottleneck details
            bottlenecks = self.what_if_simulator.fetch_project_bottlenecks(
                project_id,
                orchestrator=self.orchestrator,
                performance_agent=self.performance_agent,
                llm_manager=self.llm_manager
            )
            
            # Find the specific bottleneck
            bottleneck = next((b for b in bottlenecks if b['id'] == bottleneck_id), None)
            if not bottleneck:
                return {
                    'success': False,
                    'error': 'Bottleneck not found',
                    'consequence_points': []
                }
            
            # Get all bottleneck titles for context
            all_bottleneck_titles = [b['bottleneck'] for b in bottlenecks]
            
            # Analyze consequences
            result = self.what_if_simulator.analyze_consequences(
                bottleneck_id,
                bottleneck['bottleneck'],
                all_bottleneck_titles,
                self.llm_manager,
                project_id=project_id
            )
            
            return {
                'success': True,
                'project_id': project_id,
                'bottleneck_id': bottleneck_id,
                **result
            }
            
        except Exception as e:
            print(f"Error getting consequences: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'consequence_points': []
            }
    
    def get_risk_summary(self, project_id: str) -> Dict[str, Any]:
        """
        Get risk summary for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with risk metrics and summary
        """
        try:
            # Get cached bottlenecks ONLY (no generation)
            cached_bottlenecks = self.what_if_simulator._get_cached_bottlenecks(project_id)
            
            if not cached_bottlenecks:
                return {
                    'success': False,
                    'error': 'No data available. Please run first-time generation.',
                    'total_bottlenecks': 0,
                    'high_severity': 0,
                    'medium_severity': 0,
                    'low_severity': 0,
                    'risk_score': 0.0,
                    'last_updated': datetime.now().isoformat()
                }
            
            bottlenecks = cached_bottlenecks
            
            # Calculate risk metrics
            total_bottlenecks = len(bottlenecks)
            # Count High and Critical as high severity
            high_severity = sum(1 for b in bottlenecks if b.get('severity') in ['High', 'Critical'])
            medium_severity = sum(1 for b in bottlenecks if b.get('severity') == 'Medium')
            low_severity = sum(1 for b in bottlenecks if b.get('severity') == 'Low')
            
            # Calculate risk score (weighted by severity)
            # Formula: (High×4 + Critical×4 + Medium×2 + Low×1) / (total × 4) × 100
            # This gives a score from 0-100% where:
            # - All High/Critical = 100%
            # - All Medium = 50%
            # - All Low = 25%
            risk_score = 0.0
            if total_bottlenecks > 0:
                # Count Critical separately for weighting (Critical = 4, High = 3, Medium = 2, Low = 1)
                critical_count = sum(1 for b in bottlenecks if b.get('severity') == 'Critical')
                high_only_count = sum(1 for b in bottlenecks if b.get('severity') == 'High')
                
                # Weighted calculation: Critical×4, High×3, Medium×2, Low×1
                total_weighted_score = (critical_count * 4) + (high_only_count * 3) + (medium_severity * 2) + (low_severity * 1)
                max_possible_score = total_bottlenecks * 4  # If all were Critical
                risk_score = (total_weighted_score / max_possible_score) * 100
            
            return {
                'success': True,
                'project_id': project_id,
                'total_bottlenecks': total_bottlenecks,
                'high_severity': high_severity,
                'medium_severity': medium_severity,
                'low_severity': low_severity,
                'risk_score': round(risk_score, 2),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting risk summary: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_bottlenecks': 0,
                'risk_score': 0.0
            }

