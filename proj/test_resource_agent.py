"""
Test script for Resource Agent backend functionality
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# CRITICAL: Import chromadb patch FIRST before any other imports
from backend.chromadb_patch import chromadb

from backend.resource_agent.resource_agent import ResourceAgent
from backend.llm_manager import LLMManager
from backend.embeddings import EmbeddingsManager
from backend.database import DatabaseManager

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def test_resource_agent():
    """Test Resource Agent functionality"""
    
    print_section("RESOURCE AGENT BACKEND TEST")
    
    # Initialize managers
    print("🔧 Initializing managers...")
    llm_manager = LLMManager()
    embeddings_manager = EmbeddingsManager()
    db_manager = DatabaseManager()
    
    # Initialize Resource Agent
    print("🔧 Initializing Resource Agent...")
    resource_agent = ResourceAgent(llm_manager, embeddings_manager, db_manager)
    print("✅ Resource Agent initialized!\n")
    
    # Get a test project
    print("📋 Getting test project...")
    projects = db_manager.get_all_projects()
    
    if not projects:
        print("❌ No projects found. Please create a project first.")
        return
    
    test_project = projects[0]
    project_id = test_project['id']
    print(f"✅ Using project: {test_project.get('name', project_id)} (ID: {project_id})\n")
    
    # Get project documents
    documents = db_manager.get_project_documents(project_id)
    if not documents:
        print("❌ No documents found in project. Please upload a document first.")
        return
    
    document_id = documents[0]['id']
    print(f"✅ Using document: {documents[0].get('filename', document_id)} (ID: {document_id})\n")
    
    # Test 1: First Time Generation
    print_section("TEST 1: First Time Generation")
    try:
        result = resource_agent.first_time_generation(project_id, document_id)
        print(f"✅ First time generation completed!")
        print(f"   Tasks Analyzed: {result.get('task_analysis', {}).get('count', 0)}")
        print(f"   Dependencies Created: {result.get('dependencies', {}).get('count', 0)}")
        print(f"   Critical Path Length: {result.get('critical_path', {}).get('path_length', 0)}")
        print(f"   Overall Success: {result.get('overall_success', False)}")
    except Exception as e:
        print(f"❌ Error in first time generation: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Get Task Analysis
    print_section("TEST 2: Get Task Analysis")
    try:
        tasks = resource_agent.get_task_analysis(project_id)
        print(f"✅ Retrieved {len(tasks)} task analyses")
        if tasks:
            sample = tasks[0]
            print(f"   Sample task: {sample.get('task_name', 'Unknown')}")
            print(f"   Priority: {sample.get('priority', 'N/A')}")
            print(f"   Complexity: {sample.get('complexity', 'N/A')}")
            print(f"   Estimated Time: {sample.get('estimated_time_hours', 0)} hours")
    except Exception as e:
        print(f"❌ Error getting task analysis: {e}")
    
    # Test 3: Get Dependencies
    print_section("TEST 3: Get Task Dependencies")
    try:
        dependencies = resource_agent.get_task_dependencies(project_id)
        print(f"✅ Retrieved {len(dependencies)} dependencies")
        if dependencies:
            sample = dependencies[0]
            print(f"   Sample dependency: {sample.get('task_name', 'Unknown')}")
            depends_on = sample.get('depends_on', [])
            if isinstance(depends_on, str):
                try:
                    depends_on = json.loads(depends_on)
                except:
                    depends_on = []
            print(f"   Depends on: {len(depends_on)} tasks")
    except Exception as e:
        print(f"❌ Error getting dependencies: {e}")
    
    # Test 4: Get Critical Path
    print_section("TEST 4: Get Critical Path")
    try:
        critical_path = resource_agent.get_critical_path(project_id)
        if critical_path:
            path_tasks = critical_path.get('path_tasks', [])
            duration = critical_path.get('total_duration_hours', 0)
            print(f"✅ Critical path retrieved!")
            print(f"   Path Length: {len(path_tasks)} tasks")
            print(f"   Total Duration: {duration:.1f} hours ({duration/8:.1f} days)")
        else:
            print("⚠️ No critical path found")
    except Exception as e:
        print(f"❌ Error getting critical path: {e}")
    
    # Test 5: Work Team Management
    print_section("TEST 5: Work Team Management")
    try:
        # Add team member
        result = resource_agent.resource_optimization_agent.add_work_team_member(
            project_id,
            "Test Person",
            "person"
        )
        if result.get('success'):
            team_member_id = result.get('team_member_id')
            print(f"✅ Added team member: {result.get('name')} (ID: {team_member_id})")
            
            # Get work team
            work_team = resource_agent.get_work_team(project_id)
            print(f"✅ Retrieved {len(work_team)} work team members")
            
            # Update resource assignment
            update_result = resource_agent.resource_optimization_agent.update_resource_assignment(
                team_member_id,
                50000.0
            )
            if update_result:
                print(f"✅ Updated resource assignment: PKR 50,000")
            
            # Get updated work team
            work_team_updated = resource_agent.get_work_team(project_id)
            updated_member = next((m for m in work_team_updated if m['id'] == team_member_id), None)
            if updated_member:
                print(f"✅ Verified update: PKR {updated_member.get('assigned_resources', 0):,.2f}")
        else:
            print(f"❌ Failed to add team member: {result.get('error')}")
    except Exception as e:
        print(f"❌ Error in work team management: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 6: Financial Summary
    print_section("TEST 6: Get Financial Summary")
    try:
        financial_summary = resource_agent.get_financial_summary(project_id)
        if financial_summary.get('success'):
            print(f"✅ Financial summary retrieved!")
            print(f"   Budget: PKR {financial_summary.get('budget', 0):,.2f}")
            print(f"   Expenses: PKR {financial_summary.get('expenses', 0):,.2f}")
            print(f"   Revenue: PKR {financial_summary.get('revenue', 0):,.2f}")
            print(f"   Available: PKR {financial_summary.get('available', 0):,.2f}")
        else:
            print(f"⚠️ Financial summary not available: {financial_summary.get('error')}")
    except Exception as e:
        print(f"❌ Error getting financial summary: {e}")
    
    # Test 7: Get Current Resource Data
    print_section("TEST 7: Get Current Resource Data")
    try:
        current_data = resource_agent._get_current_resource_data(project_id)
        if current_data.get('success'):
            print(f"✅ Current resource data retrieved!")
            print(f"   Tasks Analyzed: {current_data.get('tasks_analyzed_count', 0)}")
            print(f"   Dependencies: {current_data.get('dependencies_count', 0)}")
            print(f"   Critical Path Length: {current_data.get('critical_path_length', 0)}")
            print(f"   Work Team Count: {current_data.get('work_team_count', 0)}")
        else:
            print(f"⚠️ Current data not available: {current_data.get('error')}")
    except Exception as e:
        print(f"❌ Error getting current resource data: {e}")
    
    print_section("TEST COMPLETE")
    print("✅ All tests completed!")
    print(f"📊 Project ID: {project_id}")
    print(f"📄 Document ID: {document_id}")

if __name__ == '__main__':
    try:
        test_resource_agent()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

