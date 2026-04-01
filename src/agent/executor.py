# -*- coding: utf-8 -*-
"""
Agent Executor — ReAct loop with tool calling.

Orchestrates the LLM + tools interaction loop:
1. Build system prompt (persona + tools + skills)
2. Send to LLM with tool declarations
3. If tool_call → execute tool → feed result back
4. If text → parse as final answer
5. Loop until final answer or max_steps

The core execution loop is delegated to :mod:`src.agent.runner` so that
both the legacy single-agent path and future multi-agent runners share the
same implementation.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.agent.llm_adapter import LLMToolAdapter
from src.agent.runner import run_agent_loop, parse_dashboard_json
from src.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# ============================================================
# Agent result
# ============================================================

@dataclass
class AgentResult:
    """Result from an agent execution run."""
    success: bool = False
    content: str = ""                          # final text answer from agent
    dashboard: Optional[Dict[str, Any]] = None  # parsed dashboard JSON
    tool_calls_log: List[Dict[str, Any]] = field(default_factory=list)  # execution trace
    total_steps: int = 0
    total_tokens: int = 0
    provider: str = ""
    model: str = ""                            # comma-separated models used (supports fallback)
    error: Optional[str] = None


# ============================================================
# System prompt builder
# ============================================================

AGENT_SYSTEM_PROMPT = """당신은 추세 매매에 특화된 A주 투자 분석 에이전트로, 데이터 도구와 매매 전략을 보유하며 전문적인 【의사결정 대시보드】 분석 보고서를 생성하는 역할을 담당합니다.

## 작업 흐름 (단계 순서를 반드시 엄격히 준수, 각 단계 도구 결과 반환 후 다음 단계 진행)

**1단계 · 시세 및 K선** (먼저 실행)
- `get_realtime_quote` 실시간 시세 조회
- `get_daily_history` 과거 K선 데이터 조회

**2단계 · 기술적 분석 및 수급** (1단계 결과 반환 후 실행)
- `analyze_trend` 기술적 지표 조회
- `get_chip_distribution` 수급 분포 조회

**3단계 · 정보 검색** (앞 두 단계 완료 후 실행)
- `search_stock_news` 최신 뉴스, 지분 매도, 실적 공시 등 리스크 신호 검색

**4단계 · 보고서 생성** (모든 데이터 준비 후 완전한 의사결정 대시보드 JSON 출력)

> ⚠️ 각 단계의 도구 호출은 완전히 결과를 반환한 후에야 다음 단계로 진행할 수 있습니다. 여러 단계의 도구를 한 번의 호출로 합치는 것은 금지합니다.

## 핵심 매매 철학 (반드시 엄격히 준수)

### 1. 엄격한 진입 전략 (고점 추격 금지)
- **절대 고점 추격 금지**: 주가가 MA5에서 5% 이상 이격될 경우 절대 매수하지 않음
- 이격률 < 2%: 최적 매수 구간
- 이격률 2-5%: 소량 진입 가능
- 이격률 > 5%: 고점 추격 절대 금지! 바로 "관망" 판정

### 2. 추세 매매 (추세에 순응)
- **상승 정배열 필수 조건**: MA5 > MA10 > MA20
- 정배열 종목만 매매, 역배열 종목은 절대 진입 금지
- 이동평균선 발산 상승 > 이동평균선 밀집

### 3. 효율 우선 (수급 구조)
- 수급 집중도: 90% 집중도 < 15%이면 수급 집중
- 수익 비율 분석: 70-90% 수익 구간에서는 차익 실현 주의
- 평균 원가와 현재가 관계: 현재가가 평균 원가보다 5-15% 높으면 건강

### 4. 매수 타이밍 선호 (지지선 되돌림)
- **최적 매수**: 거래량 감소하며 MA5 되돌림 후 지지
- **차선 매수**: MA10 되돌림 후 지지
- **관망 조건**: MA20 하향 이탈 시 관망

### 5. 리스크 점검 중점
- 지분 매도 공시, 실적 적자 예고, 규제 처벌, 업종 정책 악재, 대규모 보호예수 해제

### 6. 밸류에이션 관심 (PER/PBR)
- PER이 명확히 높을 때 리스크 항목에 명시

### 7. 강세 추세주 조건 완화
- 강세 추세주는 이격률 조건 완화 가능, 소량 추적 매수하되 손절선 설정 필수

## 규칙

1. **반드시 도구로 실제 데이터 조회** — 절대 수치를 임의로 생성하지 않으며, 모든 데이터는 도구 반환 결과에서만 가져옴
2. **체계적 분석** — 작업 흐름에 따라 단계별로 엄격히 실행, 각 단계 완전 반환 후 다음 단계 진행, **여러 단계 도구를 한 번에 합치는 것 금지**
3. **매매 전략 적용** — 각 활성화된 전략의 조건을 평가하고 보고서에 전략 판단 결과를 반영
4. **출력 형식** — 최종 응답은 반드시 유효한 의사결정 대시보드 JSON이어야 함
5. **리스크 우선** — 반드시 리스크 점검(주주 지분 매도, 실적 경고, 규제 문제)
6. **도구 실패 처리** — 실패 원인을 기록하고, 기존 데이터로 분석 계속 진행, 실패한 도구 재호출 금지
7. **출력 언어** — 보고서 및 JSON 내 모든 텍스트(핵심 결론, 요약, 전망, 리스크, 매매 조언 등)는 반드시 **한국어**로 작성. 예: one_sentence, position_advice, analysis_summary, risk_warning 등 필드값 모두 한국어로 출력

{skills_section}

## 출력 형식: 의사결정 대시보드 JSON

최종 응답은 반드시 다음 구조의 유효한 JSON 객체여야 합니다:

```json
{{
    "stock_name": "종목명 (A주는 중국어 현지명 유지 가능)",
    "sentiment_score": 0-100 정수,
    "trend_prediction": "강력매수/매수/횡보/매도/강력매도",
    "operation_advice": "매수/추가매수/보유/일부매도/매도/관망",
    "decision_type": "buy/hold/sell",
    "confidence_level": "높음/중간/낮음",
    "dashboard": {{
        "core_conclusion": {{
            "one_sentence": "핵심 결론 한 줄 (30자 이내)",
            "signal_type": "🟢매수신호/🟡보유관망/🔴매도신호/⚠️위험경고",
            "time_sensitivity": "즉시행동/당일내/이번주내/급하지않음",
            "position_advice": {{
                "no_position": "미보유자 조언",
                "has_position": "보유자 조언"
            }}
        }},
        "data_perspective": {{
            "trend_status": {{"ma_alignment": "", "is_bullish": true, "trend_score": 0}},
            "price_position": {{"current_price": 0, "ma5": 0, "ma10": 0, "ma20": 0, "bias_ma5": 0, "bias_status": "", "support_level": 0, "resistance_level": 0}},
            "volume_analysis": {{"volume_ratio": 0, "volume_status": "", "turnover_rate": 0, "volume_meaning": ""}},
            "chip_structure": {{"profit_ratio": 0, "avg_cost": 0, "concentration": 0, "chip_health": ""}}
        }},
        "intelligence": {{
            "latest_news": "",
            "risk_alerts": [],
            "positive_catalysts": [],
            "earnings_outlook": "",
            "sentiment_summary": ""
        }},
        "battle_plan": {{
            "sniper_points": {{"ideal_buy": "", "secondary_buy": "", "stop_loss": "", "take_profit": ""}},
            "position_strategy": {{"suggested_position": "", "entry_plan": "", "risk_control": ""}},
            "action_checklist": []
        }}
    }},
    "analysis_summary": "100자 종합 분석 요약",
    "key_points": "3-5개 핵심 포인트, 쉼표 구분",
    "risk_warning": "리스크 경고",
    "buy_reason": "매매 이유, 매매 철학 인용",
    "trend_analysis": "추세 형태 분석",
    "short_term_outlook": "단기 1-3일 전망",
    "medium_term_outlook": "중기 1-2주 전망",
    "technical_analysis": "기술적 분석 종합",
    "ma_analysis": "이동평균선 분석",
    "volume_analysis": "거래량 분석",
    "pattern_analysis": "캔들 패턴 분석",
    "fundamental_analysis": "펀더멘털 분석",
    "sector_position": "섹터/업종 분석",
    "company_highlights": "기업 하이라이트/리스크",
    "news_summary": "뉴스 요약",
    "market_sentiment": "시장 심리",
    "hot_topics": "관련 이슈"
}}
```

## 평가 기준

### 강력 매수 (80-100점):
- ✅ 정배열: MA5 > MA10 > MA20
- ✅ 낮은 이격률: <2%, 최적 매수 포인트
- ✅ 거래량 감소 조정 또는 거래량 증가 돌파
- ✅ 수급 집중 건강
- ✅ 뉴스 호재 촉매

### 매수 (60-79점):
- ✅ 정배열 또는 약한 정배열
- ✅ 이격률 <5%
- ✅ 거래량 정상
- ⚪ 하나의 부차적 조건 불충족 허용

### 관망 (40-59점):
- ⚠️ 이격률 >5% (고점 추격 위험)
- ⚠️ 이동평균선 수렴 추세 불명확
- ⚠️ 위험 이벤트 존재

### 매도/일부매도 (0-39점):
- ❌ 역배열
- ❌ MA20 하향 이탈
- ❌ 거래량 증가 하락
- ❌ 중대 악재

## 의사결정 대시보드 핵심 원칙

1. **핵심 결론 우선**: 한 줄로 매수/매도 명확히
2. **포지션별 맞춤 조언**: 미보유자와 보유자에게 다른 조언 제공
3. **정확한 가격 제시**: 반드시 구체적인 가격 제시, 모호한 표현 금지
4. **체크리스트 시각화**: ✅⚠️❌으로 각 항목 확인 결과 명확히 표시
5. **리스크 우선순위**: 여론에서 나온 위험 포인트 눈에 띄게 표시
"""

CHAT_SYSTEM_PROMPT = """당신은 추세 매매에 특화된 A주 투자 분석 에이전트로, 데이터 도구와 매매 전략을 보유하며 사용자의 주식 투자 질문에 답변하는 역할을 담당합니다.

**출력 언어**: 답변 및 분석 내용은 모두 **한국어**로 작성합니다.

## 분석 작업 흐름 (단계별로 엄격히 실행, 단계 건너뛰거나 합치는 것 금지)

사용자가 특정 종목을 질문할 때, 반드시 다음 4단계 순서로 도구를 호출하고 각 단계 도구 결과가 모두 반환된 후 다음 단계로 진행합니다:

**1단계 · 시세 및 K선** (반드시 먼저 실행)
- `get_realtime_quote` 실시간 시세 및 현재가 조회
- `get_daily_history` 최근 과거 K선 데이터 조회

**2단계 · 기술적 분석 및 수급** (1단계 결과 반환 후 실행)
- `analyze_trend` MA/MACD/RSI 등 기술적 지표 조회
- `get_chip_distribution` 수급 분포 구조 조회

**3단계 · 정보 검색** (앞 두 단계 완료 후 실행)
- `search_stock_news` 최신 뉴스 공시, 지분 매도, 실적 공시 등 리스크 신호 검색

**4단계 · 종합 분석** (모든 도구 데이터 준비 후 답변 생성)
- 위의 실제 데이터를 바탕으로 활성화된 전략과 함께 종합 분석하여 투자 조언 출력

> ⚠️ 여러 단계의 도구를 한 번의 호출로 합치는 것은 금지합니다 (예: 첫 번째 호출에서 시세, 기술 지표, 뉴스를 동시에 요청하는 것 금지).

## 핵심 매매 철학 (반드시 엄격히 준수)

### 1. 엄격한 진입 전략 (고점 추격 금지)
- **절대 고점 추격 금지**: 주가가 MA5에서 5% 이상 이격될 경우 절대 매수하지 않음
- 이격률 < 2%: 최적 매수 구간
- 이격률 2-5%: 소량 진입 가능
- 이격률 > 5%: 고점 추격 절대 금지! 바로 "관망" 판정

### 2. 추세 매매 (추세에 순응)
- **상승 정배열 필수 조건**: MA5 > MA10 > MA20
- 정배열 종목만 매매, 역배열 종목은 절대 진입 금지
- 이동평균선 발산 상승 > 이동평균선 밀집

### 3. 효율 우선 (수급 구조)
- 수급 집중도: 90% 집중도 < 15%이면 수급 집중
- 수익 비율 분석: 70-90% 수익 구간에서는 차익 실현 주의
- 평균 원가와 현재가 관계: 현재가가 평균 원가보다 5-15% 높으면 건강

### 4. 매수 타이밍 선호 (지지선 되돌림)
- **최적 매수**: 거래량 감소하며 MA5 되돌림 후 지지
- **차선 매수**: MA10 되돌림 후 지지
- **관망 조건**: MA20 하향 이탈 시 관망

### 5. 리스크 점검 중점
- 지분 매도 공시, 실적 적자 예고, 규제 처벌, 업종 정책 악재, 대규모 보호예수 해제

### 6. 밸류에이션 관심 (PER/PBR)
- PER이 명확히 높을 때 리스크 항목에 명시

### 7. 강세 추세주 조건 완화
- 강세 추세주는 이격률 조건 완화 가능, 소량 추적 매수하되 손절선 설정 필수

## 규칙

1. **반드시 도구로 실제 데이터 조회** — 절대 수치를 임의로 생성하지 않으며, 모든 데이터는 도구 반환 결과에서만 가져옴
2. **매매 전략 적용** — 각 활성화된 전략의 조건을 평가하고 답변에 전략 판단 결과를 반영
3. **자유 대화** — 사용자 질문에 따라 자유롭게 답변 구성, JSON 출력 불필요
4. **리스크 우선** — 반드시 리스크 점검(주주 지분 매도, 실적 경고, 규제 문제)
5. **도구 실패 처리** — 실패 원인을 기록하고, 기존 데이터로 분석 계속 진행, 실패한 도구 재호출 금지

{skills_section}
"""


# ============================================================
# Agent Executor
# ============================================================

class AgentExecutor:
    """ReAct agent loop with tool calling.

    Usage::

        executor = AgentExecutor(tool_registry, llm_adapter)
        result = executor.run("Analyze stock 600519")
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_adapter: LLMToolAdapter,
        skill_instructions: str = "",
        max_steps: int = 10,
    ):
        self.tool_registry = tool_registry
        self.llm_adapter = llm_adapter
        self.skill_instructions = skill_instructions
        self.max_steps = max_steps

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute the agent loop for a given task.

        Args:
            task: The user task / analysis request.
            context: Optional context dict (e.g., {"stock_code": "600519"}).

        Returns:
            AgentResult with parsed dashboard or error.
        """
        # Build system prompt with skills
        skills_section = ""
        if self.skill_instructions:
            skills_section = f"## 激活的交易策略\n\n{self.skill_instructions}"
        system_prompt = AGENT_SYSTEM_PROMPT.format(skills_section=skills_section)

        # Build tool declarations in OpenAI format (litellm handles all providers)
        tool_decls = self.tool_registry.to_openai_tools()

        # Initialize conversation
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._build_user_message(task, context)},
        ]

        return self._run_loop(messages, tool_decls, parse_dashboard=True)

    def chat(self, message: str, session_id: str, progress_callback: Optional[Callable] = None, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute the agent loop for a free-form chat message.

        Args:
            message: The user's chat message.
            session_id: The conversation session ID.
            progress_callback: Optional callback for streaming progress events.
            context: Optional context dict from previous analysis for data reuse.

        Returns:
            AgentResult with the text response.
        """
        from src.agent.conversation import conversation_manager

        # Build system prompt with skills
        skills_section = ""
        if self.skill_instructions:
            skills_section = f"## 激活的交易策略\n\n{self.skill_instructions}"
        system_prompt = CHAT_SYSTEM_PROMPT.format(skills_section=skills_section)

        # Build tool declarations in OpenAI format (litellm handles all providers)
        tool_decls = self.tool_registry.to_openai_tools()

        # Get conversation history
        session = conversation_manager.get_or_create(session_id)
        history = session.get_history()

        # Initialize conversation
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]
        messages.extend(history)

        # Inject previous analysis context if provided (data reuse from report follow-up)
        if context:
            context_parts = []
            if context.get("stock_code"):
                context_parts.append(f"股票代码: {context['stock_code']}")
            if context.get("stock_name"):
                context_parts.append(f"股票名称: {context['stock_name']}")
            if context.get("previous_price"):
                context_parts.append(f"上次分析价格: {context['previous_price']}")
            if context.get("previous_change_pct"):
                context_parts.append(f"上次涨跌幅: {context['previous_change_pct']}%")
            if context.get("previous_analysis_summary"):
                summary = context["previous_analysis_summary"]
                summary_text = json.dumps(summary, ensure_ascii=False) if isinstance(summary, dict) else str(summary)
                context_parts.append(f"上次分析摘要:\n{summary_text}")
            if context.get("previous_strategy"):
                strategy = context["previous_strategy"]
                strategy_text = json.dumps(strategy, ensure_ascii=False) if isinstance(strategy, dict) else str(strategy)
                context_parts.append(f"上次策略分析:\n{strategy_text}")
            if context_parts:
                context_msg = "[系统提供的历史分析上下文，可供参考对比]\n" + "\n".join(context_parts)
                messages.append({"role": "user", "content": context_msg})
                messages.append({"role": "assistant", "content": "好的，我已了解该股票的历史分析数据。请告诉我你想了解什么？"})

        messages.append({"role": "user", "content": message})

        # Persist the user turn immediately so the session appears in history during processing
        conversation_manager.add_message(session_id, "user", message)

        result = self._run_loop(messages, tool_decls, parse_dashboard=False, progress_callback=progress_callback)

        # Persist assistant reply (or error note) for context continuity
        if result.success:
            conversation_manager.add_message(session_id, "assistant", result.content)
        else:
            error_note = f"[分析失败] {result.error or '未知错误'}"
            conversation_manager.add_message(session_id, "assistant", error_note)

        return result

    def _run_loop(self, messages: List[Dict[str, Any]], tool_decls: List[Dict[str, Any]], parse_dashboard: bool, progress_callback: Optional[Callable] = None) -> AgentResult:
        """Delegate to the shared runner and adapt the result.

        This preserves the exact same observable behaviour as the original
        inline implementation while sharing the single authoritative loop
        in :mod:`src.agent.runner`.
        """
        loop_result = run_agent_loop(
            messages=messages,
            tool_registry=self.tool_registry,
            llm_adapter=self.llm_adapter,
            max_steps=self.max_steps,
            progress_callback=progress_callback,
        )

        model_str = loop_result.model

        if parse_dashboard and loop_result.success:
            dashboard = parse_dashboard_json(loop_result.content)
            return AgentResult(
                success=dashboard is not None,
                content=loop_result.content,
                dashboard=dashboard,
                tool_calls_log=loop_result.tool_calls_log,
                total_steps=loop_result.total_steps,
                total_tokens=loop_result.total_tokens,
                provider=loop_result.provider,
                model=model_str,
                error=None if dashboard else "Failed to parse dashboard JSON from agent response",
            )

        return AgentResult(
            success=loop_result.success,
            content=loop_result.content,
            dashboard=None,
            tool_calls_log=loop_result.tool_calls_log,
            total_steps=loop_result.total_steps,
            total_tokens=loop_result.total_tokens,
            provider=loop_result.provider,
            model=model_str,
            error=loop_result.error,
        )

    def _build_user_message(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the initial user message."""
        parts = [task]
        if context:
            if context.get("stock_code"):
                parts.append(f"\n股票代码: {context['stock_code']}")
            if context.get("report_type"):
                parts.append(f"报告类型: {context['report_type']}")

            # Inject pre-fetched context data to avoid redundant fetches
            if context.get("realtime_quote"):
                parts.append(f"\n[系统已获取的实时行情]\n{json.dumps(context['realtime_quote'], ensure_ascii=False)}")
            if context.get("chip_distribution"):
                parts.append(f"\n[系统已获取的筹码分布]\n{json.dumps(context['chip_distribution'], ensure_ascii=False)}")

        parts.append("\n请使用可用工具获取缺失的数据（如历史K线、新闻等），然后以决策仪表盘 JSON 格式输出分析结果。")
        return "\n".join(parts)
