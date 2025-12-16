"""
설정 및 상수 정의 모듈
"""
from typing import Dict, List

# FRED API 지표 정의
FRED_INDICATORS: Dict[str, str] = {
    # 경기 사이클 지표
    'UNRATE': 'Unemployment Rate',
    'UMCSENT': 'University of Michigan Consumer Sentiment',
    'INDPRO': 'Industrial Production Index',
    'TCU': 'Capacity Utilization: Manufacturing',
    
    # 금리/채권 지표
    'T10Y2Y': '10Y-2Y Treasury Spread',
    'DFF': 'Federal Funds Rate',
    'DFII10': '10-Year TIPS Real Interest Rate',
    
    # 인플레이션 지표
    'PCEPILFE': 'Core PCE Price Index (YoY)',
    'CPIAUCSL': 'Consumer Price Index',
    'PPIACO': 'Producer Price Index',
    'T5YIE': '5-Year Breakeven Inflation Rate',
    
    # 변동성 지표
    'BAMLH0A0HYM2': 'High Yield Spread',
    
    # 유동성 지표
    'WALCL': 'Fed Balance Sheet',
    'RRPONTSYD': 'Reverse Repo Balance',
    'M2SL': 'M2 Money Supply',
}

# VIX 티커 (yfinance)
VIX_TICKER = '^VIX'

# 카테고리별 가중치
WEIGHTS: Dict[str, float] = {
    'economy': 0.30,
    'rates': 0.25,
    'inflation': 0.20,
    'volatility': 0.15,
    'liquidity': 0.10
}

# 지표 카테고리 분류
INDICATOR_CATEGORIES: Dict[str, List[str]] = {
    'economy': ['UNRATE', 'UMCSENT', 'INDPRO', 'TCU'],
    'rates': ['T10Y2Y', 'DFF', 'DFII10'],
    'inflation': ['PCEPILFE', 'CPIAUCSL', 'PPIACO', 'T5YIE'],
    'volatility': ['VIX', 'BAMLH0A0HYM2'],
    'liquidity': ['WALCL', 'RRPONTSYD', 'M2SL']
}

# 점수화 임계값
SCORING_THRESHOLDS: Dict[str, Dict[str, float]] = {
    'UNRATE': {
        'excellent': 4.0,  # 4% 이하: 100점
        'poor': 6.0,       # 6% 이상: 0점
    },
    'T10Y2Y': {
        'excellent': 0.5,  # +0.5% 이상: 100점
        'poor': -0.5,      # -0.5% 이하: 0점
    },
    'VIX': {
        'excellent': 12.0,  # 12 이하: 100점
        'poor': 30.0,       # 30 이상: 0점
    },
    'UMCSENT': {
        'excellent': 100.0,  # 100 이상: 100점
        'poor': 50.0,        # 50 이하: 0점
    },
    'DFF': {
        'excellent': 2.0,   # 2% 이하: 100점 (낮은 금리 = 좋음)
        'poor': 5.0,        # 5% 이상: 0점
    },
    'DFII10': {
        'excellent': 0.5,   # 0.5% 이하: 100점
        'poor': 2.5,        # 2.5% 이상: 0점
    },
    'PCEPILFE': {
        'excellent': 2.0,   # 2% 이하: 100점
        'poor': 4.0,        # 4% 이상: 0점
    },
    'CPIAUCSL': {
        'excellent': 2.0,   # YoY 2% 이하: 100점
        'poor': 4.0,        # YoY 4% 이상: 0점
    },
    'PPIACO': {
        'excellent': 2.0,   # YoY 2% 이하: 100점
        'poor': 4.0,        # YoY 4% 이상: 0점
    },
    'T5YIE': {
        'excellent': 2.0,   # 2% 이하: 100점
        'poor': 3.5,        # 3.5% 이상: 0점
    },
    'BAMLH0A0HYM2': {
        'excellent': 3.0,   # 3% 이하: 100점
        'poor': 8.0,        # 8% 이상: 0점
    },
    'M2SL': {
        'excellent': 10.0,  # YoY 10% 이상: 100점
        'poor': -2.0,       # YoY 마이너스: 0점
    },
    'INDPRO': {
        'excellent': 3.0,   # YoY 3% 이상: 100점 (강한 경기 확장)
        'good': 1.0,        # YoY 1-3%: 70점 (정상 성장)
        'neutral': -1.0,    # YoY -1~1%: 40점 (둔화)
        'poor': -1.0,       # YoY -1% 이하: 0점 (위축)
    },
    'TCU': {
        'excellent': 75.0,  # 75-80%: 100점 (정상 범위)
        'good': 70.0,       # 70-75%: 60점 (둔화)
        'poor': 70.0,      # 70% 이하: 20점 (경기침체 신호)
        'overheat': 80.0,  # 80% 이상: 과열 우려 (인플레 압력)
    },
    'WALCL': {
        'excellent': 5.0,   # YoY 5% 이상 증가: 100점 (유동성 공급)
        'good': 0.0,        # YoY 0-5% 증가: 70점 (안정)
        'poor': -10.0,     # YoY 10% 이상 감소: 0점 (유동성 긴축)
    },
    'RRPONTSYD': {
        'excellent': 0.5,  # 0.5조 달러 이하: 100점 (적정 수준)
        'good': 1.0,       # 0.5-1조 달러: 80점 (보통)
        'neutral': 2.0,    # 1-2조 달러: 60점 (다소 높음)
        'poor': 2.0,       # 2조 달러 이상: 40점 (과도)
    },
}

# 자산배분 점수 구간
ALLOCATION_SCORES: Dict[str, Dict[str, tuple]] = {
    '80-100': {
        'stocks': (70, 80),
        'bonds': (15, 20),
        'cash': (5, 10),
        'real_estate': (5, 10)
    },
    '60-80': {
        'stocks': (50, 60),
        'bonds': (25, 30),
        'cash': (10, 15),
        'real_estate': (5, 10)
    },
    '40-60': {
        'stocks': (30, 40),
        'bonds': (40, 50),
        'cash': (15, 20),
        'real_estate': (5, 10)
    },
    '20-40': {
        'stocks': (15, 25),
        'bonds': (50, 60),
        'cash': (20, 25),
        'real_estate': (5, 10)
    },
    '0-20': {
        'stocks': (5, 15),
        'bonds': (35, 45),
        'cash': (40, 50),
        'real_estate': (5, 10)
    }
}

# 캐시 설정
CACHE_DIR = 'data'
CACHE_FILE = 'cache.json'
CACHE_EXPIRY_HOURS = 24

# 데이터 수집 설정
LOOKBACK_DAYS = 365

