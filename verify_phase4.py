"""Quick verification of Phase 4 fixes."""
from backend.csv_analysis_agent.tools.financial_tools import FinancialDataTool, TransactionTool, AnomalyTool
from backend.csv_analysis_agent.agents.data_context_agent import DataContextAgent
from backend.a2a_router.router import A2ARouter
from backend.financial_agent.agents.anomaly_detection_agent import AnomalyDetectionAgent
from backend.financial_agent.chroma_manager import FinancialChromaManager

router = A2ARouter()
chroma_manager = FinancialChromaManager()
anomaly_agent = AnomalyDetectionAgent(chroma_manager)

print("Testing FinancialDataTool...")
tool1 = FinancialDataTool(router)
assert hasattr(tool1, 'a2a_router')
assert not hasattr(tool1, 'financial_interface')
print("✓ FinancialDataTool OK")

print("Testing TransactionTool...")
tool2 = TransactionTool(router)
assert hasattr(tool2, 'a2a_router')
assert not hasattr(tool2, 'financial_interface')
print("✓ TransactionTool OK")

print("Testing AnomalyTool...")
tool3 = AnomalyTool(a2a_router=router, anomaly_agent=anomaly_agent)
assert hasattr(tool3, 'a2a_router')
print("✓ AnomalyTool OK")

print("Testing DataContextAgent...")
agent = DataContextAgent(router, anomaly_agent)
assert hasattr(agent, 'a2a_router')
assert not hasattr(agent, 'financial_interface')
print("✓ DataContextAgent OK")

print("\n✓ All Phase 4 fixes verified!")
