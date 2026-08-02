#!/usr/bin/env python3
"""
基金数据抓取脚本
从天天基金网抓取最新数据，生成 public/data/funds.json
用法: python scraper/scrape.py
"""
import re
import json
import time
import sys
import os
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://fund.eastmoney.com/',
}
DELAY = 4  # 每只基金间隔秒数
MAX_RETRIES = 3  # 单次请求最大重试次数
RETRY_BACKOFF = 2  # 重试间隔倍数（秒）


def fetch_with_retry(url, timeout=15):
    """带重试的 HTTP 请求"""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.encoding = 'utf-8'
            if resp.status_code == 200:
                return resp
            print(f'    [重试 {attempt}/{MAX_RETRIES}] HTTP {resp.status_code} for {url}')
        except Exception as e:
            last_err = e
            print(f'    [重试 {attempt}/{MAX_RETRIES}] {e} for {url}')
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF * attempt)
    raise last_err or Exception(f'请求失败: {url}')


def calc_volatility(nwt_data):
    """从日净值序列计算年化波动率
    nwt_data: [{'x': timestamp_ms, 'y': nav}, ...]
    返回: 年化波动率（如 0.22 表示 22%），不足60条数据返回 None
    """
    if not nwt_data or len(nwt_data) < 60:
        return None
    # 取最近1年的数据计算
    latest_ts = nwt_data[-1]['x']
    one_year_ms = int(365.25 * 24 * 3600 * 1000)
    ts_cutoff = latest_ts - one_year_ms
    recent = [d for d in nwt_data if d['x'] >= ts_cutoff]
    if len(recent) < 30:
        recent = nwt_data[-252:]  # 回退到最近252条（约1年交易日）

    # 计算日收益率
    daily_returns = []
    for i in range(1, len(recent)):
        prev_nav = recent[i - 1]['y']
        curr_nav = recent[i]['y']
        if prev_nav > 0 and curr_nav > 0:
            daily_returns.append(curr_nav / prev_nav - 1)

    if len(daily_returns) < 20:
        return None

    # 年化波动率 = 日收益率标准差 × sqrt(252)
    n = len(daily_returns)
    mean_r = sum(daily_returns) / n
    variance = sum((r - mean_r) ** 2 for r in daily_returns) / (n - 1)
    daily_vol = variance ** 0.5
    annual_vol = daily_vol * (252 ** 0.5)

    # 合理性检查：波动率应在 0.05-0.8 之间
    if 0.05 <= annual_vol <= 0.8:
        return round(annual_vol, 4)
    return None

# 兜底数据文件路径
FALLBACK = os.path.join(os.path.dirname(__file__), '..', 'data', 'funds_fallback.json')
# 输出路径
OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'funds.json')

FUND_LIST = [
    # (code, index_type)
    ('016532', '纳斯达克100'), ('016055', '纳斯达克100'), ('018043', '纳斯达克100'),
    ('160213', '纳斯达克100'), ('040046', '纳斯达克100'), ('000834', '纳斯达克100'),
    ('161130', '纳斯达克100'), ('270042', '纳斯达克100'), ('016452', '纳斯达克100'),
    ('539001', '纳斯达克100'), ('019547', '纳斯达克100'), ('018966', '纳斯达克100'),
    ('015299', '纳斯达克100'), ('019172', '纳斯达克100'), ('019441', '纳斯达克100'),
    ('019524', '纳斯达克100'), ('019736', '纳斯达克100'),
    ('050025', '标普500'), ('161125', '标普500'), ('017641', '标普500'),
    ('017028', '标普500'), ('018064', '标普500'), ('096001', '标普500'),
    ('007721', '标普500'),
]


def load_fallback():
    """加载兜底数据"""
    with open(FALLBACK, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {item['code']: item for item in data}


def scrape_fund_page(code):
    """从基金主页抓取"""
    url = f'https://fund.eastmoney.com/{code}.html'
    try:
        resp = fetch_with_retry(url)
        text = resp.text
        data = {}

        m = re.search(r'年化跟踪误差.*?(\d+\.\d+)%', text)
        if m: data['tracking_error'] = float(m.group(1)) / 100

        m = re.search(r'规模.*?(\d+\.\d+)\s*亿元', text)
        if m: data['scale'] = float(m.group(1))

        # 使用 pingzhongdata/{code}.js 提取精准的收益率和成立日期
        pz_url = f'http://fund.eastmoney.com/pingzhongdata/{code}.js'
        pz_resp = fetch_with_retry(pz_url)
        pz_text = pz_resp.text

        # 基金名称：使用 fS_name（权威来源）
        m_name = re.search(r'fS_name\s*=\s*"([^"]+)"', pz_text)
        if m_name:
            data['name'] = m_name.group(1)

        # 近1年涨跌幅：使用官方 syl_1n（最准确）
        m1 = re.search(r'syl_1n\s*=\s*"([^"]+)"', pz_text)
        if m1 and m1.group(1):
            data['return_1yr'] = float(m1.group(1)) / 100

        # 成立日期 + 年化波动率：从 Data_netWorthTrend 获取
        m_nwt = re.search(r'var Data_netWorthTrend\s*=\s*(\[.*?\]);', pz_text)
        if m_nwt:
            import json as _json
            from datetime import datetime as _dt, timezone as _tz, timedelta as _td
            _tz8 = _tz(_td(hours=8))
            nwt = _json.loads(m_nwt.group(1))
            if nwt:
                data['inception_date'] = _dt.fromtimestamp(
                    nwt[0]['x'] / 1000, tz=_tz8).strftime('%Y-%m-%d')
                # 从日净值序列计算年化波动率
                vol = calc_volatility(nwt)
                if vol is not None:
                    data['volatility'] = vol

        # 近3年 & 成立以来涨跌幅：使用 Data_ACWorthTrend（累计净值）
        # 累计净值已包含分红再投资，不受基金拆分/分红影响
        m_ac = re.search(r'var Data_ACWorthTrend\s*=\s*(\[.*?\]);', pz_text)
        if m_ac:
            import json as _json
            from datetime import datetime as _dt, timezone as _tz, timedelta as _td
            _tz8 = _tz(_td(hours=8))
            act = _json.loads(m_ac.group(1))
            if act:
                first_ac = act[0][1]
                last_ac = act[-1][1]
                inception_ts = act[0][0]
                latest_ts = act[-1][0]

                # 成立以来涨跌幅
                data['return_since'] = (last_ac / first_ac) - 1

                # 近3年涨跌幅
                ts_3y = latest_ts - int(3 * 365.25 * 24 * 3600 * 1000)
                if ts_3y >= inception_ts:
                    pt_3y = min(act, key=lambda d: abs(d[0] - ts_3y))
                    data['return_3yr'] = (last_ac / pt_3y[1]) - 1
                else:
                    data['return_3yr'] = None

        # 晨星评级：通过 class="jjpjX" 精准提取（X为1-5）
        m = re.search(r'jjpj(\d)', text)
        if m:
            data['morningstar'] = int(m.group(1))
        else:
            data['morningstar'] = 0

        # 限额限购解析
        # 以页面上的"申购状态"字段为准（暂停申购/限大额/开放申购）
        sg_status = re.search(r'申购状态.*?>(暂停申购|限大额|开放申购)', text)
        limit_match = re.search(r'单日累计购买上限\s*(\d+(?:\.\d+)?)\s*元', text) or re.search(r'购买上限.*?(\d+(?:\.\d+)?)\s*元', text)

        if sg_status:
            status_text = sg_status.group(1)
            if status_text == '暂停申购':
                data['daily_limit'] = 0
                data['limit_status'] = '暂停申购'
            elif status_text == '限大额' and limit_match:
                dl = int(float(limit_match.group(1)))
                data['daily_limit'] = dl
                data['limit_status'] = f'限{dl}元/日'
            elif status_text == '限大额':
                data['daily_limit'] = 0
                data['limit_status'] = '限大额'
            else:
                data['daily_limit'] = None
                data['limit_status'] = '正常'
        elif '暂停申购' in text:
            data['daily_limit'] = 0
            data['limit_status'] = '暂停申购'
        elif limit_match:
            dl = int(float(limit_match.group(1)))
            data['daily_limit'] = dl
            data['limit_status'] = f'限{dl}元/日'
        else:
            data['daily_limit'] = None
            data['limit_status'] = '正常'

        return data
    except Exception as e:
        print(f'  [WARN] 抓取 {code} 主页失败: {e}')
        return {}


def scrape_f10_page(code):
    """从 f10 基本概况页抓取详细信息"""
    url = f'https://fundf10.eastmoney.com/jbgk_{code}.html'
    try:
        resp = fetch_with_retry(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        data = {}

        # 解析所有 table.info 中的 th-td 对
        fields = {}
        for table in soup.find_all('table', class_='info'):
            for row in table.find_all('tr'):
                ths = row.find_all('th')
                tds = row.find_all('td')
                for i, th in enumerate(ths):
                    td = tds[i] if i < len(tds) else None
                    if td:
                        label = th.get_text(strip=True)
                        # 优先取链接文本
                        links = td.find_all('a')
                        value = ', '.join(a.get_text(strip=True) for a in links) if links else td.get_text(strip=True)
                        fields[label] = value

        # 映射到数据字段
        if '基金全称' in fields:
            data['full_name'] = fields['基金全称']
        if '基金类型' in fields:
            data['fund_type'] = fields['基金类型']
        if '基金管理人' in fields:
            data['manager_company'] = fields['基金管理人']
        if '基金托管人' in fields:
            data['custodian'] = fields['基金托管人']
        if '基金经理人' in fields:
            data['fund_manager'] = fields['基金经理人']
        if '业绩比较基准' in fields:
            data['benchmark'] = fields['业绩比较基准']
        if '跟踪标的' in fields:
            data['tracking_index'] = fields['跟踪标的']
        if '成立来分红' in fields:
            data['dividend_info'] = fields['成立来分红']
        if '最高认购费率' in fields:
            m = re.search(r'(\d+\.\d+)%', fields['最高认购费率'])
            if m:
                data['purchase_fee'] = float(m.group(1)) / 100
        if '销售服务费率' in fields:
            m = re.search(r'(\d+\.\d+)%', fields['销售服务费率'])
            if m:
                data['sales_fee'] = float(m.group(1)) / 100
        if '发行日期' in fields:
            m = re.search(r'(\d{4})年(\d{2})月(\d{2})日', fields['发行日期'])
            if m:
                data['issue_date'] = f'{m.group(1)}-{m.group(2)}-{m.group(3)}'

        return data
    except Exception as e:
        print(f'  [WARN] 抓取 {code} f10页失败: {e}')
        return {}


def scrape_fee_page(code):
    """从费率详情页抓取"""
    url = f'https://fundf10.eastmoney.com/jjfl_{code}.html'
    try:
        resp = fetch_with_retry(url)
        text = resp.text
        data = {}

        m = re.search(r'管理费率.*?(\d+\.\d+)%', text)
        if m: data['mgmt_fee'] = float(m.group(1)) / 100

        m = re.search(r'托管费率.*?(\d+\.\d+)%', text)
        if m: data['custody_fee'] = float(m.group(1)) / 100

        return data
    except Exception as e:
        print(f'  [WARN] 抓取 {code} 费率页失败: {e}')
        return {}


def scrape_limit_announcement(code):
    """从基金公告中提取直销渠道限购信息"""
    try:
        # 获取公告列表（需要特殊 Referer）
        ann_headers = {**HEADERS, 'Referer': 'https://fundf10.eastmoney.com/'}
        url = f'http://api.fund.eastmoney.com/f10/JJGG?callback=jQuery&fundcode={code}&pageIndex=1&pageSize=30&type=0'
        resp = requests.get(url, headers=ann_headers, timeout=15)
        resp.encoding = 'utf-8'
        m = re.search(r'jQuery\((.*)\)', resp.text, re.DOTALL)
        if not m:
            return {}
        data = json.loads(m.group(1))

        # 查找最新的限购相关公告
        target_ann_id = None
        for item in data.get('Data', []):
            title = item.get('TITLE', '')
            if any(k in title for k in ['大额申购', '暂停大额', '暂停申购', '限制大额', '调整大额', '限制申购']):
                target_ann_id = item.get('ID')
                break

        if not target_ann_id:
            return {}

        # 获取公告全文
        ann_url = f'https://np-cnotice-fund.eastmoney.com/api/content/ann?art_code={target_ann_id}&client_source=fund_pc&page_index=1&page_size=1'
        ann_resp = requests.get(ann_url, headers=HEADERS, timeout=15)
        ann_resp.encoding = 'utf-8'
        ann_data = ann_resp.json()

        content = ''
        try:
            content = ann_data['data']['notice_content']
        except (KeyError, TypeError):
            pass
        if not content:
            try:
                content = ann_data['data']['list'][0]['content']
            except (KeyError, TypeError, IndexError):
                pass

        if not content:
            return {'limit_announcement_id': target_ann_id}

        # 清理 HTML 标签，保留空格用于正则匹配
        text_norm = re.sub(r'<[^>]+>', ' ', content)
        text_norm = re.sub(r'[\n\r\t\xa0\u3000]+', ' ', text_norm)
        text_norm = re.sub(r'\s+', ' ', text_norm)

        result = {
            'direct_daily_limit': None,
            'direct_limit_status': None,
            'limit_announcement_id': target_ann_id
        }

        # === 多模式提取直销限额 ===
        # 模式1: "通过本公司直销机构...不超过 X 元"
        m1 = re.search(
            r'(?:通过|经由?)(?:本)?(?:公司|基金管理人)?直销(?:机构|渠道|平台|柜台)?'
            r'(?:申购|买入)?(?:本基金)?.*?'
            r'(?:不超过|限额为?|上限为?)\s*(\d+(?:\.\d+)?)\s*(?:元|元人民币)',
            text_norm
        )
        # 模式2: "在直销机构...超过 X 元...有权拒绝"（招商等）
        m2 = re.search(
            r'(?:在|调整)(?:本公司)?直销(?:机构|渠道|平台)?'
            r'.*?(?:超过|高于)\s*(\d+(?:\.\d+)?)\s*(?:元|元人民币)'
            r'.*?(?:有权|将予以?)(?:部分或全部)?拒绝',
            text_norm
        )
        # 模式3: "直销" 后紧跟表格数据中的限额数字（大成等）
        m3 = re.search(
            r'直销(?:机构|渠道|平台|柜台)?(?:\s*(?:（[^）]*）)?)?\s*(?:申购|买入)'
            r'.*?(?:累计金额应?不超过|累计上限为?|单笔.*?上限为?)\s*(\d+(?:\.\d+)?)\s*(?:元|元人民币)',
            text_norm
        )
        # 模式4: "直销" 段落中出现 "不超过 X 元"（宽松匹配，限制在200字符内）
        direct_section = re.search(r'直销.{0,200}?不超过\s*(\d+(?:\.\d+)?)\s*(?:元|元人民币)', text_norm)

        # 按优先级取值
        for match in [m1, m2, m3, direct_section]:
            if match:
                dl = int(float(match.group(1)))
                if dl > 0:  # 排除0的情况
                    result['direct_daily_limit'] = dl
                    result['direct_limit_status'] = f'限{dl}元/日'
                    break

        # 检查直销渠道是否暂停（覆盖上面的限额）
        if re.search(r'(?:在)?直销(?:机构|渠道|平台)?(?:\s*)?暂停', text_norm):
            result['direct_daily_limit'] = 0
            result['direct_limit_status'] = '暂停申购'

        return result
    except Exception as e:
        print(f'  [WARN] 抓取 {code} 直销限额公告失败: {e}')
        return {}


# 校验范围缓存（避免每次调用 validate 都读文件）
_VALIDATION_CACHE = None


def validate(data):
    """校验数据 - 范围从 config/algorithm.json 读取（首次读取后缓存）"""
    global _VALIDATION_CACHE
    if _VALIDATION_CACHE is None:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'algorithm.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            _VALIDATION_CACHE = {k: tuple(v) for k, v in json.load(f)['validation'].items()}
    checks = _VALIDATION_CACHE
    cleaned = {}
    for k, v in data.items():
        if k in checks:
            lo, hi = checks[k]
            if v is not None and lo <= v <= hi:
                cleaned[k] = v
            else:
                print(f'  [校验] {k}={v} 超范围，已丢弃')
        else:
            cleaned[k] = v
    return cleaned


def main():
    print('=' * 60)
    print('基金数据抓取开始')
    print('=' * 60)

    fallback = load_fallback()
    results = []
    updated = 0
    errors = []

    for code, index_type in FUND_LIST:
        print(f'\n[{code}] 抓取中...')

        # 基础数据来自兜底
        base = fallback.get(code, {})
        base['code'] = code
        base['index_type'] = index_type

        # 抓取最新数据
        page_data = scrape_fund_page(code)
        time.sleep(DELAY)
        f10_data = scrape_f10_page(code)
        time.sleep(DELAY)
        fee_data = scrape_fee_page(code)
        time.sleep(DELAY)
        limit_data = scrape_limit_announcement(code)
        time.sleep(DELAY)

        # 合并：抓取到的数据覆盖兜底数据
        merged = {**base, **page_data, **f10_data, **fee_data, **limit_data}
        merged = validate(merged)

        total_fields = len(page_data) + len(f10_data) + len(fee_data) + len(limit_data)
        if total_fields > 0:
            updated += 1
            print(f'  [OK] 更新了 {total_fields} 个字段')
        else:
            errors.append(f'{code}: 未获取到新数据，使用兜底数据')
            print(f'  [INFO] 使用兜底数据')

        # 确保有 name 字段
        if 'name' not in merged:
            merged['name'] = base.get('name', f'基金{code}')

        results.append(merged)

    # 输出时间戳（强制使用北京时间 UTC+8）
    from datetime import datetime, timezone, timedelta
    tz_beijing = timezone(timedelta(hours=8))
    timestamp = datetime.now(tz_beijing).strftime('%Y-%m-%dT%H:%M:%S')
    for r in results:
        r['updated_at'] = timestamp

    # 写入 JSON
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f'\n{"=" * 60}')
    print(f'抓取完成: {updated}/{len(FUND_LIST)} 只基金更新')
    print(f'输出: {OUTPUT}')
    if errors:
        print(f'警告: {len(errors)} 个问题')
        for e in errors:
            print(f'  - {e}')
    print('=' * 60)

    # 输出结构化摘要供 CI/CD 解析
    summary = {
        'timestamp': timestamp,
        'total': len(FUND_LIST),
        'updated': updated,
        'failed': len(errors),
        'errors': errors,
    }
    print(f'\n__SCRAPE_SUMMARY__{json.dumps(summary, ensure_ascii=False)}__SCRAPE_SUMMARY__')

    return 0 if updated > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
