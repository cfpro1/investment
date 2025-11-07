import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import json
import os
import requests

# ============================================
# OpenAI API 키 설정
# ============================================
# 아래에 OpenAI API 키를 입력하세요
# API 키는 https://platform.openai.com 에서 발급받을 수 있습니다.
OPENAI_API_KEY = ""  # 여기에 API 키를 입력하세요 (예: "sk-...")

# 페이지 설정
st.set_page_config(
    page_title="거시경제 지표 분석 시스템",
    page_icon="📈",
    layout="wide"
)

# 제목
st.title("거시경제 지표 분석 시스템")
st.markdown("---")

# 데이터 수집 함수
@st.cache_data(ttl=300)  # 5분 캐시
def fetch_market_data():
    """거시경제 지표 데이터 수집"""
    try:
        # 최근 5년 데이터 수집 (3년, 5년 차트를 위해 충분한 데이터 확보)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1825)  # 5년 (1825일)
        
        data = {}
        
        # VIX (심리지수/변동성 지수)
        try:
            vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
            if isinstance(vix.columns, pd.MultiIndex):
                vix.columns = vix.columns.droplevel(1)
            if 'Close' in vix.columns and len(vix) > 0:
                data['vix'] = vix[['Close']].dropna()
            else:
                data['vix'] = None
        except:
            data['vix'] = None
        
        # DXY (달러 인덱스)
        dxy = None
        for symbol in ["DX-Y.NYB", "^DX-Y", "DX=F"]:
            try:
                temp = yf.download(symbol, start=start_date, end=end_date, progress=False)
                if isinstance(temp.columns, pd.MultiIndex):
                    temp.columns = temp.columns.droplevel(1)
                if 'Close' in temp.columns and len(temp) > 0:
                    dxy = temp[['Close']].dropna()
                    if len(dxy) > 0:
                        break
            except:
                continue
        data['dxy'] = dxy
        
        # 금리 - 10년 국채 수익률 (^TNX)
        try:
            tnx = yf.download("^TNX", start=start_date, end=end_date, progress=False)
            if isinstance(tnx.columns, pd.MultiIndex):
                tnx.columns = tnx.columns.droplevel(1)
            if 'Close' in tnx.columns and len(tnx) > 0:
                data['tnx'] = tnx[['Close']].dropna()
            else:
                data['tnx'] = None
        except:
            data['tnx'] = None
        
        # 금리 - 3개월 국채 수익률 (^IRX)
        try:
            irx = yf.download("^IRX", start=start_date, end=end_date, progress=False)
            if isinstance(irx.columns, pd.MultiIndex):
                irx.columns = irx.columns.droplevel(1)
            if 'Close' in irx.columns and len(irx) > 0:
                data['irx'] = irx[['Close']].dropna()
            else:
                data['irx'] = None
        except:
            data['irx'] = None
        
        # S&P500
        try:
            sp500 = yf.download("^GSPC", start=start_date, end=end_date, progress=False)
            if isinstance(sp500.columns, pd.MultiIndex):
                sp500.columns = sp500.columns.droplevel(1)
            if 'Close' in sp500.columns and len(sp500) > 0:
                data['sp500'] = sp500[['Close']].dropna()
            else:
                data['sp500'] = None
        except:
            data['sp500'] = None
        
        # M2 통화량 (FRED API 사용)
        try:
            # FRED API를 통해 M2 통화량 데이터 수집 (M2SL - M2 Money Stock)
            end_date_str = end_date.strftime('%Y-%m-%d')
            start_date_str = start_date.strftime('%Y-%m-%d')
            
            # FRED API 호출 (API 키 없이도 가능, 게스트 API 사용)
            # 참고: FRED API 무료 키는 https://fred.stlouisfed.org/docs/api/api_key.html 에서 발급 가능
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                'series_id': 'M2SL',
                'api_key': 'guest',  # 게스트 API 키 (무료, 제한적)
                'file_type': 'json',
                'observation_start': start_date_str,
                'observation_end': end_date_str,
                'frequency': 'w',  # 주간 데이터 (일일 데이터는 제한적)
                'units': 'lin'  # 선형 (원본 값)
            }
            
            # User-Agent 헤더 추가 (일부 서버에서 필요)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=20)
            
            if response.status_code == 200:
                json_data = response.json()
                
                # 에러 체크
                if 'error_code' in json_data:
                    print(f"M2 통화량 API 오류: {json_data.get('error_message', 'Unknown error')}")
                    data['m2'] = None
                else:
                    observations = json_data.get('observations', [])
                    
                    if observations:
                        # 데이터프레임 생성
                        dates = []
                        values = []
                        for obs in observations:
                            if obs.get('value') != '.' and obs.get('value') is not None:
                                try:
                                    dates.append(pd.to_datetime(obs['date']))
                                    values.append(float(obs['value']))
                                except:
                                    continue
                        
                        if dates and values:
                            m2_df = pd.DataFrame({'Close': values}, index=dates)
                            m2_df = m2_df.sort_index()
                            # 주간 데이터를 일일 데이터로 보간 (가장 최근 값으로 forward fill)
                            date_range = pd.date_range(start=m2_df.index[0], end=m2_df.index[-1], freq='D')
                            m2_df = m2_df.reindex(date_range)
                            m2_df = m2_df.ffill()  # forward fill
                            # 최근 5년 데이터 유지 (필터링 제거)
                            m2_df = m2_df.dropna()
                            
                            if len(m2_df) > 0:
                                data['m2'] = m2_df
                                print(f"M2 통화량 데이터 수집 성공: {len(m2_df)}개 데이터 포인트")
                            else:
                                print("M2 통화량: 필터링 후 데이터가 없음")
                                data['m2'] = None
                        else:
                            print("M2 통화량: 유효한 데이터 포인트 없음")
                            data['m2'] = None
                    else:
                        print("M2 통화량: API 응답에 observations 없음")
                        data['m2'] = None
            else:
                print(f"M2 통화량 API 호출 실패: HTTP {response.status_code}")
                if response.status_code == 403:
                    print("API 키 인증 문제일 수 있습니다. FRED API 무료 키 발급을 권장합니다.")
                data['m2'] = None
        except requests.exceptions.Timeout:
            print("M2 통화량: API 요청 타임아웃")
            data['m2'] = None
        except requests.exceptions.ConnectionError:
            print("M2 통화량: 네트워크 연결 오류")
            data['m2'] = None
        except Exception as e:
            print(f"M2 통화량 데이터 수집 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            data['m2'] = None
        
        # 유동성 지표 (TLT - 20년 국채 ETF) - M2 보완 지표
        try:
            tlt = yf.download("TLT", start=start_date, end=end_date, progress=False)
            if isinstance(tlt.columns, pd.MultiIndex):
                tlt.columns = tlt.columns.droplevel(1)
            if 'Close' in tlt.columns and len(tlt) > 0:
                data['tlt'] = tlt[['Close']].dropna()
            else:
                data['tlt'] = None
        except:
            data['tlt'] = None
        
        # ISM 대체 - 제조업 관련 ETF나 지수 사용
        # 실제 ISM은 월간 데이터이므로 차트용으로는 제한적
        # 대신 산업 지수 사용
        try:
            xli = yf.download("XLI", start=start_date, end=end_date, progress=False)  # 산업 ETF
            if isinstance(xli.columns, pd.MultiIndex):
                xli.columns = xli.columns.droplevel(1)
            if 'Close' in xli.columns and len(xli) > 0:
                data['xli'] = xli[['Close']].dropna()
            else:
                data['xli'] = None
        except:
            data['xli'] = None
        
        # CPI 대체 - TIPS (인플레이션 보호 국채) 사용
        # TIP ETF나 TIPS 스프레드로 인플레이션 기대 측정
        try:
            tip = yf.download("TIP", start=start_date, end=end_date, progress=False)
            if isinstance(tip.columns, pd.MultiIndex):
                tip.columns = tip.columns.droplevel(1)
            if 'Close' in tip.columns and len(tip) > 0:
                data['tip'] = tip[['Close']].dropna()
            else:
                data['tip'] = None
        except:
            data['tip'] = None
        
        # 고용지표 대체 - 소비자 관련 ETF나 소비재 섹터 사용
        try:
            xly = yf.download("XLY", start=start_date, end=end_date, progress=False)  # 소비재 ETF
            if isinstance(xly.columns, pd.MultiIndex):
                xly.columns = xly.columns.droplevel(1)
            if 'Close' in xly.columns and len(xly) > 0:
                data['xly'] = xly[['Close']].dropna()
            else:
                data['xly'] = None
        except:
            data['xly'] = None
        
        # 금 (Gold) - 안전자산, 인플레이션 헤지
        try:
            gold = yf.download("GC=F", start=start_date, end=end_date, progress=False)  # 금 선물
            if isinstance(gold.columns, pd.MultiIndex):
                gold.columns = gold.columns.droplevel(1)
            if 'Close' in gold.columns and len(gold) > 0:
                data['gold'] = gold[['Close']].dropna()
            else:
                data['gold'] = None
        except:
            data['gold'] = None
        
        # 구리 (Copper) - 경기 선행지표, 산업 활동
        try:
            copper = yf.download("HG=F", start=start_date, end=end_date, progress=False)  # 구리 선물
            if isinstance(copper.columns, pd.MultiIndex):
                copper.columns = copper.columns.droplevel(1)
            if 'Close' in copper.columns and len(copper) > 0:
                data['copper'] = copper[['Close']].dropna()
            else:
                data['copper'] = None
        except:
            data['copper'] = None
        
        # 원유 (Crude Oil) - 에너지, 인플레이션
        try:
            oil = yf.download("CL=F", start=start_date, end=end_date, progress=False)  # WTI 원유 선물
            if isinstance(oil.columns, pd.MultiIndex):
                oil.columns = oil.columns.droplevel(1)
            if 'Close' in oil.columns and len(oil) > 0:
                data['oil'] = oil[['Close']].dropna()
            else:
                data['oil'] = None
        except:
            data['oil'] = None
        
        # 부동산 (Real Estate ETF)
        try:
            vnq = yf.download("VNQ", start=start_date, end=end_date, progress=False)  # 부동산 ETF
            if isinstance(vnq.columns, pd.MultiIndex):
                vnq.columns = vnq.columns.droplevel(1)
            if 'Close' in vnq.columns and len(vnq) > 0:
                data['vnq'] = vnq[['Close']].dropna()
            else:
                data['vnq'] = None
        except:
            data['vnq'] = None
        
        # 고수익 채권 스프레드 (High Yield Spread 대체) - HYG ETF 사용
        try:
            hyg = yf.download("HYG", start=start_date, end=end_date, progress=False)  # 고수익 채권 ETF
            if isinstance(hyg.columns, pd.MultiIndex):
                hyg.columns = hyg.columns.droplevel(1)
            if 'Close' in hyg.columns and len(hyg) > 0:
                data['hyg'] = hyg[['Close']].dropna()
            else:
                data['hyg'] = None
        except:
            data['hyg'] = None
        
        # 비트코인 (BTC) - 리스크 자산, 디지털 자산
        try:
            btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)
            if isinstance(btc.columns, pd.MultiIndex):
                btc.columns = btc.columns.droplevel(1)
            if 'Close' in btc.columns and len(btc) > 0:
                data['btc'] = btc[['Close']].dropna()
            else:
                data['btc'] = None
        except:
            data['btc'] = None
        
        return data
    except Exception as e:
        st.error(f"데이터 수집 중 오류 발생: {str(e)}")
        return None

# 점수 계산 함수
def calculate_score(data):
    """거시경제 지표를 기반으로 종합 점수 계산"""
    if data is None:
        return 0, {}
    
    score = 0
    details = {}
    
    # 1. VIX (심리지수) - 낮을수록 좋음
    if data.get('vix') is not None and len(data['vix']) > 0:
        current_vix = data['vix']['Close'].iloc[-1]
        if current_vix <= 15:
            vix_score = 25
        elif current_vix <= 20:
            vix_score = 15
        elif current_vix <= 30:
            vix_score = 0
        else:
            vix_score = -15
        score += vix_score
        details['VIX'] = {'value': current_vix, 'score': vix_score, 'name': '심리지수'}
    
    # 2. DXY (달러 인덱스) - 적정 수준이 좋음
    if data.get('dxy') is not None and len(data['dxy']) > 0:
        current_dxy = data['dxy']['Close'].iloc[-1]
        if 90 <= current_dxy <= 110:
            dxy_score = 15
        elif 85 <= current_dxy < 90 or 110 < current_dxy <= 115:
            dxy_score = 0
        else:
            dxy_score = -10
        score += dxy_score
        details['DXY'] = {'value': current_dxy, 'score': dxy_score, 'name': '달러 인덱스'}
    
    # 3. 금리 (10년 국채) - 적정 수준이 좋음
    if data.get('tnx') is not None and len(data['tnx']) > 0:
        current_tnx = data['tnx']['Close'].iloc[-1]
        # 금리가 너무 높으면 부담, 너무 낮으면 경기 침체 신호
        if 2.0 <= current_tnx <= 4.5:
            tnx_score = 15
        elif 1.5 <= current_tnx < 2.0 or 4.5 < current_tnx <= 5.5:
            tnx_score = 5
        elif current_tnx < 1.5:
            tnx_score = -10  # 경기 침체 우려
        else:
            tnx_score = -15  # 고금리 부담
        score += tnx_score
        details['금리(10년)'] = {'value': current_tnx, 'score': tnx_score, 'name': '10년 국채 수익률'}
    
    # 4. 금리 역전 (Yield Curve) - 10년 vs 3개월 비교
    if data.get('tnx') is not None and data.get('irx') is not None:
        if len(data['tnx']) > 0 and len(data['irx']) > 0:
            current_tnx = data['tnx']['Close'].iloc[-1]
            current_irx = data['irx']['Close'].iloc[-1]
            spread = current_tnx - current_irx
            # 역전이 발생하면 경기 침체 신호
            if spread > 1.0:
                yield_score = 10  # 정상적인 곡선
            elif spread > 0:
                yield_score = 0
            else:
                yield_score = -20  # 역전 발생
            score += yield_score
            details['금리스프레드'] = {'value': spread, 'score': yield_score, 'name': '10년-3개월 스프레드'}
    
    # 5. S&P500 추세
    if data.get('sp500') is not None and len(data['sp500']) > 0:
        current_sp500 = data['sp500']['Close'].iloc[-1]
        if len(data['sp500']) >= 50:
            ma50 = data['sp500']['Close'].rolling(50).mean().iloc[-1]
            ma20 = data['sp500']['Close'].rolling(20).mean().iloc[-1]
            if current_sp500 > ma50 > ma20:
                sp500_score = 15  # 강한 상승 추세
            elif current_sp500 > ma20:
                sp500_score = 5
            else:
                sp500_score = -10
        elif len(data['sp500']) >= 20:
            ma20 = data['sp500']['Close'].rolling(20).mean().iloc[-1]
            if current_sp500 > ma20:
                sp500_score = 10
            else:
                sp500_score = -5
        else:
            sp500_score = 0
        score += sp500_score
        details['S&P500'] = {'value': current_sp500, 'score': sp500_score, 'name': 'S&P 500'}
    
    # 6. M2 통화량 - 유동성 지표
    if data.get('m2') is not None and len(data['m2']) > 0:
        current_m2 = data['m2']['Close'].iloc[-1]
        if len(data['m2']) >= 30:
            # 전년 대비 성장률 계산
            year_ago_idx = len(data['m2']) - min(252, len(data['m2']))  # 1년 전 (약 252 거래일)
            if year_ago_idx >= 0:
                year_ago_m2 = data['m2']['Close'].iloc[year_ago_idx]
                yoy_growth = ((current_m2 - year_ago_m2) / year_ago_m2) * 100
                
                # M2 성장률이 적정 수준(5-10%)이면 긍정, 너무 높으면 인플레이션 우려
                if 5 <= yoy_growth <= 10:
                    m2_score = 15  # 적정 성장
                elif 3 <= yoy_growth < 5 or 10 < yoy_growth <= 12:
                    m2_score = 5
                elif yoy_growth > 12:
                    m2_score = -10  # 과도한 성장 (인플레이션 우려)
                else:
                    m2_score = -5  # 성장 둔화 (경기 침체 우려)
            else:
                m2_score = 0
        else:
            m2_score = 0
        score += m2_score
        details['M2통화량'] = {'value': current_m2, 'score': m2_score, 'name': 'M2 통화량 (십억 달러)'}
    
    # 7. 유동성 지표 (TLT - 장기 채권 ETF)
    if data.get('tlt') is not None and len(data['tlt']) > 0:
        current_tlt = data['tlt']['Close'].iloc[-1]
        if len(data['tlt']) >= 20:
            ma20 = data['tlt']['Close'].rolling(20).mean().iloc[-1]
            # TLT가 상승하면 유동성 증가 (금리 하락)
            if current_tlt > ma20:
                tlt_score = 10
            else:
                tlt_score = -5
        else:
            tlt_score = 0
        score += tlt_score
        details['유동성'] = {'value': current_tlt, 'score': tlt_score, 'name': 'TLT (장기채권)'}
    
    # 8. 제조업 지표 (XLI - 산업 ETF)
    if data.get('xli') is not None and len(data['xli']) > 0:
        current_xli = data['xli']['Close'].iloc[-1]
        if len(data['xli']) >= 20:
            ma20 = data['xli']['Close'].rolling(20).mean().iloc[-1]
            if current_xli > ma20:
                xli_score = 10
            else:
                xli_score = -5
        else:
            xli_score = 0
        score += xli_score
        details['제조업'] = {'value': current_xli, 'score': xli_score, 'name': 'XLI (산업)'}
    
    # 9. 인플레이션 지표 (TIP - TIPS ETF)
    if data.get('tip') is not None and len(data['tip']) > 0:
        current_tip = data['tip']['Close'].iloc[-1]
        if len(data['tip']) >= 20:
            ma20 = data['tip']['Close'].rolling(20).mean().iloc[-1]
            # TIP이 상승하면 인플레이션 기대 상승
            if current_tip > ma20:
                tip_score = 5  # 적정 인플레이션 기대
            else:
                tip_score = -5  # 디플레이션 우려
        else:
            tip_score = 0
        score += tip_score
        details['인플레이션'] = {'value': current_tip, 'score': tip_score, 'name': 'TIP (TIPS)'}
    
    # 10. 고용/소비 지표 (XLY - 소비재 ETF)
    if data.get('xly') is not None and len(data['xly']) > 0:
        current_xly = data['xly']['Close'].iloc[-1]
        if len(data['xly']) >= 20:
            ma20 = data['xly']['Close'].rolling(20).mean().iloc[-1]
            if current_xly > ma20:
                xly_score = 10
            else:
                xly_score = -5
        else:
            xly_score = 0
        score += xly_score
        details['소비/고용'] = {'value': current_xly, 'score': xly_score, 'name': 'XLY (소비재)'}
    
    # 11. 금 (Gold) - 안전자산, 인플레이션 헤지
    if data.get('gold') is not None and len(data['gold']) > 0:
        current_gold = data['gold']['Close'].iloc[-1]
        if len(data['gold']) >= 20:
            ma20 = data['gold']['Close'].rolling(20).mean().iloc[-1]
            # 금이 상승하면 인플레이션 우려 또는 불확실성 증가
            if current_gold > ma20:
                gold_score = 5  # 인플레이션 헤지 또는 불확실성 증가
            else:
                gold_score = -5
        else:
            gold_score = 0
        score += gold_score
        details['금'] = {'value': current_gold, 'score': gold_score, 'name': '금 (Gold)'}
    
    # 12. 구리 (Copper) - 경기 선행지표
    if data.get('copper') is not None and len(data['copper']) > 0:
        current_copper = data['copper']['Close'].iloc[-1]
        if len(data['copper']) >= 20:
            ma20 = data['copper']['Close'].rolling(20).mean().iloc[-1]
            # 구리가 상승하면 산업 활동 증가
            if current_copper > ma20:
                copper_score = 10
            else:
                copper_score = -5
        else:
            copper_score = 0
        score += copper_score
        details['구리'] = {'value': current_copper, 'score': copper_score, 'name': '구리 (Copper)'}
    
    # 13. 원유 (Crude Oil) - 에너지, 인플레이션
    if data.get('oil') is not None and len(data['oil']) > 0:
        current_oil = data['oil']['Close'].iloc[-1]
        if len(data['oil']) >= 20:
            ma20 = data['oil']['Close'].rolling(20).mean().iloc[-1]
            # 원유가 적정 수준이면 경기 회복, 너무 높으면 인플레이션 부담
            if 60 <= current_oil <= 100:
                if current_oil > ma20:
                    oil_score = 5
                else:
                    oil_score = 0
            elif current_oil > 100:
                oil_score = -10  # 높은 인플레이션 부담
            else:
                oil_score = -5  # 경기 침체 우려
        else:
            oil_score = 0
        score += oil_score
        details['원유'] = {'value': current_oil, 'score': oil_score, 'name': '원유 (WTI)'}
    
    # 14. 부동산 (VNQ)
    if data.get('vnq') is not None and len(data['vnq']) > 0:
        current_vnq = data['vnq']['Close'].iloc[-1]
        if len(data['vnq']) >= 20:
            ma20 = data['vnq']['Close'].rolling(20).mean().iloc[-1]
            if current_vnq > ma20:
                vnq_score = 8
            else:
                vnq_score = -5
        else:
            vnq_score = 0
        score += vnq_score
        details['부동산'] = {'value': current_vnq, 'score': vnq_score, 'name': 'VNQ (부동산)'}
    
    # 15. 고수익 채권 스프레드 (HYG)
    if data.get('hyg') is not None and len(data['hyg']) > 0:
        current_hyg = data['hyg']['Close'].iloc[-1]
        if len(data['hyg']) >= 20:
            ma20 = data['hyg']['Close'].rolling(20).mean().iloc[-1]
            # HYG 하락 = 스프레드 확대 = 신용 리스크 증가
            if current_hyg > ma20:
                hyg_score = 8  # 신용 리스크 감소
            else:
                hyg_score = -8  # 신용 리스크 증가
        else:
            hyg_score = 0
        score += hyg_score
        details['신용리스크'] = {'value': current_hyg, 'score': hyg_score, 'name': 'HYG (고수익채권)'}
    
    # 16. 비트코인 (BTC) - 리스크 자산
    if data.get('btc') is not None and len(data['btc']) > 0:
        current_btc = data['btc']['Close'].iloc[-1]
        if len(data['btc']) >= 20:
            ma20 = data['btc']['Close'].rolling(20).mean().iloc[-1]
            # BTC 상승 = 리스크 자산 선호
            if current_btc > ma20:
                btc_score = 5
            else:
                btc_score = -5
        else:
            btc_score = 0
        score += btc_score
        details['비트코인'] = {'value': current_btc, 'score': btc_score, 'name': 'BTC (비트코인)'}
    
    return score, details

# 지표별 해석 함수
def interpret_indicator(indicator_name, value, score, details_dict, data_dict=None):
    """각 지표에 대한 상세 해석"""
    interpretations = {
        'VIX': {
            'title': 'VIX (변동성 지수 / 심리지수)',
            'description': '시장의 공포와 탐욕을 측정하는 지표입니다. 낮을수록 시장이 안정적입니다.',
            'good': 'VIX가 15 이하로 낮아 시장이 매우 안정적입니다. 투자자 심리가 낙관적이며, 리스크 자산에 유리합니다.',
            'neutral': 'VIX가 15-30 범위로 보통 수준입니다. 시장이 정상적인 변동성을 보이고 있습니다.',
            'bad': 'VIX가 30을 초과하여 시장 불안이 높습니다. 리스크 자산에 대한 신중한 접근이 필요합니다.',
            'threshold_good': 15,
            'threshold_bad': 30
        },
        'DXY': {
            'title': 'DXY (달러 인덱스)',
            'description': '달러의 강세/약세를 나타내는 지표입니다. 신흥국 자본 유출과 연관됩니다.',
            'good': '달러가 적정 수준(90-110)으로 유지되어 글로벌 자본 흐름이 안정적입니다.',
            'neutral': '달러가 약간의 변동성을 보이고 있으나 큰 영향은 없습니다.',
            'bad': '달러가 극단적 수준으로 달러 강세는 신흥국 자본 유출을, 약세는 달러 신뢰도 하락을 의미할 수 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '금리(10년)': {
            'title': '금리 (10년 국채 수익률)',
            'description': '장기 금리를 나타내며, 차입 비용과 경기 전망을 반영합니다.',
            'good': '금리가 적정 수준(2-4.5%)으로 경기가 건강하게 성장하고 있습니다.',
            'neutral': '금리가 보통 수준으로 경제가 정상 범위 내에서 움직이고 있습니다.',
            'bad': '금리가 너무 낮으면 경기 침체 우려, 너무 높으면 차입 부담이 증가합니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '금리스프레드': {
            'title': '금리 스프레드 (10년-3개월)',
            'description': '장단기 금리 차이로 경기 침체 선행지표로 활용됩니다.',
            'good': '정상적인 금리 곡선으로 경기 전망이 양호합니다.',
            'neutral': '금리 곡선이 평탄화되고 있으나 역전은 아닙니다.',
            'bad': '금리 역전이 발생하여 경기 침체 가능성이 높아졌습니다. 과거 역전 후 경기 침체 사례가 많습니다.',
            'threshold_good': 1.0,
            'threshold_bad': 0
        },
        'S&P500': {
            'title': 'S&P 500',
            'description': '미국 주식시장의 대표 지수로 경기와 기업 실적을 반영합니다.',
            'good': '강한 상승 추세로 기업 실적과 경기 전망이 양호합니다.',
            'neutral': '시장이 횡보 중으로 방향성이 명확하지 않습니다.',
            'bad': '하락 추세로 시장 신뢰도가 낮아지고 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '유동성': {
            'title': '유동성 (TLT)',
            'description': '장기 채권 가격으로 유동성 상황을 간접적으로 나타냅니다.',
            'good': '유동성이 충분하여 시장이 원활하게 작동하고 있습니다.',
            'neutral': '유동성이 보통 수준입니다.',
            'bad': '유동성이 부족하여 시장 변동성이 커질 수 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '제조업': {
            'title': '제조업 (XLI)',
            'description': '제조업 활동을 나타내는 선행지표입니다.',
            'good': '제조업이 활발하여 경기가 회복되고 있습니다.',
            'neutral': '제조업이 보통 수준입니다.',
            'bad': '제조업이 둔화되어 경기 전망이 약화되고 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '인플레이션': {
            'title': '인플레이션 (TIP)',
            'description': '인플레이션 보호 국채로 물가 상승 기대를 반영합니다.',
            'good': '적정 수준의 인플레이션 기대로 경기가 건강합니다.',
            'neutral': '인플레이션 기대가 보통 수준입니다.',
            'bad': '인플레이션 기대가 낮아 디플레이션 우려가 있거나, 너무 높아 금리 부담이 증가할 수 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '소비/고용': {
            'title': '소비/고용 (XLY)',
            'description': '소비재 섹터로 내수와 고용 상황을 간접적으로 나타냅니다.',
            'good': '소비와 고용이 활발하여 내수 경제가 건강합니다.',
            'neutral': '소비와 고용이 보통 수준입니다.',
            'bad': '소비와 고용이 둔화되어 내수 경제가 약화되고 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        'M2통화량': {
            'title': 'M2 통화량',
            'description': '경제 내 통화 공급량으로 유동성과 인플레이션 압력을 나타냅니다.',
            'good': 'M2가 적정 수준으로 성장하여 경제에 충분한 유동성을 제공하면서도 인플레이션 압력이 크지 않습니다.',
            'neutral': 'M2가 보통 수준으로 성장하고 있습니다.',
            'bad': 'M2가 너무 빠르게 성장하면 인플레이션 우려가, 너무 느리게 성장하면 유동성 부족 우려가 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '금': {
            'title': '금 (Gold)',
            'description': '안전자산으로 인플레이션 헤지 및 불확실성 증가를 나타냅니다.',
            'good': '금이 상승하여 인플레이션 헤지 수요가 있거나 자산 보호 수요가 증가했습니다.',
            'neutral': '금이 보통 수준으로 안정적입니다.',
            'bad': '금이 하락하여 인플레이션 우려가 낮거나 달러 강세가 지속되고 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '구리': {
            'title': '구리 (Copper)',
            'description': '경기 선행지표로 산업 활동과 건설 수요를 나타냅니다.',
            'good': '구리가 상승하여 산업 활동이 활발하고 경기 회복 신호입니다.',
            'neutral': '구리가 보통 수준입니다.',
            'bad': '구리가 하락하여 산업 활동이 둔화되고 경기 전망이 약화되고 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '원유': {
            'title': '원유 (Crude Oil)',
            'description': '에너지 가격으로 인플레이션과 경기 전망을 나타냅니다.',
            'good': '원유가 적정 수준으로 경기 회복을 지원하고 있습니다.',
            'neutral': '원유가 보통 수준입니다.',
            'bad': '원유가 너무 높으면 인플레이션 부담, 너무 낮으면 경기 침체 우려가 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '부동산': {
            'title': '부동산 (VNQ)',
            'description': '부동산 시장 상황을 나타내는 지표입니다.',
            'good': '부동산 시장이 활발하여 경기가 회복되고 있습니다.',
            'neutral': '부동산 시장이 보통 수준입니다.',
            'bad': '부동산 시장이 둔화되어 경기 전망이 약화되고 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '신용리스크': {
            'title': '신용 리스크 (HYG)',
            'description': '고수익 채권 ETF로 기업 신용도와 리스크를 나타냅니다.',
            'good': '신용 리스크가 낮아 기업 신용도가 양호합니다.',
            'neutral': '신용 리스크가 보통 수준입니다.',
            'bad': '신용 리스크가 증가하여 기업 신용도가 약화되고 있습니다.',
            'threshold_good': None,
            'threshold_bad': None
        },
        '비트코인': {
            'title': '비트코인 (BTC)',
            'description': '디지털 자산으로 리스크 자산 선호도를 나타냅니다.',
            'good': '비트코인이 상승하여 리스크 자산에 대한 선호가 높습니다.',
            'neutral': '비트코인이 보통 수준입니다.',
            'bad': '비트코인이 하락하여 리스크 자산에 대한 선호가 낮습니다.',
            'threshold_good': None,
            'threshold_bad': None
        }
    }
    
    if indicator_name not in interpretations:
        return None
    
    info = interpretations[indicator_name]
    interpretation = {
        'title': info['title'],
        'description': info['description'],
        'current_value': value,
        'score': score
    }
    
    # 점수와 현재값에 따른 상세 해석 및 이유
    if score > 10:
        interpretation['meaning'] = info['good']
        interpretation['status'] = '긍정적'
        # 이유 추가
        if indicator_name == 'VIX':
            interpretation['reasoning'] = f"VIX가 {value:.2f}로 낮은 수준(15 이하)입니다. 이는 시장이 안정적이고 투자자들의 공포심이 낮다는 것을 의미합니다. 낮은 변동성은 리스크 자산(주식)에 유리한 환경을 조성합니다."
        elif indicator_name == 'DXY':
            interpretation['reasoning'] = f"DXY가 {value:.2f}로 적정 범위(90-110)에 있습니다. 이는 달러가 글로벌 자본 흐름에 큰 교란을 주지 않으면서도 신뢰를 유지하고 있음을 의미합니다."
        elif indicator_name == '금리(10년)':
            interpretation['reasoning'] = f"10년 국채 금리가 {value:.2f}%로 적정 수준(2-4.5%)입니다. 이는 경기가 건강하게 성장하고 있으며, 차입 비용이 적절한 수준임을 나타냅니다."
        elif indicator_name == '금리스프레드':
            interpretation['reasoning'] = f"금리 스프레드가 {value:.2f}%p로 정상적인 곡선을 보이고 있습니다. 장기 금리가 단기 금리보다 높아 경기 전망이 양호함을 의미합니다."
        elif indicator_name == 'S&P500':
            interpretation['reasoning'] = f"S&P 500이 {value:.2f}로 상승 추세를 보이고 있습니다. 이는 기업 실적과 경기 전망이 양호함을 시사합니다."
        elif indicator_name == 'M2통화량':
            # 전년 대비 성장률 계산
            if data_dict and 'm2' in data_dict:
                m2_data = data_dict['m2']
                if m2_data is not None and len(m2_data) >= 30:
                    year_ago_idx = len(m2_data) - min(52, len(m2_data))  # 약 1년 전 (52주)
                    if year_ago_idx >= 0:
                        year_ago_m2 = m2_data['Close'].iloc[year_ago_idx]
                        yoy_growth = ((value - year_ago_m2) / year_ago_m2) * 100
                        if 5 <= yoy_growth <= 10:
                            interpretation['reasoning'] = f"M2 통화량이 {value/1000:.2f}조 달러로 전년 대비 {yoy_growth:.2f}% 성장하여 적정 수준입니다. 이는 경제에 충분한 유동성을 제공하면서도 인플레이션 압력이 크지 않음을 의미합니다."
                        else:
                            interpretation['reasoning'] = f"M2 통화량이 {value/1000:.2f}조 달러로 전년 대비 {yoy_growth:.2f}% 성장하고 있습니다."
                    else:
                        interpretation['reasoning'] = f"M2 통화량이 {value/1000:.2f}조 달러로 적정 수준으로 성장하고 있습니다. 이는 경제에 충분한 유동성을 제공하면서도 인플레이션 압력이 크지 않음을 의미합니다."
                else:
                    interpretation['reasoning'] = f"M2 통화량이 {value/1000:.2f}조 달러로 적정 수준으로 성장하고 있습니다. 이는 경제에 충분한 유동성을 제공하면서도 인플레이션 압력이 크지 않음을 의미합니다."
            else:
                interpretation['reasoning'] = f"M2 통화량이 {value/1000:.2f}조 달러로 적정 수준으로 성장하고 있습니다. 이는 경제에 충분한 유동성을 제공하면서도 인플레이션 압력이 크지 않음을 의미합니다."
        elif indicator_name in ['유동성', '제조업', '소비/고용', '부동산']:
            interpretation['reasoning'] = f"{indicator_name} 지표가 상승 추세를 보이고 있습니다. 이는 해당 부문의 활발한 활동과 경기 회복 신호를 나타냅니다."
        elif indicator_name == '구리':
            interpretation['reasoning'] = f"구리가 상승 추세를 보이고 있습니다. 구리는 경기 선행지표로, 산업 활동과 건설 수요가 증가하고 있음을 의미합니다."
        elif indicator_name == '원유':
            interpretation['reasoning'] = f"원유가 {value:.2f}달러로 적정 수준(60-100달러)에 있습니다. 이는 경기 회복을 지원하면서도 인플레이션 부담이 크지 않음을 의미합니다."
        elif indicator_name == '신용리스크':
            interpretation['reasoning'] = f"HYG가 상승 추세를 보이고 있습니다. 이는 고수익 채권 스프레드가 좁아지고 있어 기업 신용도가 개선되고 있음을 의미합니다."
        elif indicator_name == '비트코인':
            interpretation['reasoning'] = f"비트코인이 상승 추세를 보이고 있습니다. 이는 리스크 자산에 대한 선호가 높아지고 있음을 나타냅니다."
        else:
            interpretation['reasoning'] = f"{indicator_name}가 긍정적인 신호를 보이고 있어 시장에 유리한 영향을 미칩니다."
    elif score < -10:
        interpretation['meaning'] = info['bad']
        interpretation['status'] = '부정적'
        # 이유 추가
        if indicator_name == 'VIX':
            interpretation['reasoning'] = f"VIX가 {value:.2f}로 높은 수준(30 초과)입니다. 이는 시장 불안이 높고 투자자들의 공포심이 증가하고 있음을 의미합니다. 높은 변동성은 리스크 자산에 부정적 영향을 줄 수 있습니다."
        elif indicator_name == 'DXY':
            interpretation['reasoning'] = f"DXY가 {value:.2f}로 극단적 수준입니다. 달러 강세는 신흥국 자본 유출을, 달러 약세는 달러 신뢰도 하락을 의미할 수 있어 글로벌 자본 흐름에 부정적 영향을 줄 수 있습니다."
        elif indicator_name == '금리(10년)':
            if value < 1.5:
                interpretation['reasoning'] = f"10년 국채 금리가 {value:.2f}%로 매우 낮습니다. 이는 경기 침체 우려나 디플레이션 우려가 있음을 의미합니다."
            else:
                interpretation['reasoning'] = f"10년 국채 금리가 {value:.2f}%로 높은 수준입니다. 이는 차입 비용이 증가하여 기업 이익과 부동산 시장에 부정적 영향을 줄 수 있습니다."
        elif indicator_name == '금리스프레드':
            interpretation['reasoning'] = f"금리 스프레드가 {value:.2f}%p로 역전되었습니다. 이는 경기 침체 선행지표로, 과거 역전 후 평균 6-18개월 내 경기 침체가 발생한 사례가 많습니다."
        elif indicator_name == 'S&P500':
            interpretation['reasoning'] = f"S&P 500이 하락 추세를 보이고 있습니다. 이는 시장 신뢰도가 낮아지고 기업 실적과 경기 전망에 대한 우려가 증가하고 있음을 의미합니다."
        elif indicator_name == 'M2통화량':
            # 전년 대비 성장률 고려
            interpretation['reasoning'] = f"M2 통화량이 {value/1000:.2f}조 달러로 비정상적인 수준입니다. 너무 빠르게 성장하면 인플레이션 우려가, 너무 느리게 성장하면 유동성 부족으로 경기 침체 가능성이 있습니다."
        elif indicator_name == '원유':
            if value > 100:
                interpretation['reasoning'] = f"원유가 {value:.2f}달러로 매우 높은 수준입니다. 이는 인플레이션 부담을 증가시키고 소비자와 기업의 비용을 상승시킬 수 있습니다."
            else:
                interpretation['reasoning'] = f"원유가 {value:.2f}달러로 낮은 수준입니다. 이는 경기 침체 우려나 수요 감소를 나타낼 수 있습니다."
        elif indicator_name == '신용리스크':
            interpretation['reasoning'] = f"HYG가 하락 추세를 보이고 있습니다. 이는 고수익 채권 스프레드가 확대되고 있어 기업 신용도가 약화되고 있음을 의미합니다."
        else:
            interpretation['reasoning'] = f"{indicator_name}가 부정적인 신호를 보이고 있어 시장에 우려를 주고 있습니다."
    else:
        interpretation['meaning'] = info['neutral']
        interpretation['status'] = '중립'
        # 이유 추가
        interpretation['reasoning'] = f"{indicator_name}가 {value:.2f}로 중립적 수준입니다. 현재 명확한 방향성을 보이지 않으며, 다른 지표들과 종합적으로 판단해야 합니다."
    
    return interpretation

# 종합 해석 함수
def generate_analysis(details, score):
    """지표들을 종합적으로 해석"""
    analysis = []
    
    # 긍정적 지표
    positive = [k for k, v in details.items() if v['score'] > 10]
    # 부정적 지표
    negative = [k for k, v in details.items() if v['score'] < -10]
    # 중립 지표
    neutral = [k for k, v in details.items() if -10 <= v['score'] <= 10]
    
    # 종합 상황 분석
    analysis.append("### 📊 현재 시장 상황")
    
    if positive:
        analysis.append(f"**✅ 강세 지표 ({len(positive)}개)**: {', '.join(positive)}")
        analysis.append("   → 이 지표들이 시장에 긍정적인 신호를 보내고 있습니다.")
    
    if neutral:
        analysis.append(f"**➖ 중립 지표 ({len(neutral)}개)**: {', '.join(neutral)}")
        analysis.append("   → 이 지표들은 현재 명확한 방향성을 보이지 않습니다.")
    
    if negative:
        analysis.append(f"**⚠️ 약세 지표 ({len(negative)}개)**: {', '.join(negative)}")
        analysis.append("   → 이 지표들에 주의가 필요하며, 투자 시 신중한 접근이 요구됩니다.")
    
    analysis.append("")
    analysis.append("### 🔍 주요 리스크 요인")
    
    # 금리 역전 체크
    if '금리스프레드' in details:
        spread = details['금리스프레드']['value']
        if spread < 0:
            analysis.append("🚨 **금리 역전 발생**: 10년 금리가 3개월 금리보다 낮아 경기 침체 선행지표가 작동했습니다.")
            analysis.append("   → 과거 금리 역전 후 평균 6-18개월 내 경기 침체가 발생한 사례가 많습니다.")
            analysis.append("   → 리스크 자산(주식) 비중을 줄이고 현금 비중을 늘리는 것이 바람직합니다.")
        elif spread < 0.5:
            analysis.append("⚠️ **금리 곡선 평탄화**: 금리 스프레드가 좁아지고 있어 주의가 필요합니다.")
    
    # VIX 체크
    if 'VIX' in details:
        vix_val = details['VIX']['value']
        if vix_val > 30:
            analysis.append("🚨 **시장 공포 급증**: VIX가 30을 초과하여 시장 불안이 매우 높습니다.")
            analysis.append("   → 변동성이 크므로 공격적 투자보다 방어적 자산 배분이 적절합니다.")
        elif vix_val > 25:
            analysis.append("⚠️ **변동성 증가**: VIX가 상승하여 시장 불안이 증가하고 있습니다.")
        elif vix_val < 12:
            analysis.append("✅ **시장 안정**: VIX가 매우 낮아 시장이 과도하게 낙관적일 수 있습니다.")
            analysis.append("   → 과거 VIX가 매우 낮을 때 시장 조정이 발생한 사례가 있어 주의가 필요합니다.")
    
    # 금리 체크
    if '금리(10년)' in details:
        tnx_val = details['금리(10년)']['value']
        if tnx_val > 5.5:
            analysis.append("⚠️ **고금리 부담**: 금리가 5.5%를 초과하여 차입 비용이 크게 증가했습니다.")
            analysis.append("   → 기업 이익과 부동산 시장에 부정적 영향을 줄 수 있습니다.")
        elif tnx_val < 1.5:
            analysis.append("⚠️ **저금리 우려**: 금리가 1.5% 미만으로 경기 침체 또는 디플레이션 우려가 있습니다.")
    
    # DXY 체크
    if 'DXY' in details:
        dxy_val = details['DXY']['value']
        if dxy_val > 115:
            analysis.append("⚠️ **달러 강세**: 달러가 매우 강세로 신흥국 자본 유출이 발생할 수 있습니다.")
        elif dxy_val < 85:
            analysis.append("⚠️ **달러 약세**: 달러가 약세로 달러 신뢰도 하락 우려가 있습니다.")
    
    analysis.append("")
    analysis.append("### 💡 투자 전략 제안")
    
    # 종합 평가에 따른 투자 전략
    if score >= 50:
        analysis.append("**💪 매우 낙관적 환경**")
        analysis.append("- 리스크 자산(주식) 비중을 높일 수 있는 시점입니다.")
        analysis.append("- 성장주와 사이클링 소비재 섹터에 집중하는 것을 고려하세요.")
        analysis.append("- 단, 지속적인 모니터링을 통해 리스크 변화를 감지하세요.")
    elif score >= 30:
        analysis.append("**👍 낙관적 환경**")
        analysis.append("- 균형 잡힌 자산 배분이 적절합니다.")
        analysis.append("- 주식과 채권을 적절히 배분하여 리스크를 관리하세요.")
        analysis.append("- 점진적으로 주식 비중을 늘릴 수 있습니다.")
    elif score >= 10:
        analysis.append("**➖ 약간 낙관적 환경**")
        analysis.append("- 보수적 자산 배분이 적절합니다.")
        analysis.append("- 주식 비중을 점진적으로 늘리되, 현금 비중을 충분히 유지하세요.")
        analysis.append("- 방어적 섹터(필수소비재, 유틸리티)를 고려하세요.")
    elif score >= -10:
        analysis.append("**➖ 중립적 환경**")
        analysis.append("- 방어적 자산 배분이 필요합니다.")
        analysis.append("- 주식 비중을 줄이고 채권과 현금 비중을 늘리세요.")
        analysis.append("- 고품질 배당주와 국채에 집중하는 것을 고려하세요.")
    elif score >= -30:
        analysis.append("**⚠️ 보수적 환경**")
        analysis.append("- 매우 방어적인 자산 배분이 필요합니다.")
        analysis.append("- 현금 비중을 높이고 리스크 자산을 줄이세요.")
        analysis.append("- 고품질 채권과 금에 투자하는 것을 고려하세요.")
    else:
        analysis.append("**🚨 매우 보수적 환경**")
        analysis.append("- 최대한 방어적인 자산 배분이 필요합니다.")
        analysis.append("- 현금 비중을 최대한 높이고 리스크 자산을 최소화하세요.")
        analysis.append("- 고품질 국채와 금에 집중하고, 시장 안정화를 기다리세요.")
    
    return analysis

# LLM 종합 해석 함수
def generate_llm_analysis(details, data, score, allocation):
    """모든 지표 데이터를 LLM에 전달하여 종합 해석 생성"""
    import time
    
    try:
        # OpenAI  사용
        try:
            import openai
            from openai import APIConnectionError, APITimeoutError, RateLimitError
        except ImportError:
            return None, "OpenAI 라이브러리가 설치되지 않았습니다. 'pip install openai'로 설치해주세요."
        
        # API 키 확인
        api_key = OPENAI_API_KEY
        if not api_key or api_key == "":
            return None, "API 키가 설정되지 않았습니다. 코드 상단의 OPENAI_API_KEY 변수에 API 키를 입력해주세요."
        
        # 지표 데이터 정리 (상세 해석 및 추이 포함)
        indicators_summary = []
        indicators_detailed = []
        
        for indicator, info in details.items():
            # 기본 요약
            indicators_summary.append({
                '지표명': indicator,
                '현재값': round(info['value'], 2),
                '점수': info['score'],
                '상태': '긍정' if info['score'] > 10 else '부정' if info['score'] < -10 else '중립'
            })
            
            # 상세 해석 생성
            interpretation = interpret_indicator(indicator, info['value'], info['score'], details, data)
            if interpretation:
                # 추이 분석 추가
                data_key = get_data_key_for_indicator(indicator)
                trend_info = {}
                if data_key and data.get(data_key) is not None:
                    trend_analysis, trend_interpretation = analyze_trend(data.get(data_key), indicator)
                    if trend_analysis:
                        trend_info = {
                            '추이': trend_analysis,
                            '추이해석': trend_interpretation
                        }
                        
                        # 변화율 계산
                        if len(data[data_key]) > 1:
                            current = data[data_key]['Close'].iloc[-1]
                            prev = data[data_key]['Close'].iloc[-2]
                            daily_change = ((current - prev) / prev) * 100
                            trend_info['일일변화율'] = round(daily_change, 2)
                
                indicators_detailed.append({
                    '지표명': indicator,
                    '현재값': round(info['value'], 2),
                    '점수': info['score'],
                    '상태': interpretation['status'],
                    '해석': interpretation['meaning'],
                    '이유': interpretation.get('reasoning', ''),
                    **trend_info  # 추이 정보 추가
                })
        
        # 변화율 계산 (기존 호환성 유지)
        changes = {}
        for key in ['vix', 'dxy', 'tnx', 'sp500', 'irx', 'm2', 'tlt', 'xli', 'xly', 'tip', 'gold', 'copper', 'oil', 'vnq', 'hyg', 'btc']:
            if data.get(key) is not None and len(data[key]) > 1:
                current = data[key]['Close'].iloc[-1]
                prev = data[key]['Close'].iloc[-2]
                change = ((current - prev) / prev) * 100
                changes[key] = round(change, 2)
        
        # 프롬프트 생성
        prompt = f"""당신은 전문 거시경제 분석가입니다. 아래의 거시경제 지표 데이터와 각 지표에 대한 상세 해석을 종합적으로 분석하여 투자자에게 도움이 되는 해석을 제공해주세요.

## 현재 거시경제 지표 현황

### 지표별 기본 요약:
{json.dumps(indicators_summary, ensure_ascii=False, indent=2)}

### 지표별 상세 해석 (각 지표의 의미와 결론 도출 이유):
{json.dumps(indicators_detailed, ensure_ascii=False, indent=2)}

### 주요 지표 변화율:
- VIX: {changes.get('vix', 'N/A')}%
- DXY: {changes.get('dxy', 'N/A')}%
- 10년 국채 금리: {changes.get('tnx', 'N/A')}%
- S&P 500: {changes.get('sp500', 'N/A')}%
- 금: {changes.get('gold', 'N/A')}%
- 구리: {changes.get('copper', 'N/A')}%
- 원유: {changes.get('oil', 'N/A')}%

### 종합 점수: {score:.1f}점
### 추천 자산 배분: 주식 {allocation['stocks']}%, 채권 {allocation['bonds']}%, 현금 {allocation['cash']}%

## 분석 요청사항:

위의 각 지표별 상세 해석, 이유, 그리고 **추이 정보**를 모두 종합적으로 참고하여, 다음 4가지 섹션으로 구분하여 깊이 있게 분석해주세요:

**중요**: 각 지표의 현재 값뿐만 아니라 추이(상승/하락/횡보)와 추이 해석도 함께 고려하여 분석해주세요. 예를 들어, 현재 값이 높지만 하락 추세라면, 또는 낮지만 상승 추세라면 다른 의미를 가질 수 있습니다.

1. **현재 시장 상황 종합 평가** (400-500자)
   - 각 지표별 현재 값과 추이를 종합하여 현재 시장 상황을 설명
   - 긍정적 지표들이 나타내는 강점과 그 이유 (추이도 함께 고려)
   - 부정적 지표들이 시사하는 약점과 그 이유 (추이도 함께 고려)
   - 지표들 간의 상호 연관성과 의미
   - 특히 추이 변화가 중요한 지표와 그 이유

2. **주요 리스크 요인 상세 분석** (300-400자)
   - 부정적 지표들이 나타내는 구체적인 리스크 요인
   - 각 리스크 요인이 발생한 배경과 이유 (현재 값과 추이를 종합)
   - 추이를 고려한 리스크의 지속 가능성 (예: 하락 추세라면 리스크 증가)
   - 리스크가 실현될 경우 예상되는 영향
   - 특히 주의해야 할 지표와 그 이유 (추이 분석 포함)

3. **투자 기회 및 유리한 요인** (300-400자)
   - 긍정적 지표들이 나타내는 투자 기회
   - 각 기회가 발생한 배경과 지속 가능성 (추이를 고려)
   - 추이를 고려한 기회의 강도 (예: 상승 추세라면 기회 강화)
   - 어떤 섹터나 자산에 유리한 환경인지
   - 특히 주목해야 할 지표와 그 이유 (추이 분석 포함)

4. **구체적인 투자 전략 제안** (400-500자)
   - 종합 점수와 각 지표의 값과 추이를 바탕으로 한 구체적 자산 배분 전략
   - 단기(1-3개월): 현재 지표 값과 추이를 고려한 단기 전략
   - 중기(3-12개월): 지표 추세가 지속될 경우를 고려한 중기 전략
   - 장기(1년 이상): 구조적 변화와 추이 변화를 고려한 장기 전략
   - 각 전략의 근거와 이유를 명확히 설명 (값과 추이를 종합)
   - 리스크 관리 방안 (추이 변화를 고려한 동적 리스크 관리)

분석은 한국어로 작성하고, 각 지표의 현재 값, 해석, 이유, 그리고 **추이 정보**를 모두 종합하여 논리적이고 실용적인 내용으로 작성해주세요. 특히 "왜 이렇게 판단했는지" 그 이유를 명확히 설명하고, 추이 변화가 판단에 어떤 영향을 미치는지도 함께 설명해주세요."""

        # OpenAI API 호출 (재시도 로직 포함)
        # 더 긴 타임아웃과 재시도 설정으로 네트워크 불안정성 대응
        client = openai.OpenAI(
            api_key=api_key,
            timeout=120.0,  # 타임아웃 설정 (120초로 증가)
            max_retries=0  # 수동 재시도 로직 사용
        )
        
        # 재시도 로직 (exponential backoff)
        max_retries = 5  # 재시도 횟수 증가 (3 -> 5)
        retry_delay = 3  # 초기 재시도 지연 시간 (초) 증가 (2 -> 3)
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # 또는 "gpt-4", "gpt-3.5-turbo"
                    messages=[
                        {"role": "system", "content": "당신은 전문 거시경제 분석가입니다. 각 지표의 상세 해석과 이유를 참고하여 논리적이고 실용적인 투자 분석을 제공합니다. 특히 '왜 이렇게 판단했는지' 그 이유를 명확히 설명합니다."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2500  # 더 상세한 분석을 위해 토큰 증가
                )
                
                analysis_text = response.choices[0].message.content
                return analysis_text, None
                
            except APIConnectionError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # exponential backoffX
                    time.sleep(wait_time)
                    # 클라이언트 재생성 (새로운 연결 시도)
                    client = openai.OpenAI(
                        api_key=api_key,
                        timeout=120.0,
                        max_retries=0
                    )
                    continue
                else:
                    return None, f"네트워크 연결 오류: OpenAI API 서버에 연결할 수 없습니다. 인터넷 연결을 확인하거나 잠시 후 다시 시도해주세요. (시도 횟수: {max_retries}회, 오류: {str(e)})"
            
            except APITimeoutError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    # 클라이언트 재생성
                    client = openai.OpenAI(
                        api_key=api_key,
                        timeout=120.0,
                        max_retries=0
                    )
                    continue
                else:
                    return None, f"요청 타임아웃: API 응답이 너무 오래 걸렸습니다. 잠시 후 다시 시도해주세요. (시도 횟수: {max_retries}회, 오류: {str(e)})"
            
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt) * 2  # Rate limit은 더 긴 대기
                    time.sleep(wait_time)
                    # 클라이언트 재생성
                    client = openai.OpenAI(
                        api_key=api_key,
                        timeout=120.0,
                        max_retries=0
                    )
                    continue
                else:
                    return None, f"API 사용량 제한: 요청이 너무 많습니다. 잠시 후 다시 시도해주세요. (시도 횟수: {max_retries}회, 오류: {str(e)})"
            
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                
                # 구체적인 에러 메시지 생성
                if "Connection" in error_type or "connection" in error_msg.lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        time.sleep(wait_time)
                        # 클라이언트 재생성
                        client = openai.OpenAI(
                            api_key=api_key,
                            timeout=120.0,
                            max_retries=0
                        )
                        continue
                    else:
                        return None, f"연결 오류: 네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인하고 잠시 후 다시 시도해주세요. (시도 횟수: {max_retries}회, 오류: {error_msg})"
                elif "timeout" in error_msg.lower() or "Timeout" in error_type:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        time.sleep(wait_time)
                        continue
                    else:
                        return None, f"타임아웃 오류: 요청 시간이 초과되었습니다. 잠시 후 다시 시도해주세요. (오류: {error_msg})"
                else:
                    return None, f"LLM 분석 중 오류 발생 ({error_type}): {error_msg}"
        
        return None, "최대 재시도 횟수를 초과했습니다. 잠시 후 다시 시도해주세요."
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        return None, f"LLM 분석 중 오류 발생 ({error_type}): {error_msg}"

# 자산 배분 추천 함수
def recommend_allocation(score):
    """점수 기반 자산 배분 추천"""
    if score >= 50:
        stocks = 75
        bonds = 20
        cash = 5
        sentiment = "매우 낙관적"
    elif score >= 30:
        stocks = 60
        bonds = 30
        cash = 10
        sentiment = "낙관적"
    elif score >= 10:
        stocks = 45
        bonds = 35
        cash = 20
        sentiment = "약간 낙관적"
    elif score >= -10:
        stocks = 35
        bonds = 40
        cash = 25
        sentiment = "중립"
    elif score >= -30:
        stocks = 25
        bonds = 40
        cash = 35
        sentiment = "보수적"
    else:
        stocks = 15
        bonds = 35
        cash = 50
        sentiment = "매우 보수적"
    
    return {
        'stocks': stocks,
        'bonds': bonds,
        'cash': cash,
        'sentiment': sentiment
    }

# 추이 분석 함수
def analyze_trend(data, indicator_name):
    """지표 데이터의 추이를 상세히 분석하고 해석"""
    if data is None or len(data) < 2:
        return None, "데이터가 부족하여 추이 분석을 할 수 없습니다."
    
    current = data['Close'].iloc[-1]
    prev = data['Close'].iloc[-2]
    
    # 단기 추이 (1일, 5일, 10일)
    daily_change = ((current - prev) / prev) * 100
    
    trend_details = {
        '단기': {},
        '중기': {},
        '장기': {},
        '모멘텀': {},
        '변동성': {}
    }
    
    # 단기 추이 분석 (5일, 10일)
    if len(data) >= 5:
        price_5d_ago = data['Close'].iloc[-5] if len(data) >= 5 else None
        change_5d = ((current - price_5d_ago) / price_5d_ago) * 100 if price_5d_ago else None
        trend_details['단기']['5일변화율'] = round(change_5d, 2) if change_5d else None
    
    if len(data) >= 10:
        price_10d_ago = data['Close'].iloc[-10]
        change_10d = ((current - price_10d_ago) / price_10d_ago) * 100
        trend_details['단기']['10일변화율'] = round(change_10d, 2)
    
    # 중기 추이 (20일 이동평균)
    trend_analysis = ""
    short_term_direction = ""
    medium_term_direction = ""
    long_term_direction = ""
    
    if len(data) >= 20:
        ma20 = data['Close'].rolling(20).mean().iloc[-1]
        ma20_prev = data['Close'].rolling(20).mean().iloc[-2] if len(data) > 20 else None
        
        # 현재가와 이동평균 비교
        ma20_deviation = ((current - ma20) / ma20) * 100
        
        if current > ma20:
            medium_term_direction = "상승"
            trend_strength = "강한" if current > ma20 * 1.05 else "보통" if current > ma20 * 1.02 else "약한"
        else:
            medium_term_direction = "하락"
            trend_strength = "강한" if current < ma20 * 0.95 else "보통" if current < ma20 * 0.98 else "약한"
        
        trend_analysis = f"{trend_strength} {medium_term_direction} 추세"
        trend_details['중기']['20일이동평균'] = round(ma20, 2)
        trend_details['중기']['이동평균대비편차'] = round(ma20_deviation, 2)
        
        # 이동평균 자체의 추세
        if ma20_prev:
            ma20_change = ((ma20 - ma20_prev) / ma20_prev) * 100
            trend_details['중기']['이동평균추세'] = "상승" if ma20_change > 0 else "하락"
            trend_details['중기']['이동평균변화율'] = round(ma20_change, 2)
        
        # 장기 추이 (50일 이동평균)
        if len(data) >= 50:
            ma50 = data['Close'].rolling(50).mean().iloc[-1]
            ma50_prev = data['Close'].rolling(50).mean().iloc[-2] if len(data) > 50 else None
            ma50_deviation = ((current - ma50) / ma50) * 100
            
            if current > ma50:
                long_term_direction = "장기 상승 추세"
            else:
                long_term_direction = "장기 하락 추세"
            
            trend_analysis += f" (장기: {long_term_direction})"
            trend_details['장기']['50일이동평균'] = round(ma50, 2)
            trend_details['장기']['이동평균대비편차'] = round(ma50_deviation, 2)
            
            # 단기/중기/장기 일관성 확인
            if current > ma20 > ma50:
                trend_details['장기']['추세일관성'] = "강한 상승 추세 (단기>중기>장기)"
            elif current < ma20 < ma50:
                trend_details['장기']['추세일관성'] = "강한 하락 추세 (단기<중기<장기)"
            else:
                trend_details['장기']['추세일관성'] = "추세 전환 가능성"
    else:
        if daily_change > 0:
            trend_analysis = "단기 상승 추세"
            short_term_direction = "상승"
        else:
            trend_analysis = "단기 하락 추세"
            short_term_direction = "하락"
    
    # 모멘텀 분석 (RSI 개념 적용)
    if len(data) >= 14:
        # 14일 상승분과 하락분 계산
        gains = []
        losses = []
        for i in range(len(data) - 14, len(data)):
            if i > 0:
                change = data['Close'].iloc[i] - data['Close'].iloc[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0.0001  # 0으로 나누기 방지
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        trend_details['모멘텀']['RSI'] = round(rsi, 2)
        if rsi > 70:
            trend_details['모멘텀']['상태'] = "과매수 (조정 가능성)"
        elif rsi < 30:
            trend_details['모멘텀']['상태'] = "과매도 (반등 가능성)"
        else:
            trend_details['모멘텀']['상태'] = "정상 범위"
    
    # 변동성 분석
    if len(data) >= 20:
        returns = data['Close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100  # 연율화 변동성
        trend_details['변동성']['연율화변동성'] = round(volatility, 2)
        
        recent_volatility = returns.tail(5).std() * np.sqrt(252) * 100
        trend_details['변동성']['최근5일변동성'] = round(recent_volatility, 2)
        
        if recent_volatility > volatility * 1.2:
            trend_details['변동성']['상태'] = "변동성 증가 중"
        elif recent_volatility < volatility * 0.8:
            trend_details['변동성']['상태'] = "변동성 감소 중"
        else:
            trend_details['변동성']['상태'] = "정상 범위"
    
    # 상세 추이 해석 생성
    interpretation_parts = []
    
    # 단기 추이 해석
    if daily_change > 2:
        interpretation_parts.append(f"전일 대비 {daily_change:.2f}% 급등하여 강한 상승 모멘텀을 보이고 있습니다.")
    elif daily_change < -2:
        interpretation_parts.append(f"전일 대비 {daily_change:.2f}% 급락하여 하락 압력이 강합니다.")
    elif daily_change > 0.5:
        interpretation_parts.append(f"전일 대비 {daily_change:.2f}% 소폭 상승하여 긍정적인 신호입니다.")
    elif daily_change < -0.5:
        interpretation_parts.append(f"전일 대비 {daily_change:.2f}% 소폭 하락하여 약간의 부정적 신호입니다.")
    else:
        interpretation_parts.append(f"전일 대비 {abs(daily_change):.2f}% 변화로 거의 변화 없이 안정적입니다.")
    
    # 중기 추이 해석
    if len(data) >= 20:
        ma20_deviation = trend_details['중기'].get('이동평균대비편차', 0)
        if "강한" in trend_analysis:
            if medium_term_direction == "상승":
                interpretation_parts.append(f"20일 이동평균보다 {abs(ma20_deviation):.2f}% 높아 강한 상승 추세를 유지하고 있습니다.")
            else:
                interpretation_parts.append(f"20일 이동평균보다 {abs(ma20_deviation):.2f}% 낮아 강한 하락 추세를 보이고 있습니다.")
        elif "보통" in trend_analysis:
            interpretation_parts.append(f"20일 이동평균 대비 {abs(ma20_deviation):.2f}% 편차로 보통 수준의 {medium_term_direction} 추세입니다.")
        else:
            interpretation_parts.append(f"20일 이동평균 근처에서 {medium_term_direction} 추세를 보이고 있습니다.")
        
        # 이동평균 자체 추세
        if trend_details['중기'].get('이동평균추세'):
            ma_trend = trend_details['중기']['이동평균추세']
            ma_change = trend_details['중기'].get('이동평균변화율', 0)
            if abs(ma_change) > 0.1:
                interpretation_parts.append(f"20일 이동평균 자체가 {ma_change:.2f}% 변화하여 {ma_trend} 추세를 보이고 있습니다.")
    
    # 장기 추이 해석
    if len(data) >= 50:
        ma50_deviation = trend_details['장기'].get('이동평균대비편차', 0)
        if long_term_direction == "장기 상승 추세":
            interpretation_parts.append(f"50일 이동평균보다 {abs(ma50_deviation):.2f}% 높아 장기 상승 추세가 지속되고 있습니다.")
        else:
            interpretation_parts.append(f"50일 이동평균보다 {abs(ma50_deviation):.2f}% 낮아 장기 하락 추세를 보이고 있습니다.")
        
        # 추세 일관성
        consistency = trend_details['장기'].get('추세일관성', '')
        if "강한" in consistency:
            interpretation_parts.append(f"단기, 중기, 장기 추세가 모두 일관되게 {long_term_direction.split()[-2]} 방향으로 정렬되어 추세가 강합니다.")
        elif "전환" in consistency:
            interpretation_parts.append(f"단기, 중기, 장기 추세가 일치하지 않아 추세 전환 가능성이 있습니다.")
    
    # 모멘텀 해석
    if trend_details['모멘텀'].get('RSI'):
        rsi = trend_details['모멘텀']['RSI']
        momentum_status = trend_details['모멘텀'].get('상태', '')
        interpretation_parts.append(f"RSI {rsi:.1f}로 {momentum_status} 상태입니다.")
    
    # 변동성 해석
    if trend_details['변동성'].get('상태'):
        vol_status = trend_details['변동성']['상태']
        vol_value = trend_details['변동성'].get('연율화변동성', 0)
        interpretation_parts.append(f"변동성 {vol_value:.1f}%로 {vol_status} 중입니다.")
    
    # 지표별 맞춤 해석 추가
    if indicator_name == 'VIX':
        if daily_change > 5:
            interpretation_parts.insert(0, f"VIX가 {daily_change:.2f}% 급등하여 시장 불안이 급증하고 있습니다. 변동성 확대는 리스크 자산에 부정적입니다.")
        elif daily_change < -5:
            interpretation_parts.insert(0, f"VIX가 {daily_change:.2f}% 급락하여 시장 안정성이 크게 개선되었습니다.")
        elif medium_term_direction == "상승":
            interpretation_parts.insert(0, f"VIX가 상승 추세를 보이며 시장 불안이 증가하고 있습니다. 주의가 필요합니다.")
        elif medium_term_direction == "하락":
            interpretation_parts.insert(0, f"VIX가 하락 추세를 보이며 시장이 안정화되고 있습니다.")
    elif indicator_name == 'DXY':
        if daily_change > 1:
            interpretation_parts.insert(0, f"달러가 {daily_change:.2f}% 급등하여 강세를 보이고 있습니다. 신흥국 자본 유출 가능성이 있습니다.")
        elif daily_change < -1:
            interpretation_parts.insert(0, f"달러가 {daily_change:.2f}% 급락하여 약세를 보이고 있습니다.")
    elif indicator_name in ['금리(10년)', '금리스프레드']:
        if daily_change > 0.1:
            interpretation_parts.insert(0, f"금리가 상승하여 차입 비용이 증가하고 있습니다.")
        elif daily_change < -0.1:
            interpretation_parts.insert(0, f"금리가 하락하여 유동성이 개선되고 있습니다.")
    elif indicator_name == 'M2통화량':
        if daily_change > 0.5:
            interpretation_parts.insert(0, f"M2 통화량이 {daily_change:.2f}% 증가하여 유동성이 확대되고 있습니다. 인플레이션 압력 모니터링이 필요합니다.")
        elif daily_change < -0.5:
            interpretation_parts.insert(0, f"M2 통화량이 {daily_change:.2f}% 감소하여 유동성이 축소되고 있습니다.")
        else:
            interpretation_parts.insert(0, f"M2 통화량이 안정적으로 유지되고 있습니다.")
    elif indicator_name == 'S&P500':
        if daily_change > 1:
            interpretation_parts.insert(0, f"S&P 500이 {daily_change:.2f}% 상승하여 강한 매수세를 보이고 있습니다.")
        elif daily_change < -1:
            interpretation_parts.insert(0, f"S&P 500이 {daily_change:.2f}% 하락하여 매도 압력이 있습니다.")
    
    # 추이 분석 요약 생성
    trend_summary = trend_analysis
    if trend_details['단기'].get('5일변화율'):
        trend_summary += f" (5일: {trend_details['단기']['5일변화율']:+.2f}%)"
    if trend_details['단기'].get('10일변화율'):
        trend_summary += f" (10일: {trend_details['단기']['10일변화율']:+.2f}%)"
    
    # 전체 해석 결합
    interpretation = " ".join(interpretation_parts)
    
    return trend_summary, interpretation

# 차트 생성 함수
def create_chart(data, title, yaxis_title, color='#1f77b4', period_days=None):
    """Plotly 차트 생성 (기간 필터링 지원)"""
    if data is None or len(data) == 0 or 'Close' not in data.columns:
        return None
    
    # 기간 필터링
    filtered_data = data.copy()
    if period_days:
        cutoff_date = datetime.now() - timedelta(days=period_days)
        filtered_data = filtered_data[filtered_data.index >= cutoff_date]
    
    if len(filtered_data) == 0:
        return None
    
    fig = go.Figure()
    
    # 기본 라인
    fig.add_trace(go.Scatter(
        x=filtered_data.index,
        y=filtered_data['Close'],
        mode='lines',
        name='현재가',
        line=dict(color=color, width=2)
    ))
    
    # 이동평균선 추가 (데이터가 충분한 경우)
    if len(filtered_data) >= 20:
        ma20 = filtered_data['Close'].rolling(20).mean()
        fig.add_trace(go.Scatter(
            x=filtered_data.index,
            y=ma20,
            mode='lines',
            name='20일 이동평균',
            line=dict(color='gray', width=1, dash='dash'),
            opacity=0.7
        ))
    
    if len(filtered_data) >= 50:
        ma50 = filtered_data['Close'].rolling(50).mean()
        fig.add_trace(go.Scatter(
            x=filtered_data.index,
            y=ma50,
            mode='lines',
            name='50일 이동평균',
            line=dict(color='orange', width=1, dash='dot'),
            opacity=0.7
        ))
    
    # 장기 이동평균선 (200일, 3년 이상 데이터가 있는 경우)
    if len(filtered_data) >= 200:
        ma200 = filtered_data['Close'].rolling(200).mean()
        fig.add_trace(go.Scatter(
            x=filtered_data.index,
            y=ma200,
            mode='lines',
            name='200일 이동평균',
            line=dict(color='purple', width=1, dash='dot'),
            opacity=0.6
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="날짜",
        yaxis_title=yaxis_title,
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_white",
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

# 지표 이름과 데이터 키 매핑
def get_data_key_for_indicator(indicator_name):
    """지표 이름을 데이터 키로 변환"""
    mapping = {
        'VIX': 'vix',
        'DXY': 'dxy',
        '금리(10년)': 'tnx',
        '금리스프레드': None,  # 계산된 값이므로 차트 없음
        'S&P500': 'sp500',
        'M2통화량': 'm2',
        '유동성': 'tlt',
        '제조업': 'xli',
        '인플레이션': 'tip',
        '소비/고용': 'xly',
        '금': 'gold',
        '구리': 'copper',
        '원유': 'oil',
        '부동산': 'vnq',
        '신용리스크': 'hyg',
        '비트코인': 'btc'
    }
    return mapping.get(indicator_name)

# 메인 로직
def main():
    # 데이터 로드
    with st.spinner("데이터를 불러오는 중..."):
        data = fetch_market_data()
    
    if data is None:
        st.error("데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.")
        return
    
    # 주요 지표 요약 카드
    st.subheader("📊 주요 거시경제 지표")
    
    # 첫 번째 행: 핵심 지표
    col1, col2, col3, col4 = st.columns(4)
    
    indicators_first = [
        ('vix', 'VIX', '심리지수'),
        ('dxy', 'DXY', '달러 인덱스'),
        ('tnx', '금리(10년)', '10년 국채'),
        ('sp500', 'S&P 500', 'S&P 500')
    ]
    
    for idx, (key, label, desc) in enumerate(indicators_first):
        with [col1, col2, col3, col4][idx]:
            if data.get(key) is not None and len(data[key]) > 0:
                current = data[key]['Close'].iloc[-1]
                if len(data[key]) > 1:
                    change = ((current - data[key]['Close'].iloc[-2]) / data[key]['Close'].iloc[-2]) * 100
                else:
                    change = 0.0
                st.metric(
                    label=label,
                    value=f"{current:.2f}",
                    delta=f"{change:.2f}%"
                )
            else:
                st.metric(label=label, value="N/A", delta="데이터 없음")
    
    # 두 번째 행: 추가 지표
    col5, col6, col7, col8 = st.columns(4)
    
    indicators_second = [
        ('irx', '금리(3개월)', '3개월 국채'),
        ('m2', 'M2 통화량', 'M2 Money Stock'),
        ('tlt', 'TLT', '유동성'),
        ('xli', 'XLI', '제조업')
    ]
    
    for idx, (key, label, desc) in enumerate(indicators_second):
        with [col5, col6, col7, col8][idx]:
            if data.get(key) is not None and len(data[key]) > 0:
                current = data[key]['Close'].iloc[-1]
                if len(data[key]) > 1:
                    change = ((current - data[key]['Close'].iloc[-2]) / data[key]['Close'].iloc[-2]) * 100
                else:
                    change = 0.0
                # M2는 값이 크므로 천 단위로 표시
                if key == 'm2':
                    # M2는 십억 달러 단위이므로 조 단위로 변환 (1조 = 1000 십억)
                    display_value = f"{current/1000:.2f}조"
                else:
                    display_value = f"{current:.2f}"
                st.metric(
                    label=label,
                    value=display_value,
                    delta=f"{change:.2f}%"
                )
            else:
                st.metric(label=label, value="N/A", delta="데이터 없음")
    
    # 세 번째 행: 원자재 및 추가 지표
    col9, col10, col11, col12 = st.columns(4)
    
    indicators_third = [
        ('xly', 'XLY', '소비/고용'),
        ('gold', '금', 'Gold'),
        ('copper', '구리', 'Copper'),
        ('oil', '원유', 'WTI')
    ]
    
    for idx, (key, label, desc) in enumerate(indicators_third):
        with [col9, col10, col11, col12][idx]:
            if data.get(key) is not None and len(data[key]) > 0:
                current = data[key]['Close'].iloc[-1]
                if len(data[key]) > 1:
                    change = ((current - data[key]['Close'].iloc[-2]) / data[key]['Close'].iloc[-2]) * 100
                else:
                    change = 0.0
                st.metric(
                    label=label,
                    value=f"{current:.2f}",
                    delta=f"{change:.2f}%"
                )
            else:
                st.metric(label=label, value="N/A", delta="데이터 없음")
    
    # 네 번째 행: 추가 리스크 지표
    col13, col14, col15, col16 = st.columns(4)
    
    indicators_fourth = [
        ('hyg', 'HYG', '신용리스크'),
        ('btc', 'BTC', '비트코인'),
        ('tip', 'TIP', '인플레이션'),
        (None, None, None)  # 빈 칸
    ]
    
    for idx, (key, label, desc) in enumerate(indicators_fourth):
        with [col13, col14, col15, col16][idx]:
            if key is None:
                st.empty()
            elif data.get(key) is not None and len(data[key]) > 0:
                current = data[key]['Close'].iloc[-1]
                if len(data[key]) > 1:
                    change = ((current - data[key]['Close'].iloc[-2]) / data[key]['Close'].iloc[-2]) * 100
                else:
                    change = 0.0
                st.metric(
                    label=label,
                    value=f"{current:.2f}",
                    delta=f"{change:.2f}%"
                )
            else:
                st.metric(label=label, value="N/A", delta="데이터 없음")
    
    st.markdown("---")
    
    # 점수 계산 및 표시
    score, details = calculate_score(data)
    
    st.subheader("📊 종합 거시경제 점수")
    
    score_col1, score_col2 = st.columns([2, 1])
    
    with score_col1:
        # 점수 범위를 0-100으로 정규화 (예상 범위: -50 ~ +80)
        normalized_score = max(0, min(100, (score + 50) * 100 / 130))
        
        st.metric(
            label="종합 점수",
            value=f"{score:.1f}점",
            delta=f"({normalized_score:.0f}/100)"
        )
        
        # 점수 바
        st.progress(normalized_score / 100)
        
        # 종합 해석
        analysis = generate_analysis(details, score)
        for item in analysis:
            if item.startswith("###"):
                st.markdown(item)
            elif item.startswith("**"):
                st.markdown(item)
            else:
                st.markdown(f"  {item}")
    
    with score_col2:
        st.write("**상세 점수:**")
        # 점수 순으로 정렬
        sorted_details = sorted(details.items(), key=lambda x: x[1]['score'], reverse=True)
        for indicator, info in sorted_details:
            score_color = "🟢" if info['score'] > 10 else "🔴" if info['score'] < -10 else "🟡"
            st.write(f"{score_color} **{indicator}**: {info['score']:+d}점")
            st.caption(f"({info['name']}: {info['value']:.2f})")
    
    st.markdown("---")
    
    # 자산 배분 추천 (먼저 계산하여 LLM 해석에 사용)
    allocation = recommend_allocation(score)
    
    # LLM 종합 해석 섹션
    st.subheader("🤖 LLM 종합 해석")
    
    if OPENAI_API_KEY and OPENAI_API_KEY != "":
        if st.button("🔄 LLM 종합 해석 생성", type="primary"):
            with st.spinner("LLM이 지표를 분석 중입니다..."):
                llm_analysis, error = generate_llm_analysis(details, data, score, allocation)
                
                if error:
                    st.error(error)
                elif llm_analysis:
                    st.session_state['llm_analysis'] = llm_analysis
                    st.rerun()
        
        # 저장된 LLM 해석 표시
        if 'llm_analysis' in st.session_state and st.session_state['llm_analysis']:
            st.markdown("---")
            st.markdown("### 📝 AI 종합 분석 결과")
            
            # LLM 해석을 섹션별로 분리하여 표시
            analysis_text = st.session_state['llm_analysis']
            
            # 섹션별로 분리하여 더 나은 표시
            lines = analysis_text.split('\n')
            current_section = []
            in_section = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    if current_section:
                        section_text = ' '.join(current_section)
                        # 섹션 내용에 따라 스타일 적용
                        if any(keyword in section_text for keyword in ['리스크', '경고', '주의', '⚠️']):
                            st.warning(section_text)
                        elif any(keyword in section_text for keyword in ['기회', '유리', '긍정', '✅']):
                            st.success(section_text)
                        elif any(keyword in section_text for keyword in ['전략', '제안', '추천']):
                            st.info(section_text)
                        else:
                            st.write(section_text)
                        current_section = []
                    continue
                
                # 제목 처리
                if line.startswith('**') and line.endswith('**'):
                    if current_section:
                        section_text = ' '.join(current_section)
                        st.write(section_text)
                        current_section = []
                    st.markdown(f"#### {line}")
                elif line.startswith('1.') or line.startswith('2.') or line.startswith('3.'):
                    if current_section:
                        section_text = ' '.join(current_section)
                        st.write(section_text)
                        current_section = []
                    st.markdown(f"**{line}**")
                else:
                    current_section.append(line)
            
            # 마지막 섹션 처리
            if current_section:
                section_text = ' '.join(current_section)
                st.write(section_text)
            
            # 원본 텍스트도 접을 수 있게 표시
            with st.expander("📄 전체 분석 텍스트 보기"):
                st.text(analysis_text)
        else:
            st.info("💡 위의 'LLM 종합 해석 생성' 버튼을 클릭하여 AI 종합 분석을 받아보세요.")
    else:
        st.warning("⚠️ OpenAI API 키가 설정되지 않았습니다.")
        st.markdown("""
        **LLM 종합 해석 기능을 사용하려면:**
        1. 코드 상단의 `OPENAI_API_KEY` 변수에 API 키를 입력하세요.
        2. API 키는 [platform.openai.com](https://platform.openai.com)에서 발급받을 수 있습니다.
        
        **LLM 종합 해석 기능:**
        - 모든 거시경제 지표를 종합적으로 분석
        - 현재 시장 상황 평가
        - 주요 리스크 및 기회 파악
        - 구체적인 투자 전략 제안
        """)
    
    st.markdown("---")
    
    # 각 지표별 상세 해석
    st.subheader("📖 지표별 상세 해석")
    
    # 탭으로 지표별 해석 표시
    indicator_names = list(details.keys())
    if indicator_names:
        tabs = st.tabs([name[:10] for name in indicator_names])
        
        for idx, (indicator_name, info) in enumerate(details.items()):
            with tabs[idx]:
                interpretation = interpret_indicator(indicator_name, info['value'], info['score'], details, data)
                if interpretation:
                    # 상단: 기본 정보와 차트 나란히
                    col_info, col_chart = st.columns([1, 1])
                    
                    with col_info:
                        st.markdown(f"### {interpretation['title']}")
                        st.info(f"**설명**: {interpretation['description']}")
                        
                        col_left, col_right = st.columns(2)
                        with col_left:
                            st.metric("현재 값", f"{interpretation['current_value']:.2f}")
                        with col_right:
                            status_color = "🟢" if interpretation['status'] == '긍정적' else "🔴" if interpretation['status'] == '부정적' else "🟡"
                            st.metric("상태", f"{status_color} {interpretation['status']}")
                        
                        # 값, 상태 바로 아래에 해석 표시
                        st.markdown("**현재 의미:**")
                        st.write(interpretation['meaning'])
                        
                        # 결론 도출 이유
                        if 'reasoning' in interpretation:
                            st.markdown("**📊 결론 도출 이유:**")
                            st.info(interpretation['reasoning'])
                        
                        # 추이 분석 (상세) - 투자 영향에 사용
                        data_key = get_data_key_for_indicator(indicator_name)
                        trend_analysis_for_investment = None
                        if data_key and data.get(data_key) is not None:
                            trend_analysis, trend_interpretation = analyze_trend(data.get(data_key), indicator_name)
                            if trend_analysis:
                                trend_analysis_for_investment = {
                                    'analysis': trend_analysis,
                                    'interpretation': trend_interpretation
                                }
                        
                        # 투자 영향 (추세까지 고려)
                        st.markdown("**💼 투자에 미치는 영향 (추세 포함):**")
                        
                        # 상태와 추세를 종합한 투자 영향 분석
                        impact_text = ""
                        if trend_analysis_for_investment:
                            trend_dir = trend_analysis_for_investment['analysis']
                            is_uptrend = "상승" in trend_dir or "강한" in trend_dir
                            is_downtrend = "하락" in trend_dir or "약한" in trend_dir
                            
                            if interpretation['status'] == '긍정적':
                                if is_uptrend:
                                    impact_text = f"✅ **매우 유리**: {indicator_name}가 긍정적 상태이며 상승 추세를 보이고 있어 리스크 자산(주식) 투자에 매우 유리한 환경입니다. 추세가 지속될 경우 추가 상승 가능성이 있습니다."
                                elif is_downtrend:
                                    impact_text = f"⚠️ **주의 필요**: {indicator_name}가 긍정적이지만 하락 추세로 전환되고 있어 추세 변화를 모니터링해야 합니다. 추세가 지속될 경우 긍정적 영향이 약화될 수 있습니다."
                                else:
                                    impact_text = f"✅ **유리**: {indicator_name}가 긍정적으로 작용하여 리스크 자산에 유리한 환경입니다. 추세 변화를 지켜보며 점진적으로 투자 비중을 늘릴 수 있습니다."
                            elif interpretation['status'] == '부정적':
                                if is_downtrend:
                                    impact_text = f"🔴 **매우 불리**: {indicator_name}가 부정적 상태이며 하락 추세를 보이고 있어 방어적 자산 배분이 시급합니다. 현금 비중을 높이고 리스크 자산 비중을 줄이는 것을 권장합니다."
                                elif is_uptrend:
                                    impact_text = f"⚠️ **개선 가능**: {indicator_name}가 부정적이지만 상승 추세로 전환되고 있어 상황이 개선될 가능성이 있습니다. 하지만 추세 확인이 필요한 시점입니다."
                                else:
                                    impact_text = f"⚠️ **불리**: {indicator_name}가 부정적으로 작용하여 방어적 자산 배분을 고려해야 합니다. 추세 변화를 모니터링하며 보수적으로 접근하세요."
                            else:
                                if is_uptrend:
                                    impact_text = f"📈 **점진적 개선**: {indicator_name}가 중립적이지만 상승 추세를 보이고 있어 점진적으로 개선될 가능성이 있습니다. 다른 지표들과 종합하여 판단하되, 추세가 지속될 경우 낙관적으로 접근할 수 있습니다."
                                elif is_downtrend:
                                    impact_text = f"📉 **주의 관찰**: {indicator_name}가 중립적이지만 하락 추세로 전환되고 있어 주의 깊은 관찰이 필요합니다. 추세가 지속될 경우 방어적 자산 배분을 고려하세요."
                                else:
                                    impact_text = f"➖ **중립 관찰**: {indicator_name}가 중립적이므로 다른 지표들과 종합적으로 판단해야 합니다. 추세 변화를 모니터링하며 대기하는 것이 좋습니다."
                        else:
                            # 추세 정보가 없는 경우 기존 로직
                            if interpretation['status'] == '긍정적':
                                impact_text = f"✅ {indicator_name}가 긍정적으로 작용하여 리스크 자산(주식)에 유리한 환경입니다."
                            elif interpretation['status'] == '부정적':
                                impact_text = f"⚠️ {indicator_name}가 부정적으로 작용하여 방어적 자산 배분을 고려해야 합니다."
                            else:
                                impact_text = f"➖ {indicator_name}가 중립적이므로 다른 지표들과 종합적으로 판단해야 합니다."
                        
                        if interpretation['status'] == '긍정적':
                            st.success(impact_text)
                        elif interpretation['status'] == '부정적':
                            st.error(impact_text)
                        else:
                            st.warning(impact_text)
                    
                    with col_chart:
                        # 차트 표시
                        data_key = get_data_key_for_indicator(indicator_name)
                        if data_key and data.get(data_key) is not None:
                            # 차트 기간 선택 (1년, 3년, 5년)
                            period_options = {
                                '1년': 365,
                                '3년': 1095,
                                '5년': 1825
                            }
                            selected_period = st.selectbox(
                                "차트 기간 선택",
                                options=list(period_options.keys()),
                                index=0,  # 기본값: 1년
                                key=f"period_{indicator_name}"
                            )
                            period_days = period_options[selected_period]
                            
                            # 차트 색상 결정
                            chart_colors = {
                                'vix': '#e74c3c',
                                'dxy': '#3498db',
                                'tnx': '#9b59b6',
                                'sp500': '#2ecc71',
                                'm2': '#27ae60',
                                'tlt': '#16a085',
                                'xli': '#f39c12',
                                'xly': '#e67e22',
                                'tip': '#c0392b',
                                'gold': '#ffd700',
                                'copper': '#b87333',
                                'oil': '#000000',
                                'vnq': '#9b59b6',
                                'hyg': '#e74c3c',
                                'btc': '#f7931a'
                            }
                            color = chart_colors.get(data_key, '#1f77b4')
                            
                            fig = create_chart(data.get(data_key), f"{indicator_name} 추이 ({selected_period})", interpretation['title'], color, period_days)
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # 추이 분석 (상세) - 선택된 기간에 맞춰 분석
                            # 선택된 기간의 데이터만 사용하여 추이 분석
                            filtered_data = data.get(data_key).copy()
                            if period_days:
                                cutoff_date = datetime.now() - timedelta(days=period_days)
                                filtered_data = filtered_data[filtered_data.index >= cutoff_date]
                            
                            trend_analysis, trend_interpretation = analyze_trend(filtered_data, indicator_name)
                            if trend_analysis:
                                st.markdown("**📈 추이 분석 (상세)**")
                                
                                # 추세 요약
                                st.markdown(f"**추세**: {trend_analysis}")
                                
                                # 상세 해석을 여러 줄로 표시
                                interpretation_sentences = trend_interpretation.split('. ')
                                with st.expander("📊 상세 추이 해석 보기", expanded=True):
                                    for sentence in interpretation_sentences:
                                        if sentence.strip():
                                            st.write(f"• {sentence.strip()}")
                                st.caption("💡 추이 분석은 단기, 중기, 장기 추세와 모멘텀, 변동성을 종합적으로 분석한 결과입니다.")
                        elif indicator_name == '금리스프레드':
                            st.info("금리 스프레드는 계산된 값이므로 차트를 제공하지 않습니다.")
                        else:
                            st.info("차트 데이터를 사용할 수 없습니다.")
                    
    
    st.markdown("---")
    
    st.subheader("💼 추천 자산 배분")
    
    alloc_col1, alloc_col2 = st.columns([2, 1])
    
    with alloc_col1:
        # 파이 차트
        fig_pie = go.Figure(data=[go.Pie(
            labels=['주식', '채권', '현금'],
            values=[allocation['stocks'], allocation['bonds'], allocation['cash']],
            hole=0.4,
            marker_colors=['#2ecc71', '#3498db', '#f39c12']
        )])
        
        fig_pie.update_layout(
            title="자산 배분 비율",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with alloc_col2:
        st.write(f"**시장 심리: {allocation['sentiment']}**")
        st.write("")
        st.write(f"📈 **주식**: {allocation['stocks']}%")
        st.write(f"📊 **채권**: {allocation['bonds']}%")
        st.write(f"💰 **현금**: {allocation['cash']}%")
        
        st.write("")
        st.info("💡 종합 점수에 따라 자산 배분이 자동으로 조정됩니다.")
    
    st.markdown("---")
    
    # 차트 섹션
    st.subheader("📈 지표 차트 (최근 1년)")
    
    # 핵심 지표 차트
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        fig_vix = create_chart(data.get('vix'), "VIX (심리지수/변동성)", "VIX", '#e74c3c')
        if fig_vix:
            st.plotly_chart(fig_vix, use_container_width=True)
        
        fig_tnx = create_chart(data.get('tnx'), "금리 (10년 국채)", "수익률 (%)", '#9b59b6')
        if fig_tnx:
            st.plotly_chart(fig_tnx, use_container_width=True)
        
        fig_tlt = create_chart(data.get('tlt'), "TLT (유동성 지표)", "가격", '#16a085')
        if fig_tlt:
            st.plotly_chart(fig_tlt, use_container_width=True)
    
    with chart_col2:
        fig_dxy = create_chart(data.get('dxy'), "DXY (달러 인덱스)", "DXY", '#3498db')
        if fig_dxy:
            st.plotly_chart(fig_dxy, use_container_width=True)
        
        fig_sp500 = create_chart(data.get('sp500'), "S&P 500", "S&P 500", '#2ecc71')
        if fig_sp500:
            st.plotly_chart(fig_sp500, use_container_width=True)
        
        fig_xli = create_chart(data.get('xli'), "XLI (제조업 지표)", "가격", '#f39c12')
        if fig_xli:
            st.plotly_chart(fig_xli, use_container_width=True)
    
    # 추가 지표 차트
    chart_col3, chart_col4 = st.columns(2)
    
    with chart_col3:
        fig_xly = create_chart(data.get('xly'), "XLY (소비/고용 지표)", "가격", '#e67e22')
        if fig_xly:
            st.plotly_chart(fig_xly, use_container_width=True)
        
        fig_tip = create_chart(data.get('tip'), "TIP (인플레이션 지표)", "가격", '#c0392b')
        if fig_tip:
            st.plotly_chart(fig_tip, use_container_width=True)
    
    with chart_col4:
        fig_irx = create_chart(data.get('irx'), "금리 (3개월 국채)", "수익률 (%)", '#8e44ad')
        if fig_irx:
            st.plotly_chart(fig_irx, use_container_width=True)
    
    # 원자재 및 추가 지표 차트
    chart_col5, chart_col6 = st.columns(2)
    
    with chart_col5:
        fig_gold = create_chart(data.get('gold'), "금 (Gold)", "가격 ($/oz)", '#ffd700')
        if fig_gold:
            st.plotly_chart(fig_gold, use_container_width=True)
        
        fig_copper = create_chart(data.get('copper'), "구리 (Copper)", "가격 ($/lb)", '#b87333')
        if fig_copper:
            st.plotly_chart(fig_copper, use_container_width=True)
        
        fig_vnq = create_chart(data.get('vnq'), "VNQ (부동산)", "가격", '#9b59b6')
        if fig_vnq:
            st.plotly_chart(fig_vnq, use_container_width=True)
    
    with chart_col6:
        fig_oil = create_chart(data.get('oil'), "원유 (WTI)", "가격 ($/barrel)", '#000000')
        if fig_oil:
            st.plotly_chart(fig_oil, use_container_width=True)
        
        fig_hyg = create_chart(data.get('hyg'), "HYG (신용 리스크)", "가격", '#e74c3c')
        if fig_hyg:
            st.plotly_chart(fig_hyg, use_container_width=True)
        
        fig_btc = create_chart(data.get('btc'), "BTC (비트코인)", "가격 ($)", '#f7931a')
        if fig_btc:
            st.plotly_chart(fig_btc, use_container_width=True)
    
    # 데이터 새로고침 버튼
    st.markdown("---")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()
