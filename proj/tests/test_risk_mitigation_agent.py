"""
Test file for Risk Mitigation Agent components
Tests individual components and end-to-end functionality
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import unittest
from unittest.mock import Mock, patch, MagicMock
from backend.risk_mitigation_agent.chroma_manager import RiskChromaManager
from backend.risk_mitigation_agent.agents.what_if_simulator_agent import WhatIfSimulatorAgent
from backend.risk_mitigation_agent.risk_mitigation_agent import RiskMitigationAgent
from backend.llm_manager import LLMManager
from backend.embeddings import EmbeddingsManager
from backend.database import DatabaseManager


class TestRiskChromaManager(unittest.TestCase):
    """Test RiskChromaManager"""
    
    def setUp(self):
        self.chroma_manager = RiskChromaManager()
    
    def test_initialization(self):
        """Test that RiskChromaManager initializes correctly"""
        self.assertIsNotNone(self.chroma_manager.client)
        self.assertIsNotNone(self.chroma_manager.model)
        self.assertIn('risk_bottlenecks', self.chroma_manager.collections)
        self.assertIn('mitigation_suggestions', self.chroma_manager.collections)
    
    def test_get_risk_collection(self):
        """Test getting risk collections"""
        collection = self.chroma_manager.get_risk_collection('risk_bottlenecks')
        self.assertIsNotNone(collection)
    
    def test_store_risk_data(self):
        """Test storing risk data"""
        test_data = [{
            'id': 'test_1',
            'text': 'Test bottleneck',
            'metadata': {'project_id': 'test_project', 'severity': 'High'}
        }]
        count = self.chroma_manager.store_risk_data('risk_bottlenecks', test_data, 'test_project')
        self.assertEqual(count, 1)
    
    def test_get_risk_data(self):
        """Test getting risk data"""
        # First store some data
        test_data = [{
            'id': 'test_2',
            'text': 'Test bottleneck 2',
            'metadata': {'project_id': 'test_project_2', 'severity': 'Medium'}
        }]
        self.chroma_manager.store_risk_data('risk_bottlenecks', test_data, 'test_project_2')
        
        # Then retrieve it
        data = self.chroma_manager.get_risk_data('risk_bottlenecks', 'test_project_2')
        self.assertGreaterEqual(len(data), 1)


class TestWhatIfSimulatorAgent(unittest.TestCase):
    """Test WhatIfSimulatorAgent"""
    
    def setUp(self):
        self.chroma_manager = RiskChromaManager()
        self.simulator = WhatIfSimulatorAgent(self.chroma_manager)
    
    def test_initialization(self):
        """Test that WhatIfSimulatorAgent initializes correctly"""
        self.assertIsNotNone(self.simulator.chroma_manager)
    
    @patch('backend.risk_mitigation_agent.agents.what_if_simulator_agent.PerformanceChromaManager')
    def test_fetch_bottlenecks_direct(self, mock_perf_chroma):
        """Test fetching bottlenecks via direct ChromaDB access"""
        # Mock performance chroma manager
        mock_manager = MagicMock()
        mock_manager.get_performance_data.return_value = [
            {
                'id': 'bottleneck_1',
                'content': 'Test bottleneck',
                'metadata': {
                    'category': 'resource',
                    'severity': 'High',
                    'impact': 'schedule_delay',
                    'project_id': 'test_project'
                }
            }
        ]
        self.simulator.performance_chroma_manager = mock_manager
        
        bottlenecks = self.simulator.fetch_project_bottlenecks('test_project')
        self.assertGreater(len(bottlenecks), 0)
        self.assertEqual(bottlenecks[0]['bottleneck'], 'Test bottleneck')
    
    def test_generate_graph_data(self):
        """Test graph data generation"""
        bottlenecks = [
            {
                'id': 'b1',
                'bottleneck': 'Bottleneck 1',
                'severity': 'High',
                'category': 'resource',
                'impact': 'delay',
                'order_priority': 1
            },
            {
                'id': 'b2',
                'bottleneck': 'Bottleneck 2',
                'severity': 'Medium',
                'category': 'technical',
                'impact': 'quality',
                'order_priority': 2
            }
        ]
        
        graph_data = self.simulator.generate_graph_data(bottlenecks)
        
        self.assertIn('nodes', graph_data)
        self.assertIn('edges', graph_data)
        self.assertEqual(len(graph_data['nodes']), 2)
        self.assertEqual(graph_data['nodes'][0]['id'], 'b1')
        self.assertEqual(graph_data['nodes'][0]['severity'], 'High')


class TestRiskMitigationAgent(unittest.TestCase):
    """Test RiskMitigationAgent"""
    
    def setUp(self):
        self.llm_manager = LLMManager()
        self.embeddings_manager = EmbeddingsManager()
        self.db_manager = DatabaseManager()
        self.risk_agent = RiskMitigationAgent(
            self.llm_manager,
            self.embeddings_manager,
            self.db_manager
        )
    
    def test_initialization(self):
        """Test that RiskMitigationAgent initializes correctly"""
        self.assertIsNotNone(self.risk_agent.chroma_manager)
        self.assertIsNotNone(self.risk_agent.what_if_simulator)
    
    @patch('backend.risk_mitigation_agent.risk_mitigation_agent.WhatIfSimulatorAgent')
    def test_get_risk_summary(self, mock_simulator):
        """Test getting risk summary"""
        # Mock simulator
        mock_sim = MagicMock()
        mock_sim.fetch_project_bottlenecks.return_value = [
            {'id': 'b1', 'severity': 'High'},
            {'id': 'b2', 'severity': 'Medium'},
            {'id': 'b3', 'severity': 'Low'}
        ]
        self.risk_agent.what_if_simulator = mock_sim
        
        summary = self.risk_agent.get_risk_summary('test_project')
        
        self.assertTrue(summary['success'])
        self.assertEqual(summary['total_bottlenecks'], 3)
        self.assertEqual(summary['high_severity'], 1)
        self.assertEqual(summary['medium_severity'], 1)
        self.assertEqual(summary['low_severity'], 1)
        self.assertGreater(summary['risk_score'], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for end-to-end functionality"""
    
    def setUp(self):
        self.llm_manager = LLMManager()
        self.embeddings_manager = EmbeddingsManager()
        self.db_manager = DatabaseManager()
        self.risk_agent = RiskMitigationAgent(
            self.llm_manager,
            self.embeddings_manager,
            self.db_manager
        )
    
    @unittest.skip("Requires actual project data")
    def test_end_to_end_workflow(self):
        """Test complete workflow with real project"""
        # This test requires a real project with bottlenecks
        # Skip by default, enable when testing with real data
        project_id = "test_project_id"
        
        # Get What If Simulator data
        result = self.risk_agent.get_what_if_simulator_data(project_id)
        
        self.assertIn('success', result)
        self.assertIn('bottlenecks', result)
        self.assertIn('graph_data', result)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestRiskChromaManager))
    suite.addTests(loader.loadTestsFromTestCase(TestWhatIfSimulatorAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestRiskMitigationAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 80)
    print("Risk Mitigation Agent Test Suite")
    print("=" * 80)
    print()
    
    success = run_tests()
    
    print()
    print("=" * 80)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed. Check output above.")
    print("=" * 80)
    
    sys.exit(0 if success else 1)

