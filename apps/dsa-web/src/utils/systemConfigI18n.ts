import type { SystemConfigCategory } from '../types/systemConfig';

const categoryTitleMap: Record<SystemConfigCategory, string> = {
  base: '기본 설정',
  data_source: '데이터 소스',
  ai_model: 'AI 모델',
  notification: '알림 채널',
  system: '시스템 설정',
  agent: 'Agent 설정',
  backtest: '백테스트 설정',
  uncategorized: '기타',
};

const categoryDescriptionMap: Partial<Record<SystemConfigCategory, string>> = {
  base: '관심 종목 및 기본 실행 파라미터를 관리합니다.',
  data_source: '시세 데이터 소스 및 우선순위 전략을 관리합니다.',
  ai_model: '모델 공급자, 모델명 및 추론 파라미터를 관리합니다.',
  notification: '봇, Webhook 및 메시지 알림 설정을 관리합니다.',
  system: '스케줄러, 로그, 포트 등 시스템 수준 파라미터를 관리합니다.',
  agent: 'Agent 모드, 전략 및 멀티 Agent 오케스트레이션 설정을 관리합니다.',
  backtest: '백테스트 활성화, 평가 기간 및 엔진 파라미터를 관리합니다.',
  uncategorized: '기타 미분류 설정 항목입니다.',
};

const fieldTitleMap: Record<string, string> = {
  STOCK_LIST: '관심 종목 목록',
  TUSHARE_TOKEN: 'Tushare Token',
  BOCHA_API_KEYS: 'Bocha API Keys',
  TAVILY_API_KEYS: 'Tavily API Keys',
  SERPAPI_API_KEYS: 'SerpAPI API Keys',
  BRAVE_API_KEYS: 'Brave API Keys',
  SEARXNG_BASE_URLS: 'SearXNG Base URLs',
  MINIMAX_API_KEYS: 'MiniMax API Keys',
  REALTIME_SOURCE_PRIORITY: '실시간 데이터 소스 우선순위',
  ENABLE_REALTIME_TECHNICAL_INDICATORS: '장중 실시간 기술 지표',
  LITELLM_MODEL: '주 모델',
  LITELLM_FALLBACK_MODELS: '백업 모델',
  LITELLM_CONFIG: 'LiteLLM 설정 파일',
  LLM_CHANNELS: 'LLM 채널 목록',
  LLM_TEMPERATURE: '샘플링 온도',
  AIHUBMIX_KEY: 'AIHubmix Key',
  DEEPSEEK_API_KEY: 'DeepSeek API Key',
  GEMINI_API_KEY: 'Gemini API Key',
  GEMINI_MODEL: 'Gemini 모델',
  GEMINI_TEMPERATURE: 'Gemini 온도 파라미터',
  OPENAI_API_KEY: 'OpenAI API Key',
  OPENAI_BASE_URL: 'OpenAI Base URL',
  OPENAI_MODEL: 'OpenAI 모델',
  WECHAT_WEBHOOK_URL: '위챗 기업용 Webhook',
  DINGTALK_APP_KEY: '딩톡 App Key',
  DINGTALK_APP_SECRET: '딩톡 App Secret',
  PUSHPLUS_TOKEN: 'PushPlus Token',
  REPORT_SUMMARY_ONLY: '분석 결과 요약만',
  SCHEDULE_TIME: '정기 작업 시간',
  HTTP_PROXY: 'HTTP 프록시',
  LOG_LEVEL: '로그 레벨',
  WEBUI_PORT: 'WebUI 포트',
  AGENT_MODE: 'Agent 모드 활성화',
  AGENT_MAX_STEPS: 'Agent 최대 스텝 수',
  AGENT_SKILLS: 'Agent 활성화 전략',
  AGENT_STRATEGY_DIR: 'Agent 전략 디렉터리',
  AGENT_ARCH: 'Agent 아키텍처 모드',
  AGENT_ORCHESTRATOR_MODE: '오케스트레이션 모드',
  AGENT_ORCHESTRATOR_TIMEOUT_S: '오케스트레이션 타임아웃(초)',
  AGENT_RISK_OVERRIDE: '리스크 Agent 거부권',
  AGENT_STRATEGY_AUTOWEIGHT: '전략 자동 가중치',
  AGENT_STRATEGY_ROUTING: '전략 라우팅 모드',
  AGENT_MEMORY_ENABLED: '메모리 및 보정',
  BACKTEST_ENABLED: '백테스트 활성화',
  BACKTEST_EVAL_WINDOW_DAYS: '백테스트 평가 기간(거래일)',
  BACKTEST_MIN_AGE_DAYS: '백테스트 최소 히스토리 일수',
  BACKTEST_ENGINE_VERSION: '백테스트 엔진 버전',
  BACKTEST_NEUTRAL_BAND_PCT: '백테스트 중립 구간 임계값(%)',
};

const fieldDescriptionMap: Record<string, string> = {
  STOCK_LIST: '쉼표로 종목 코드를 구분하세요. 예: 600519,300750',
  TUSHARE_TOKEN: 'Tushare Pro 데이터 서비스 접근 자격 증명입니다.',
  BOCHA_API_KEYS: '뉴스 검색용 Bocha 키, 쉼표로 여러 개 입력 가능(최고 우선순위).',
  TAVILY_API_KEYS: '뉴스 검색용 Tavily 키, 쉼표로 여러 개 입력 가능.',
  SERPAPI_API_KEYS: '뉴스 검색용 SerpAPI 키, 쉼표로 여러 개 입력 가능.',
  BRAVE_API_KEYS: '뉴스 검색용 Brave Search 키, 쉼표로 여러 개 입력 가능.',
  SEARXNG_BASE_URLS: '자체 호스팅 SearXNG 인스턴스 주소(쉼표 구분). settings.yml에서 format: json 활성화 필요.',
  MINIMAX_API_KEYS: '뉴스 검색용 MiniMax 키, 쉼표로 여러 개 입력 가능(최저 우선순위).',
  REALTIME_SOURCE_PRIORITY: '쉼표로 구분하여 데이터 소스 호출 우선순위를 입력하세요.',
  ENABLE_REALTIME_TECHNICAL_INDICATORS: '장중 분석 시 실시간 가격으로 MA5/MA10/MA20 및 정배열 계산(Issue #234). 비활성화 시 전일 종가 사용.',
  LITELLM_MODEL: '주 모델, 형식: provider/model (예: gemini/gemini-2.5-flash). 채널 설정 후 자동 추론.',
  LITELLM_FALLBACK_MODELS: '백업 모델, 쉼표 구분. 주 모델 실패 시 순서대로 시도.',
  LITELLM_CONFIG: 'LiteLLM YAML 설정 파일 경로(고급 사용), 최고 우선순위.',
  LLM_CHANNELS: '채널 이름 목록(쉼표 구분). 위의 채널 편집기로 관리하는 것을 권장.',
  LLM_TEMPERATURE: '모델 출력 무작위성 조절. 0은 결정적 출력, 2는 최대 무작위성. 0.7 권장.',
  AIHUBMIX_KEY: 'AIHubmix 통합 키, 자동으로 aihubmix.com/v1을 사용.',
  DEEPSEEK_API_KEY: 'DeepSeek 공식 API 키. 입력 후 자동으로 deepseek-chat 모델 사용.',
  GEMINI_API_KEY: 'Gemini 서비스 호출용 키.',
  GEMINI_MODEL: 'Gemini 분석 모델명 설정.',
  GEMINI_TEMPERATURE: '모델 출력 무작위성 조절, 범위는 보통 0.0~2.0.',
  OPENAI_API_KEY: 'OpenAI 호환 서비스 호출용 키.',
  OPENAI_BASE_URL: 'OpenAI 호환 API 주소. 예: https://api.deepseek.com/v1',
  OPENAI_MODEL: 'OpenAI 호환 모델명. 예: gpt-4o-mini, deepseek-chat',
  WECHAT_WEBHOOK_URL: '위챗 기업용 봇 Webhook 주소.',
  DINGTALK_APP_KEY: '딩톡 앱 모드 App Key.',
  DINGTALK_APP_SECRET: '딩톡 앱 모드 App Secret.',
  PUSHPLUS_TOKEN: 'PushPlus 푸시 토큰.',
  REPORT_SUMMARY_ONLY: '분석 결과 요약만 전송, 개별 종목 상세 내용 제외. 다중 종목 시 빠른 확인에 적합.',
  SCHEDULE_TIME: '일일 정기 작업 실행 시간, HH:MM 형식.',
  HTTP_PROXY: '네트워크 프록시 주소. 비워도 됩니다.',
  LOG_LEVEL: '로그 출력 레벨 설정.',
  WEBUI_PORT: '웹 페이지 서비스 수신 포트.',
  AGENT_MODE: 'ReAct Agent를 사용하여 주식 분석을 활성화할지 여부.',
  AGENT_MAX_STEPS: 'Agent가 사고하고 도구를 호출하는 최대 스텝 수.',
  AGENT_SKILLS: '쉼표로 구분된 매매 전략 목록. 예: bull_trend,ma_golden_cross,shrink_pullback',
  AGENT_STRATEGY_DIR: 'Agent 전략 YAML 파일이 저장된 디렉터리 경로.',
  AGENT_ARCH: 'Agent 실행 아키텍처 선택. single: 클래식 단일 Agent; multi: 멀티 Agent 오케스트레이션(실험적).',
  AGENT_ORCHESTRATOR_MODE: '멀티 Agent 오케스트레이션 깊이. quick(기술→결정), standard(기술→정보→결정), full(리스크 포함), strategy(전략 평가 포함).',
  AGENT_ORCHESTRATOR_TIMEOUT_S: '멀티 Agent 오케스트레이션 총 타임아웃 예산(초). 0은 제한 없음.',
  AGENT_RISK_OVERRIDE: '리스크 Agent가 핵심 리스크 발견 시 매수 신호 거부 허용.',
  AGENT_STRATEGY_AUTOWEIGHT: '백테스트 성과에 따라 전략 가중치 자동 조정.',
  AGENT_STRATEGY_ROUTING: '전략 선택 방식. auto: 시장 상태에 따라 자동 선택, manual: AGENT_SKILLS 목록 사용.',
  AGENT_MEMORY_ENABLED: '메모리 및 보정 시스템 활성화. 과거 분석 정확도를 추적하고 신뢰도 자동 조정.',
  BACKTEST_ENABLED: '백테스트 기능 활성화 여부(true/false).',
  BACKTEST_EVAL_WINDOW_DAYS: '백테스트 평가 기간 길이, 단위: 거래일.',
  BACKTEST_MIN_AGE_DAYS: '해당 일수보다 오래된 분석 기록만 백테스트.',
  BACKTEST_ENGINE_VERSION: '백테스트 엔진 버전 식별자, 결과 버전 구분에 사용.',
  BACKTEST_NEUTRAL_BAND_PCT: '중립 구간 임계값 퍼센트. 예: 2는 -2%~+2% 의미.',
};

export function getCategoryTitleZh(category: SystemConfigCategory, fallback?: string): string {
  return categoryTitleMap[category] || fallback || category;
}

export function getCategoryDescriptionZh(category: SystemConfigCategory, fallback?: string): string {
  return categoryDescriptionMap[category] || fallback || '';
}

export function getFieldTitleZh(key: string, fallback?: string): string {
  return fieldTitleMap[key] || fallback || key;
}

export function getFieldDescriptionZh(key: string, fallback?: string): string {
  return fieldDescriptionMap[key] || fallback || '';
}
