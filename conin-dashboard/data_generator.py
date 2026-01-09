import random
from datetime import datetime, timedelta
from typing import List, Dict, Literal
import pandas as pd

Coin = Literal['BTC', 'ETH', 'ADA', 'DOT', 'XRP', 'SOL', 'DOGE']
Signal = Literal['Long', 'Stay', 'Short']

COIN_BASE_PRICES = {
    'BTC': 65000,
    'ETH': 3500,
    'ADA': 0.5,
    'DOT': 7,
    'XRP': 0.6,
    'SOL': 150,
    'DOGE': 0.15,
}

def random_between(min_val: float, max_val: float) -> float:
    return random.random() * (max_val - min_val) + min_val

def random_signal() -> Signal:
    rand = random.random()
    if rand < 0.4:
        return 'Long'
    elif rand < 0.7:
        return 'Stay'
    else:
        return 'Short'

def generate_models() -> List[Dict]:
    """3개 모델 생성"""
    return [
        {'id': 'G', 'name': 'Model G', 'performance3M': random_between(-15, 45)},
        {'id': 'A', 'name': 'Model A', 'performance3M': random_between(-15, 45)},
        {'id': 'B', 'name': 'Model B', 'performance3M': random_between(-15, 45)},
    ]

def generate_price_data(coin: Coin, days: int) -> pd.DataFrame:
    """가격 데이터 생성"""
    base_price = COIN_BASE_PRICES[coin]
    dates = []
    prices = []
    current_price = base_price
    today = datetime.now()
    
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        change = random_between(-0.05, 0.05)
        current_price = max(current_price * (1 + change), base_price * 0.5)
        dates.append(date)
        prices.append(current_price)
    
    return pd.DataFrame({'date': dates, 'price': prices})

def generate_today_signals(models: List[Dict]) -> pd.DataFrame:
    """오늘의 시그널 생성"""
    coins = ['BTC', 'ETH', 'ADA', 'DOT', 'XRP', 'SOL', 'DOGE']
    data = []
    
    for coin in coins:
        price_data = generate_price_data(coin, 30)
        current_price = price_data['price'].iloc[-1]
        
        data.append({
            'coin': coin,
            'current_price': current_price,
            'modelG': random_signal(),
            'modelA': random_signal(),
            'modelB': random_signal(),
        })
    
    return pd.DataFrame(data)

def generate_signal_history(coin: Coin, days: int = 7) -> pd.DataFrame:
    """시그널 히스토리 생성"""
    today = datetime.now()
    data = []
    base_price = COIN_BASE_PRICES[coin]
    
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        price = base_price * random_between(0.9, 1.1)
        data.append({
            'date': date,
            'coin': coin,
            'signal': random_signal(),
            'price': price,
        })
    
    return pd.DataFrame(data)

def generate_model_signal_history(coin: Coin, model_id: str, days: int = 7) -> pd.DataFrame:
    """특정 모델의 시그널 히스토리 생성 (정답 여부 포함)"""
    today = datetime.now()
    data = []
    base_price = COIN_BASE_PRICES[coin]
    prices = []
    
    # 먼저 모든 날짜의 가격 생성
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        if i == days - 1:
            price = base_price * random_between(0.9, 1.1)
        else:
            # 이전 가격을 기준으로 변동
            prev_price = prices[-1]
            change = random_between(-0.05, 0.05)
            price = prev_price * (1 + change)
        prices.append(price)
    
    # 시그널과 정답 여부 생성
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        price = prices[days - 1 - i]
        signal = random_signal()
        
        # 정답 여부 판단: 다음 날 가격과 비교
        is_correct = None
        if i > 0:  # 마지막 날이 아닌 경우
            next_price = prices[days - 1 - (i - 1)]
            price_change = (next_price - price) / price * 100
            
            if signal == 'Long':
                is_correct = price_change > 1.0  # 1% 이상 상승
            elif signal == 'Short':
                is_correct = price_change < -1.0  # 1% 이상 하락
            else:  # Stay
                is_correct = abs(price_change) <= 1.0  # 1% 이내 변동
        
        data.append({
            'date': date,
            'coin': coin,
            'model': model_id,
            'signal': signal,
            'price': price,
            'is_correct': is_correct,
        })
    
    return pd.DataFrame(data)

def generate_performance_data(model_id: str) -> pd.DataFrame:
    """성과 데이터 생성"""
    periods = ['1M', '3M', '6M', '1Y', '2Y', '3Y']
    period_multipliers = {
        '1M': 1, '3M': 1, '6M': 1.2,
        '1Y': 1.5, '2Y': 2, '3Y': 2.5
    }
    
    data = []
    for period in periods:
        base_return = random_between(-20, 50)
        data.append({
            'period': period,
            'return': base_return * period_multipliers[period],
            'sharpeRatio': random_between(0.5, 2.5),
            'winRate': random_between(45, 75),
            'maxDrawdown': random_between(-5, -25),
            'numTrades': int(random_between(10, 100)),
        })
    
    return pd.DataFrame(data)

def generate_cumulative_returns(days: int) -> pd.DataFrame:
    """누적 수익률 생성"""
    today = datetime.now()
    dates = []
    returns = []
    cumulative_return = 0
    
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        daily_return = random_between(-2, 2)
        cumulative_return += daily_return
        dates.append(date)
        returns.append(cumulative_return)
    
    return pd.DataFrame({'date': dates, 'return': returns})

def generate_model_positions(model_id: str) -> pd.DataFrame:
    """현재 포지션 생성"""
    coins = ['BTC', 'ETH', 'ADA', 'DOT', 'XRP', 'SOL', 'DOGE']
    data = []
    
    for coin in coins:
        base_price = COIN_BASE_PRICES[coin]
        entry_price = base_price * random_between(0.9, 1.1)
        current_price = base_price * random_between(0.85, 1.15)
        pnl = ((current_price - entry_price) / entry_price) * 100
        
        data.append({
            'coin': coin,
            'signal': random_signal(),
            'entryPrice': entry_price,
            'currentPrice': current_price,
            'pnl': pnl,
        })
    
    return pd.DataFrame(data)

def generate_signal_history_all(days: int = 20) -> pd.DataFrame:
    """전체 시그널 히스토리 생성 (정답 여부 포함)"""
    coins = ['BTC', 'ETH', 'ADA', 'DOT', 'XRP', 'SOL', 'DOGE']
    data = []
    today = datetime.now()
    
    # 코인별 가격 히스토리 저장
    coin_prices = {coin: [] for coin in coins}
    
    # 먼저 가격 데이터 생성
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i // 3)
        coin = random.choice(coins)
        base_price = COIN_BASE_PRICES[coin]
        
        if coin not in coin_prices or len(coin_prices[coin]) == 0:
            price = base_price * random_between(0.9, 1.1)
        else:
            prev_price = coin_prices[coin][-1]['price']
            change = random_between(-0.05, 0.05)
            price = prev_price * (1 + change)
        
        coin_prices[coin].append({'date': date, 'price': price})
    
    # 시그널과 정답 여부 생성
    coin_price_idx = {coin: 0 for coin in coins}
    
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i // 3)
        coin = random.choice(coins)
        
        if coin_price_idx[coin] < len(coin_prices[coin]):
            price_data = coin_prices[coin][coin_price_idx[coin]]
            price = price_data['price']
            coin_price_idx[coin] += 1
        else:
            base_price = COIN_BASE_PRICES[coin]
            price = base_price * random_between(0.9, 1.1)
        
        signal = random_signal()
        
        # 정답 여부 판단
        is_correct = None
        if i > 0 and coin_price_idx[coin] < len(coin_prices[coin]):
            next_price_data = coin_prices[coin][coin_price_idx[coin]]
            next_price = next_price_data['price']
            price_change = (next_price - price) / price * 100
            
            if signal == 'Long':
                is_correct = price_change > 1.0
            elif signal == 'Short':
                is_correct = price_change < -1.0
            else:  # Stay
                is_correct = abs(price_change) <= 1.0
        
        data.append({
            'date': date,
            'coin': coin,
            'signal': signal,
            'price': price,
            'is_correct': is_correct,
        })
    
    return pd.DataFrame(data).sort_values('date', ascending=False)

