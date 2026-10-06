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
    fund_codes: List[str] = field(default_factory=list)
    share_classes: List[str] = field(default_factory=list)
    action: Optional[str] = None       # 'SUSPEND', 'RESUME', 'ADJUST', 'RESTRICT', 'NOT_OFFERED'
    quota: Optional[int] = None
    raw_quota_str: Optional[str] = None


@dataclass
class FSMResult:
    direct_daily_limit: Optional[int] = None
    direct_limit_status: Optional[str] = None
    agency_daily_limit: Optional[int] = None
    agency_limit_status: Optional[str] = None
    event_type: str = 'UNKNOWN'
    quota_sharing: Optional[str] = None  # 'SHARED', 'INDEPENDENT', 'NONE'
    quota_shared_desc: Optional[str] = None
    announcement_id: Optional[str] = None
    is_direct_explicit: bool = False
    is_agency_explicit: bool = False
    clauses: List[FSMClause] = field(default_factory=list)


class FinancialEventFSM:
    """金融事件槽位填充有限状态机"""

    # 标点符号与列表分句符（保留行内标号，仅在换行或空白后的列表标号切分，避免中句破坏）
    CLAUSE_SPLIT_REGEX = re.compile(
        r'[。\n；;\r]+|(?:(?<=[\n\r\s])[（(][0-9一二三四1234][)）])'
    )

    # 调整模式：由 X 元调整为 Y 元 -> 捕获目标 Y
    ADJUST_REGEX = re.compile(
        r'由\D{0,15}?([0-9,]+(?:\.\d+)?)\s*元.*?(?:调整为|上调至|下调至|调整至)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*元'
    )

    # 限额模式：支持不超过/上限/限额为/高于X元限制/单笔X元以上暂停等全语系
    RESTRICT_REGEX = re.compile(
        r'(?:不超过|不得超(?:过)?|限额(?:仍)?为?|上限为?|限制(?:金额)?(?:仍)?为?|限制金额|均应不超过|限制为)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)?|'
        r'(?:高于|超过|大于)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*(?:元|元人民币)?.*?(?:进行限制|有权拒绝|予以拒绝|有权不予确认|不予确认)|'
        r'单笔(?:金额)?\s*([0-9,]+(?:\.\d+)?)\s*元以上.*?(?:暂停|限制)'
    )

    # 暂停申购（支持中间包含平台/机构描述，排除“暂停大额申购”）
    SUSPEND_REGEX = re.compile(
        r'暂停(?:\S{0,35}?)?(?<!大额)申购|停止(?:\S{0,35}?)?(?:办理)?申购|暂停办理(?:\S{0,35}?)?(?<!大额)申购'
    )

    # 恢复申购
    RESUME_REGEX = re.compile(r'恢复办理|恢复申购|恢复大额|取消限额|取消大额|取消上限')

    # 渠道未开通/暂不上线模式 (如: 暂不上线直销机构、未开通直销业务、不通过直销机构销售等)
    NOT_OFFERED_DIRECT_REGEX = re.compile(
        r'(?:暂不上线|暂不通过|暂不开通|未开通|不通过|不开放|未上线|不开展)(?:\S{0,15}?)?(?:直销(?:机构|渠道|平台|系统|柜台)?|本公司直销)|'
        r'直销(?:机构|渠道|平台|系统|柜台)?(?:\S{0,15}?)?(?:暂不上线|暂不开通|未开通|不销售|不开放|暂不办理|未开放)'
    )
    NOT_OFFERED_AGENCY_REGEX = re.compile(
        r'(?:尚未开通|未开通|暂不开通|暂不上线)(?:\S{0,15}?)?代销|代销(?:机构|渠道)?(?:\S{0,15}?)?(?:暂不上线|暂不开通|未开通)'
    )

    # 额度合并与共享识别模式 (A/C等份额共享额度 vs 独立计算)
    COMBINED_QUOTA_REGEX = re.compile(
        r'合并计算|合计不超过|合并进行限制|各份额合并|份额合并|各类别基金份额合并|两类份额合并'
    )
    SEPARATE_QUOTA_REGEX = re.compile(
        r'不同份额分别计算|各类份额单独计算|分别计算|各份额独立'
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
            cl = re.sub(r'^[（(][0-9一二三四1234][)）]\s*', '', raw_cl)
            cl = re.sub(r'^[0-9一二三四1234][、\.]\s*', '', cl)
            cl = re.sub(r'\s+', '', cl)
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

            # 代码识别（支持多代码）
            cl_codes = re.findall(r'([0-9]{6})', cl)
            cl_code = fund_code if (fund_code and fund_code in cl_codes) else (cl_codes[0] if cl_codes else None)

            # 份额识别（支持多份额）
            cl_classes = []
            for sc in ['A', 'C', 'D', 'E', 'I', 'F', 'H']:
                if f'{sc}类' in cl or f'{sc}份额' in cl or f'{sc}端' in cl:
                    cl_classes.append(sc)
            cl_class = share_class if (share_class and share_class in cl_classes) else (cl_classes[0] if cl_classes else None)

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
                    val = m_res.group(1) or m_res.group(2) or m_res.group(3)
                    quota = int(float(val.replace(',', '')))

            parsed_clauses.append(FSMClause(
                text=cl,
                channel=channel,
                share_class=cl_class,
                fund_code=cl_code,
                fund_codes=cl_codes,
                share_classes=cl_classes,
                action=action,
                quota=quota
            ))

        # 结构化分级基金表格解析（如天弘代码与暂停/恢复业务映射表）
        lines = [l.strip() for l in text_clean.splitlines() if l.strip()]
        for i, line in enumerate(lines):
            line_codes = re.findall(r'([0-9]{6})', line)
            if len(line_codes) >= 2:
                for j in range(i + 1, min(i + 6, len(lines))):
                    flag_line = lines[j]
                    flags = re.findall(r'([是否])', flag_line)
                    if len(flags) == len(line_codes):
                        is_susp = '暂停' in flag_line
                        is_resume = '恢复' in flag_line or '开放' in flag_line
                        for cd, flg in zip(line_codes, flags):
                            act = None
                            q = None
                            if is_susp:
                                act = 'SUSPEND' if flg == '是' else 'RESUME'
                                q = 0 if flg == '是' else None
                            elif is_resume:
                                act = 'RESUME' if flg == '是' else 'SUSPEND'
                                q = None if flg == '是' else 0
                            if act:
                                parsed_clauses.append(FSMClause(
                                    text=f"表格项:{cd}_{act}",
                                    channel='ALL',
                                    fund_code=cd,
                                    fund_codes=[cd],
                                    action=act,
                                    quota=q
                                ))
                        break

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
                    if target_cd and (c.fund_code == target_cd or target_cd in c.fund_codes):
                        p1_code_match = c
                        break
                    elif target_sc and (c.share_class == target_sc or target_sc in c.share_classes):
                        if not p2_class_match:
                            if not c.fund_codes or (target_cd and target_cd in c.fund_codes):
                                p2_class_match = c
                    elif not c.fund_codes and not c.share_classes:
                        if not p3_general:
                            p3_general = c

            match_c = p1_code_match or p2_class_match or p3_general
            is_explicit = (match_c is p1_code_match) or (match_c is p2_class_match)
            return match_c, is_explicit

        direct_candidate, is_direct_explicit = resolve_channel_candidate(('DIRECT', 'DIRECT_AND_AGENCY', 'ALL'))
        agency_candidate, is_agency_explicit = resolve_channel_candidate(('AGENCY', 'DIRECT_AND_AGENCY', 'ALL'))

        result.is_direct_explicit = is_direct_explicit
        result.is_agency_explicit = is_agency_explicit

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
            elif direct_candidate.action in ('ADJUST', 'RESTRICT') and direct_candidate.quota is not None:
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
                if result.event_type == 'UNKNOWN':
                    result.event_type = 'SUSPEND'
            elif agency_candidate.action == 'RESUME':
                result.agency_daily_limit = None
                result.agency_limit_status = '开放申购'
                if result.event_type == 'UNKNOWN':
                    result.event_type = 'RESUME'
            elif agency_candidate.action in ('ADJUST', 'RESTRICT') and agency_candidate.quota is not None:
                result.agency_daily_limit = agency_candidate.quota
                result.agency_limit_status = f'限{agency_candidate.quota}元/日'
                if result.event_type == 'UNKNOWN':
                    result.event_type = agency_candidate.action

        # 判定份额间额度共享属性 (Shared Quota vs Independent Quota)
        if cls.SEPARATE_QUOTA_REGEX.search(content):
            result.quota_sharing = 'INDEPENDENT'
            result.quota_shared_desc = '各份额独立计算单日限额（不合并）'
        elif cls.COMBINED_QUOTA_REGEX.search(content):
            result.quota_sharing = 'SHARED'
            result.quota_shared_desc = '本基金多类份额共享单日限额，合并计算'

        return result
