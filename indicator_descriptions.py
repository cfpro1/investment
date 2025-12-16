"""
지표 설명 및 기준점 정의 모듈
"""
from typing import Dict, Tuple

# 지표 설명 및 기준점
INDICATOR_DESCRIPTIONS: Dict[str, Dict[str, any]] = {
    'UNRATE': {
        'description': '실업률 (Unemployment Rate)',
        'detail': '전체 노동력 중 실업자 비율. 낮을수록 경기가 좋음.',
        'criteria': {
            'excellent': '4% 이하: 양호 (100점)',
            'good': '4-5%: 보통 (70점)',
            'poor': '6% 이상: 주의 (0점)'
        }
    },
    'UMCSENT': {
        'description': '미시간 소비자신뢰지수',
        'detail': '소비자의 경제 전망에 대한 신뢰도. 높을수록 소비 의향이 높음.',
        'criteria': {
            'excellent': '100 이상: 양호 (100점)',
            'good': '70-100: 보통 (70점)',
            'poor': '50 이하: 주의 (0점)'
        }
    },
    'INDPRO': {
        'description': '산업생산지수 (Industrial Production Index)',
        'detail': '제조업, 광업, 전기·가스·수도업의 생산량 지수. YoY 증가율로 평가.',
        'criteria': {
            'excellent': '3% 이상: 강한 경기 확장 (100점)',
            'good': '1-3%: 정상 성장 (70점)',
            'neutral': '-1~1%: 둔화 (40점)',
            'poor': '-1% 이하: 위축 (0점)'
        }
    },
    'TCU': {
        'description': '제조업 가동률 (Capacity Utilization)',
        'detail': '제조업 설비 가동률. 너무 높으면 인플레 압력, 너무 낮으면 경기침체 신호.',
        'criteria': {
            'excellent': '75-80%: 정상 범위 (100점)',
            'good': '70-75%: 둔화 (60점)',
            'poor': '70% 이하: 경기침체 신호 (20점)',
            'overheat': '80% 이상: 과열 우려 (인플레 압력)'
        }
    },
    'T10Y2Y': {
        'description': '10년-2년 국채 스프레드',
        'detail': '장단기 금리 차이. 음수면 역전(경기침체 신호), 양수면 정상.',
        'criteria': {
            'excellent': '+0.5% 이상: 양호 (100점)',
            'good': '0~+0.5%: 보통 (70점)',
            'poor': '-0.5% 이하: 주의 (0점)'
        }
    },
    'DFF': {
        'description': '연방기금금리 (Federal Funds Rate)',
        'detail': '미 연준의 기준금리. 낮을수록 주식시장에 유리.',
        'criteria': {
            'excellent': '2% 이하: 양호 (100점)',
            'good': '2-3.5%: 보통 (70점)',
            'poor': '5% 이상: 주의 (0점)'
        }
    },
    'DFII10': {
        'description': '10년 TIPS 실질금리',
        'detail': '인플레이션을 제외한 실질 금리. 낮을수록 좋음.',
        'criteria': {
            'excellent': '0.5% 이하: 양호 (100점)',
            'good': '0.5-1.5%: 보통 (70점)',
            'poor': '2.5% 이상: 주의 (0점)'
        }
    },
    'PCEPILFE': {
        'description': '근원 PCE 물가지수 (Core PCE)',
        'detail': '에너지·식품 제외 소비자물가. 연준의 목표 인플레이션 지표.',
        'criteria': {
            'excellent': '2% 이하: 양호 (100점)',
            'good': '2-3%: 보통 (70점)',
            'poor': '4% 이상: 주의 (0점)'
        }
    },
    'CPIAUCSL': {
        'description': '소비자물가지수 (CPI)',
        'detail': '소비자가 구매하는 상품·서비스의 평균 가격 변화율.',
        'criteria': {
            'excellent': 'YoY 2% 이하: 양호 (100점)',
            'good': 'YoY 2-3%: 보통 (70점)',
            'poor': 'YoY 4% 이상: 주의 (0점)'
        }
    },
    'PPIACO': {
        'description': '생산자물가지수 (PPI)',
        'detail': '생산자가 받는 가격 변화율. CPI의 선행지표.',
        'criteria': {
            'excellent': 'YoY 2% 이하: 양호 (100점)',
            'good': 'YoY 2-3%: 보통 (70점)',
            'poor': 'YoY 4% 이상: 주의 (0점)'
        }
    },
    'T5YIE': {
        'description': '5년 브레이크이븐 인플레이션',
        'detail': '시장이 예상하는 5년 후 인플레이션율.',
        'criteria': {
            'excellent': '2% 이하: 양호 (100점)',
            'good': '2-2.5%: 보통 (70점)',
            'poor': '3.5% 이상: 주의 (0점)'
        }
    },
    'VIX': {
        'description': 'VIX (변동성 지수)',
        'detail': 'S&P 500 옵션 기반 변동성 지수. 낮을수록 시장이 안정적.',
        'criteria': {
            'excellent': '12 이하: 양호 (100점)',
            'good': '12-20: 보통 (70점)',
            'poor': '30 이상: 주의 (0점)'
        }
    },
    'BAMLH0A0HYM2': {
        'description': '하이일드 스프레드',
        'detail': '하이일드 채권과 국채 금리 차이. 높을수록 신용위험 증가.',
        'criteria': {
            'excellent': '3% 이하: 양호 (100점)',
            'good': '3-5%: 보통 (70점)',
            'poor': '8% 이상: 주의 (0점)'
        }
    },
    'WALCL': {
        'description': '연준 대차대조표',
        'detail': '연준이 보유한 자산 규모. 양적완화/긴축의 지표.',
        'criteria': {
            'excellent': '증가: 유동성 공급 (긍정적)',
            'poor': '감소: 유동성 회수 (부정적)'
        }
    },
    'RRPONTSYD': {
        'description': '역레포 잔액',
        'detail': '은행이 연준에 예치한 초과 유동성. 높을수록 유동성 과잉.',
        'criteria': {
            'excellent': '적정 수준: 양호',
            'poor': '과도: 유동성 과잉'
        }
    },
    'M2SL': {
        'description': 'M2 통화량',
        'detail': '경제에 공급된 통화량. YoY 증가율로 평가.',
        'criteria': {
            'excellent': 'YoY 10% 이상: 양호 (100점)',
            'good': 'YoY 5-10%: 보통 (70점)',
            'poor': 'YoY 마이너스: 주의 (0점)'
        }
    }
}



