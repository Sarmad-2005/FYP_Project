"""
What If Scenario Simulator Agent
Worker agent for risk mitigation that fetches bottlenecks, orders them, and provides mitigation suggestions
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.chromadb_patch import chromadb


class WhatIfSimulatorAgent:
    """Worker agent for What If Scenario Simulator"""
    
    def __init__(self, chroma_manager, performance_chroma_manager=None):
        """
        Initialize What If Simulator Agent
        
        Args:
            chroma_manager: RiskChromaManager instance
            performance_chroma_manager: PerformanceChromaManager instance (for direct access in monolith mode)
        """
        self.chroma_manager = chroma_manager
        self.performance_chroma_manager = performance_chroma_manager
    
    def _get_cached_bottlenecks(self, project_id: str) -> List[Dict]:
        """Get cached enhanced bottlenecks from ChromaDB"""
        try:
            cached_data = self.chroma_manager.get_risk_data('enhanced_bottlenecks', project_id)
            if not cached_data:
                return []
            
            bottlenecks = []
            for item in cached_data:
                metadata = item.get('metadata', {})
                bottlenecks.append({
                    'id': metadata.get('bottleneck_id', ''),
                    'bottleneck': item.get('content', ''),
                    'category': metadata.get('category', 'General'),
                    'severity': metadata.get('severity', 'Medium'),
                    'impact': metadata.get('impact', 'Unknown impact'),
                    'created_at': metadata.get('created_at', ''),
                    'source_document': metadata.get('source_document', '')
                })
            return bottlenecks
        except Exception as e:
            print(f"Error retrieving cached bottlenecks: {e}")
            return []
    
    def _cache_bottlenecks(self, project_id: str, bottlenecks: List[Dict]):
        """Cache enhanced bottlenecks in ChromaDB"""
        try:
            # Clear old cache first
            # Store new bottlenecks
            data_to_store = []
            for bottleneck in bottlenecks:
                data_to_store.append({
                    'id': f"enhanced_{bottleneck['id']}",
                    'text': bottleneck.get('bottleneck', ''),
                    'metadata': {
                        'bottleneck_id': bottleneck.get('id', ''),
                        'category': bottleneck.get('category', 'General'),
                        'severity': bottleneck.get('severity', 'Medium'),
                        'impact': bottleneck.get('impact', 'Unknown impact'),
                        'source_document': bottleneck.get('source_document', '')
                    }
                })
            
            if data_to_store:
                self.chroma_manager.store_risk_data('enhanced_bottlenecks', data_to_store, project_id)
                print(f"✅ Cached {len(data_to_store)} enhanced bottlenecks")
        except Exception as e:
            print(f"Error caching bottlenecks: {e}")
    
    def fetch_project_bottlenecks(self, project_id: str, orchestrator=None, 
                                 performance_agent=None, llm_manager=None, use_cache=True) -> List[Dict]:
        """
        Fetch bottlenecks from Performance Agent and enhance impact for unknown ones
        First checks cache, then fetches fresh if needed
        
        Supports both A2A (microservice) and direct access (monolith) modes
        
        Args:
            project_id: Project identifier
            orchestrator: Orchestrator instance for A2A protocol (optional)
            performance_agent: PerformanceAgent instance for direct access (optional)
            llm_manager: LLM manager for impact enhancement (optional)
            use_cache: If True, check cache first (default: True)
            
        Returns:
            List of bottleneck dictionaries with details
        """
        try:
            # Check cache first
            if use_cache:
                cached_bottlenecks = self._get_cached_bottlenecks(project_id)
                if cached_bottlenecks:
                    print(f"✅ Retrieved {len(cached_bottlenecks)} bottlenecks from cache")
                    return cached_bottlenecks
            
            bottlenecks = []
            
            print(f"🔍 Fetching bottlenecks for project {project_id[:20]}...")
            print(f"   Performance ChromaDB available: {self.performance_chroma_manager is not None}")
            
            # ALWAYS USE DIRECT CHROMADB ACCESS - Most reliable method
            if self.performance_chroma_manager:
                try:
                    print("   📂 Direct ChromaDB access to bottlenecks collection...")
                    # Get all items from bottlenecks collection
                    from backend.chromadb_patch import chromadb
                    bottlenecks_collection = self.performance_chroma_manager.client.get_collection(
                        name='project_bottlenecks',
                        embedding_function=self.performance_chroma_manager.embedding_function
                    )
                    
                    # Query for project bottlenecks
                    results = bottlenecks_collection.query(
                        query_embeddings=[[0.0] * 384],  # Dummy query to get all
                        where={"project_id": project_id},
                        n_results=1000
                    )
                    
                    print(f"   📊 Found {len(results['ids'][0])} items in bottlenecks collection")
                    
                    # Parse results and filter
                    for i, (bottleneck_text, metadata) in enumerate(zip(
                        results['documents'][0], 
                        results['metadatas'][0]
                    )):
                        # Skip suggestions (they have a 'type' field)
                        item_type = metadata.get('type', '')
                        if item_type == 'bottleneck_suggestion':
                            print(f"   ⏭️  Skipping suggestion: {bottleneck_text[:50]}...")
                            continue
                        if item_type:  # Skip anything with a type (suggestions, tasks, etc.)
                            print(f"   ⏭️  Skipping type '{item_type}': {bottleneck_text[:50]}...")
                            continue
                        
                        # Validate bottleneck text
                        if not bottleneck_text or bottleneck_text.strip() == '' or bottleneck_text == 'Unknown Bottleneck':
                            print(f"   ⏭️  Skipping invalid bottleneck: '{bottleneck_text[:50]}'")
                            continue
                        
                        # This is a valid bottleneck
                        bottlenecks.append({
                            'id': results['ids'][0][i],
                            'bottleneck': bottleneck_text.strip(),
                            'category': metadata.get('category', 'General'),
                            'severity': metadata.get('severity', 'Medium'),
                            'impact': metadata.get('impact', 'Unknown impact'),
                            'created_at': metadata.get('created_at', ''),
                            'source_document': metadata.get('source_document', '')
                        })
                    
                    print(f"✅ Fetched {len(bottlenecks)} ACTUAL bottlenecks via ChromaDB")
                    if bottlenecks:
                        print(f"   Sample: '{bottlenecks[0].get('bottleneck', 'N/A')[:60]}...'")
                        print(f"   Categories: {set(b.get('category') for b in bottlenecks)}")
                        print(f"   Severities: {set(b.get('severity') for b in bottlenecks)}")
                except Exception as e:
                    print(f"⚠️ ChromaDB access failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # No fallback needed - ChromaDB is the primary and most reliable method
            
            if not bottlenecks:
                print(f"❌ Could not fetch bottlenecks for project {project_id}")
                return []
            
            # Enhance impact for bottlenecks with "Unknown impact"
            if llm_manager:
                bottlenecks = self._enhance_bottleneck_impacts(bottlenecks, llm_manager)
            
            # Cache the enhanced bottlenecks
            if bottlenecks:
                self._cache_bottlenecks(project_id, bottlenecks)
            
            return bottlenecks
            
        except Exception as e:
            print(f"Error fetching project bottlenecks: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _enhance_bottleneck_impacts(self, bottlenecks: List[Dict], llm_manager) -> List[Dict]:
        """
        Enhance impact for bottlenecks that have "Unknown impact"
        
        Args:
            bottlenecks: List of bottleneck dictionaries
            llm_manager: LLM manager instance
            
        Returns:
            List of bottlenecks with enhanced impacts
        """
        try:
            # Find bottlenecks with unknown impact
            unknown_impact_bottlenecks = [
                b for b in bottlenecks 
                if b.get('impact', '').lower() in ['unknown impact', 'unknown', '']
            ]
            
            if not unknown_impact_bottlenecks:
                return bottlenecks
            
            print(f"🔍 Enhancing impact for {len(unknown_impact_bottlenecks)} bottlenecks with unknown impact...")
            
            # Process in batches to avoid overwhelming the LLM
            batch_size = 5
            for i in range(0, len(unknown_impact_bottlenecks), batch_size):
                batch = unknown_impact_bottlenecks[i:i + batch_size]
                
                # Create prompt for batch
                bottleneck_list = "\n".join([
                    f"- {b['bottleneck']} (Category: {b.get('category', 'General')}, Severity: {b.get('severity', 'Medium')})"
                    for b in batch
                ])
                
                prompt = f"""You are a project risk analyst. Analyze the following bottlenecks and determine their specific impact on the project.

Bottlenecks:
{bottleneck_list}

For each bottleneck, provide a specific, concise impact description. Consider:
- Schedule/timeline impacts
- Budget/cost impacts
- Quality/technical impacts
- Resource/team impacts
- Stakeholder/communication impacts

Return ONLY a JSON object mapping bottleneck descriptions to their impacts.
Format:
{{
  "bottleneck description 1": "Specific impact description",
  "bottleneck description 2": "Specific impact description"
}}

Only return valid JSON, no additional text."""
                
                # Call LLM
                llm_response = llm_manager.simple_chat(prompt)
                
                if not llm_response.get('success'):
                    print(f"   ⚠️ LLM call failed: {llm_response.get('error', 'Unknown error')}")
                    continue
                
                response_text = llm_response.get('response', '')
                
                # Parse JSON response
                response_text = response_text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                try:
                    impact_map = json.loads(response_text)
                    
                    # Update bottlenecks with enhanced impacts
                    for bottleneck in batch:
                        bottleneck_text = bottleneck['bottleneck']
                        if bottleneck_text in impact_map:
                            bottleneck['impact'] = impact_map[bottleneck_text]
                            print(f"   ✅ Enhanced impact for: {bottleneck_text[:50]}...")
                        else:
                            # Try partial match
                            for key, value in impact_map.items():
                                if bottleneck_text.lower() in key.lower() or key.lower() in bottleneck_text.lower():
                                    bottleneck['impact'] = value
                                    print(f"   ✅ Enhanced impact (partial match) for: {bottleneck_text[:50]}...")
                                    break
                except json.JSONDecodeError as e:
                    print(f"   ⚠️ Failed to parse impact enhancement response: {e}")
                    # Continue with original impacts
            
            return bottlenecks
            
        except Exception as e:
            print(f"Error enhancing bottleneck impacts: {e}")
            import traceback
            traceback.print_exc()
            return bottlenecks
    
    def order_bottlenecks_by_priority(self, bottlenecks: List[Dict], llm_manager) -> List[Dict]:
        """
        Order bottlenecks by which will occur first using LLM
        
        Args:
            bottlenecks: List of bottleneck dicts with 'id' and 'bottleneck' (title)
            llm_manager: LLM manager instance
            
        Returns:
            List of bottlenecks with 'order_priority' field added (1 = first, 2 = second, etc.)
        """
        try:
            if not bottlenecks:
                return []
            
            # Extract only IDs and titles for LLM (to save context window)
            bottleneck_summary = [
                {'id': b['id'], 'title': b['bottleneck']}
                for b in bottlenecks
            ]
            
            # Create prompt
            prompt = f"""Analyze the following project bottlenecks and order them by which will occur first in the project timeline.

Bottlenecks:
{json.dumps(bottleneck_summary, indent=2)}

Consider factors like:
- Dependencies between bottlenecks
- Project timeline and phases
- Critical path impacts
- Resource availability constraints

Return a JSON object with the bottleneck IDs in order (first to occur = first in array).
Format: {{"ordered_ids": ["id1", "id2", "id3", ...]}}

Only return valid JSON, no additional text."""
            
            # Call LLM
            llm_response = llm_manager.simple_chat(prompt)
            
            if not llm_response.get('success'):
                print(f"⚠️ LLM call failed: {llm_response.get('error', 'Unknown error')}")
                # Return original order if LLM fails
                for i, bottleneck in enumerate(bottlenecks):
                    bottleneck['order_priority'] = i + 1
                return bottlenecks
            
            response_text = llm_response.get('response', '')
            
            # Parse JSON response (handle cases where LLM adds extra text)
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            ordered_ids = result.get('ordered_ids', [])
            
            # Add order_priority to bottlenecks
            for bottleneck in bottlenecks:
                if bottleneck['id'] in ordered_ids:
                    bottleneck['order_priority'] = ordered_ids.index(bottleneck['id']) + 1
                else:
                    bottleneck['order_priority'] = len(bottlenecks) + 1  # Put unlisted ones at end
            
            # Sort by order_priority
            ordered_bottlenecks = sorted(bottlenecks, key=lambda x: x.get('order_priority', 999))
            
            print(f"✅ Ordered {len(ordered_bottlenecks)} bottlenecks by priority")
            return ordered_bottlenecks
            
        except Exception as e:
            print(f"Error ordering bottlenecks: {e}")
            import traceback
            traceback.print_exc()
            # Return original order if LLM fails
            for i, bottleneck in enumerate(bottlenecks):
                bottleneck['order_priority'] = i + 1
            return bottlenecks
    
    def generate_graph_data(self, ordered_bottlenecks: List[Dict]) -> Dict:
        """
        Generate data structure for interactive graph visualization
        
        Args:
            ordered_bottlenecks: List of ordered bottlenecks with order_priority
            
        Returns:
            Dict with 'nodes' and 'edges' for graph visualization
        """
        try:
            nodes = []
            edges = []
            
            for bottleneck in ordered_bottlenecks:
                # Determine node color based on severity
                severity_colors = {
                    'High': {'background': '#fee2e2', 'border': '#dc2626'},  # red
                    'Medium': {'background': '#fed7aa', 'border': '#ea580c'},  # orange
                    'Low': {'background': '#fef3c7', 'border': '#d97706'}  # yellow
                }
                
                severity = bottleneck.get('severity', 'Medium')
                colors = severity_colors.get(severity, severity_colors['Medium'])
                
                node = {
                    'id': bottleneck['id'],
                    'label': bottleneck['bottleneck'],
                    'order_priority': bottleneck.get('order_priority', 0),
                    'category': bottleneck.get('category', 'General'),
                    'severity': severity,
                    'impact': bottleneck.get('impact', 'Unknown impact'),
                    'color': {
                        'background': colors['background'],
                        'border': colors['border'],
                        'highlight': {
                            'background': colors['background'],
                            'border': colors['border']
                        }
                    }
                }
                nodes.append(node)
            
            # Create edges to show ordering flow (which bottleneck comes first, then next, etc.)
            # Connect each bottleneck to the next one in the ordered sequence
            for i in range(len(ordered_bottlenecks) - 1):
                current_id = ordered_bottlenecks[i]['id']
                next_id = ordered_bottlenecks[i + 1]['id']
                
                edge = {
                    'id': f"edge_{i}",
                    'from': current_id,
                    'to': next_id,
                    'arrows': {
                        'to': {
                            'enabled': True,
                            'scaleFactor': 1.2,
                            'type': 'arrow'
                        }
                    },
                    'color': {
                        'color': '#94a3b8',
                        'highlight': '#64748b',
                        'hover': '#475569'
                    },
                    'width': 2,
                    'smooth': {
                        'type': 'curvedCW',
                        'roundness': 0.5
                    }
                }
                edges.append(edge)
            
            print(f"✅ Created {len(edges)} edges to show bottleneck ordering flow")
            
            graph_data = {
                'nodes': nodes,
                'edges': edges
            }
            
            print(f"✅ Generated graph data with {len(nodes)} nodes")
            return graph_data
            
        except Exception as e:
            print(f"Error generating graph data: {e}")
            return {'nodes': [], 'edges': []}
    
    def get_mitigation_suggestions_from_db(self, bottleneck_id: str, project_id: str) -> Optional[Dict]:
        """
        Retrieve mitigation suggestions from ChromaDB if they exist
        
        Args:
            bottleneck_id: ID of the bottleneck
            project_id: Project identifier
            
        Returns:
            Dict with mitigation_points if found, None otherwise
        """
        try:
            print(f"🔍 Looking for mitigation suggestions: bottleneck_id={bottleneck_id[:30]}..., project_id={project_id[:20]}...")
            mitigation_data = self.chroma_manager.get_risk_data('mitigation_suggestions', project_id)
            print(f"   📊 Found {len(mitigation_data)} items in mitigation_suggestions collection")
            
            # Find the most recent suggestion for this bottleneck
            # Try exact match first, then partial match (in case IDs have prefixes)
            for item in mitigation_data:
                metadata = item.get('metadata', {})
                stored_bottleneck_id = metadata.get('bottleneck_id', '')
                
                # Exact match
                if stored_bottleneck_id == bottleneck_id:
                    print(f"   ✅ Found exact match: {stored_bottleneck_id[:30]}...")
                    try:
                        # Parse the JSON string back to list
                        content = item.get('content', '[]')
                        if isinstance(content, str):
                            mitigation_points = json.loads(content)
                        else:
                            mitigation_points = content
                        
                        return {
                            'bottleneck_id': bottleneck_id,
                            'bottleneck_title': metadata.get('bottleneck_title', ''),
                            'mitigation_points': mitigation_points,
                            'generated_at': metadata.get('created_at', ''),
                            'from_cache': True
                        }
                    except json.JSONDecodeError as e:
                        print(f"   ⚠️ Error parsing JSON: {e}")
                        continue
                
                # Partial match (in case ID has prefix like "enhanced_")
                if bottleneck_id in stored_bottleneck_id or stored_bottleneck_id in bottleneck_id:
                    print(f"   ✅ Found partial match: {stored_bottleneck_id[:30]}... matches {bottleneck_id[:30]}...")
                    try:
                        content = item.get('content', '[]')
                        if isinstance(content, str):
                            mitigation_points = json.loads(content)
                        else:
                            mitigation_points = content
                        
                        return {
                            'bottleneck_id': bottleneck_id,
                            'bottleneck_title': metadata.get('bottleneck_title', ''),
                            'mitigation_points': mitigation_points,
                            'generated_at': metadata.get('created_at', ''),
                            'from_cache': True
                        }
                    except json.JSONDecodeError as e:
                        print(f"   ⚠️ Error parsing JSON: {e}")
                        continue
            
            print(f"   ⚠️ No mitigation suggestions found for bottleneck_id: {bottleneck_id[:30]}...")
            print(f"   Available bottleneck_ids in DB: {[m.get('metadata', {}).get('bottleneck_id', 'N/A')[:30] for m in mitigation_data[:5]]}")
            return None
        except Exception as e:
            print(f"❌ Error retrieving mitigation suggestions from DB: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_mitigation_suggestions(self, bottleneck_id: str, bottleneck_title: str,
                                      all_bottleneck_titles: List[str], llm_manager, 
                                      project_id: str = None, force_regenerate: bool = False) -> Dict:
        """
        Generate AI-powered mitigation suggestions for a bottleneck
        Checks DB first unless force_regenerate is True
        
        Args:
            bottleneck_id: ID of the bottleneck
            bottleneck_title: Title of the bottleneck
            all_bottleneck_titles: List of all bottleneck titles in project (for context)
            llm_manager: LLM manager instance
            project_id: Project identifier (for DB lookup)
            force_regenerate: If True, regenerate even if exists in DB
            
        Returns:
            Dict with 'mitigation_points' list
        """
        try:
            # Check DB first unless forcing regeneration
            if not force_regenerate and project_id:
                cached = self.get_mitigation_suggestions_from_db(bottleneck_id, project_id)
                if cached:
                    print(f"   ✅ Retrieved mitigation suggestions from DB for {bottleneck_id[:20]}...")
                    return cached
            
            # Create prompt
            prompt = f"""You are a project risk management expert. Analyze the following bottleneck and provide specific, actionable mitigation strategies.

Current Bottleneck: {bottleneck_title}

Other Bottlenecks in Project (for context):
{chr(10).join(f"- {title}" for title in all_bottleneck_titles)}

Provide 3-5 specific, actionable mitigation strategies for this bottleneck. Each strategy should be:
- Specific and actionable
- Practical and implementable
- Focused on addressing the root cause

Return JSON format:
{{
    "mitigation_points": [
        "Strategy 1: Specific action to take",
        "Strategy 2: Another specific action",
        "Strategy 3: Additional mitigation approach"
    ]
}}

Only return valid JSON, no additional text."""
            
            # Call LLM
            llm_response = llm_manager.simple_chat(prompt)
            
            if not llm_response.get('success'):
                return {
                    'bottleneck_id': bottleneck_id,
                    'bottleneck_title': bottleneck_title,
                    'mitigation_points': [],
                    'error': llm_response.get('error', 'Unknown error'),
                    'generated_at': datetime.now().isoformat()
                }
            
            response_text = llm_response.get('response', '')
            
            # Parse JSON response
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            mitigation_points = result.get('mitigation_points', [])
            
            # Store in ChromaDB
            project_id_for_storage = project_id or (bottleneck_id.split('_')[0] if '_' in bottleneck_id else '')
            self.chroma_manager.store_risk_data(
                'mitigation_suggestions',
                [{
                    'id': f"mitigation_{bottleneck_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'text': json.dumps(mitigation_points),
                    'metadata': {
                        'bottleneck_id': bottleneck_id,
                        'bottleneck_title': bottleneck_title
                    }
                }],
                project_id_for_storage,
                {'bottleneck_id': bottleneck_id}
            )
            
            return {
                'bottleneck_id': bottleneck_id,
                'bottleneck_title': bottleneck_title,
                'mitigation_points': mitigation_points,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating mitigation suggestions: {e}")
            import traceback
            traceback.print_exc()
            return {
                'bottleneck_id': bottleneck_id,
                'bottleneck_title': bottleneck_title,
                'mitigation_points': [],
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def get_consequences_from_db(self, bottleneck_id: str, project_id: str) -> Optional[Dict]:
        """
        Retrieve consequences from ChromaDB if they exist
        
        Args:
            bottleneck_id: ID of the bottleneck
            project_id: Project identifier
            
        Returns:
            Dict with consequence_points if found, None otherwise
        """
        try:
            print(f"🔍 Looking for consequences: bottleneck_id={bottleneck_id[:30]}..., project_id={project_id[:20]}...")
            consequence_data = self.chroma_manager.get_risk_data('consequences', project_id)
            print(f"   📊 Found {len(consequence_data)} items in consequences collection")
            
            # Find the most recent consequence for this bottleneck
            # Try exact match first, then partial match (in case IDs have prefixes)
            for item in consequence_data:
                metadata = item.get('metadata', {})
                stored_bottleneck_id = metadata.get('bottleneck_id', '')
                
                # Exact match
                if stored_bottleneck_id == bottleneck_id:
                    print(f"   ✅ Found exact match: {stored_bottleneck_id[:30]}...")
                    try:
                        # Parse the JSON string back to list
                        content = item.get('content', '[]')
                        if isinstance(content, str):
                            consequence_points = json.loads(content)
                        else:
                            consequence_points = content
                        
                        return {
                            'bottleneck_id': bottleneck_id,
                            'bottleneck_title': metadata.get('bottleneck_title', ''),
                            'consequence_points': consequence_points,
                            'generated_at': metadata.get('created_at', ''),
                            'from_cache': True
                        }
                    except json.JSONDecodeError as e:
                        print(f"   ⚠️ Error parsing JSON: {e}")
                        continue
                
                # Partial match (in case ID has prefix like "enhanced_")
                if bottleneck_id in stored_bottleneck_id or stored_bottleneck_id in bottleneck_id:
                    print(f"   ✅ Found partial match: {stored_bottleneck_id[:30]}... matches {bottleneck_id[:30]}...")
                    try:
                        content = item.get('content', '[]')
                        if isinstance(content, str):
                            consequence_points = json.loads(content)
                        else:
                            consequence_points = content
                        
                        return {
                            'bottleneck_id': bottleneck_id,
                            'bottleneck_title': metadata.get('bottleneck_title', ''),
                            'consequence_points': consequence_points,
                            'generated_at': metadata.get('created_at', ''),
                            'from_cache': True
                        }
                    except json.JSONDecodeError as e:
                        print(f"   ⚠️ Error parsing JSON: {e}")
                        continue
            
            print(f"   ⚠️ No consequences found for bottleneck_id: {bottleneck_id[:30]}...")
            print(f"   Available bottleneck_ids in DB: {[m.get('metadata', {}).get('bottleneck_id', 'N/A')[:30] for m in consequence_data[:5]]}")
            return None
        except Exception as e:
            print(f"❌ Error retrieving consequences from DB: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def analyze_consequences(self, bottleneck_id: str, bottleneck_title: str,
                            all_bottleneck_titles: List[str], llm_manager,
                            project_id: str = None, force_regenerate: bool = False) -> Dict:
        """
        Analyze consequences of a bottleneck
        Checks DB first unless force_regenerate is True
        
        Args:
            bottleneck_id: ID of the bottleneck
            bottleneck_title: Title of the bottleneck
            all_bottleneck_titles: List of all bottleneck titles in project (for context)
            llm_manager: LLM manager instance
            project_id: Project identifier (for DB lookup)
            force_regenerate: If True, regenerate even if exists in DB
            
        Returns:
            Dict with 'consequence_points' list
        """
        try:
            # Check DB first unless forcing regeneration
            if not force_regenerate and project_id:
                cached = self.get_consequences_from_db(bottleneck_id, project_id)
                if cached:
                    print(f"   ✅ Retrieved consequences from DB for {bottleneck_id[:20]}...")
                    return cached
            
            # Create prompt
            prompt = f"""You are a project risk management expert. Analyze the consequences if the following bottleneck is not addressed.

Bottleneck: {bottleneck_title}

Other Bottlenecks in Project (for context):
{chr(10).join(f"- {title}" for title in all_bottleneck_titles)}

Provide 3-5 specific consequences that could occur if this bottleneck is not mitigated. Each consequence should be:
- Specific and measurable
- Realistic and likely
- Impact-focused (schedule, budget, quality, resources)

Return JSON format:
{{
    "consequence_points": [
        "Consequence 1: Specific impact on project",
        "Consequence 2: Another specific impact",
        "Consequence 3: Additional consequence"
    ]
}}

Only return valid JSON, no additional text."""
            
            # Call LLM
            llm_response = llm_manager.simple_chat(prompt)
            
            if not llm_response.get('success'):
                return {
                    'bottleneck_id': bottleneck_id,
                    'bottleneck_title': bottleneck_title,
                    'consequence_points': [],
                    'error': llm_response.get('error', 'Unknown error'),
                    'generated_at': datetime.now().isoformat()
                }
            
            response_text = llm_response.get('response', '')
            
            # Parse JSON response
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            consequence_points = result.get('consequence_points', [])
            
            # Store in ChromaDB
            project_id_for_storage = project_id or (bottleneck_id.split('_')[0] if '_' in bottleneck_id else '')
            self.chroma_manager.store_risk_data(
                'consequences',
                [{
                    'id': f"consequence_{bottleneck_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'text': json.dumps(consequence_points),
                    'metadata': {
                        'bottleneck_id': bottleneck_id,
                        'bottleneck_title': bottleneck_title
                    }
                }],
                project_id_for_storage,
                {'bottleneck_id': bottleneck_id}
            )
            
            return {
                'bottleneck_id': bottleneck_id,
                'bottleneck_title': bottleneck_title,
                'consequence_points': consequence_points,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error analyzing consequences: {e}")
            import traceback
            traceback.print_exc()
            return {
                'bottleneck_id': bottleneck_id,
                'bottleneck_title': bottleneck_title,
                'consequence_points': [],
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }

