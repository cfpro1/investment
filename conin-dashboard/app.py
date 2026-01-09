import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from data_generator import (
    generate_models, generate_today_signals, generate_signal_history,
    generate_performance_data, generate_cumulative_returns,
    generate_model_positions, generate_signal_history_all,
    generate_price_data, generate_model_signal_history
)

# 페이지 설정
st.set_page_config(
    page_title="코인 선물 예측 모델 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS 스타일 (모바일 반응형)
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .model-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .positive {
        color: #00cc00;
        font-weight: bold;
    }
    .negative {
        color: #ff3333;
        font-weight: bold;
    }
    .signal-long {
        background-color: #10b981;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        display: inline-block;
        font-size: 0.9rem;
    }
    .signal-short {
        background-color: #ef4444;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        display: inline-block;
        font-size: 0.9rem;
    }
    .signal-stay {
        background-color: #6b7280;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        display: inline-block;
        font-size: 0.9rem;
    }
    
    /* 모바일 반응형 스타일 */
    @media screen and (max-width: 768px) {
        .main-header {
            font-size: 1.8rem;
        }
        .model-card {
            padding: 1rem;
            margin-bottom: 0.8rem;
        }
        .model-card h3 {
            font-size: 1.2rem;
        }
        .model-card p {
            font-size: 1.2rem !important;
        }
        .signal-long, .signal-short, .signal-stay {
            padding: 0.25rem 0.6rem;
            font-size: 0.85rem;
        }
        /* 테이블 가로 스크롤 */
        .dataframe {
            overflow-x: auto;
            display: block;
        }
        /* Streamlit 컬럼을 모바일에서 세로로 배치 */
        [data-testid="column"] {
            width: 100% !important;
            flex: 0 0 100% !important;
        }
    }
    
    /* 작은 화면 (480px 이하) */
    @media screen and (max-width: 480px) {
        .main-header {
            font-size: 1.5rem;
        }
        .model-card {
            padding: 0.8rem;
        }
        .model-card h3 {
            font-size: 1rem;
        }
        .model-card p {
            font-size: 1rem !important;
        }
    }
    
    /* 테이블 모바일 최적화 */
    @media screen and (max-width: 768px) {
        div[data-testid="stDataFrame"] {
            overflow-x: auto;
        }
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'models' not in st.session_state:
    st.session_state.models = generate_models()
if 'signals' not in st.session_state:
    st.session_state.signals = generate_today_signals(st.session_state.models)

def format_percent(value):
    sign = '+' if value >= 0 else ''
    return f"{sign}{value:.2f}%"

def format_currency(value):
    return f"${value:,.2f}"

def get_signal_color(signal):
    if signal == 'Long':
        return '🟢'
    elif signal == 'Short':
        return '🔴'
    else:
        return '⚪'

# 메인 페이지
def main_dashboard():
    st.markdown('<div class="main-header">코인 선물 예측 모델 대시보드</div>', unsafe_allow_html=True)
    st.markdown(f"**날짜:** {datetime.now().strftime('%Y년 %m월 %d일')}")
    
    # 최고 성과 모델 찾기
    best_model = max(st.session_state.models, key=lambda x: x['performance3M'])
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 모델별 3개월 수익률 요약")
    with col2:
        st.caption(f"**최고 성과:** {best_model['name']} ({format_percent(best_model['performance3M'])})")
    
    # 모델 카드 - PC에서는 3열, 모바일에서는 자동으로 세로 배치
    cols = st.columns(3)
    for idx, model in enumerate(st.session_state.models):
        with cols[idx]:
            perf = model['performance3M']
            color_class = 'positive' if perf >= 0 else 'negative'
            st.markdown(f"""
            <div class="model-card">
                <h3>{model['name']}</h3>
                <p style="font-size: 1.5rem;">
                    <span class="{color_class}">{format_percent(perf)}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"{model['name']} 상세보기", key=f"btn_{model['id']}", use_container_width=True):
                st.session_state.selected_model = model['id']
                st.rerun()
    
    st.divider()
    
    # 필터 - PC에서는 2열, 모바일에서는 자동으로 세로 배치
    col1, col2 = st.columns(2)
    with col1:
        selected_model_filter = st.selectbox(
            "모델 필터",
            ['전체', 'Model G', 'Model A', 'Model B'],
            key='model_filter'
        )
    with col2:
        show_active_only = st.checkbox("활성 시그널만 보기 (Stay 제외)", key='active_only')
    
    # 새로고침 버튼
    if st.button("🔄 데이터 새로고침"):
        st.session_state.models = generate_models()
        st.session_state.signals = generate_today_signals(st.session_state.models)
        st.rerun()
    
    st.markdown("### 오늘의 시그널")
    
    # 시그널 테이블
    signals_df = st.session_state.signals.copy()
    
    # 필터 적용
    if show_active_only:
        signals_df = signals_df[
            (signals_df['modelG'] != 'Stay') |
            (signals_df['modelA'] != 'Stay') |
            (signals_df['modelB'] != 'Stay')
        ]
    
    for _, row in signals_df.iterrows():
        with st.expander(f"{row['coin']} - {format_currency(row['current_price'])}", expanded=False):
            # 오늘의 시그널 표시 - 모바일 친화적으로
            st.markdown("### 오늘의 시그널")
            # 모바일에서는 작은 화면에서도 잘 보이도록 조정
            cols = st.columns(3)
            
            with cols[0]:
                st.markdown("**Model G**")
                signal = row['modelG']
                st.markdown(f'<span class="signal-{signal.lower()}">{signal}</span>', unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown("**Model A**")
                signal = row['modelA']
                st.markdown(f'<span class="signal-{signal.lower()}">{signal}</span>', unsafe_allow_html=True)
            
            with cols[2]:
                st.markdown("**Model B**")
                signal = row['modelB']
                st.markdown(f'<span class="signal-{signal.lower()}">{signal}</span>', unsafe_allow_html=True)
            
            st.divider()
            
            # 가격 차트와 모델별 수익률 차트
            st.markdown(f"### {row['coin']} 가격 차트 및 모델별 수익률 (30일)")
            
            # 30일 가격 데이터 생성
            price_data = generate_price_data(row['coin'], 30)
            
            # 각 모델의 30일간 시그널 히스토리 가져오기
            models = ['G', 'A', 'B']
            model_names = {'G': 'Model G', 'A': 'Model A', 'B': 'Model B'}
            
            # 각 모델별 누적 수익률 계산
            model_returns = {}
            for model_id in models:
                model_history = generate_model_signal_history(row['coin'], model_id, 30)
                cumulative_return = 0
                returns_data = []
                
                for i in range(len(model_history)):
                    if i == 0:
                        returns_data.append({'date': model_history.iloc[i]['date'], 'return': 0})
                    else:
                        prev_price = model_history.iloc[i-1]['price']
                        curr_price = model_history.iloc[i]['price']
                        signal = model_history.iloc[i-1]['signal']
                        
                        # 시그널에 따른 수익률 계산
                        if signal == 'Long':
                            daily_return = (curr_price - prev_price) / prev_price * 100
                        elif signal == 'Short':
                            daily_return = (prev_price - curr_price) / prev_price * 100
                        else:  # Stay
                            daily_return = 0
                        
                        cumulative_return += daily_return
                        returns_data.append({
                            'date': model_history.iloc[i]['date'],
                            'return': cumulative_return
                        })
                
                model_returns[model_id] = pd.DataFrame(returns_data)
            
            # 이중 Y축 차트 생성
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 가격 차트 (왼쪽 Y축)
            fig.add_trace(
                go.Scatter(
                    x=price_data['date'],
                    y=price_data['price'],
                    name='가격',
                    line=dict(color='#1f77b4', width=2),
                    mode='lines'
                ),
                secondary_y=False,
            )
            
            # 각 모델의 수익률 차트 (오른쪽 Y축)
            colors = {'G': '#10b981', 'A': '#3b82f6', 'B': '#f59e0b'}
            for model_id in models:
                returns_df = model_returns[model_id]
                fig.add_trace(
                    go.Scatter(
                        x=returns_df['date'],
                        y=returns_df['return'],
                        name=f"{model_names[model_id]} 수익률",
                        line=dict(color=colors[model_id], width=2, dash='dash'),
                        mode='lines'
                    ),
                    secondary_y=True,
                )
            
            # Y축 레이블 설정
            fig.update_xaxes(title_text="날짜")
            fig.update_yaxes(title_text="가격 (USD)", secondary_y=False)
            fig.update_yaxes(title_text="누적 수익률 (%)", secondary_y=True)
            
            fig.update_layout(
                height=400,
                title=f"{row['coin']} 가격 및 모델별 수익률 차트",
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=50, r=50, t=60, b=40)
            )
            
            # 모바일에서 차트가 잘 보이도록 설정
            fig.update_xaxes(tickangle=-45 if len(price_data) > 20 else 0)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            st.divider()
            
            # 각 모델별 7일간 시그널 히스토리를 하나의 테이블로 통합
            st.markdown("### 지난 7일간 모델별 시그널 히스토리")
            
            models = ['G', 'A', 'B']
            
            # 모든 모델의 히스토리 수집
            all_histories = {}
            for model_id in models:
                model_history = generate_model_signal_history(row['coin'], model_id, 7)
                all_histories[model_id] = model_history
            
            # 첫 번째 모델의 날짜와 가격을 기준으로 통합
            base_history = all_histories['G'].copy()
            base_history = base_history.rename(columns={'signal': 'Model G', 'is_correct': '정답_G'})
            base_history = base_history.drop(columns=['coin', 'model'], errors='ignore')
            
            # 다른 모델들의 시그널과 정답 여부 추가
            for model_id in ['A', 'B']:
                model_history = all_histories[model_id].copy()
                model_history = model_history.rename(columns={
                    'signal': f'Model {model_id}',
                    'is_correct': f'정답_{model_id}'
                })
                base_history = base_history.merge(
                    model_history[['date', f'Model {model_id}', f'정답_{model_id}']],
                    on='date',
                    how='left'
                )
            
            # 컬럼 순서 재정렬 (날짜 컬럼명 변경 전에)
            column_order = ['date', 'price', 'Model G', '정답_G', 'Model A', '정답_A', 'Model B', '정답_B']
            base_history = base_history[[col for col in column_order if col in base_history.columns]]
            
            # 날짜와 가격 컬럼명 변경
            base_history = base_history.rename(columns={
                'date': '날짜',
                'price': '가격'
            })
            
            # 시그널을 색상으로 표시하기 위한 스타일링 함수
            def style_signal_columns(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                for col in ['Model G', 'Model A', 'Model B']:
                    if col in df.columns:
                        styles[col] = df[col].apply(lambda x: 
                            'background-color: #10b981; color: white' if x == 'Long' else
                            'background-color: #ef4444; color: white' if x == 'Short' else
                            'background-color: #6b7280; color: white'
                        )
                # 정답 여부 스타일링
                for col in ['정답_G', '정답_A', '정답_B']:
                    if col in df.columns:
                        styles[col] = df[col].apply(lambda x: 
                            'background-color: #10b981; color: white' if x == True else
                            'background-color: #ef4444; color: white' if x == False else
                            'background-color: #e5e7eb; color: #6b7280'
                        )
                return styles
            
            # 날짜 포맷팅
            base_history['날짜'] = pd.to_datetime(base_history['날짜']).dt.strftime('%Y-%m-%d')
            
            # 정답 여부를 텍스트로 변환
            for col in ['정답_G', '정답_A', '정답_B']:
                if col in base_history.columns:
                    base_history[col] = base_history[col].apply(
                        lambda x: '정답' if x == True else '오답' if x == False else '-'
                    )
            
            # 컬럼 순서 재정렬
            column_order = ['날짜', '가격', 'Model G', '정답_G', 'Model A', '정답_A', 'Model B', '정답_B']
            base_history = base_history[[col for col in column_order if col in base_history.columns]]
            
            styled_df = base_history.style.format({
                '가격': '${:,.2f}'
            }).apply(style_signal_columns, axis=None)
            
            # 모바일에서 테이블이 가로 스크롤 가능하도록
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True
            )
            # 모바일 사용자를 위한 안내
            st.caption("💡 모바일에서는 테이블을 좌우로 스와이프하여 전체 내용을 확인할 수 있습니다.")

# 모델 상세 페이지
def model_detail_page(model_id: str):
    model = next((m for m in st.session_state.models if m['id'] == model_id), None)
    if not model:
        st.error("모델을 찾을 수 없습니다.")
        return
    
    # 헤더 영역: 뒤로 버튼, 모델명, 코인 선택
    col_back, col_title, col_coin = st.columns([1, 3, 2])
    
    with col_back:
        if st.button("← 뒤로"):
            if 'selected_model' in st.session_state:
                del st.session_state.selected_model
            st.rerun()
    
    with col_title:
        st.markdown(f'<div class="main-header">{model["name"]}</div>', unsafe_allow_html=True)
    
    with col_coin:
        # 코인 선택
        coins = ['BTC', 'ETH', 'ADA', 'DOT', 'XRP', 'SOL', 'DOGE']
        selected_coin_key = f'coin_select_{model_id}'
        
        # 초기값 설정
        if selected_coin_key not in st.session_state:
            st.session_state[selected_coin_key] = '전체'
        
        # 현재 값 가져오기
        current_value = st.session_state.get(selected_coin_key, '전체')
        options = ['전체'] + coins
        try:
            default_index = options.index(current_value) if current_value in options else 0
        except:
            default_index = 0
        
        selected_coin = st.selectbox(
            "코인 선택",
            options,
            key=selected_coin_key,
            index=default_index,
            label_visibility="collapsed"  # 라벨 숨기기
        )
        st.caption("코인 선택")  # 라벨을 캡션으로 표시
    
    # 성과 탭
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(['1M', '3M', '6M', '1Y', '2Y', '3Y'])
    
    tabs = {'1M': tab1, '3M': tab2, '6M': tab3, '1Y': tab4, '2Y': tab5, '3Y': tab6}
    
    for period, tab in tabs.items():
        with tab:
            perf_data = generate_performance_data(model_id)
            period_data = perf_data[perf_data['period'] == period].iloc[0]
            
            # 성과 지표 - PC에서는 5열, 모바일에서는 자동으로 조정
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("총 수익률", format_percent(period_data['return']))
            with col2:
                st.metric("샤프 비율", f"{period_data['sharpeRatio']:.2f}")
            with col3:
                st.metric("승률", format_percent(period_data['winRate']))
            with col4:
                st.metric("최대 낙폭", format_percent(period_data['maxDrawdown']))
            with col5:
                st.metric("거래 횟수", int(period_data['numTrades']))
            
            st.divider()
            
            # 전체 수익률 차트 또는 코인별 차트
            period_days = {'1M': 30, '3M': 90, '6M': 180, '1Y': 365, '2Y': 730, '3Y': 1095}[period]
            
            if selected_coin == '전체':
                # 전체 누적 수익률 차트
                st.markdown(f"### 전체 누적 수익률 차트 ({period})")
                returns_data = generate_cumulative_returns(period_days)
                
                fig = px.line(
                    returns_data,
                    x='date',
                    y='return',
                    title=f"누적 수익률 차트 ({period})",
                    labels={'return': '누적 수익률 (%)', 'date': '날짜'}
                )
                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=20, t=40, b=40)
                )
                fig.update_xaxes(tickangle=-45 if len(returns_data) > 30 else 0)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                # 코인별 가격 및 수익률 차트
                st.markdown(f"### {selected_coin} 가격 및 수익률 차트 ({period})")
                
                # 코인 가격 데이터 생성
                coin_price_data = generate_price_data(selected_coin, period_days)
                
                # 해당 모델의 시그널 히스토리 가져오기
                model_history = generate_model_signal_history(selected_coin, model_id, period_days)
                
                # 수익률 계산
                cumulative_return = 0
                returns_data = []
                
                for i in range(len(model_history)):
                    if i == 0:
                        returns_data.append({'date': model_history.iloc[i]['date'], 'return': 0})
                    else:
                        prev_price = model_history.iloc[i-1]['price']
                        curr_price = model_history.iloc[i]['price']
                        signal = model_history.iloc[i-1]['signal']
                        
                        # 시그널에 따른 수익률 계산
                        if signal == 'Long':
                            daily_return = (curr_price - prev_price) / prev_price * 100
                        elif signal == 'Short':
                            daily_return = (prev_price - curr_price) / prev_price * 100
                        else:  # Stay
                            daily_return = 0
                        
                        cumulative_return += daily_return
                        returns_data.append({
                            'date': model_history.iloc[i]['date'],
                            'return': cumulative_return
                        })
                
                returns_df = pd.DataFrame(returns_data)
                
                # 이중 Y축 차트 생성
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # 가격 차트 (왼쪽 Y축)
                fig.add_trace(
                    go.Scatter(
                        x=coin_price_data['date'],
                        y=coin_price_data['price'],
                        name='가격',
                        line=dict(color='#1f77b4', width=2),
                        mode='lines'
                    ),
                    secondary_y=False,
                )
                
                # 수익률 차트 (오른쪽 Y축)
                fig.add_trace(
                    go.Scatter(
                        x=returns_df['date'],
                        y=returns_df['return'],
                        name=f'{model["name"]} 수익률',
                        line=dict(color='#10b981', width=2, dash='dash'),
                        mode='lines'
                    ),
                    secondary_y=True,
                )
                
                # Y축 레이블 설정
                fig.update_xaxes(title_text="날짜")
                fig.update_yaxes(title_text="가격 (USD)", secondary_y=False)
                fig.update_yaxes(title_text="누적 수익률 (%)", secondary_y=True)
                
                fig.update_layout(
                    height=400,
                    title=f"{selected_coin} 가격 및 {model['name']} 수익률 차트 ({period})",
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    margin=dict(l=50, r=50, t=60, b=40)
                )
                
                fig.update_xaxes(tickangle=-45 if len(coin_price_data) > 30 else 0)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    st.divider()
    
    # 현재 포지션
    st.markdown("### 현재 포지션")
    positions = generate_model_positions(model_id)
    
    def color_pnl(val):
        color = 'green' if val >= 0 else 'red'
        return f'color: {color}'
    
    styled_positions = positions.style.format({
        'entryPrice': '${:,.2f}',
        'currentPrice': '${:,.2f}',
        'pnl': '{:.2f}%'
    }).applymap(color_pnl, subset=['pnl'])
    
    st.dataframe(
        styled_positions,
        use_container_width=True,
        hide_index=True
    )
    st.caption("💡 모바일에서는 테이블을 좌우로 스와이프하여 전체 내용을 확인할 수 있습니다.")
    
    st.divider()
    
    # 시그널 히스토리
    st.markdown("### 시그널 히스토리")
    selected_coin = st.selectbox("코인 필터", ['전체'] + list(positions['coin'].unique()), key='coin_filter')
    
    history_all = generate_signal_history_all(20)
    if selected_coin != '전체':
        history_all = history_all[history_all['coin'] == selected_coin]
    
    # 정답 여부를 텍스트로 변환
    history_display = history_all.head(20).copy()
    if 'is_correct' in history_display.columns:
        history_display['정답여부'] = history_display['is_correct'].apply(
            lambda x: '정답' if x == True else '오답' if x == False else '-'
        )
        history_display = history_display.drop(columns=['is_correct'])
    
    # 시그널 스타일링 함수
    def style_history_signal(df):
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        if 'signal' in df.columns:
            styles['signal'] = df['signal'].apply(lambda x: 
                'background-color: #10b981; color: white' if x == 'Long' else
                'background-color: #ef4444; color: white' if x == 'Short' else
                'background-color: #6b7280; color: white'
            )
        if '정답여부' in df.columns:
            styles['정답여부'] = df['정답여부'].apply(lambda x: 
                'background-color: #10b981; color: white' if x == '정답' else
                'background-color: #ef4444; color: white' if x == '오답' else
                'background-color: #e5e7eb; color: #6b7280'
            )
        return styles
    
    # 컬럼 이름 변경
    history_display = history_display.rename(columns={
        'date': '날짜',
        'coin': '코인',
        'signal': '시그널',
        'price': '가격'
    })
    
    # 컬럼 순서 재정렬
    column_order = ['날짜', '코인', '시그널', '가격', '정답여부']
    history_display = history_display[[col for col in column_order if col in history_display.columns]]
    
    styled_history = history_display.style.format({
        '가격': '${:,.2f}',
        '날짜': lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else ''
    }).apply(style_history_signal, axis=None)
    
    st.dataframe(
        styled_history,
        use_container_width=True,
        hide_index=True
    )
    st.caption("💡 모바일에서는 테이블을 좌우로 스와이프하여 전체 내용을 확인할 수 있습니다.")

# 메인 로직
if 'selected_model' in st.session_state:
    model_detail_page(st.session_state.selected_model)
else:
    main_dashboard()

