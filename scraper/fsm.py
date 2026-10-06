#!/usr/bin/env python3
"""
金融事件槽位有限状态机 (Financial Slot-Filling FSM)
用于从基金公告、交易通知和披露原件中确定性解析申购政策、渠道额度与生效状态。

架构特点：
1. 原子子句隔离（Clause-by-Clause Semantic Isolation）：消除长文本跨句污染与贪婪匹配
2. 渠道状态机（Channel FSM）：严格区分 DIRECT（直销）、AGENCY（代销）与 ALL（全渠道）
3. 份额槽位绑定（Share-Class Slot Binding）：支持 A/C/D/E/I 份额与基金代码专属匹配
4. 动作状态转移（Action Transition）：SUSPEND、RESUME、ADJUST（目标值提取）、RESTRICT
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class FSMClause:
    text: str
    channel: str           # 'DIRECT', 'AGENCY', 'ALL'
    share_class: Optional[str] = None  # 'A', 'C', 'D', 'E', 'I', None
    fund_code: Optional[str] = None
    action: Optional[str] = None       # 'SUSPEND', 'RESUME', 'ADJUST', 'RESTRICT'
    quota: Optional[int] = None
    raw_quota_str: Optional[str] = None


@dataclass
class FSMResult:
    direct_daily_limit: Optional[int] = None
    direct_limit_status: Optional[str] = None
    agency_daily_limit: Optional[int] = None
    agency_limit_status: Optional[str] = None
    event_type: str = 'UNKNOWN'
    announcement_id: Optional[str] = None
    clauses: List[FSMClause] = field(default_factory=list)


class FinancialEventFSM:
    """金融事件槽位填充有限状态机"""

    # 标点符号与列表分句符
    CLAUSE_SPLIT_REGEX = re.compile(
        r'[。\n；;\r]+|(?:[（(][0-9一二三四1234][)）])|(?:(?<=\s)[0-9一二三四1234][、\.])'
    )

    # 调整模式：由 X 元调整为 Y 元 -> 捕获目标 Y
    ADJUST_REGEX = re.compile(
        r'由\D{0,15}?([0-9,]+(?:\.\d+)?)\s*元.*?(?:调整为|上调至|下调至|调整至)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*元'
    )

    # 限额模式：不超过 / 上限 / 限额为 / 限制金额 X 元
    RESTRICT_REGEX = re.compile(
        r'(?:不超过|不得超(?:过)?|限额(?:仍)?为?|上限为?|限制(?:金额)?(?:仍)?为?|限制金额|均应不超过)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)?'
    )

    # 暂停申购（支持中间包含平台/机构描述，排除“暂停大额申购”）
    SUSPEND_REGEX = re.compile(
        r'暂停(?:\S{0,35}?)?(?<!大额)申购|停止(?:\S{0,35}?)?(?:办理)?申购|暂停办理(?:\S{0,35}?)?(?<!大额)申购'
    )

    # 恢复申购
    RESUME_REGEX = re.compile(r'恢复办理|恢复申购|恢复大额|取消限额|取消大额|取消上限')

    # 渠道未开通/暂不上线模式 (如: 暂不上线直销机构、未开通直销业务、不通过直销机构销售等)
    NOT_OFFERED_DIRECT_REGEX = re.compile(
        r'(?:暂不上线|暂不通过|暂不开通|未开通|不通过|不开放|未上线)(?:\S{0,15}?)?(?:直销(?:机构|渠道|平台|系统|柜台)?|本公司直销)|'
        r'直销(?:机构|渠道|平台|系统|柜台)?(?:\S{0,15}?)?(?:暂不上线|暂不开通|未开通|不销售|不开放|暂不办理)'
    )
    NOT_OFFERED_AGENCY_REGEX = re.compile(
        r'(?:尚未开通|未开通|暂不开通|暂不上线)(?:\S{0,15}?)?代销|代销(?:机构|渠道)?(?:\S{0,15}?)?(?:暂不上线|暂不开通|未开通)'
    )

    @classmethod
    def parse_announcement(
        cls,
        content: str,
        title: str = '',
        fund_code: Optional[str] = None,
        share_class: Optional[str] = None,
        ann_id: Optional[str] = None
    ) -> FSMResult:
        result = FSMResult(announcement_id=ann_id)
        if not content and not title:
            return result

        # 1. 标题预处理与状态快速判定
        title_clean = re.sub(r'\s+', '', title or '')
        if '恢复' in title_clean or '取消' in title_clean:
            if '代销' in title_clean and '直销' not in title_clean:
                result.agency_limit_status = '开放申购'
                result.agency_daily_limit = None
            else:
                result.direct_limit_status = '开放申购'
                result.direct_daily_limit = None
                result.event_type = 'RESUME'

        # 2. 正文清理与分句切分
        text_clean = re.sub(r'<[^>]+>', ' ', content or '')
        clauses_raw = cls.CLAUSE_SPLIT_REGEX.split(text_clean)

        parsed_clauses: List[FSMClause] = []

        for raw_cl in clauses_raw:
            cl = re.sub(r'\s+', '', raw_cl)
            if not cl or len(cl) < 3:
                continue

            # 渠道分类
            has_direct = any(k in cl for k in ['直销', '直销柜台', '网上直销', '电子交易平台', '直销电子平台'])
            has_agency = any(k in cl for k in ['代销', '代销机构', '第三方销售', '代销渠道'])
            if has_direct and not has_agency:
                channel = 'DIRECT'
            elif has_agency and not has_direct:
                channel = 'AGENCY'
            elif has_direct and has_agency:
                channel = 'DIRECT_AND_AGENCY'
            else:
                channel = 'ALL'

            # 代码识别
            cl_code = None
            if fund_code and fund_code in cl:
                cl_code = fund_code
            else:
                m_code = re.search(r'([0-9]{6})', cl)
                if m_code:
                    cl_code = m_code.group(1)

            # 份额识别
            cl_class = None
            for sc in ['A', 'C', 'D', 'E', 'I']:
                if f'{sc}类' in cl or f'{sc}份额' in cl or f'{sc}端' in cl:
                    cl_class = sc
                    break

            # 动作识别与槽位提取
            action = None
            quota = None

            # (a) 检查是否未开通/暂不上线渠道
            if cls.NOT_OFFERED_DIRECT_REGEX.search(cl):
                action = 'NOT_OFFERED'
                quota = 0
                channel = 'DIRECT'
            elif cls.NOT_OFFERED_AGENCY_REGEX.search(cl):
                action = 'NOT_OFFERED'
                quota = 0
                channel = 'AGENCY'
            # (b) 检查是否为“由 X 调整为 Y”
            elif cls.ADJUST_REGEX.search(cl):
                m_adj = cls.ADJUST_REGEX.search(cl)
                action = 'ADJUST'
                quota = int(float(m_adj.group(2).replace(',', '')))
            # (c) 检查是否暂停申购
            elif cls.SUSPEND_REGEX.search(cl) and '暂停大额' not in cl:
                action = 'SUSPEND'
                quota = 0
            # (d) 检查是否恢复申购
            elif cls.RESUME_REGEX.search(cl):
                action = 'RESUME'
                quota = None
            # (e) 检查限额
            else:
                m_res = cls.RESTRICT_REGEX.search(cl)
                if m_res:
                    action = 'RESTRICT'
                    quota = int(float(m_res.group(1).replace(',', '')))

            parsed_clauses.append(FSMClause(
                text=cl,
                channel=channel,
                share_class=cl_class,
                fund_code=cl_code,
                action=action,
                quota=quota
            ))

        result.clauses = parsed_clauses

        # 3. 槽位消解 (Slot Resolution)
        # 优先级：代码匹配 (Priority 1) > 份额匹配 (Priority 2) > 全局通用 (Priority 3)
        target_sc = share_class.upper() if share_class else None
        target_cd = fund_code if fund_code else None

        def resolve_channel_candidate(channels):
            p1_code_match = None
            p2_class_match = None
            p3_general = None

            for c in parsed_clauses:
                if c.channel in channels and c.action:
                    if target_cd and c.fund_code == target_cd:
                        p1_code_match = c
                        break
                    elif target_sc and c.share_class == target_sc:
                        if not p2_class_match:
                            p2_class_match = c
                    elif not c.fund_code and not c.share_class:
                        if not p3_general:
                            p3_general = c

            return p1_code_match or p2_class_match or p3_general

        direct_candidate = resolve_channel_candidate(('DIRECT', 'DIRECT_AND_AGENCY', 'ALL'))
        agency_candidate = resolve_channel_candidate(('AGENCY', 'DIRECT_AND_AGENCY', 'ALL'))

        if direct_candidate:
            if direct_candidate.action == 'NOT_OFFERED':
                result.direct_daily_limit = 0
                result.direct_limit_status = '未开通直销'
                result.event_type = 'NOT_OFFERED'
            elif direct_candidate.action == 'SUSPEND':
                result.direct_daily_limit = 0
                result.direct_limit_status = '暂停申购'
                result.event_type = 'SUSPEND'
            elif direct_candidate.action == 'RESUME':
                result.direct_daily_limit = None
                result.direct_limit_status = '开放申购'
                result.event_type = 'RESUME'
            elif direct_candidate.action in ('ADJUST', 'RESTRICT') and direct_candidate.quota:
                result.direct_daily_limit = direct_candidate.quota
                result.direct_limit_status = f'限{direct_candidate.quota}元/日'
                result.event_type = direct_candidate.action

        if agency_candidate:
            if agency_candidate.action == 'NOT_OFFERED':
                result.agency_daily_limit = 0
                result.agency_limit_status = '未开通代销'
            elif agency_candidate.action == 'SUSPEND':
                result.agency_daily_limit = 0
                result.agency_limit_status = '暂停申购'
                result.event_type = 'SUSPEND'
            elif agency_candidate.action == 'RESUME':
                result.agency_daily_limit = None
                result.agency_limit_status = '开放申购'
            elif agency_candidate.action in ('ADJUST', 'RESTRICT') and agency_candidate.quota:
                result.agency_daily_limit = agency_candidate.quota
                result.agency_limit_status = f'限{agency_candidate.quota}元/日'

        return result
