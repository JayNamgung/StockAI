"""
각종 기술적 지표를 분석하기 위한 함수
"""

from typing import Literal

import talib
from datetime import datetime, timedelta

# DataFrame.ta를 사용하기 위해 반드시 import pandas_ta as ta 입포트 필요
import pandas_ta as ta
from pandas import DataFrame, notna
import numpy as np

from models.errors import FunctionError
from stores.search.stock import get_exchange_code
from utils.envs import TIMEZONE
from .basic import get_daily_stock_prices

# _identify_patterns에서 사용하는 상수 정의
DOJI_THRESHOLD = 0.1
HAMMER_BODY_THRESHOLD = 0.3
HAMMER_WICK_THRESHOLD = 0.6
ENGULFING_THRESHOLD = 1.0
HARAMI_THRESHOLD = 0.6
STAR_BODY_THRESHOLD = 0.1
MARUBOZU_THRESHOLD = 0.95
BELT_HOLD_THRESHOLD = 0.7
PRICE_PRECISION = 0.001  # 가격 정밀도, 품목에 따라 조정

async def _get_daily_stock_price_to_dataframe(
   code: str, end_date: datetime, period: int
) -> tuple[DataFrame, str]:
   
   start_date = end_date - timedelta(days=period * 1.5)
   
   prices, name = await get_daily_stock_prices(
       code, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
   )
   
   if not prices:
       raise FunctionError(f"데이터 없음: 해당 종목에 대한 데이터가 없습니다.")
   
   price_df = DataFrame([item.model_dump(by_alias=True) for item in prices]).iloc[::-1]
   
   return price_df, name

async def _calculate_technical_indicators(code: str) -> tuple[DataFrame, str]:
   """
   해당 종목의 각종 기술적 지표를 계산한다.
   """
   
   # 이동 평균 계산을 위해 period를 60일로 고정
   period = 365
   
   price_df, name = await _get_daily_stock_price_to_dataframe(
       code, datetime.now(TIMEZONE), period
   )
   
   if price_df.empty:
       raise ValueError(f"데이터 없음: 해당 종목에 대한 데이터가 없습니다.")
   
   # 1. 추세 지표 (Trend Indicators)
   price_df["EMA_20"] = talib.EMA(price_df["close_price"], timeperiod=20)
   price_df["SMA_20"] = talib.SMA(price_df["close_price"], timeperiod=20)
   price_df["SMA_60"] = talib.SMA(price_df["close_price"], timeperiod=60)
   price_df["SMA_120"] = talib.SMA(price_df["close_price"], timeperiod=120)
   price_df["SMA_200"] = talib.SMA(price_df["close_price"], timeperiod=200)
   price_df["MACD"], price_df["MACD_signal"], price_df["MACD_hist"] = talib.MACD(
       price_df["close_price"]
   )
   
   price_df["ADX"] = talib.ADX(
       price_df["high_price"],
       price_df["low_price"],
       price_df["close_price"],
       timeperiod=14,
   )
   
   price_df["PLUS_DI"] = talib.PLUS_DI(
       price_df["high_price"],
       price_df["low_price"],
       price_df["close_price"],
       timeperiod=14,
   )
   
   price_df["MINUS_DI"] = talib.MINUS_DI(
       price_df["high_price"],
       price_df["low_price"],
       price_df["close_price"],
       timeperiod=14,
   )
   
   price_df["SAR"] = talib.SAR(price_df["high_price"], price_df["low_price"])
   price_df["TRIX"] = talib.TRIX(price_df["close_price"], timeperiod=30)
   price_df["AROON_up"], price_df["AROON_down"] = talib.AROON(
       price_df["high_price"], price_df["low_price"], timeperiod=14
   )
   price_df["DEMA"] = talib.DEMA(price_df["close_price"], timeperiod=20)
   price_df["TEMA"] = talib.TEMA(price_df["close_price"], timeperiod=20)
   
   # 일목균형표 (Ichimoku Cloud)
   high_9 = price_df["high_price"].rolling(window=9).max()
   low_9 = price_df["low_price"].rolling(window=9).min()
   price_df["ICHIMOKU_CONVERSION"] = (high_9 + low_9) / 2
   high_26 = price_df["high_price"].rolling(window=26).max()
   low_26 = price_df["low_price"].rolling(window=26).min()
   price_df["ICHIMOKU_BASE"] = (high_26 + low_26) / 2
   price_df["ICHIMOKU_SPAN_A"] = (
       (price_df["ICHIMOKU_CONVERSION"] + price_df["ICHIMOKU_BASE"]) / 2
   ).shift(26)
   price_df["ICHIMOKU_SPAN_B"] = (
       (
           price_df["high_price"].rolling(window=52).max()
           + price_df["low_price"].rolling(window=52).min()
       )
       / 2
   ).shift(26)
   
   # 이격도 추가
   for period in [20, 60, 120, 200]:
       price_df[f"DISPARITY_{period}"] = (
           price_df["close_price"] / price_df[f"SMA_{period}"] - 1
       ) * 100
   
   # DMI 추가
   price_df["DMI"] = price_df["PLUS_DI"] - price_df["MINUS_DI"]
   
   # 2. 모멘텀 지표 (Momentum Indicators)
   price_df["RSI"] = talib.RSI(price_df["close_price"], timeperiod=14)
   price_df["STOCH_K"], price_df["STOCH_D"] = talib.STOCH(
       price_df["high_price"], price_df["low_price"], price_df["close_price"]
   )
   price_df["WILLR"] = talib.WILLR(
       price_df["high_price"],
       price_df["low_price"],
       price_df["close_price"],
       timeperiod=14,
   )
   price_df["CCI"] = talib.CCI(
       price_df["high_price"],
       price_df["low_price"],
       price_df["close_price"],
       timeperiod=14,
   )
   price_df["MOM"] = talib.MOM(price_df["close_price"], timeperiod=10)
   price_df["MFI"] = talib.MFI(
       price_df["high_price"],
       price_df["low_price"],
       price_df["close_price"],
       price_df["volume"],
       timeperiod=14,
   )
   
   # 3. 변동성 지표 (Volatility Indicators)
   price_df["ATR"] = talib.ATR(
       price_df["high_price"],
       price_df["low_price"],
       price_df["close_price"],
       timeperiod=14,
   )
   price_df["DONCHIAN_HIGH"] = price_df["high_price"].rolling(window=20).max()
   price_df["DONCHIAN_LOW"] = price_df["low_price"].rolling(window=20).min()
   
   # 볼린저 밴드 추가
   price_df["BBANDS_upper"], price_df["BBANDS_middle"], price_df["BBANDS_lower"] = \
       talib.BBANDS(price_df["close_price"], timeperiod=20)
   
   price_df["BBANDS_WIDTH"] = (
       (price_df["BBANDS_upper"] - price_df["BBANDS_lower"])
       / price_df["BBANDS_middle"]
       * 100
   )
   
   # 엔벨로프 추가
   price_df["ENVELOPE_UPPER"] = price_df["SMA_20"] * 1.025
   price_df["ENVELOPE_LOWER"] = price_df["SMA_20"] * 0.975
   
   # 4. 거래량 지표 (Volume Indicators)
   price_df["OBV"] = talib.OBV(price_df["close_price"], price_df["volume"])
   price_df["AD"] = talib.AD(
       price_df["high_price"],
       price_df["low_price"],
       price_df["close_price"],
       price_df["volume"],
   )
   price_df["ADOSC"] = talib.ADOSC(
       price_df["high_price"],
       price_df["low_price"],
       price_df["close_price"],
       price_df["volume"],
       fastperiod=3,
       slowperiod=10,
   )
   
   # VWAP (거래량가중평균가격)
   price_df["VWAP"] = (
       price_df["volume"]
       * (price_df["high_price"] + price_df["low_price"] + price_df["close_price"])
       / 3
   ).cumsum() / price_df["volume"].cumsum()
   
   # Chaikin Money Flow (CMF)
   price_df["CMF"] = (
       talib.ADOSC(
           price_df["high_price"],
           price_df["low_price"],
           price_df["close_price"],
           price_df["volume"],
           fastperiod=3,
           slowperiod=10,
       )
       / price_df["volume"].rolling(window=20).sum()
   )
   
   # Force Index
   price_df["FORCE_INDEX"] = (
       talib.MOM(price_df["close_price"], timeperiod=1) * price_df["volume"]
   )
   
   # 5. 지지/저항 레벨 지표 (Support/Resistance Indicators)
   # Fibonacci Retracement
   high = price_df["high_price"].max()
   low = price_df["low_price"].min()
   diff = high - low
   price_df["FIBO_23.6"] = high - 0.236 * diff
   price_df["FIBO_38.2"] = high - 0.382 * diff
   price_df["FIBO_50.0"] = high - 0.5 * diff
   price_df["FIBO_61.8"] = high - 0.618 * diff
   
   # Pivot Points
   price_df["PP"] = (
       price_df["high_price"].shift(1)
       + price_df["low_price"].shift(1)
       + price_df["close_price"].shift(1)
   ) / 3
   price_df["R1"] = 2 * price_df["PP"] - price_df["low_price"].shift(1)
   price_df["S1"] = 2 * price_df["PP"] - price_df["high_price"].shift(1)
   price_df["R2"] = price_df["PP"] + (
       price_df["high_price"].shift(1) - price_df["low_price"].shift(1)
   )
   price_df["S2"] = price_df["PP"] - (
       price_df["high_price"].shift(1) - price_df["low_price"].shift(1)
   )
   
   # 52주 최고가 및 최저가 계산
   price_df["52W_high_price"] = price_df["high_price"].rolling(window=252).max()
   price_df["52W_low_price"] = price_df["low_price"].rolling(window=252).min()
   
   return price_df, name

def _summarize_indicators_full(exchange_code: str, code: str, name: str, df: DataFrame):
   latest = df.iloc[-1]
   prev_day = df.iloc[-2]
   first = df.iloc[0]
   
   # 가격 포맷팅 함수
   def format_price(price):
       return (
           f"{price:.0f}"
           if exchange_code and exchange_code.casefold() == "krx"
           else f"{price:.2f}"
       )
   
   summary = [
       f"증권코드: {code}\n",
       f"종목명: {name}\n",
       f"데이터 조회 날짜: {first['date'].strftime('%Y-%m-%d')} ~ {latest['date'].strftime('%Y-%m-%d')}\n",
       f"시가: {format_price(latest['open_price'])}, 종가: {format_price(latest['close_price'])}\n",
       f"고가: {format_price(latest['high_price'])}\n",
       f"저가: {format_price(latest['low_price'])}\n",
       "주가 등락률:",
       f"- 1일: {((latest['close_price'] / prev_day['close_price']) - 1) * 100:.2f}%",
       f"- 20일: {((latest['close_price'] / df.iloc[-6]['close_price']) - 1) * 100:.2f}%",
       f"- 52주 최고가: {format_price(latest['52W_high_price'])}\n",
       f"- 52주 최저가: {format_price(latest['52W_low_price'])}\n",
       f"- 현재가 대비 52주 최고가와의 차이: {((latest['close_price'] / latest['52W_high_price']) - 1) * 100:.2f}%",
       f"- 현재가 대비 52주 최저가와의 차이: {((latest['close_price'] / latest['52W_low_price']) - 1) * 100:.2f}%\n",
       f"- 당일 거래량: {latest['volume']:,}\n",
       f"- 20일 평균 대비: {latest['volume'] / df['volume'].rolling(window=20).mean().iloc[-1]:.2f}",
       f"- 60일 평균 대비: {latest['volume'] / df['volume'].rolling(window=60).mean().iloc[-1]:.2f}",
       f"- 120일 평균 대비: {latest['volume'] / df['volume'].rolling(window=120).mean().iloc[-1]:.2f}\n",
       "1. 추세 지표:",
       f"  - 20일 지수이동평균 (EMA-20): {format_price(latest['EMA_20'])}\n",
       f"  - 20일 단순이동평균 (SMA-20): {format_price(latest['SMA_20'])}\n",
       f"  - 60일 단순이동평균 (SMA-60): {format_price(latest['SMA_60'])}\n",
       f"  - 120일 단순이동평균 (SMA-120): {format_price(latest['SMA_120'])}\n",
       f"  - 200일 단순이동평균 (SMA-200): {format_price(latest['SMA_200'])}\n",
       f"  - MACD (12,26,9): {format_price(latest['MACD'])}, Signal: {format_price(latest['MACD_signal'])}, Histogram: {format_price(latest['MACD_hist'])}\n",
       f"  - ADX (14): {latest['ADX']:.2f} (강한 추세: >25, 매우 강한 추세: >50)",
       f"  - +DI (14): {latest['PLUS_DI']:.2f}, -DI (14): {latest['MINUS_DI']:.2f}\n",
       f"  - Parabolic SAR (0.02, 0.2): {format_price(latest['SAR'])}\n",
       f"  - TRIX (30): {latest['TRIX']:.4f}\n",
       f"  - Aroon (14): Up {latest['AROON_up']:.2f}, Down {latest['AROON_down']:.2f}\n",
       f"  - DEMA (20): {format_price(latest['DEMA'])}\n",
       f"  - TEMA (20): {format_price(latest['TEMA'])}\n",
       f"  - Ichimoku Cloud (9,26,52):\n",
       f"    Conversion (9): {format_price(latest['ICHIMOKU_CONVERSION'])}, Base (26): {format_price(latest['ICHIMOKU_BASE'])}\n",
       f"    Span A: {format_price(latest['ICHIMOKU_SPAN_A'])}, Span B (52): {format_price(latest['ICHIMOKU_SPAN_B'])}\n",
       f"  - 이격도:",
   ]
   
   for period in [20, 60, 120, 200]:
       summary.append(f"    - {period}일: {latest[f'DISPARITY_{period}']:.2f}%")
   summary.append(f"  - DMI: {latest['DMI']:.2f}")
   
   summary.append("2. 모멘텀 지표:")
   summary.append(f"  - RSI (14): {latest['RSI']:.2f} (과매수: >70, 과매도: <30)")
   summary.append(
       f"  - 스토캐스틱 (14,3,3): K {latest['STOCH_K']:.2f}, D {latest['STOCH_D']:.2f} (과매수: >80, 과매도: <20)"
   )
   summary.append(
       f"  - Williams %R (14): {latest['WILLR']:.2f} (과매수: <-20, 과매도: >-80)"
   )
   summary.append(f"  - CCI (14): {latest['CCI']:.2f} (과매수: >100, 과매도: <-100)")
   summary.append(f"  - Momentum (10): {latest['MOM']:.2f}")
   summary.append(f"  - MFI (14): {latest['MFI']:.2f} (과매수: >80, 과매도: <20)\n")
   
   summary.append("3. 변동성 지표:")
   summary.append(
       f"  - Bollinger Bands (20,2): 상단 {format_price(latest['BBANDS_upper'])}, 중간 {format_price(latest['BBANDS_middle'])}, 하단 {format_price(latest['BBANDS_lower'])}"
   )
   summary.append(f"  - Bollinger Bandwidth: {latest['BBANDS_WIDTH']:.2f}%")
   summary.append(
       f"  - Envelope(20,2.5%): 상단 {format_price(latest['ENVELOPE_UPPER'])}, 하단 {format_price(latest['ENVELOPE_LOWER'])}\n"
   )
   summary.append(f"  - ATR (14): {format_price(latest['ATR'])}")
   summary.append(
       f"  - Donchian Channel (20): 상단 {format_price(latest['DONCHIAN_HIGH'])}, 하단 {format_price(latest['DONCHIAN_LOW'])}\n"
   )
   
   summary.append("4. 거래량 지표:")
   summary.append(f"  - OBV: {latest['OBV']:.0f}")
   summary.append(f"  - VWAP: {format_price(latest['VWAP'])}")
   summary.append(f"  - Chaikin A/D Oscillator (3,10): {latest['ADOSC']:.2f}")
   summary.append(f"  - Chaikin Money Flow (20): {latest['CMF']:.4f}")
   summary.append(f"  - Force Index (1): {latest['FORCE_INDEX']:.2f}\n")
   
   summary.append("5. 지지/저항 레벨 지표:")
   summary.append(f"  - Fibonacci Retracement:")
   summary.append(f"    - 23.6%: {format_price(latest['FIBO_23.6'])}")
   summary.append(f"    - 38.2%: {format_price(latest['FIBO_38.2'])}")
   summary.append(f"    - 50.0%: {format_price(latest['FIBO_50.0'])}")
   summary.append(f"    - 61.8%: {format_price(latest['FIBO_61.8'])}")
   summary.append(f"  - Pivot Points:")
   summary.append(f"    - PP: {format_price(latest['PP'])}")
   summary.append(
       f"    R1: {format_price(latest['R1'])}, R2: {format_price(latest['R2'])}"
   )
   summary.append(
       f"    S1: {format_price(latest['S1'])}, S2: {format_price(latest['S2'])}\n"
   )

   return "\n".join(summary)

def _summarize_indicators_full(exchange_code: str, code: str, name: str, df: DataFrame):
   latest = df.iloc[-1]
   prev_day = df.iloc[-2]
   first = df.iloc[0]
   
   # 가격 포맷팅 함수
   def format_price(price):
       return (
           f"{price:.0f}"
           if exchange_code and exchange_code.casefold() == "krx"
           else f"{price:.2f}"
       )
   
   summary = [
       f"증권코드: {code}\n",
       f"종목명: {name}\n",
       f"데이터 조회 날짜: {first['date'].strftime('%Y-%m-%d')} ~ {latest['date'].strftime('%Y-%m-%d')}\n",
       f"시가: {format_price(latest['open_price'])}, 종가: {format_price(latest['close_price'])}\n",
       f"고가: {format_price(latest['high_price'])}\n",
       f"저가: {format_price(latest['low_price'])}\n",
       "주가 등락률:",
       f"- 1일: {((latest['close_price'] / prev_day['close_price']) - 1) * 100:.2f}%",
       f"- 5일: {((latest['close_price'] / df.iloc[-6]['close_price']) - 1) * 100:.2f}%",
       f"- 20일: {((latest['close_price'] / df.iloc[-21]['close_price']) - 1) * 100:.2f}%\n",
       f"- 52주 최고가: {format_price(latest['52W_high_price'])}\n",
       f"- 52주 최저가: {format_price(latest['52W_low_price'])}\n",
       f"- 현재가 대비 52주 최고가와의 차이: {((latest['close_price'] / latest['52W_high_price']) - 1) * 100:.2f}%",
       f"- 현재가 대비 52주 최저가와의 차이: {((latest['close_price'] / latest['52W_low_price']) - 1) * 100:.2f}%\n",
       "거래량:",
       f"- 당일 거래량: {latest['volume']:,}\n",
       f"- 20일 평균 대비: {latest['volume'] / df['volume'].rolling(window=20).mean().iloc[-1]:.2f}",
       f"- 60일 평균 대비: {latest['volume'] / df['volume'].rolling(window=60).mean().iloc[-1]:.2f}",
       f"- 120일 평균 대비: {latest['volume'] / df['volume'].rolling(window=120).mean().iloc[-1]:.2f}\n",
       "1. 추세 지표:",
       f"  - 20일 지수이동평균 (EMA-20): {format_price(latest['EMA_20'])}\n",
       f"  - 20일 단순이동평균 (SMA-20): {format_price(latest['SMA_20'])}\n",
       f"  - 60일 단순이동평균 (SMA-60): {format_price(latest['SMA_60'])}\n",
       f"  - 120일 단순이동평균 (SMA-120): {format_price(latest['SMA_120'])}\n",
       f"  - 200일 단순이동평균 (SMA-200): {format_price(latest['SMA_200'])}\n",
       f"  - MACD (12,26,9): {format_price(latest['MACD'])}, Signal: {format_price(latest['MACD_signal'])}, Histogram: {format_price(latest['MACD_hist'])}\n",
       f"  - ADX (14): {latest['ADX']:.2f} (강한 추세: >25, 매우 강한 추세: >50)",
       f"  - +DI (14): {latest['PLUS_DI']:.2f}, -DI (14): {latest['MINUS_DI']:.2f}\n",
       f"  - Parabolic SAR (0.02, 0.2): {format_price(latest['SAR'])}\n",
       f"  - TRIX (30): {latest['TRIX']:.4f}\n",
       f"  - Aroon (14): Up {latest['AROON_up']:.2f}, Down {latest['AROON_down']:.2f}\n",
       f"  - DEMA (20): {format_price(latest['DEMA'])}\n",
       f"  - TEMA (20): {format_price(latest['TEMA'])}\n",
       f"  - Ichimoku Cloud (9,26,52):",
       f"    Conversion (9): {format_price(latest['ICHIMOKU_CONVERSION'])}, Base (26): {format_price(latest['ICHIMOKU_BASE'])}\n",
       f"    Span A: {format_price(latest['ICHIMOKU_SPAN_A'])}, Span B (52): {format_price(latest['ICHIMOKU_SPAN_B'])}\n",
       f"  - 이격도:",
   ]
   
   for period in [20, 60, 120, 200]:
       summary.append(f"    - {period}일: {latest[f'DISPARITY_{period}']:.2f}%")
   summary.append(f"  - DMI: {latest['DMI']:.2f}")
   
   summary.append("2. 모멘텀 지표:")
   summary.append(f"  - RSI (14): {latest['RSI']:.2f} (과매수: >70, 과매도: <30)")
   summary.append(
       f"  - 스토캐스틱 (14,3,3): K {latest['STOCH_K']:.2f}, D {latest['STOCH_D']:.2f} (과매수: >80, 과매도: <20)"
   )
   summary.append(
       f"  - Williams %R (14): {latest['WILLR']:.2f} (과매수: <-20, 과매도: >-80)"
   )
   summary.append(f"  - CCI (14): {latest['CCI']:.2f} (과매수: >100, 과매도: <-100)")
   summary.append(f"  - Momentum (10): {latest['MOM']:.2f}")
   summary.append(f"  - MFI (14): {latest['MFI']:.2f} (과매수: >80, 과매도: <20)\n")
   
   summary.append("3. 변동성 지표:")
   summary.append(
       f"  - Bollinger Bands (20,2): 상단 {format_price(latest['BBANDS_upper'])}, 중간 {format_price(latest['BBANDS_middle'])}, 하단 {format_price(latest['BBANDS_lower'])}"
   )
   summary.append(f"  - Bollinger Bandwidth: {latest['BBANDS_WIDTH']:.2f}%")
   summary.append(
       f"  - Envelope(20,2.5%): 상단 {format_price(latest['ENVELOPE_UPPER'])}, 하단 {format_price(latest['ENVELOPE_LOWER'])}\n"
   )
   summary.append(f"  - ATR (14): {format_price(latest['ATR'])}")
   summary.append(
       f"  - Donchian Channel (20): 상단 {format_price(latest['DONCHIAN_HIGH'])}, 하단 {format_price(latest['DONCHIAN_LOW'])}\n"
   )
   
   summary.append("4. 거래량 지표:")
   summary.append(f"  - OBV: {latest['OBV']:.0f}")
   summary.append(f"  - VWAP: {format_price(latest['VWAP'])}")
   summary.append(f"  - Chaikin A/D Oscillator (3,10): {latest['ADOSC']:.2f}")
   summary.append(f"  - Chaikin Money Flow (20): {latest['CMF']:.4f}")
   summary.append(f"  - Force Index (1): {latest['FORCE_INDEX']:.2f}\n")
   
   summary.append("5. 지지/저항 레벨 지표:")
   summary.append(f"  - Fibonacci Retracement:")
   summary.append(f"    - 23.6%: {format_price(latest['FIBO_23.6'])}")
   summary.append(f"    - 38.2%: {format_price(latest['FIBO_38.2'])}")
   summary.append(f"    - 50.0%: {format_price(latest['FIBO_50.0'])}")
   summary.append(f"    - 61.8%: {format_price(latest['FIBO_61.8'])}")
   summary.append(f"  - Pivot Points:")
   summary.append(f"    - PP: {format_price(latest['PP'])}")
   summary.append(f"    - R1: {format_price(latest['R1'])}, R2: {format_price(latest['R2'])}")
   summary.append(f"    - S1: {format_price(latest['S1'])}, S2: {format_price(latest['S2'])}\n")
   
   return "\n".join(summary)

def _summarize_indicators_brief(
   exchange_code: str, code: str, name: str, df: DataFrame
):
   latest = df.iloc[-1]
   prev_day = df.iloc[-2]
   first = df.iloc[0]
   
   def format_price(price: float):
       return (
           f"{price:.0f}"
           if exchange_code and exchange_code.casefold() == "krx"
           else f"{price:.2f}"
       )
   
   summary = [
       f"증권코드: {code}\n",
       f"종목명: {name}\n",
       f"데이터 조회 날짜: {first['date'].strftime('%Y-%m-%d')} ~ {latest['date'].strftime('%Y-%m-%d')}\n",
       f"현재가({latest['date'].strftime('%Y-%m-%d')}): {format_price(latest['close_price'])}\n",
       f"시가: {format_price(latest['open_price'])}\n",
       f"고가: {format_price(latest['high_price'])}\n",
       f"저가: {format_price(latest['low_price'])}\n",
       "주가 등락률:",
       f"- 1일: {((latest['close_price'] / prev_day['close_price']) - 1) * 100:.2f}%",
       f"- 5일: {((latest['close_price'] / df.iloc[-6]['close_price']) - 1) * 100:.2f}%",
       f"- 20일: {((latest['close_price'] / df.iloc[-21]['close_price']) - 1) * 100:.2f}%\n",
       "주요 기술적 지표:",
       f"- RSI (14): {latest['RSI']:.2f}",
       f"- MACD (12,26,9): {format_price(latest['MACD'])}, Signal: {format_price(latest['MACD_signal'])}\n",
       f"- 볼린저 밴드 (20,2): 상단 {format_price(latest['BBANDS_upper'])}, 중간 {format_price(latest['BBANDS_middle'])}, 하단 {format_price(latest['BBANDS_lower'])}\n",
       f"- 20일 이동평균: {format_price(latest['SMA_20'])}\n",
       f"- 60일 이동평균: {format_price(latest['SMA_60'])}\n",
       f"- 스토캐스틱 (14,3,3): K {latest['STOCH_K']:.2f}, D {latest['STOCH_D']:.2f}",
       "\n주의 사항: 위 지표는 과거 데이터 기반이며, 투자 결정에 참고용으로만 사용하세요.",
   ]
   
   return "\n".join(summary)


async def get_technical_indicators(code: str, version="full"):
   """
   type: "function"
   function:
       name: get_technical_indicators
       description: "주어진 종목코드에 대한 각종 기술적 지표를 분석합니다."
       message: "지표 분석 중"
       parameters:
           type: "object"
           properties:
               code:
                   type: "string"
                   description: "종목 코드 (예: '005930' for 삼성전자, 'AAPL' for 애플)"
               version:
                   type: "string"
                   description: "상세 또는 간략 분석 (예: 'full' for 상세, 'brief' for 간략)"
           required:
               - code
   """
   code = code.upper()
   
   try:
       exchange_code, name = get_exchange_code(code)
   except FunctionError:
       exchange_code = None
       name = code
       
   price_df, name_ = await _calculate_technical_indicators(code)
   
   if name_:
       name = name_
   
   if version == "full":
       return _summarize_indicators_full(exchange_code, code, name, price_df)
   elif version == "brief":
       return _summarize_indicators_brief(exchange_code, code, name, price_df)
   else:
       raise ValueError("버전은 'full' 또는 'brief'만 가능합니다.")

async def find_candlestick_patterns(
   code: str, period=10, return_type: Literal["json", "str"] = "str"
) -> list | str:
   """
   type: "function"
   function:
       name: find_candlestick_patterns
       description: "(기술적분석) 주어진 주식 코드에 대한 최근 일수 동안의 캔들스틱 패턴을 식별하고 반환합니다."
       message: "캔들 스틱 패턴 식별 중"
       parameters:
           type: "object"
           properties:
               code:
                   type: "string"
                   description: "종목 코드 (예: '005930' for 삼성전자, 'AAPL' for 애플)"
               period:
                   type: "string"
                   description: "분석할 최근 일수. 기본값은 10일입니다."
                   default: 10
           required:
               - code
   """
   # 기간을 20일에서 60일 사이로 제한
   period = max(20, min(60, period))
   
   code = code.upper()
   
   # 주식 데이터 가져오기 (2024년부터)
   prices_df, name = await _get_daily_stock_price_to_dataframe(
       code, datetime.now(TIMEZONE), period
   )
   
   # 패턴 식별
   patterns_dict = _identify_patterns(prices_df)
   
   # 패턴 DataFrame 생성
   patterns_df = DataFrame(
       [
           (
               date,
               ", ".join([f"{pattern} ({strength:.2f})" for pattern, strength in patterns])
           )
           for date, patterns in patterns_dict.items()
       ],
       columns=["Date", "Pattern"],
   )
   patterns_df.set_index("Date", inplace=True)
   
   result_df = prices_df.join(patterns_df)
   
   if return_type == "json":
       result_df["Pattern"] = result_df["Pattern"].fillna("")
       result_df = result_df.fillna(0.0)
       return result_df.to_dict(orient="records")
   
   # 결과를 텍스트로 변환
   text_data = _df_to_text_concise(result_df.tail(period))
   
   return text_data


def _df_to_text_concise(df: DataFrame):
   text = "날짜,시가,고가,저가,종가,거래량,변동률,이동평균,추세,거래량MA,ATR,패턴\n"
   for index, row in df.iterrows():
       text += f"{row['date'].strftime('%Y-%m-%d')},"
       text += f"{row['open_price']:.0f},{row['high_price']:.0f},{row['low_price']:.0f},{row['close_price']:.0f},"
       text += f"{row['volume']},"
       text += f"{row['fluctuation_rate']:.4f},"
       text += f"{row['MA']:.0f},"
       text += f"{row['Trend']},"
       text += f"{row['volume_MA']:.0f},"
       text += f"{row['ATR']:.2f},"
       text += f"{row['Pattern'] if notna(row['Pattern']) else '없음'}\n"
   return text


def _identify_patterns(df: DataFrame, window=10):
   patterns = {}
   
   df["MA"] = df["close_price"].rolling(window=window).mean()
   df["Trend"] = np.where(df["close_price"] > df["MA"], "Uptrend", "Downtrend")
   df["volume_MA"] = df["volume"].rolling(window=window).mean()
   df["ATR"] = df.ta.atr(length=window)
   
   for i in range(window, len(df)):
       date = df.index[i]
       patterns[date] = []
       
       current = df.iloc[i]
       prev = df.iloc[i - 1]
       prev2 = df.iloc[i - 2] if i > 1 else None
       
       body = abs(current["open_price"] - current["close_price"])
       wick_up = current["high_price"] - max(
           current["open_price"], current["close_price"]
       )
       wick_down = (
           min(current["open_price"], current["close_price"]) - current["low_price"]
       )
       candle_range = current["high_price"] - current["low_price"]
       
       # Doji
       if body / candle_range < DOJI_THRESHOLD:
           doji_strength = min(
               1,
               (1 - (body / candle_range) / DOJI_THRESHOLD)
               * (candle_range / current["ATR"]),
           )
           patterns[date].append(("Doji", doji_strength))
           
           if (
               wick_down / candle_range > HAMMER_WICK_THRESHOLD
               and wick_up / candle_range < DOJI_THRESHOLD
           ):
               patterns[date].append(
                   ("Dragonfly Doji", min(1, wick_down / candle_range))
               )
           elif (
               wick_up / candle_range > HAMMER_WICK_THRESHOLD
               and wick_down / candle_range < DOJI_THRESHOLD
           ):
               patterns[date].append(
                   ("Gravestone Doji", min(1, wick_up / candle_range))
               )
       
       # Hammer and Hanging Man
       if (
           body / candle_range < HAMMER_BODY_THRESHOLD
           and wick_down / candle_range > HAMMER_WICK_THRESHOLD
       ):
           hammer_strength = min(1, wick_down / (2 * body))
           if current["Trend"] == "Downtrend":
               patterns[date].append(("Hammer", hammer_strength))
           elif current["Trend"] == "Uptrend":
               patterns[date].append(("Hanging Man", hammer_strength))
       
       # Shooting Star
       if (
           body / candle_range < HAMMER_BODY_THRESHOLD
           and wick_up / candle_range > HAMMER_WICK_THRESHOLD
           and current["Trend"] == "Uptrend"
       ):
           star_strength = min(1, wick_up / (2 * body))
           patterns[date].append(("Shooting Star", star_strength))
       
       # Engulfing patterns
       if (
           current["open_price"] < current["close_price"]
           and current["open_price"] <= prev["close_price"]
           < prev["open_price"]
           < current["close_price"]
       ):
           strength = _calculate_pattern_strength(df, i, "Bullish Engulfing")
           patterns[date].append(("Bullish Engulfing", strength))
       elif (
           current["open_price"] > current["close_price"]
           and current["open_price"] >= prev["close_price"]
           > prev["open_price"]
           > current["close_price"]
       ):
           strength = _calculate_pattern_strength(df, i, "Bearish Engulfing")
           patterns[date].append(("Bearish Engulfing", strength))
       
       # Harami patterns
       if (
           prev["open_price"] > prev["close_price"]
           and prev["close_price"] < current["open_price"]
           < current["close_price"]
           < prev["open_price"]
           and body < (prev["open_price"] - prev["close_price"]) * HARAMI_THRESHOLD
       ):
           strength = min(
               1,
               (current["close_price"] - current["open_price"])
               / (prev["open_price"] - prev["close_price"]),
           )
           patterns[date].append(("Bullish Harami", strength))
       elif (
           prev["open_price"] < prev["close_price"]
           and prev["close_price"] > current["open_price"]
           > current["close_price"]
           > prev["open_price"]
           and body < (prev["close_price"] - prev["open_price"]) * HARAMI_THRESHOLD
       ):
           strength = min(
               1,
               (current["open_price"] - current["close_price"])
               / (prev["close_price"] - prev["open_price"]),
           )
           patterns[date].append(("Bearish Harami", strength))
       
       # Piercing Line and Dark Cloud Cover
       if (
           prev["close_price"] < prev["open_price"]
           and current["open_price"] < prev["low_price"]
           and (prev["open_price"] + prev["close_price"]) / 2
           < current["close_price"]
           < prev["open_price"]
       ):
           strength = (current["close_price"] - current["open_price"]) / (
               prev["open_price"] - prev["close_price"]
           )
           patterns[date].append(("Piercing Line", strength))
       elif (
           prev["close_price"] > prev["open_price"]
           and current["open_price"] > prev["high_price"]
           and (prev["open_price"] + prev["close_price"]) / 2
           > current["close_price"]
           > prev["open_price"]
       ):
           strength = (current["open_price"] - current["close_price"]) / (
               prev["close_price"] - prev["open_price"]
           )
           patterns[date].append(("Dark Cloud Cover", strength))
       
       # Tweezer patterns
       if (
           abs(current["low_price"] - prev["low_price"]) / current["low_price"]
           < PRICE_PRECISION
           and abs(current["high_price"] - prev["high_price"]) / current["high_price"]
            < PRICE_PRECISION
       ):
           tweezer_strength = (
               1
               - (
                   abs(current["low_price"] - prev["low_price"]) / current["low_price"]
                   + abs(current["high_price"] - prev["high_price"])
                   / current["high_price"]
               )
               / 2
           )
           if current["Trend"] == "Uptrend" and prev["Trend"] == "Uptrend":
               patterns[date].append(("Tweezer Top", tweezer_strength))
           elif current["Trend"] == "Downtrend" and prev["Trend"] == "Downtrend":
               patterns[date].append(("Tweezer Bottom", tweezer_strength))
       
       # Morning and Evening Star
       if i > 1:
           if (
               prev2["close_price"] < prev2["open_price"]
               and abs(prev["close_price"] - prev["open_price"])
               / (prev["high_price"] - prev["low_price"])
               < STAR_BODY_THRESHOLD
               and current["open_price"] < current["close_price"]
               and current["close_price"]
               > (prev2["open_price"] + prev2["close_price"]) / 2
           ):
               price_move = (
                   current["close_price"]
                   - min(prev2["low_price"], prev["low_price"], current["low_price"])
               ) / (3 * current["ATR"])
               volume_factor = min(1, current["volume"] / current["volume_MA"])
               trend_reversal = (
                   current["close_price"] - prev2["close_price"]
               ) / prev2["close_price"]
               strength = min(1, price_move * volume_factor * (1 + trend_reversal))
               patterns[date].append(("Morning Star", strength))
           if i > 1:
               if (
                   prev2["close_price"] > prev2["open_price"]
                   and abs(prev["close_price"] - prev["open_price"])
                   / (prev["high_price"] - prev["low_price"])
                   < STAR_BODY_THRESHOLD
                   and current["open_price"] > current["close_price"]
                   and current["close_price"]
                   < (prev2["open_price"] + prev2["close_price"]) / 2
                ):
                   price_move = (
                       max(prev2["high_price"], prev["high_price"], current["high_price"])
                       - current["close_price"]
                   ) / (3 * current["ATR"])
                   volume_factor = min(1, current["volume"] / current["volume_MA"])
                   trend_reversal = (
                       prev2["close_price"] - current["close_price"]
                   ) / prev2["close_price"]
                   strength = min(1, price_move * volume_factor * (1 + trend_reversal))
                   patterns[date].append(("Evening Star", strength))
       
       # Three White Soldiers and Three Black Crows
       if i > 1:
           if all(
               df["close_price"].iloc[j] > df["open_price"].iloc[j]
               for j in range(i - 2, i + 1)
           ) and all(
               df["open_price"].iloc[j] < df["close_price"].iloc[j - 1]
               for j in range(i - 1, i + 1)
           ):
               strength = (
                   sum(
                       df["close_price"].iloc[j] - df["open_price"].iloc[j]
                       for j in range(i - 2, i + 1)
                   )
                   / df["close_price"].iloc[i - 2]
               )
               patterns[date].append(("Three White Soldiers", strength))
           elif all(
               df["close_price"].iloc[j] < df["open_price"].iloc[j]
               for j in range(i - 2, i + 1)
           ) and all(
               df["open_price"].iloc[j] > df["close_price"].iloc[j - 1]
               for j in range(i - 1, i + 1)
           ):
               strength = (
                   sum(
                       df["open_price"].iloc[j] - df["close_price"].iloc[j]
                       for j in range(i - 2, i + 1)
                   )
                   / df["open_price"].iloc[i - 2]
               )
               patterns[date].append(("Three Black Crows", strength))
       
       # Marubozu
       if body / candle_range > MARUBOZU_THRESHOLD and (
           abs(current["open_price"] - current["low_price"]) < PRICE_PRECISION
           and abs(current["close_price"] - current["high_price"]) < PRICE_PRECISION
           or abs(current["open_price"] - current["high_price"]) < PRICE_PRECISION
           and abs(current["close_price"] - current["low_price"]) < PRICE_PRECISION
       ):
           marubozu_strength = min(1, body / current["ATR"])
           if current["close_price"] > current["open_price"]:
               patterns[date].append(("Bullish Marubozu", marubozu_strength))
           else:
               patterns[date].append(("Bearish Marubozu", marubozu_strength))
       
       # Belt Hold
       if body / candle_range > BELT_HOLD_THRESHOLD:
           if (
               abs(current["open_price"] - current["low_price"]) < PRICE_PRECISION
               and current["close_price"] > current["open_price"]
           ):
               strength = _calculate_pattern_strength(df, i, "Bullish Belt Hold")
               patterns[date].append(("Bullish Belt Hold", strength))
           elif (
               abs(current["open_price"] - current["high_price"]) < PRICE_PRECISION
               and current["close_price"] < current["open_price"]
           ):
               strength = _calculate_pattern_strength(df, i, "Bearish Belt Hold")
               patterns[date].append(("Bearish Belt Hold", strength))
       
       # 4개의 캔들 패턴 추가
       if i > 3:
           prev3 = df.iloc[i - 3]
           
           # Rising Three Methods
           if (
               prev3["close_price"] > prev3["open_price"]
               and prev2["close_price"] < prev2["open_price"]
               and prev["close_price"] < prev["open_price"]
               and current["open_price"] > current["close_price"] > prev3["open_price"]
               and min(prev2["low_price"], prev["low_price"], current["low_price"])
               > prev3["open_price"]
               and max(prev2["high_price"], prev["high_price"], current["high_price"])
               < prev3["close_price"]
           ):
               strength = (current["close_price"] - prev3["open_price"]) / prev3[
                   "open_price"
               ]
               patterns[date].append(("Rising Three Methods", strength))
           
           # Falling Three Methods
           elif (
               prev3["close_price"] < prev3["open_price"]
               and prev2["close_price"] > prev2["open_price"]
               and prev["close_price"] > prev["open_price"]
               and current["open_price"] < current["close_price"] < prev3["open_price"]
               and max(prev2["high_price"], prev["high_price"], current["high_price"])
               < prev3["open_price"]
               and min(prev2["low_price"], prev["low_price"], current["low_price"])
               > prev3["close_price"]
           ):
               strength = (prev3["open_price"] - current["close_price"]) / prev3[
                   "open_price"
               ]
               patterns[date].append(("Falling Three Methods", strength))
           
           # Bullish Three Line Strike
           if (
               prev3["close_price"] > prev3["open_price"]
               and prev2["close_price"] > prev2["open_price"]
               and prev["open_price"] < prev["close_price"] < current["open_price"]
               and current["close_price"] < prev3["open_price"]
           ):
               strength = (prev["close_price"] - prev3["open_price"]) / prev3[
                   "open_price"
               ]
               patterns[date].append(("Bullish Three Line Strike", strength))
           
           # Bearish Three Line Strike
           elif (
               prev3["close_price"] < prev3["open_price"]
               and prev2["close_price"] < prev2["open_price"]
               and prev["open_price"] > prev["close_price"] > current["open_price"]
               and current["close_price"] > prev3["open_price"]
           ):
               strength = (prev3["open_price"] - prev["close_price"]) / prev3[
                   "open_price"
               ]
               patterns[date].append(("Bearish Three Line Strike", strength))
           
           # Bullish Tri-Star
           if (
               abs(prev3["open_price"] - prev3["close_price"])
               / (prev3["high_price"] - prev3["low_price"])
               < DOJI_THRESHOLD
               and abs(prev2["open_price"] - prev2["close_price"])
               / (prev2["high_price"] - prev2["low_price"])
               < DOJI_THRESHOLD
               and abs(prev["open_price"] - prev["close_price"])
               / (prev["high_price"] - prev["low_price"])
               < DOJI_THRESHOLD
               and current["close_price"] > current["open_price"]
               and current["close_price"]
               > max(prev3["high_price"], prev2["high_price"], prev["high_price"])
           ):
               strength = (
                   current["close_price"]
                   - min(prev3["low_price"], prev2["low_price"], prev["low_price"])
               ) / min(prev3["low_price"], prev2["low_price"], prev["low_price"])
               patterns[date].append(("Bullish Tri-Star", strength))
           
           # Bearish Tri-Star
           elif (
               abs(prev3["open_price"] - prev3["close_price"])
               / (prev3["high_price"] - prev3["low_price"])
               < DOJI_THRESHOLD
               and abs(prev2["open_price"] - prev2["close_price"])
               / (prev2["high_price"] - prev2["low_price"])
               < DOJI_THRESHOLD
               and abs(prev["open_price"] - prev["close_price"])
               / (prev["high_price"] - prev["low_price"])
               < DOJI_THRESHOLD
               and current["close_price"] < current["open_price"]
               and current["close_price"]
               < min(prev3["low_price"], prev2["low_price"], prev["low_price"])
           ):
               strength = (
                   max(prev3["high_price"], prev2["high_price"], prev["high_price"])
                   - current["close_price"]
               ) / max(prev3["high_price"], prev2["high_price"], prev["high_price"])
               patterns[date].append(("Bearish Tri-Star", strength))
           
           # Bullish Meeting Lines
           elif (
               prev3["close_price"] < prev3["open_price"]
               and prev2["close_price"] < prev2["open_price"]
               and abs(prev["close_price"] - prev["open_price"]) < PRICE_PRECISION
               and abs(prev["close_price"] - prev["open_price"]) < PRICE_PRECISION
               and current["close_price"] > current["open_price"]
               and current["close_price"] > prev["close_price"]
           ):
               price_move = (
                   current["close_price"]
                   - min(
                       prev3["low_price"],
                       prev2["low_price"],
                       prev["low_price"],
                       current["low_price"],
                   )
               ) / (4 * current["ATR"])
               volume_factor = min(1, current["volume"] / current["volume_MA"])
               trend_reversal = (
                   current["close_price"] - prev3["close_price"]
               ) / prev3["close_price"]
               strength = min(1, price_move * volume_factor * (1 + trend_reversal))
               patterns[date].append(("Bullish Meeting Lines", strength))
           
           # Bearish Meeting Lines
           elif (
               prev3["close_price"] > prev3["open_price"]
               and prev2["close_price"] > prev2["open_price"]
               and abs(prev["close_price"] - prev["open_price"]) < PRICE_PRECISION
               and current["close_price"] < current["open_price"]
               and current["close_price"] < prev["close_price"]
           ):
               price_move = (
                   max(
                       prev3["high_price"],
                       prev2["high_price"],
                       prev["high_price"],
                       current["high_price"],
                   )
                   - current["close_price"]
               ) / (4 * current["ATR"])
               volume_factor = min(1, current["volume"] / current["volume_MA"])
               trend_reversal = (
                   prev3["close_price"] - current["close_price"]
               ) / prev3["close_price"]
               strength = min(1, price_move * volume_factor * (1 + trend_reversal))
               patterns[date].append(("Bearish Meeting Lines", strength))
           
           # Gap 패턴들
           if current["low_price"] > prev["high_price"]:
               strength = min(
                   1, (current["low_price"] - prev["high_price"]) / current["ATR"]
               )
               patterns[date].append(("Bullish Gap Up", strength))
           elif current["high_price"] < prev["low_price"]:
               strength = min(
                   1, (prev["low_price"] - current["high_price"]) / current["ATR"]
               )
               patterns[date].append(("Bearish Gap Down", strength))
           
           # Island Reversal
           if i > 1:
               if (
                   prev2["low_price"] > prev["high_price"]
                   and current["low_price"] > prev["high_price"]
               ) or (
                   prev2["high_price"] < prev["low_price"]
                   and current["high_price"] < prev["low_price"]
               ):
                   strength = (
                       abs(current["close_price"] - prev["close_price"])
                       / prev["close_price"]
                   )
                   patterns[date].append(("Island Reversal", strength))
           
           # Kicking Pattern
           if (
               abs(current["open_price"] - current["close_price"])
               / (current["high_price"] - current["low_price"])
               > MARUBOZU_THRESHOLD
               and abs(prev["open_price"] - prev["close_price"])
               / (prev["high_price"] - prev["low_price"])
               > MARUBOZU_THRESHOLD
           ):
               if (
                   prev["close_price"] < current["open_price"] < current["close_price"]
                   and prev["close_price"] < prev["open_price"]
               ):
                   strength = (current["close_price"] - prev["close_price"]) / prev[
                       "close_price"
                   ]
                   patterns[date].append(("Bullish Kicking", strength))
               elif (
                   prev["close_price"] > current["open_price"] > current["close_price"]
                   and prev["close_price"] > prev["open_price"]
               ):
                   strength = (prev["close_price"] - current["close_price"]) / prev["close_price"]
               patterns[date].append(("Bearish Kicking", strength))
           
           # Abandoned Baby
           if i > 1:
               if (
                   abs(prev["open_price"] - prev["close_price"])
                   / (prev["high_price"] - prev["low_price"])
                   < DOJI_THRESHOLD
                   and prev2["low_price"] > prev["high_price"]
                   and current["low_price"] > prev["high_price"]
                   and (
                       (
                           prev2["close_price"] < prev2["open_price"]
                           and current["close_price"] > current["open_price"]
                       )
                       or (
                           prev2["close_price"] > prev2["open_price"]
                           and current["close_price"] < current["open_price"]
                       )
                   )
               ):
                   strength = (
                       abs(current["close_price"] - prev2["close_price"])
                       / prev2["close_price"]
                   )
                   patterns[date].append(("Abandoned Baby", strength))
           
           # Three Inside Up/Down
           if i > 1:
               if (
                   prev2["close_price"] < prev2["open_price"]
                   and prev["open_price"] > prev2["close_price"]
                   and prev["close_price"] < prev2["open_price"]
                   and current["close_price"] > prev["high_price"]
               ):
                   strength = min(
                       1,
                       (current["close_price"] - prev2["low_price"])
                       / (3 * current["ATR"]),
                   )
                   patterns[date].append(("Three Inside Up", strength))
               elif (
                   prev2["close_price"] > prev2["open_price"]
                   and prev["open_price"] < prev2["close_price"]
                   and prev["close_price"] > prev2["open_price"]
                   and current["close_price"] < prev["low_price"]
               ):
                   strength = min(
                       1,
                       (prev2["high_price"] - current["close_price"])
                       / (3 * current["ATR"]),
                   )
                   patterns[date].append(("Three Inside Down", strength))
           
           # Three Outside Up/Down
           if i > 1:
               if (
                   prev["open_price"]
                   < prev2["close_price"]
                   < prev2["open_price"]
                   < prev["close_price"]
                   and current["close_price"] > prev["high_price"]
               ):
                   strength = min(
                       1,
                       (current["close_price"] - prev2["low_price"])
                       / (3 * current["ATR"]),
                   )
                   patterns[date].append(("Three Outside Up", strength))
               elif (
                   prev["close_price"]
                   < prev2["open_price"]
                   < prev2["close_price"]
                   < prev["open_price"]
                   and current["close_price"] < prev["low_price"]
               ):
                   strength = min(
                       1,
                       (prev2["high_price"] - current["close_price"])
                       / (3 * current["ATR"]),
                   )
                   patterns[date].append(("Three Outside Down", strength))
           
           # Tasuki Gap
           if i > 1:
               prev2 = df.iloc[i - 2]
               if (
                   prev2["close_price"] < prev["low_price"]
                   and prev["close_price"] > prev["open_price"]
                   and current["open_price"] > prev["open_price"]
                   and prev["close_price"] > current["close_price"] > prev2["high_price"]
               ):
                   gap_size = (prev["low_price"] - prev2["high_price"]) / prev2[
                       "high_price"
                   ]
                   base_strength = min(gap_size * 5, 1)  # 갭 크기에 따른 기본 강도
                   pattern_strength = _calculate_pattern_strength(
                       df, i, "Bullish Tasuki Gap"
                   )
                   strength = base_strength * 0.6 + pattern_strength * 0.4
                   patterns[date].append(("Bullish Tasuki Gap", strength))
               elif (
                   prev2["close_price"] > prev["high_price"]
                   and prev["close_price"] < prev["open_price"]
                   and current["open_price"] < prev["open_price"]
                   and prev["close_price"] < current["close_price"] < prev2["low_price"]
               ):
                   gap_size = (prev2["low_price"] - prev["high_price"]) / prev2[
                       "low_price"
                   ]
                   base_strength = min(gap_size * 5, 1)  # 갭 크기에 따른 기본 강도
                   pattern_strength = _calculate_pattern_strength(
                       df, i, "Bearish Tasuki Gap"
                   )
                   strength = base_strength * 0.6 + pattern_strength * 0.4
                   patterns[date].append(("Bearish Tasuki Gap", strength))
           # Side-by-Side White Lines
           if i > 1:
               if (
                   prev2["close_price"] < prev["low_price"]
                   and prev["close_price"] > prev["open_price"]
                   and current["close_price"] > current["open_price"]
                   and abs(current["close_price"] - prev["close_price"])
                   / prev["close_price"]
                   < 0.01
               ):
                   strength = (current["close_price"] - prev2["close_price"]) / prev2[
                       "close_price"
                   ]
                   patterns[date].append(("Side-by-Side White Lines", strength))
           
           # Separating Lines
           if (
              abs(current["open_price"] - prev["open_price"]) / prev["open_price"]
           ):
              if (
               current["close_price"] > current["open_price"]
               and prev["close_price"] < prev["open_price"]
              ):
               strength = (current["close_price"] - current["open_price"]) / current[
                "open_price"
               ]
               patterns[date].append(("Bullish Separating Lines", strength))
              elif (
               current["close_price"] < current["open_price"]
               and prev["close_price"] > prev["open_price"]
              ):
               strength = (current["open_price"] - current["close_price"]) / current[
                "open_price"
               ]
               patterns[date].append(("Bearish Separating Lines", strength))

           # Thrust Pattern
           if i > 1:
              if (
                  prev2["close_price"] < prev["low_price"]
                  and current["open_price"] > prev["high_price"]
                  and current["close_price"] < prev["close_price"]
                  ):
                  strength = (prev["close_price"] - current["close_price"]) / prev[
                            "close_price"
                        ]
                  patterns[date].append(("Bearish Thrust", strength))
              elif (
                  prev2["close_price"] > prev["high_price"]
                  and current["open_price"] < prev["low_price"]
                  and current["close_price"] > prev["close_price"]
                  ):
                  strength = (current["close_price"] - prev["close_price"]) / prev[
                            "close_price"
                        ]
                  patterns[date].append(("Bullish Thrust", strength))

           # Mat Hold
           if i > 3:
            if (
                df["open_price"].iloc[i - 4] < df["close_price"].iloc[i - 4]
                and df["close_price"].iloc[i - 3] < df["open_price"].iloc[i - 3]
                and df["open_price"].iloc[i - 3] > df["close_price"].iloc[i]
                and all(
                    df["close_price"].iloc[j] < df["open_price"].iloc[j]
                    for j in range(i - 3, i)
                )
                and all(
                    df["low_price"].iloc[j] > df["low_price"].iloc[i - 4]
                    for j in range(i - 3, i)
                )
                and current["close_price"] > df["high_price"].iloc[i - 4]
            ):
                strength = (current["close_price"] - df["low_price"].iloc[i - 4]) / df["low_price"].iloc[i - 4]
                patterns[date].append(("Bullish Mat Hold", strength))

            # Stick Sandwich
            if i > 1:
                if (
                    prev2["close_price"] < prev2["open_price"]
                    and prev["close_price"] > prev["open_price"]
                    and abs(prev2["close_price"] - prev2["open_price"]) / prev2["close_price"] > PRICE_PRECISION
                    and current["close_price"] < current["open_price"]
                ):
                    strength = (prev2["open_price"] - current["close_price"]) / current["close_price"]
                    patterns[date].append(("Bearish Stick Sandwich", strength))

            # Potential Bullish Reversal
            if i >= 3:  # 최소 4개의 캔들을 필요로 한다
                last_3_candles = df.iloc[i - 3: i]
                if (
                    all(last_3_candles["close_price"] < last_3_candles["open_price"])
                    and current["close_price"] > current["open_price"]
                ):
                    reversal_strength = (
                        current["close_price"] - current["open_price"]
                    ) / current["ATR"]
                    patterns[date].append(("Potential Bullish Reversal", min(1, reversal_strength)))

            return patterns

def _calculate_pattern_strength(df: DataFrame, idx: int, pattern_type: str):
    current = df.iloc[idx]

    # 캔들 크기
    candle_size = abs(current["close_price"] - current["open_price"]) / current["ATR"]

    # 거래량 증가
    volume_increase = min(current["volume"] / current["volume_MA"], 3)

    # 추세 반전
    trend_reversal = 1
    if any([
        pattern_type.startswith("Bullish") and current["close_price"] > current["MA"] > df["MA"].iloc[idx - 5],
        pattern_type.startswith("Bearish") and current["close_price"] < current["MA"] < df["MA"].iloc[idx - 5]
    ]):
        trend_reversal = 2

    # 종합 강도 계산
    strength = candle_size * 0.4 + volume_increase * 0.3 + trend_reversal * 0.3  # 최대 강도는 1로 제한

    return min(strength, 1)