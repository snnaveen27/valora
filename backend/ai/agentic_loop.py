"""
Agentic Loop - Opus-inspired iterative reasoning system
Implements: Think → Act → Observe → Reflect → loop
"""

from typing import Dict, List, Any, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio
import time
import logging

from .tools_registry import ToolRegistry, get_tool_registry
from .agentic_memory import AgenticMemory, get_agentic_memory
from .self_learning import SelfLearningEngine, get_self_learning_engine

logger = logging.getLogger("valora.agentic_loop")


@dataclass
class AgentStep:
    """A single step in the agentic loop"""
    step_number: int
    thought: str  # LLM reasoning
    action: Optional[str] = None  # Tool to call
    action_params: Optional[Dict] = None  # Tool parameters
    observation: Optional[str] = None  # Tool result
    reflection: Optional[str] = None  # Reflection on result
    timestamp: datetime = field(default_factory=datetime.now)
    is_final: bool = False  # Is this the final answer step?


@dataclass
class AgentPlan:
    """A plan created by the agent"""
    query: str
    steps: List[AgentStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "steps": [
                {
                    "step_number": s.step_number,
                    "thought": s.thought,
                    "action": s.action,
                    "action_params": s.action_params,
                    "observation": s.observation,
                    "reflection": s.reflection,
                    "is_final": s.is_final
                }
                for s in self.steps
            ],
            "final_answer": self.final_answer,
            "confidence": self.confidence,
            "step_count": len(self.steps)
        }


class AgenticLoop:
    """
    Opus-inspired agentic reasoning loop with:
    - Persistent memory (recall previous results per location)
    - Parallel tool execution (concurrent independent tools)
    - Self-learning (track effectiveness, learn optimal sequences)
    Implements: Think → Act → Observe → Reflect → (repeat or finalize)
    """
    
    def __init__(self, tool_registry: Optional[ToolRegistry] = None, max_steps: int = 5):
        self.tool_registry = tool_registry or get_tool_registry()
        self.max_steps = max_steps
        self.current_plan: Optional[AgentPlan] = None
        self.memory: AgenticMemory = get_agentic_memory()
        self.learner: SelfLearningEngine = get_self_learning_engine()
        self._current_intent: Optional[str] = None
        self._current_location: Optional[str] = None
    
    async def run(
        self,
        query: str,
        llm_client: Any,  # LLM client for reasoning
        context: Optional[Dict] = None,
        streaming: bool = True
    ) -> AsyncGenerator[Dict, None]:
        """
        Run the agentic loop with streaming updates.
        Yields: step updates, tool calls, observations, final answer
        """
        t_start = time.time()
        self.current_plan = AgentPlan(query=query)
        step_count = 0
        accumulated_context = context or {}
        tools_used = []
        self._current_intent = context.get("intent") if context else None
        self._current_location = self._extract_location_from_query(query)
        
        # --- Memory recall: inject cached results for this location ---
        memory_hits = []
        if self._current_location:
            memory_hits = self.memory.recall_location(self._current_location)
            if memory_hits:
                mem_summary = "; ".join(
                    f"[{m['tool']}] {json.dumps(m['data'])[:200]}" for m in memory_hits[:3]
                )
                accumulated_context["memory"] = mem_summary
        
        # --- Self-learning: get recommended tools for this intent ---
        recommended_tools = []
        if self._current_intent:
            recommended_tools = self.learner.recommend_tools(self._current_intent, query)
        
        # Yield start event
        yield {
            "type": "agent_start",
            "query": query,
            "max_steps": self.max_steps,
            "memory_hits": len(memory_hits),
            "recommended_tools": recommended_tools,
        }
        
        while step_count < self.max_steps:
            step_count += 1
            
            # =========================================================================
            # THINK: Generate reasoning for next action
            # =========================================================================
            
            thought = await self._think(
                query=query,
                step_number=step_count,
                previous_steps=self.current_plan.steps,
                accumulated_context=accumulated_context,
                llm_client=llm_client
            )
            
            step = AgentStep(
                step_number=step_count,
                thought=thought
            )
            
            # Check if we should finalize
            if await self._should_finalize(
                thought=thought,
                step_number=step_count,
                llm_client=llm_client
            ):
                step.is_final = True
                step.reflection = "Sufficient information gathered, formulating final answer"
                
                # Generate final answer
                final_answer = await self._generate_final_answer(
                    query=query,
                    steps=self.current_plan.steps,
                    llm_client=llm_client
                )
                
                step.observation = final_answer
                self.current_plan.steps.append(step)
                self.current_plan.final_answer = final_answer
                self.current_plan.completed_at = datetime.now()
                self.current_plan.confidence = await self._calculate_confidence(
                    steps=self.current_plan.steps,
                    llm_client=llm_client
                )
                
                yield {
                    "type": "agent_final",
                    "step_number": step_count,
                    "thought": thought,
                    "reflection": step.reflection,
                    "final_answer": final_answer,
                    "confidence": self.current_plan.confidence,
                    "plan": self.current_plan.to_dict()
                }
                break
            
            # =========================================================================
            # ACT: Select and execute tool
            # =========================================================================
            
            action, action_params = await self._select_action(
                thought=thought,
                tool_registry=self.tool_registry,
                llm_client=llm_client
            )
            
            step.action = action
            step.action_params = action_params
            
            yield {
                "type": "agent_action",
                "step_number": step_count,
                "thought": thought,
                "action": action,
                "action_params": action_params
            }
            
            # Execute tool — with memory check and self-learning
            observation = None
            if action and action != "finalize":
                t_tool = time.time()
                tool_success = False
                try:
                    # Check memory first
                    cached = self.memory.recall(action, action_params)
                    if cached:
                        observation = json.dumps(cached, indent=2)
                        observation = str(observation)[:2000]
                        tool_success = True
                        logger.info(f"[AgenticLoop] Memory hit for {action}")
                    else:
                        tool = self.tool_registry.get_tool(action)
                        if tool:
                            raw_result = await tool.invoke(**action_params)
                            tool_success = not (isinstance(raw_result, dict) and "error" in raw_result)
                            # Store in memory
                            if tool_success and isinstance(raw_result, dict):
                                self.memory.store(
                                    action, action_params, raw_result,
                                    location=self._current_location,
                                    confidence=0.8,
                                )
                            # Format for LLM
                            if isinstance(raw_result, (dict, list)):
                                observation = json.dumps(raw_result, indent=2)
                            observation = str(observation or raw_result)[:2000]
                except Exception as e:
                    observation = f"Error executing {action}: {str(e)}"
                
                # Record in self-learning
                latency = int((time.time() - t_tool) * 1000)
                richness = self._score_data_richness(observation)
                self.learner.record_tool_outcome(
                    tool_name=action, location=self._current_location,
                    intent=self._current_intent, params=action_params,
                    success=tool_success, data_richness=richness,
                    latency_ms=latency, was_useful=tool_success and richness > 0.2,
                )
                tools_used.append(action)
            
            step.observation = observation
            
            yield {
                "type": "agent_observation",
                "step_number": step_count,
                "observation": observation
            }
            
            # Update accumulated context
            if observation:
                accumulated_context[f"step_{step_count}_result"] = observation
            
            # =========================================================================
            # REFLECT: Analyze result and decide next step
            # =========================================================================
            
            reflection = await self._reflect(
                step=step,
                accumulated_context=accumulated_context,
                llm_client=llm_client
            )
            
            step.reflection = reflection
            self.current_plan.steps.append(step)
            
            yield {
                "type": "agent_reflection",
                "step_number": step_count,
                "thought": thought,
                "reflection": reflection,
                "action": action,
                "observation": observation
            }
        
        else:
            # Max steps reached — force generate final answer
            final_answer = await self._generate_final_answer(query, self.current_plan.steps, llm_client)
            self.current_plan.final_answer = final_answer
            self.current_plan.completed_at = datetime.now()
            yield {
                "type": "agent_max_steps",
                "message": f"Reached maximum steps ({self.max_steps})",
                "final_answer": final_answer,
                "plan": self.current_plan.to_dict()
            }
        
        # --- Post-run: log to memory and self-learning ---
        total_ms = int((time.time() - t_start) * 1000)
        self.memory.log_query(
            query=query, location=self._current_location,
            intent=self._current_intent, tools_used=tools_used,
            step_count=len(self.current_plan.steps),
            confidence=self.current_plan.confidence,
            response_time_ms=total_ms,
            success=self.current_plan.final_answer is not None,
        )
        if tools_used and self._current_intent:
            self.learner.record_tool_sequence(
                intent=self._current_intent, query=query,
                tool_sequence=tools_used,
                confidence=self.current_plan.confidence,
                steps=len(self.current_plan.steps),
            )
    
    async def _think(
        self,
        query: str,
        step_number: int,
        previous_steps: List[AgentStep],
        accumulated_context: Dict,
        llm_client: Any
    ) -> str:
        """Generate reasoning for next action using LLM."""
        prev_summary = ""
        for s in previous_steps:
            obs = s.observation[:150] if s.observation else "No result"
            prev_summary += f"\n- Step {s.step_number}: {s.action}({json.dumps(s.action_params or {})}) → {obs}"

        tool_desc = self.tool_registry.get_tool_descriptions()

        # Include memory and learned recommendations
        memory_hint = ""
        if accumulated_context.get("memory"):
            memory_hint = f"\nCached data from previous sessions: {accumulated_context['memory'][:300]}\n"

        learned_hint = ""
        recommended = self.learner.recommend_tools(
            self._current_intent or "general", query
        )
        if recommended:
            learned_hint = f"\nLearned recommendation: try tools in order: {', '.join(recommended)}\n"

        prompt = (
            f"You are Valora AI's autonomous reasoning agent for Bangalore real estate.\n\n"
            f"User Query: {query}\n"
            f"Step: {step_number}/{self.max_steps}\n"
            f"Previous:{prev_summary or ' None'}\n"
            f"{memory_hint}{learned_hint}\n"
            f"Available Tools:\n{tool_desc}\n\n"
            f"Decide: Which tool to call next, OR say FINALIZE if you have enough data.\n"
            f"For comparison queries, you can request PARALLEL tools.\n"
            f"Reply in 1-2 sentences."
        )

        try:
            response = await llm_client.generate(prompt, max_tokens=150, temperature=0.3)
            return response.strip() if response else f"Step {step_number}: Analyzing query."
        except Exception:
            return f"Step {step_number}: Analyzing query to determine best action."
    
    async def _should_finalize(
        self,
        thought: str,
        step_number: int,
        llm_client: Any
    ) -> bool:
        """Determine if we have enough information to finalize."""
        tl = thought.lower()
        finalize_signals = ['finalize', 'enough', 'sufficient', 'ready to answer',
                            'have all', 'no more tools', 'can now answer', 'conclude']
        has_signal = any(kw in tl for kw in finalize_signals)
        # Finalize if: LLM says so at step 2+, or forced at max_steps-1
        if has_signal and step_number >= 2:
            return True
        if step_number >= self.max_steps - 1:
            return True
        return False
    
    async def _select_action(
        self,
        thought: str,
        tool_registry: ToolRegistry,
        llm_client: Any
    ) -> tuple:
        """LLM-driven tool selection with JSON parameter extraction."""
        tools = tool_registry.list_tools()
        if not tools:
            return "finalize", {}

        tool_schema = "\n".join(
            f'  {{"tool": "{t.name}", "params": {json.dumps({p: "<value>" for p in t.required_params})}}}'
            for t in tools
        )

        prompt = (
            f"Based on this reasoning:\n\"{thought}\"\n\n"
            f"Select ONE tool to call. Respond with ONLY valid JSON:\n"
            f'{{"tool": "<name>", "params": {{...}}}}\n\n'
            f"Available tools:\n{tool_schema}\n\n"
            f'Or respond {{"tool": "finalize", "params": {{}}}} if no tool is needed.\n'
            f"JSON:"
        )

        try:
            response = await llm_client.generate(prompt, max_tokens=200, temperature=0.1)
            parsed = self._extract_json(response)
            if parsed:
                tool_name = parsed.get("tool", "finalize")
                params = parsed.get("params", {})
                # Validate tool exists
                if tool_name != "finalize" and tool_registry.get_tool(tool_name):
                    return tool_name, params
                elif tool_name == "finalize":
                    return "finalize", {}
        except Exception:
            pass

        # Fallback: pattern-match tool names in the thought text
        for t in tools:
            if t.name.replace("_", " ") in thought.lower() or t.name in thought.lower():
                # Try to extract location from the original query
                params = self._extract_params_from_context(t, self.current_plan.query if self.current_plan else "")
                return t.name, params

        return "finalize", {}

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict]:
        """Robustly extract first JSON object from LLM output."""
        import re
        # Strip thinking tags
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        # Find JSON
        start = text.find('{')
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return None
        return None

    @staticmethod
    def _extract_params_from_context(tool, query: str) -> Dict:
        """Extract tool parameters from the user query using simple NLP."""
        import re
        params = {}
        ql = query.lower()

        for param_name in tool.required_params:
            if param_name in ("location", "location_a"):
                # Extract location: look for known Bangalore locality patterns
                loc_match = re.search(
                    r'(?:in|near|around|of|about|at|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                    query
                )
                if loc_match:
                    params[param_name] = loc_match.group(1)
                else:
                    # Fallback: use capitalized words
                    caps = re.findall(r'\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*)\b', query)
                    params[param_name] = caps[0] if caps else query.split()[-1]
            elif param_name == "location_b":
                # For comparison: second location after "vs", "and", "or"
                parts = re.split(r'\bvs\.?\b|\bversus\b|\band\b|\bor\b|\bcompare\b', ql)
                if len(parts) > 1:
                    caps = re.findall(r'\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*)\b', query)
                    params[param_name] = caps[-1] if len(caps) > 1 else parts[-1].strip()
                else:
                    params[param_name] = "Bangalore"
            elif param_name == "bhk":
                bhk_match = re.search(r'(\d)\s*bhk', ql)
                if bhk_match:
                    params[param_name] = int(bhk_match.group(1))
            elif param_name == "budget_max":
                budget_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cr|crore|lakh|lakhs|l)', ql)
                if budget_match:
                    val = float(budget_match.group(1))
                    unit = re.search(r'(cr|crore|lakh|lakhs|l)', ql)
                    if unit and unit.group(1).startswith('cr'):
                        val *= 10000000
                    else:
                        val *= 100000
                    params[param_name] = val
            else:
                params[param_name] = query

        return params
    
    async def _reflect(
        self,
        step: AgentStep,
        accumulated_context: Dict,
        llm_client: Any
    ) -> str:
        """Reflect on the step result to decide next action."""
        if not step.observation:
            return "No observation to reflect on."

        prompt = (
            f"You called tool '{step.action}' and got:\n"
            f"{step.observation[:600]}\n\n"
            f"Original query: {self.current_plan.query if self.current_plan else 'unknown'}\n"
            f"Is this enough to answer? Reply: 'SUFFICIENT: <reason>' or 'NEED MORE: <what tool to call next>'"
        )

        try:
            response = await llm_client.generate(prompt, max_tokens=100, temperature=0.3)
            return response.strip() if response else "Data received, continuing analysis."
        except Exception:
            return "Data received, continuing analysis."
    
    async def _generate_final_answer(
        self,
        query: str,
        steps: List[AgentStep],
        llm_client: Any
    ) -> str:
        """Generate final answer from all gathered tool data."""
        research = []
        for s in steps:
            if s.observation and s.action and s.action != "finalize":
                research.append(f"[{s.action}] {s.observation[:500]}")

        research_text = "\n\n".join(research) if research else "No tool data gathered."

        prompt = (
            f"You are Valora AI, Bangalore's real estate intelligence assistant.\n\n"
            f"User asked: {query}\n\n"
            f"You autonomously gathered this grounded data:\n{research_text}\n\n"
            f"RULES:\n"
            f"- Base ALL claims on the data above. Never invent numbers.\n"
            f"- Be specific: cite exact metrics, scores, prices from the data.\n"
            f"- Use markdown with clear sections.\n"
            f"- If data is missing, say so honestly.\n"
            f"- Keep response concise but thorough (150-300 words).\n\n"
            f"Answer:"
        )

        try:
            response = await llm_client.generate(prompt, max_tokens=1024, temperature=0.5)
            return response.strip() if response else f"Based on {len(steps)} analysis steps, here's what I found..."
        except Exception:
            return f"Based on {len(steps)} analysis steps, here's what I found..."
    
    async def _calculate_confidence(
        self,
        steps: List[AgentStep],
        llm_client: Any
    ) -> float:
        """Calculate confidence score for the plan"""
        if not steps:
            return 0.0
        successful_steps = sum(1 for s in steps if s.observation and 'error' not in s.observation.lower())
        return round((successful_steps / len(steps)) * 100, 1)

    # =========================================================================
    # Parallel tool execution
    # =========================================================================

    async def run_parallel_tools(
        self,
        tool_calls: List[Tuple[str, Dict]],
    ) -> List[Tuple[str, Dict, Any]]:
        """Execute multiple independent tools concurrently.
        Returns list of (tool_name, params, result) tuples.
        """
        async def _exec_one(name: str, params: Dict):
            t0 = time.time()
            try:
                # Check memory first
                cached = self.memory.recall(name, params)
                if cached:
                    logger.info(f"[Parallel] Memory hit: {name}")
                    return name, params, cached
                tool = self.tool_registry.get_tool(name)
                if not tool:
                    return name, params, {"error": f"Tool '{name}' not found"}
                result = await tool.invoke(**params)
                # Store in memory
                if isinstance(result, dict) and "error" not in result:
                    self.memory.store(name, params, result,
                                     location=self._current_location, confidence=0.8)
                # Record in self-learning
                latency = int((time.time() - t0) * 1000)
                richness = self._score_data_richness(
                    json.dumps(result)[:500] if isinstance(result, dict) else str(result)[:500]
                )
                self.learner.record_tool_outcome(
                    tool_name=name, location=self._current_location,
                    intent=self._current_intent, params=params,
                    success=True, data_richness=richness,
                    latency_ms=latency, was_useful=richness > 0.2,
                )
                return name, params, result
            except Exception as e:
                latency = int((time.time() - t0) * 1000)
                self.learner.record_tool_outcome(
                    tool_name=name, location=self._current_location,
                    intent=self._current_intent, params=params,
                    success=False, data_richness=0, latency_ms=latency, was_useful=False,
                )
                return name, params, {"error": str(e)}

        tasks = [_exec_one(n, p) for n, p in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = []
        for r in results:
            if isinstance(r, Exception):
                out.append(("unknown", {}, {"error": str(r)}))
            else:
                out.append(r)
        return out

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _extract_location_from_query(query: str) -> Optional[str]:
        """Extract the primary location mention from a query."""
        import re
        # Match "in/near/about/at Location Name"
        m = re.search(
            r'(?:in|near|around|of|about|at|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', query
        )
        if m:
            return m.group(1)
        # Fallback: first capitalized multi-char word
        caps = re.findall(r'\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*)\b', query)
        return caps[0] if caps else None

    @staticmethod
    def _score_data_richness(observation: str) -> float:
        """Score how data-rich an observation is (0.0 to 1.0)."""
        if not observation:
            return 0.0
        score = 0.0
        obs = observation.lower()
        # Has numeric data
        import re
        nums = re.findall(r'\d+\.?\d*', obs)
        score += min(len(nums) * 0.05, 0.3)
        # Has key metrics
        for kw in ["price", "score", "count", "sqft", "elevation", "risk", "walkability", "poi"]:
            if kw in obs:
                score += 0.1
        # Length bonus
        score += min(len(observation) / 2000, 0.2)
        # Penalty for errors
        if "error" in obs:
            score *= 0.2
        return min(round(score, 2), 1.0)


# Singleton instance
_agentic_loop = None

def get_agentic_loop(tool_registry: Optional[ToolRegistry] = None, max_steps: int = 10) -> AgenticLoop:
    """Get or create global agentic loop"""
    global _agentic_loop
    if _agentic_loop is None:
        _agentic_loop = AgenticLoop(tool_registry=tool_registry, max_steps=max_steps)
    return _agentic_loop


if __name__ == "__main__":
    # Test
    print("Agentic Loop module loaded successfully")
    loop = get_agentic_loop()
    print(f"Agentic loop initialized with max_steps={loop.max_steps}")
