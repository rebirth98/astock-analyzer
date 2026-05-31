"""
A股智能分析助手 - Flask后端
股票数据：新浪财经API | AI分析：DeepSeek
"""
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from flask_caching import Cache

app = Flask(__name__)
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 900
cache = Cache(app)

# ==================== API Key ====================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
if not DEEPSEEK_API_KEY:
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'key.txt')
    if os.path.exists(key_file):
        with open(key_file, 'r') as f:
            DEEPSEEK_API_KEY = f.read().strip()


# ==================== 工具函数 ====================

def http_get(url, referer='https://finance.sina.com.cn', timeout=20):
    """使用Python http.client获取HTTP数据"""
    import http.client
    import ssl
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname
    path = parsed.path + ('?' + parsed.query if parsed.query else '')
    port = parsed.port or 443

    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection(host, port, context=ctx, timeout=timeout)

    headers = {
        'Host': host,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': referer,
    }

    try:
        conn.request('GET', path, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        # Sina returns GBK encoded data
        try:
            return raw.decode('gbk')
        except:
            return raw.decode('utf-8', errors='replace')
    finally:
        conn.close()


def post_json(url, payload, headers_extra=None, timeout=180):
    """使用Python http.client发送POST JSON请求"""
    import http.client
    import ssl
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname
    path = parsed.path + ('?' + parsed.query if parsed.query else '')
    port = parsed.port or 443

    payload_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')

    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection(host, port, context=ctx, timeout=timeout)

    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Host': host,
        'User-Agent': 'Mozilla/5.0',
    }
    if headers_extra:
        headers.update(headers_extra)

    try:
        conn.request('POST', path, body=payload_bytes, headers=headers)
        resp = conn.getresponse()
        body = resp.read().decode('utf-8')
        return json.loads(body)
    finally:
        conn.close()


def get_market(code):
    """判断市场"""
    code = str(code).zfill(6)
    return ('sh' if code[0] in ('6','9') else 'sz'), code


def parse_sina_quote(text):
    """解析新浪行情数据"""
    # 格式: var hq_str_sh600519="数据,数据,...";
    match = re.search(r'"([^"]*)"', text)
    if not match:
        return None
    parts = match.group(1).split(',')
    if len(parts) < 32:
        return None
    return {
        "name": parts[0],
        "open": float(parts[1]) if parts[1] else 0,
        "prev_close": float(parts[2]) if parts[2] else 0,
        "price": float(parts[3]) if parts[3] else 0,
        "high": float(parts[4]) if parts[4] else 0,
        "low": float(parts[5]) if parts[5] else 0,
        "volume": float(parts[8]) if parts[8] else 0,
        "amount": float(parts[9]) if parts[9] else 0,
        "date": parts[30] if len(parts) > 30 else '',
        "time": parts[31] if len(parts) > 31 else '',
    }


# ==================== 路由 ====================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/quote/<code>')
@cache.cached(timeout=30, key_prefix='q_%s')
def api_quote(code):
    """实时行情 - 新浪财经"""
    try:
        market, clean_code = get_market(code)
        sym = f'{market}{clean_code}'
        text = http_get(f'https://hq.sinajs.cn/list={sym}', timeout=10)
        q = parse_sina_quote(text)
        if not q or q['price'] == 0:
            return jsonify({"error": f"未找到股票 {clean_code}"}), 404

        change_pct = ((q['price'] - q['prev_close']) / q['prev_close'] * 100) if q['prev_close'] else 0
        return jsonify({
            "code": clean_code, "name": q['name'],
            "price": q['price'], "change_pct": round(change_pct, 2),
            "change_amt": round(q['price'] - q['prev_close'], 2),
            "open": q['open'], "high": q['high'], "low": q['low'],
            "prev_close": q['prev_close'], "volume": q['volume'], "amount": q['amount'],
            "turnover_rate": 0, "pe": 0, "total_market_cap": 0,
        })
    except Exception as e:
        return jsonify({"error": f"获取行情失败: {str(e)}"}), 500


@app.route('/api/kline/<code>')
@cache.cached(timeout=60, key_prefix='kl_%s')
def api_kline(code):
    """K线数据 - 新浪财经"""
    try:
        market, clean_code = get_market(code)
        sym = f'{market}{clean_code}'
        url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen=90'
        raw = json.loads(http_get(url, timeout=15))

        klines = []
        for item in raw[-90:]:
            klines.append({
                "date": item['day'],
                "open": float(item['open']),
                "close": float(item['close']),
                "high": float(item['high']),
                "low": float(item['low']),
                "volume": float(item['volume']),
                "pct_change": 0,
            })
        # Calculate pct_change
        for i in range(1, len(klines)):
            if klines[i-1]['close'] != 0:
                klines[i]['pct_change'] = round((klines[i]['close'] - klines[i-1]['close']) / klines[i-1]['close'] * 100, 2)

        return jsonify({"klines": klines, "count": len(klines)})
    except Exception as e:
        return jsonify({"error": f"获取K线失败: {str(e)}"}), 500


# ==================== AI分析 ====================

SYSTEM_PROMPT = """你是一位专业的A股股票分析师。你的任务是基于提供的实时行情、90日K线走势和相关新闻，对股票短期走势做出全面深入的分析预测。

分析原则：
1. 从技术面、消息面、资金面、行业面、政策面五个维度深度分析，每个维度2-3条具体依据
2. 每条依据引用具体数据/事件，不可泛泛而谈
3. 客观分析多空双方因素，权衡后做出判断
4. 给出3日、5日、7日、1个月的看涨/看跌/震荡判断及置信度
5. 推理详细、专业、有数据支撑

你必须返回严格JSON格式，不要包含其他文字：

{
  "stock_code": "600519",
  "stock_name": "贵州茅台",
  "current_price": 1326.00,
  "analysis_summary": "综合各维度的一句话总结",
  "predictions": {
    "3_days": {"direction": "bullish", "confidence": 65, "reasoning": "详细推理至少50字", "key_factors": ["因素1","因素2"]},
    "5_days": {"direction": "bullish", "confidence": 55, "reasoning": "详细推理至少50字", "key_factors": ["因素1","因素2"]},
    "7_days": {"direction": "neutral", "confidence": 50, "reasoning": "详细推理至少50字", "key_factors": ["因素1","因素2"]},
    "1_month": {"direction": "bearish", "confidence": 45, "reasoning": "详细推理至少50字", "key_factors": ["因素1","因素2"]}
  },
  "dimensions": {
    "technical": ["依据1","依据2","依据3"],
    "news": ["依据1","依据2"],
    "capital": ["依据1","依据2"],
    "industry": ["依据1","依据2"],
    "policy": ["依据1","依据2"]
  },
  "risk_warnings": ["风险1","风险2","风险3"]
}

注意：direction只能是bullish/bearish/neutral；confidence是0-100整数；每个reasoning至少50字；dimensions每个至少2条；返回纯JSON，不包含```json```标记"""


def build_user_prompt(code, name, quote, klines, news):
    """构建提示词"""
    recent = klines[-20:] if len(klines) > 20 else klines
    kline_lines = [f"{k['date']} 开{k['open']:.2f} 收{k['close']:.2f} 高{k['high']:.2f} 低{k['low']:.2f} 量{k['volume']:.0f}" for k in recent]

    closes = [k['close'] for k in klines]
    ma5 = sum(closes[-5:])/5 if len(closes)>=5 else closes[-1]
    ma10 = sum(closes[-10:])/10 if len(closes)>=10 else closes[-1]
    ma20 = sum(closes[-20:])/20 if len(closes)>=20 else closes[-1]

    news_lines = [f"{i+1}. {n['title']} ({n.get('time','')})" for i,n in enumerate(news[:10])] if news else ['暂无']

    return f"""请分析以下股票：

【基本信息】代码：{code} 名称：{name} 市场：{'上海' if code.startswith('6') else '深圳'}证券交易所

【实时行情】当前价格：{quote['price']:.2f}元 | 涨跌幅：{quote['change_pct']:+.2f}% | 今开：{quote['open']:.2f} | 最高：{quote['high']:.2f} | 最低：{quote['low']:.2f} | 昨收：{quote['prev_close']:.2f} | 成交量：{quote['volume']:.0f}股

【技术指标】MA5={ma5:.2f} MA10={ma10:.2f} MA20={ma20:.2f} | 均线排列：{'多头' if ma5>ma10>ma20 else ('空头' if ma5<ma10<ma20 else '交叉震荡')}

【近20日K线】
{chr(10).join(kline_lines)}

【最新新闻】
{chr(10).join(news_lines)}

请给出全面深入的分析预测，返回严格JSON格式。"""


@app.route('/api/analyze/<code>')
# @cache.cached(timeout=900, key_prefix='ai_%s')  # 暂时关闭缓存调试
def api_analyze(code):
    """AI综合分析"""
    if not DEEPSEEK_API_KEY:
        return jsonify({"error": "未配置DeepSeek API Key", "hint": "在key.txt中设置或设置环境变量DEEPSEEK_API_KEY"}), 500

    try:
        market, clean_code = get_market(code)
        sym = f'{market}{clean_code}'

        # 1. 行情
        try:
            text = http_get(f'https://hq.sinajs.cn/list={sym}', timeout=10)
            q = parse_sina_quote(text)
        except Exception as e:
            return jsonify({"error": f"行情获取失败: {str(e)}"}), 500
        if not q or q['price'] == 0:
            return jsonify({"error": f"未找到股票 {clean_code}"}), 404
        change_pct = ((q['price']-q['prev_close'])/q['prev_close']*100) if q['prev_close'] else 0
        quote = {"code": clean_code, "name": q['name'], "price": q['price'],
                 "change_pct": round(change_pct,2), "change_amt": round(q['price']-q['prev_close'],2),
                 "open": q['open'], "high": q['high'], "low": q['low'], "prev_close": q['prev_close'],
                 "volume": q['volume'], "amount": q['amount'], "turnover_rate": 0}

        # 2. K线
        kurl = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen=90'
        raw_kl = json.loads(http_get(kurl, timeout=15))
        klines = []
        for item in raw_kl[-90:]:
            klines.append({"date": item['day'], "open": float(item['open']), "close": float(item['close']),
                          "high": float(item['high']), "low": float(item['low']), "volume": float(item['volume']), "pct_change": 0})
        for i in range(1, len(klines)):
            if klines[i-1]['close']!=0:
                klines[i]['pct_change'] = round((klines[i]['close']-klines[i-1]['close'])/klines[i-1]['close']*100, 2)

        # 3. 新闻（可选）
        news_list = []

        # 4. DeepSeek AI
        user_prompt = build_user_prompt(clean_code, q['name'], quote, klines, news_list)
        ai_resp = post_json('https://api.deepseek.com/v1/chat/completions', {
            "model": "deepseek-chat",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
            "temperature": 0.3, "max_tokens": 3000,
        }, headers_extra={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'})
        ai_text = ai_resp['choices'][0]['message']['content'].strip()
        ai_text = re.sub(r'^```(?:json)?\s*', '', ai_text)
        ai_text = re.sub(r'\s*```$', '', ai_text)

        try:
            ai_result = json.loads(ai_text)
        except json.JSONDecodeError:
            # Retry
            ai_resp2 = post_json('https://api.deepseek.com/v1/chat/completions', {
                "model": "deepseek-chat",
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt},
                            {"role": "assistant", "content": ai_text},
                            {"role": "user", "content": "请返回纯JSON，不要markdown标记。"}],
                "temperature": 0.1, "max_tokens": 3000,
            }, headers_extra={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'})
            ai_text2 = ai_resp2['choices'][0]['message']['content'].strip()
            ai_text2 = re.sub(r'^```(?:json)?\s*', '', ai_text2)
            ai_text2 = re.sub(r'\s*```$', '', ai_text2)
            try:
                ai_result = json.loads(ai_text2)
            except json.JSONDecodeError:
                ai_result = {"error": "AI返回格式异常", "raw_text": ai_text[:800]}

        return jsonify({"quote": quote, "klines": klines, "news": news_list, "ai_analysis": ai_result})

    except Exception as e:
        return jsonify({"error": f"分析失败: {str(e)}"}), 500


# ==================== 启动 ====================
if __name__ == '__main__':
    print("=" * 50)
    print("   A-stock AI Analyzer - Backend Service")
    print("=" * 50)
    print(f"[OK] DeepSeek: {'configured' if DEEPSEEK_API_KEY else 'NOT CONFIGURED'}")
    print(f"[OK] Data source: Sina Finance API")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=5099)
