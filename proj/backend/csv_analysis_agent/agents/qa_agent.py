"""
QA Agent
Worker agent for question answering using full LangChain ReAct agent
"""

from typing import Dict, Any, List, Optional
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from ..utils.langchain_wrapper import LLMManagerWrapper


class QAAgent:
    """Worker agent for answering questions about CSV and financial data using LangChain"""
    
    def __init__(self, llm_manager, tools: list):
        """
        Initialize QA Agent with full LangChain support
        
        Args:
            llm_manager: LLMManager instance
            tools: List of LangChain tools
        """
        self.llm_manager = llm_manager
        self.tools = tools
        
        # Wrap LLMManager for LangChain compatibility
        self.langchain_llm = LLMManagerWrapper(llm_manager)
        
        # Create ReAct agent
        self.agent_executor = self._create_agent_executor()
    
    def _create_agent_executor(self) -> AgentExecutor:
        """Create LangChain ReAct agent executor"""
        
        # Define the ReAct prompt template - ULTRA STRICT FORMAT
        template = """You answer CSV and financial data questions using tools.

{tools}

STRICT FORMAT - ONE STEP AT A TIME:

Question: {input}
Thought: I need to use a tool
Action: [ONLY ONE tool name from: {tool_names}]
Action Input: {{"key": "value"}}

DO NOT WRITE "Final Answer" AFTER ACTION!
WAIT FOR OBSERVATION FIRST!

After observation, you can either:
1. Use another tool (write Thought + Action + Input)
2. Give final answer (write ONLY "Final Answer: [answer]")

NEVER EVER write both Action and Final Answer together!

{agent_scratchpad}"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "agent_scratchpad", "tools", "tool_names"]
        )
        
        # Create ReAct agent
        agent = create_react_agent(
            llm=self.langchain_llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create agent executor with strict limits
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,  # Reduced to prevent long loops
            max_execution_time=30,  # 30 second timeout
            return_intermediate_steps=True,  # Capture reasoning steps
            early_stopping_method="force"  # Use supported early stopping method
        )
    
    def answer_question(
        self,
        question: str,
        csv_path: str,
        selected_cells: Optional[List[Dict]] = None,
        financial_context: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer a question about CSV data using LangChain ReAct agent
        
        Args:
            question: User's question
            csv_path: Path to CSV file
            selected_cells: Optional list of selected cell data
            financial_context: Optional financial context string
            project_id: Optional project identifier for financial tools
            
        Returns:
            Answer with sources, reasoning, and agent thoughts
        """
        try:
            # Build enriched question with context
            enriched_question = self._build_enriched_question(
                question,
                csv_path,
                selected_cells,
                financial_context,
                project_id
            )
            
            # Run LangChain agent
            result = self.agent_executor.invoke({"input": enriched_question})
            
            # Extract answer
            answer = result.get('output', 'Unable to generate answer')
            
            # Check if agent hit limits
            if 'Agent stopped' in answer or 'iteration limit' in answer.lower():
                # Try to extract any partial answer from intermediate steps
                intermediate_steps = result.get('intermediate_steps', [])
                if intermediate_steps:
                    # Get the last thought/observation
                    last_step = intermediate_steps[-1]
                    if len(last_step) > 1:
                        last_observation = str(last_step[1])
                        answer = f"Based on the data analysis: {last_observation}"
            
            # Extract intermediate steps (the agent's thinking process)
            intermediate_steps = result.get('intermediate_steps', [])
            
            # Parse reasoning chain
            reasoning_chain = self._parse_reasoning_chain(intermediate_steps)
            
            # Extract tools used
            tools_used = self._extract_tools_used(intermediate_steps)
            
            # Build sources
            sources = self._build_sources(csv_path, selected_cells, financial_context, tools_used)
            
            return {
                'success': True,
                'answer': answer,
                'question': question,
                'sources': sources,
                'agent_chain': reasoning_chain,
                'tools_used': list(set(tools_used)),  # Unique tools
                'reasoning_steps': intermediate_steps  # Raw steps for detailed display
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Provide better error messages for common issues
            if 'iteration limit' in error_msg.lower() or 'max_iterations' in error_msg.lower():
                error_msg = "The question was too complex and required too many steps. Try asking a simpler or more specific question."
            elif 'timeout' in error_msg.lower() or 'time limit' in error_msg.lower():
                error_msg = "The analysis took too long. Try asking a simpler question or selecting fewer data rows."
            elif 'parsing' in error_msg.lower():
                error_msg = "I had trouble understanding the data format. Please try rephrasing your question."
            
            return {
                'success': False,
                'error': error_msg,
                'answer': f"⚠️ {error_msg}",
                'agent_chain': [f"Error: {error_msg}"],
                'sources': []
            }
    
    def _build_enriched_question(
        self,
        question: str,
        csv_path: str,
        selected_cells: Optional[List[Dict]] = None,
        financial_context: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> str:
        """Build question with additional context for the agent"""
        
        parts = [f"{question}"]
        
        # Add CSV path for tools to use
        parts.append(f"\n\nIMPORTANT CONTEXT:")
        parts.append(f"\n- CSV file location: {csv_path}")
        
        # Add project_id for financial tools
        if project_id:
            parts.append(f"\n- Project ID: {project_id} (REQUIRED for financial_data, transactions, and anomalies tools)")
        
        # Add selection info if provided
        if selected_cells and len(selected_cells) > 0:
            parts.append(f"\n- User has selected {len(selected_cells)} rows from the CSV.")
            parts.append(f"\n- Selected cells data: {selected_cells}")
        
        # Add financial context if available
        if financial_context:
            parts.append(f"\n- Project financial context: {financial_context}")
        
        return "".join(parts)
    
    def _parse_reasoning_chain(self, intermediate_steps: List) -> List[str]:
        """
        Parse intermediate steps into human-readable reasoning chain
        
        Args:
            intermediate_steps: List of (AgentAction, observation) tuples
            
        Returns:
            List of reasoning step descriptions
        """
        reasoning = []
        
        try:
            for i, step in enumerate(intermediate_steps, 1):
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    
                    # Extract thought from action log
                    if hasattr(action, 'log'):
                        log = action.log
                        if 'Thought:' in log:
                            thought_text = log.split('Thought:')[-1].split('Action:')[0].strip()
                            if thought_text and len(thought_text) > 0:
                                reasoning.append(f"💭 Step {i}: {thought_text[:200]}")
                    
                    # Add action taken
                    if hasattr(action, 'tool'):
                        tool_name = action.tool
                        reasoning.append(f"🔧 Used tool: {tool_name}")
                        
                        # Add observation summary (clean it up)
                        obs_str = str(observation)
                        # Skip error observations in display
                        if not obs_str.startswith('Error:') and not obs_str.startswith('Context Building Error'):
                            obs_preview = obs_str[:150] + '...' if len(obs_str) > 150 else obs_str
                            reasoning.append(f"✅ Got result")
        except Exception as e:
            print(f"⚠️ Error parsing reasoning chain: {e}")
        
        if not reasoning:
            reasoning.append("✅ Analyzed selected data and generated answer")
        
        return reasoning
    
    def _extract_tools_used(self, intermediate_steps: List) -> List[str]:
        """Extract list of tools used by the agent"""
        tools_used = []
        
        try:
            for step in intermediate_steps:
                if len(step) >= 1:
                    action = step[0]
                    if hasattr(action, 'tool'):
                        tool_name = action.tool
                        # Filter out error/invalid tool names
                        if tool_name and not tool_name.startswith('_') and tool_name != 'Exception':
                            tools_used.append(tool_name)
        except Exception as e:
            print(f"⚠️ Error extracting tools: {e}")
        
        # Return unique tools only
        return list(set(tools_used)) if tools_used else ['Selected cell analysis']
    
    def _build_sources(
        self,
        csv_path: str,
        selected_cells: Optional[List[Dict]],
        financial_context: Optional[str],
        tools_used: List[str]
    ) -> List[Dict]:
        """Build sources list based on what was accessed"""
        sources = []
        
        # CSV source
        if any(tool in ['csv_read', 'CSVReadTool'] for tool in tools_used):
            sources.append({
                'type': 'csv_data',
                'description': f'CSV file data from {csv_path.split("/")[-1]}',
                'icon': '📄'
            })
        
        # Selected cells
        if selected_cells and len(selected_cells) > 0:
            sources.append({
                'type': 'selection',
                'description': f'{len(selected_cells)} selected rows',
                'icon': '✓'
            })
        
        # Financial data sources
        if any(tool in ['financial_data', 'FinancialDataTool'] for tool in tools_used):
            sources.append({
                'type': 'financial_data',
                'description': 'Project budget, expenses, revenue, and health metrics',
                'icon': '💰'
            })
        
        if any(tool in ['transactions', 'TransactionTool'] for tool in tools_used):
            sources.append({
                'type': 'transactions',
                'description': 'Project transaction history',
                'icon': '💳'
            })
        
        if any(tool in ['anomalies', 'AnomalyTool'] for tool in tools_used):
            sources.append({
                'type': 'anomalies',
                'description': 'Anomaly detection results',
                'icon': '⚠️'
            })
        
        # Calculations
        if any(tool in ['calculate', 'CalculationTool'] for tool in tools_used):
            sources.append({
                'type': 'calculation',
                'description': 'Mathematical calculations performed',
                'icon': '🔢'
            })
        
        # Context building
        if any(tool in ['build_context', 'ContextTool'] for tool in tools_used):
            sources.append({
                'type': 'context',
                'description': 'Data context analysis',
                'icon': '📋'
            })
        
        return sources
