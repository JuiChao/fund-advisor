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
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fsm import FinancialEventFSM

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://fund.eastmoney.com/',
}
DELAY = 0.5  # 每步请求间隔秒数（平衡抓取性能与稳定性）
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

def load_fallback():
    """加载兜底数据"""
    with open(FALLBACK, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {item['code']: item for item in data}


# 全量标的池：从 data/funds_fallback.json 自动提取（涵盖A/C/D/E/I全量份额）
_FB_DATA = load_fallback()
FUND_LIST = [
    (item['code'], item['index_type'])
    for item in sorted(_FB_DATA.values(), key=lambda x: (0 if x.get('index_type') == '纳斯达克100' else 1, x.get('family_id', ''), x['code']))
]


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
        # 1. 检查是否为直销专属 / 尚未开通天天基金代销
        is_sale_false = 'fundIsSale = false' in text
        not_agency = ('尚未开通天天基金代销' in text) or ('不开放购买' in text and 'fundBuyStatus = "4"' in text)
        if is_sale_false or not_agency:
            data['daily_limit'] = 0
            data['limit_status'] = '未开通代销'
            return data

        # 优先使用天天基金官方页面底层状态变量 fundBuyStatus（权威第一信源）："4"=暂停申购, "1"=开放/限额
        m_buy = re.search(r'var\s+fundBuyStatus\s*=\s*"([^"]+)"', text)
        buy_code = m_buy.group(1) if m_buy else None

        sg_status = re.search(r'申购状态.*?>(暂停申购|限大额|开放申购)', text)
        limit_match = re.search(r'(?:单日累计购买上限|购买上限|单日上限|限额)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*元', text)

        if buy_code == '4' or (sg_status and sg_status.group(1) == '暂停申购'):
            data['daily_limit'] = 0
            data['limit_status'] = '暂停申购'
        elif limit_match:
            dl = int(float(limit_match.group(1)))
            data['daily_limit'] = dl
            data['limit_status'] = f'限{dl}元/日'
        elif sg_status and sg_status.group(1) == '限大额':
            data['daily_limit'] = 0
            data['limit_status'] = '限大额'
        elif '暂停申购' in text:
            data['daily_limit'] = 0
            data['limit_status'] = '暂停申购'
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
    """从费率详情页抓取，精准解析运作费用表格与优惠费率"""
    url = f'https://fundf10.eastmoney.com/jjfl_{code}.html'
    try:
        resp = fetch_with_retry(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        data = {}

        for td in soup.find_all(['td', 'th']):
            txt = td.get_text(strip=True)
            if txt in ['管理费率', '托管费率', '销售服务费率']:
                next_td = td.find_next_sibling('td')
                if next_td:
                    val_txt = next_td.get_text(strip=True)
                    m = re.search(r'(\d+(?:\.\d+)?)%', val_txt)
                    if m:
                        val = float(m.group(1)) / 100
                        if txt == '管理费率': data['mgmt_fee'] = val
                        elif txt == '托管费率': data['custody_fee'] = val
                        elif txt == '销售服务费率': data['sales_fee'] = val
                    elif '---' in val_txt or '-' in val_txt:
                        if txt == '销售服务费率': data['sales_fee'] = 0.0

        # 前端申购费解析
        m_pur = re.search(r'申购费率.*?(\d+(?:\.\d+)?)%', resp.text)
        if m_pur:
            data['purchase_fee'] = float(m_pur.group(1)) / 100

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

        # 查找最新的限购相关公告（标题关键词匹配）
        title_keywords = [
            '大额申购', '暂停大额', '暂停申购', '限制大额', '调整大额', '限制申购',
            '申购业务上限', '金额限制', '限额申购',
            '恢复申购', '恢复大额', '恢复办理', '取消限额', '取消大额', '取消上限', '取消申购上限',
            '直销电子交易平台', '直销渠道',
            '规模上限', '总规模',
            '费率优惠', '降低费率', '调整费率',
        ]
        target_ann_id = None
        # 根据当前基金份额类型，动态排除其他互斥份额的专属公告
        fallback_item = _FB_DATA.get(code, {})
        my_class = fallback_item.get('share_class', '')
        all_classes = {'A', 'C', 'D', 'E', 'I', 'F', 'H'}
        other_classes = all_classes - {my_class} if my_class else {'E', 'I', 'F', 'H'}
        exclude_keywords = [f'{c}类' for c in other_classes]
        target_title = ''
        for item in data.get('Data', []):
            title = item.get('TITLE', '')

            # 如果公告明确指明了本份额（如标题含"A类"或"C类"），绝不排除
            if my_class and f'{my_class}类' in title:
                pass
            elif any(k in title for k in exclude_keywords):
                # 只有当公告明确指定了其他份额，且未提及本份额时，才排除
                continue

            # 排除节假日/休市临时暂停公告（此类公告属于市场休市，非日常申购限额政策）
            if any(k in title for k in ['节假日', '非交易日', '休市', '主要投资市场节假日']):
                continue

            # 排除纯美元份额公告（所有收录标的均为人民币份额）
            if any(k in title for k in ['美元份额', '美元现汇', '美元现钞']) and '人民币' not in title:
                continue
            
            if any(k in title for k in title_keywords):
                target_ann_id = item.get('ID')
                target_title = title
                break

        if not target_ann_id:
            return {}

        # 双源获取公告全文：优先使用 JSON API，若失败或被重置则自动回退下载东财官方 PDF 原件提取
        content = ''
        try:
            ann_url = f'https://np-cnotice-fund.eastmoney.com/api/content/ann?art_code={target_ann_id}&client_source=fund_pc&page_index=1&page_size=1'
            ann_resp = requests.get(ann_url, headers=HEADERS, timeout=8)
            ann_resp.encoding = 'utf-8'
            ann_data = ann_resp.json()
            content = ann_data.get('data', {}).get('notice_content', '') or ann_data.get('data', {}).get('list', [{}])[0].get('content', '')
        except Exception:
            pass

        if not content:
            try:
                pdf_url = f'http://pdf.dfcfw.com/pdf/H2_{target_ann_id}_1.pdf'
                pr = requests.get(pdf_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                if pr.status_code == 200:
                    import io
                    from pypdf import PdfReader
                    pdf = PdfReader(io.BytesIO(pr.content))
                    content = '\n'.join(p.extract_text() or '' for p in pdf.pages)
            except Exception:
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

        # === 核心解析：使用金融事件槽位有限状态机 (Financial Slot-Filling FSM) ===
        fsm_res = FinancialEventFSM.parse_announcement(
            content=content,
            title=target_title,
            fund_code=code,
            share_class=my_class,
            ann_id=target_ann_id
        )
        if fsm_res.direct_daily_limit is not None or fsm_res.direct_limit_status is not None:
            result['direct_daily_limit'] = fsm_res.direct_daily_limit
            result['direct_limit_status'] = fsm_res.direct_limit_status
            return result

        # === 优先匹配直销专属暂停公告（如华夏标普：在华夏直销电子交易平台暂停申购业务） ===
        # 注意：排除“暂停大额申购”（大额限制不等于完全暂停）
        if (re.search(r'在(?:本公司)?直销(?:电子交易平台|机构|渠道)?(?:暂停|停止)(?:办理)?(?:本基金)?.*?(?<!大额)申购', text_norm) or \
            re.search(r'暂停(?:在)?(?:本公司)?直销(?:电子交易平台|机构|渠道)?.*?(?<!大额)申购', text_norm) or \
            re.search(r'直销(?:电子交易平台|机构|渠道)?暂停(?<!大额)申购', text_norm)) and \
           not re.search(r'直销.*?暂停大额申购', text_norm):
            result['direct_daily_limit'] = 0
            result['direct_limit_status'] = '暂停申购'
            return result

        # === 优先匹配份额专属暂停公告（如天弘：A份额、C份额暂停申购） ===
        # 注意：必须是完全“暂停申购”，排除“暂停大额申购”或仅暂停美元份额的公告
        if my_class and '大额' not in target_title:
            if target_title and re.search(rf'{my_class}\s*(?:类|份额).*?暂停(?<!大额)申购', target_title):
                result['direct_daily_limit'] = 0
                result['direct_limit_status'] = '暂停申购'
                return result
            m_susp = re.search(rf'{my_class}\s*(?:类|份额)[^。\n]*?暂停(?:(?<!大额)申购|办理)', text_norm) or \
                     re.search(rf'暂停\s*[^。\n]*?{my_class}\s*(?:类|份额)[^。\n]*?(?<!大额)申购', text_norm)
            if m_susp and '大额' not in m_susp.group(0) and '美元' not in m_susp.group(0):
                result['direct_daily_limit'] = 0
                result['direct_limit_status'] = '暂停申购'
                return result

        # === 优先匹配恢复申购 / 取消大额申购限制公告 ===
        is_resumption = ('恢复' in target_title and '申购' in target_title) or \
                        ('取消' in target_title and any(k in target_title for k in ['限额', '上限', '规模', '额度']))
        if is_resumption:
            # 确认是否仅适用于代销渠道
            if '代销' in target_title and '直销' not in target_title:
                pass
            else:
                result['direct_daily_limit'] = None
                result['direct_limit_status'] = '开放申购'
                return result

        # === 多模式提取直销限额 ===
        # 模式0a: "由 X 元调整为 Y 元"（精准提取调整后的目标金额 Y，剔除被替代的原限额 X）
        m_adjust = re.search(
            r'(?:直销(?:机构|渠道|平台|柜台)?.*?)?由\D{0,15}?([0-9,]+(?:\.\d+)?)\s*元.*?(?:调整为|上调至|下调至|调整至)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*元',
            text_norm
        )
        if m_adjust:
            val = int(float(m_adjust.group(2).replace(',', '')))
            if val > 0:
                result['direct_daily_limit'] = val
                result['direct_limit_status'] = f'限{val}元/日'
                return result

        # 模式0: 基金代码精准匹配表格（如南方021000公告表格）
        m_code = re.search(rf'{code}\D{{0,60}}?(?:该基金份额的)?(?:限制金额|限额)\s*([0-9,]+(?:\.\d+)?)\s*元', text_norm) or \
                 re.search(rf'(?:限制金额|限额)\D{{0,60}}?{code}\D{{0,20}}?([0-9,]+(?:\.\d+)?)\s*元', text_norm)

        # 模式0b: 优先匹配本份额专属直销限额或公告
        m0 = None
        if my_class:
            m0 = re.search(
                rf'{my_class}\s*(?:类|份额)[^A-Z。\n]{{0,120}}?(?:不超过|不得超(?:过)?|上限为?|限额为?)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)',
                text_norm
            ) or re.search(
                r'(?:通过|经由?|在)?(?:本)?(?:公司|基金管理人)?直销(?:机构|渠道|平台|柜台)?'
                rf'.*?{my_class}[^A-Z。\n]{{0,80}}?'
                r'(?:不超过|不得超(?:过)?|限额为?|上限为?)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)',
                text_norm
            ) or re.search(
                rf'单个基金账户单日累计申购\s*{my_class}.*?金额(?:不得超(?:过)?|不超过)\s*([0-9,]+(?:\.\d+)?)\s*元',
                text_norm
            )

        # 模式0c: 若公告标题指明了本份额（如"I类基金份额申购...金额限制的公告"），提取该公告中的金额
        m_title_class = None
        if my_class and f'{my_class}类' in text_norm[:200]:
            m_title_class = re.search(r'(?:调整后)?限额\s*([0-9,]+(?:\.\d+)?)\s*元', text_norm) or \
                            re.search(r'限制金额\s*([0-9,]+(?:\.\d+)?)\s*元', text_norm)

        # 模式1: "通过本公司直销机构...不超过 X 元"
        m1 = re.search(
            r'(?:通过|经由?)(?:本)?(?:公司|基金管理人)?直销(?:机构|渠道|平台|柜台|中心)?'
            r'(?:(?!代销).)*?'
            r'(?:不超过|限额为?|上限为?|均应不超过|限制(?:仍)?为?)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)',
            text_norm
        )
        # 模式2: "在直销机构...金额上限为 X 元" / "超过 X 元...有权拒绝"（招商、华夏、万家等）
        m2 = re.search(
            r'直销(?:机构|渠道|平台|柜台|中心)?(?:(?!代销).)*?(?:金额上限为|上限为|限额为?|不超过|均应不超过|限制(?:仍)?为?)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)',
            text_norm
        ) or re.search(
            r'(?:在|调整)(?:本公司)?直销(?:机构|渠道|平台|中心)?'
            r'(?:(?!代销).)*?(?:超过|高于)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)',
            text_norm
        )
        # 模式3: "直销" 后紧跟表格数据中的限额数字（大成等）
        m3 = re.search(
            r'直销(?:机构|渠道|平台|柜台|中心)?(?:\s*(?:（[^）]*）)?)?\s*(?:申购|买入)'
            r'.*?(?:累计金额应?不超过|累计上限为?|单笔.*?上限为?)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)',
            text_norm
        )
        # 模式4: "直销" 段落中出现 "不超过 X 元"（宽松匹配，排除包含代销的跨句子干扰）
        m4 = re.search(r'直销(?:(?!代销).){0,300}?(?:不超过|上限|均应不超过|限制(?:仍)?为?)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)', text_norm)
        # 模式5: "直销电子交易平台" 专用（华夏等，允许更长距离匹配）
        m5 = re.search(r'直销电子交易平台.{0,500}?(?:不超过|上限为?)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)', text_norm)

        # 按优先级取值
        match_candidates = ([m_code] if m_code else []) + ([m0] if m0 else []) + ([m_title_class] if m_title_class else []) + [m1, m2, m3, m5, m4]
        for match in match_candidates:
            if match:
                raw_val = match.group(1).replace(',', '')
                dl = int(float(raw_val))
                if dl > 0:
                    result['direct_daily_limit'] = dl
                    result['direct_limit_status'] = f'限{dl}元/日'
                    break

        # 检查直销渠道是否全面暂停（仅当未提取到限额时才判定，且严格排除“暂停大额申购”）
        if not result['direct_daily_limit']:
            if my_class and re.search(rf'{my_class}\s*类基金份额暂停(?<!大额)申购', text_norm) and '大额' not in target_title:
                result['direct_daily_limit'] = 0
                result['direct_limit_status'] = '暂停申购'
            elif (re.search(r'(?:在)?直销(?:机构|渠道|平台|中心)?.{0,10}?暂停(?<!大额)申购', text_norm) or \
                  re.search(r'直销.*?暂停(?<!大额)申购', text_norm)) and \
                 '大额' not in target_title and not re.search(r'直销.*?暂停大额', text_norm):
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


def load_cached_funds():
    """加载已存在的 public/data/funds.json 缓存"""
    if os.path.exists(OUTPUT):
        try:
            with open(OUTPUT, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return {item['code']: item for item in data if isinstance(item, dict) and 'code' in item}
        except Exception as e:
            print(f'  [WARN] 读取本地缓存失败: {e}')
    return {}


def fetch_market_announcement_feed(max_pages=3, page_size=100, timeout=10):
    """
    【CDC增量流】获取全市场最新公告 Feed 流
    从东财全市场公告接口拉取最近 N 页公告，用于快速检测标的池是否有新公告发布
    """
    ann_headers = {**HEADERS, 'Referer': 'https://fundf10.eastmoney.com/'}
    feed_items = []
    for page in range(1, max_pages + 1):
        url = f'http://api.fund.eastmoney.com/f10/JJGG?callback=jQuery&fundcode=&pageIndex={page}&pageSize={page_size}&type=0'
        try:
            resp = requests.get(url, headers=ann_headers, timeout=timeout)
            resp.encoding = 'utf-8'
            m = re.search(r'jQuery\((.*)\)', resp.text, re.DOTALL)
            if not m:
                break
            data = json.loads(m.group(1))
            items = data.get('Data', [])
            if not items:
                break
            feed_items.extend(items)
        except Exception as e:
            print(f'  [WARN] 获取全市场公告 Feed 第 {page} 页失败: {e}')
            break
    return feed_items


def detect_cdc_affected_funds(feed_items, universe_codes, fallback_data):
    """
    【CDC增量流】从全市场公告中精确定位属于标的池且与申购/限额/费率相关的标的代码
    """
    LIMIT_KEYWORDS = [
        '大额申购', '暂停大额', '暂停申购', '限制大额', '调整大额', '限制申购',
        '申购业务上限', '金额限制', '限额申购',
        '恢复申购', '恢复大额', '恢复办理', '取消限额', '取消大额', '取消上限', '取消申购上限',
        '直销电子交易平台', '直销渠道', '直销柜台',
        '规模上限', '总规模',
        '费率优惠', '降低费率', '调整费率',
    ]

    affected_codes = set()
    universe_set = set(universe_codes)

    for item in feed_items:
        fc = item.get('FUNDCODE')
        title = item.get('TITLE', '')
        # 排除节假日临时休市和纯美元份额
        if any(k in title for k in ['节假日', '非交易日', '休市', '主要投资市场节假日']):
            continue
        if any(k in title for k in ['美元份额', '美元现汇', '美元现钞']) and '人民币' not in title:
            continue

        is_quota_event = any(kw in title for kw in LIMIT_KEYWORDS)
        if not is_quota_event:
            continue

        # 检查是否直接命中代码
        if fc in universe_set:
            affected_codes.add(fc)
            print(f'  [CDC事件命中] 标的代码 {fc} 发布限购相关公告: {title} ({item.get("PUBLISHDATEDesc")})')
            continue

        # 检查标题中是否包含代码
        for code in universe_set:
            if code in title:
                affected_codes.add(code)
                print(f'  [CDC事件命中] 公告标题提及标的代码 {code}: {title}')

    return affected_codes


def scrape_single_fund_record(code, index_type, fallback_item, cached_item=None, full_refresh=True):
    """
    抓取单只基金的数据。
    若 full_refresh 为 True，拉取主页、F10、费率、公告原件全文；
    若 full_refresh 为 False，拉取主页行情并复用缓存中已核验的 F10 档案、费率和直销政策。
    """
    base = dict(fallback_item or {})
    base['code'] = code
    base['index_type'] = index_type

    page_data = scrape_fund_page(code)

    if full_refresh or not cached_item:
        f10_data = scrape_f10_page(code)
        fee_data = scrape_fee_page(code)
        limit_data = scrape_limit_announcement(code)
    else:
        # 增量模式：复用已核验的静态信息与直销公告结论
        static_keys = ['full_name', 'fund_type', 'manager_company', 'custodian', 'manager_person', 'inception_date']
        fee_keys = ['mgmt_fee', 'custody_fee', 'sales_fee', 'purchase_fee']
        ann_keys = ['direct_daily_limit', 'direct_limit_status', 'limit_announcement_id']

        f10_data = {k: cached_item[k] for k in static_keys if k in cached_item}
        fee_data = {k: cached_item[k] for k in fee_keys if k in cached_item}
        limit_data = {k: cached_item[k] for k in ann_keys if k in cached_item}

        # 如果主页解析出了代销限购变动，同步更新
        if 'limit_status' in page_data:
            limit_data['daily_limit'] = page_data.get('daily_limit')
            limit_data['limit_status'] = page_data.get('limit_status')

    # 先合并除限额公告外的所有数据（以获取最准确的代销状态，包含兜底逻辑）
    merged = {**base, **page_data, **f10_data, **fee_data}

    # 交叉验证与限额合并规则：
    # 1. 若代销是"未开通代销"，说明代销渠道未开放，不能将直销回退为代销状态（应保留直销提取额度或兜底）
    if merged.get('limit_status') == '未开通代销':
        if limit_data.get('direct_daily_limit') is None:
            limit_data['direct_daily_limit'] = base.get('direct_daily_limit', 0)
            limit_data['direct_limit_status'] = base.get('direct_limit_status', '暂停申购')
    else:
        # 代销已开通的情况：
        agency_limit = merged.get('daily_limit')
        agency_status = merged.get('limit_status')
        direct_limit = limit_data.get('direct_daily_limit')
        direct_status = limit_data.get('direct_limit_status')

        # 优先采纳从官方公告第一信源提取到的直销限额与政策（彻底废除历史硬编码白名单）
        if direct_status is not None:
            pass
        # 仅当未提取到直销专属公告时，直销渠道默认跟随代销渠道政策：
        elif agency_status == '暂停申购':
            limit_data['direct_daily_limit'] = 0
            limit_data['direct_limit_status'] = '暂停申购'
        elif agency_limit is not None and agency_limit > 0:
            limit_data['direct_daily_limit'] = agency_limit
            limit_data['direct_limit_status'] = agency_status
        else:
            limit_data['direct_daily_limit'] = agency_limit
            limit_data['direct_limit_status'] = agency_status

    # 合并限额公告数据
    merged.update(limit_data)
    merged = validate(merged)

    # 确保有 name 字段
    if 'name' not in merged:
        merged['name'] = base.get('name', f'基金{code}')

    total_fields = len(page_data) + len(f10_data) + len(fee_data) + len(limit_data)
    return merged, total_fields


def main():
    parser = argparse.ArgumentParser(description="基金数据抓取与量化工程引擎 (含 CDC 增量变更流与并发通算)")
    parser.add_argument('codes', nargs='*', default=None, help="指定抓取的基金代码列表（如留空则处理标的池全量基金）")
    parser.add_argument('--full', action='store_true', help="强制全量抓取所有基金的全部4项数据（主页、F10、费率、公告）")
    parser.add_argument('--incremental', '--cdc', action='store_true', help="启用 CDC 增量变更流模式（推荐，秒级更新）")
    parser.add_argument('--workers', type=int, default=5, help="并发网络线程数（默认 5）")
    args = parser.parse_args()

    print('=' * 60)
    print('基金数据抓取与量化工程引擎启动')
    print('=' * 60)

    fallback = load_fallback()
    cached = load_cached_funds()

    # 确定目标标的列表与运行模式
    if args.codes:
        target_list = [(c, fallback.get(c, {}).get('index_type', '')) for c in args.codes]
        force_full = True
        is_cdc = False
        print(f"模式: 指定标的抓取 ({len(target_list)} 只标的)")
    elif args.full:
        target_list = FUND_LIST
        force_full = True
        is_cdc = False
        print(f"模式: 全量深度抓取 ({len(target_list)} 只标的，全维度并发拉取)")
    else:
        target_list = FUND_LIST
        force_full = False
        is_cdc = True
        print(f"模式: CDC 增量变更流模式 (全市场事件驱动，秒级更新)")

    affected_codes = set()
    if is_cdc:
        print("[CDC 增量流] 正在拉取全市场最新公告 Feed 流...")
        feed_items = fetch_market_announcement_feed(max_pages=3, page_size=100)
        universe_codes = [c for c, _ in FUND_LIST]
        affected_codes = detect_cdc_affected_funds(feed_items, universe_codes, fallback)
        if affected_codes:
            print(f"[CDC 增量流] 发现 {len(affected_codes)} 只基金有最新限额/费率公告，将对这部分标的执行深度重解析: {sorted(list(affected_codes))}")
        else:
            print("[CDC 增量流] 全市场 Feed 未检测到标的池限购公告变更，全量 59 只标的将通过并发增量流刷新行情，并复用已审计档案")

    # 并发执行抓取任务
    results_map = {}
    updated = 0
    errors = []

    def run_fund_task(item):
        code, index_type = item
        fb_item = fallback.get(code, {})
        cached_item = cached.get(code)
        # 判断是否需要全量深度抓取
        full_req = force_full or (code in affected_codes) or (cached_item is None)
        try:
            fund_dict, total_fields = scrape_single_fund_record(
                code, index_type, fb_item, cached_item, full_refresh=full_req
            )
            return code, fund_dict, total_fields, full_req, None
        except Exception as e:
            return code, None, 0, full_req, str(e)

    workers = max(1, min(args.workers, len(target_list)))
    print(f"\n启动并发工作线程池 (Workers={workers})...")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_fund_task, item): item[0] for item in target_list}
        for future in as_completed(futures):
            code = futures[future]
            try:
                c, f_dict, total_fields, full_req, err = future.result()
                if err:
                    errors.append(f'{code}: 抓取失败: {err}')
                    # 失败回退到本地缓存或兜底
                    fb_item = fallback.get(code, {})
                    results_map[code] = cached.get(code) or fb_item
                    print(f'  [WARN] [{code}] 抓取异常，使用兜底/缓存: {err}')
                else:
                    results_map[code] = f_dict
                    if total_fields > 0:
                        updated += 1
                    status_lbl = "深度抓取" if full_req else "增量行情"
                    print(f'  [OK] [{code}] {f_dict.get("name", "")} ({status_lbl}, {total_fields} 字段)')
            except Exception as ex:
                errors.append(f'{code}: 线程未捕获异常: {ex}')
                results_map[code] = cached.get(code) or fallback.get(code, {})

    # 按照 FUND_LIST 原始顺序整理结果，若只抓取特定代码则与现有 public/data/funds.json 合并
    if args.codes:
        final_results = []
        for code, idx_type in FUND_LIST:
            if code in results_map:
                final_results.append(results_map[code])
            elif code in cached:
                final_results.append(cached[code])
            else:
                final_results.append(fallback.get(code, {}))
    else:
        final_results = [results_map[code] for code, _ in FUND_LIST if code in results_map]

    # 输出时间戳（强制使用北京时间 UTC+8）
    from datetime import datetime, timezone, timedelta
    tz_beijing = timezone(timedelta(hours=8))
    timestamp = datetime.now(tz_beijing).strftime('%Y-%m-%dT%H:%M:%S')
    for r in final_results:
        r['updated_at'] = timestamp

    # 增润量化多因子指标 (TD / IR)
    try:
        from simulate import enrich_funds_with_quant_factors
        final_results, _ = enrich_funds_with_quant_factors(final_results)
    except Exception as ex:
        print(f'  [WARN] 增润量化多因子指标异常: {ex}')

    # 写入 JSON
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)

    print(f'\n{"=" * 60}')
    print(f'抓取完成: {updated}/{len(target_list)} 只基金更新 (总计 {len(final_results)} 只标的)')
    print(f'输出: {OUTPUT}')
    if errors:
        print(f'警告: {len(errors)} 个问题')
        for e in errors:
            print(f'  - {e}')
    print('=' * 60)

    # 输出结构化摘要供 CI/CD 解析
    summary = {
        'timestamp': timestamp,
        'total': len(target_list),
        'updated': updated,
        'failed': len(errors),
        'errors': errors,
    }
    print(f'\n__SCRAPE_SUMMARY__{json.dumps(summary, ensure_ascii=False)}__SCRAPE_SUMMARY__')

    return 0 if updated > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
