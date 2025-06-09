"""
ReAct Agent Implementation
추론과 행동을 결합한 지능형 에이전트
"""
from typing import Dict, Any, List, Optional
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class ReactAgent:
    """ReAct 에이전트"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_MODEL,
            temperature=0.1
        )
        self.agent = None
        self.agent_executor = None
        self._initialized = False
    
    async def create_agent(self) -> AgentExecutor:
        """ReAct Agent 생성"""
        try:
            # 사용 가능한 도구들 가져오기
            tools = self.tool_registry.get_all_tools()
            
            # ReAct 프롬프트 템플릿
            react_prompt = PromptTemplate.from_template("""
다음 도구들을 사용하여 질문에 답변하세요. 도구를 사용할 때는 정확한 형식을 따르세요.

사용 가능한 도구들:
{tools}

도구 사용 형식:
```
Action: 도구명
Action Input: 도구에 전달할 입력
```

질문: {input}

생각 과정을 단계별로 설명하고 필요한 도구를 사용하세요.

{agent_scratchpad}
""")
            
            # ReAct Agent 생성
            agent = create_react_agent(
                llm=self.llm,
                tools=tools,
                prompt=react_prompt
            )
            
            # AgentExecutor 생성
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=5,
                max_execution_time=60,
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )
            
            logger.info(f"ReAct Agent 생성 완료 (도구 {len(tools)}개)")
            return agent_executor
            
        except Exception as e:
            logger.error(f"ReAct Agent 생성 실패: {e}")
            raise 