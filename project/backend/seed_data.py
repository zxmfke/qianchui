"""
种子数据脚本 - 千锤·营销话术AI操作系统
生成大量真实感测试数据，让所有页面都有内容展示。
运行方式: python seed_data.py  (使用 .env 中的 DATABASE_URL)
"""
import asyncio
import random
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from passlib.context import CryptContext
from sqlalchemy import select

from app.database import async_session_factory, engine
from app.models.base import Base
from app.models.enterprise import Enterprise
from app.models.user import User
from app.models.script import Script, ScriptUsage
from app.models.memory import PainPoint, Product, ServiceItem
from app.models.diagnosis import DiagnosisReport
from app.models.training import TrainingRecord
from app.models.simulation import SimulationSession
from app.models.conversation import Conversation, Message
from app.models.channel_material import ChannelMaterial
from app.models.optimization import OptimizationTask, OptimizationStrategy  # noqa: F401
from app.models.flywheel import FlywheelEvent, StrategyCascade  # noqa: F401

pwd_context = CryptContext(schemes=["bcrypt"])
now = datetime.now(timezone.utc)


def days_ago(n: int) -> datetime:
    return now - timedelta(days=n)


def hours_ago(n: int) -> datetime:
    return now - timedelta(hours=n)


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[1/10] 数据库表结构已同步。")

    async with async_session_factory() as session:
        result = await session.execute(
            select(Enterprise).where(Enterprise.name == "千锤科技")
        )
        if result.scalar_one_or_none():
            print("企业 '千锤科技' 已存在，跳过。")
            return

        # ── 1. 企业 ──────────────────────────────────────────
        ent = Enterprise(id=uuid4(), name="千锤科技", industry="消费医疗", is_active=True)
        session.add(ent)
        await session.flush()
        print("[2/10] 企业创建完成。")

        # ── 2. 超级管理员 ─────────────────────────────────────
        sa_hashed = pwd_context.hash("kst@2026")
        hashed = pwd_context.hash("demo123456")
        super_admin_ent = Enterprise(id=uuid4(), name="千锤平台", industry="平台运营", is_active=True)
        session.add(super_admin_ent)
        await session.flush()

        super_admin_user = User(
            id=uuid4(), enterprise_id=super_admin_ent.id,
            email="superadmin@qianchui.com", username="superadmin",
            hashed_password=sa_hashed, role="super_admin", is_active=True,
        )
        session.add(super_admin_user)
        await session.flush()
        print("[2.5/10] 超级管理员创建完成 (superadmin / kst@2026)。")

        # ── 3. 团队用户 (5人) ────────────────────────────────
        team = []
        user_defs = [
            ("demo@qianchui.com", "demo", "admin"),
            ("zhangming@qianchui.com", "张明", "manager"),
            ("liting@qianchui.com", "李婷", "staff"),
            ("wanghao@qianchui.com", "王浩", "staff"),
            ("liufang@qianchui.com", "刘芳", "staff"),
        ]
        for email, username, role in user_defs:
            u = User(
                id=uuid4(), enterprise_id=ent.id,
                email=email, username=username,
                hashed_password=hashed, role=role, is_active=True,
            )
            session.add(u)
            team.append(u)
        await session.flush()
        admin = team[0]
        print("[3/10] 5个团队用户创建完成。")

        # ── 3. 话术库 (20条，status=published) ──────────────
        script_defs = [
            ("价格异议-锚定策略", "异议处理", ["价格", "锚定"], "客户对价格敏感,需通过锚定效应重塑价值认知", "先抛出高价锚点,再引导到实际价格形成对比", "您关注价格说明您很理性，其实对比下来我们的性价比是最高的。很多客户最初也觉得贵，了解完方案后都说物超所值。我给您算一笔账：单次治疗看起来5000，但效果可以维持2-3年，平均每天不到7块钱，比很多护肤品都划算..."),
            ("首次咨询-破冰话术", "开场白", ["破冰", "信任"], "初次咨询客户防备心强,需快速建立信任", "通过共情+专业展示降低防备", "您好！感谢您的咨询。看您关注我们产品有一段时间了，很多客户最初也有同样的顾虑，我先帮您做个简单评估，您完全不用有任何压力..."),
            ("竞品对比-差异化引导", "竞品应对", ["竞品", "差异化"], "客户拿竞品对比,心理正在权衡", "承认竞品优势再引导到差异化", "您提到的XX产品确实也不错，在基础功能上他们做得很好。不过在核心技术上我们有三个独特优势：第一是AI实时推荐精准度高达92%，第二是话术库可以根据您的行业定制，第三是我们有7x24小时的技术支持团队..."),
            ("犹豫不决-紧迫感制造", "促成", ["促成", "紧迫"], "客户已产生兴趣但犹豫不决", "用限时优惠+社会证明推动决策", "我完全理解您需要考虑一下。不过给您说个好消息，本月是我们的周年庆活动，前50位签约客户可以享受8折优惠。目前已经有38位了，名额确实有限。这个月签约的客户还能免费获得3个月的培训服务..."),
            ("售后投诉-共情转化", "售后", ["售后", "共情"], "客户对产品或服务不满意", "先共情再解决,化危机为商机", "非常理解您的心情，遇到这种情况确实很不愉快。感谢您直接跟我们反馈，说明您对我们还是信任的。我现在就帮您优先处理，大概30分钟就能给您一个解决方案。另外我给您申请一个VIP服务补偿..."),
            ("复购推荐-增值服务", "复购", ["复购", "增值"], "老客户维护,提升复购率", "从已有满意体验出发推荐升级", "感谢您一直以来的信任！最近我们升级了一个专属老客户的增值服务包，基于您之前的使用数据，系统分析出最适合您团队的功能组合。上个季度续约的老客户都反馈效果提升了30%以上..."),
            ("需求挖掘-SPIN提问", "异议处理", ["需求", "SPIN"], "客户需求模糊,需要深入了解", "用SPIN提问法层层递进", "我想先了解下您目前团队的情况。您现在有多少客服人员？他们日均处理多少咨询？您觉得目前转化率大概在什么水平？如果转化率能提升5个百分点，按您现在的咨询量算，每月能多带来多少收入？"),
            ("预算不足-分期方案", "促成", ["预算", "分期"], "客户有意向但预算有限", "提供灵活付费方案降低决策门槛", "预算有限是很常见的情况，其实我们有几种灵活的付费方式。您可以选择按季度付费，首季度还有7折优惠。很多中小企业客户都是从基础版开始，效果好了再升级，投入产出比非常高..."),
            ("功能质疑-案例证明", "竞品应对", ["功能", "案例"], "客户对产品功能有质疑", "用真实案例数据打消疑虑", "您提到的这个功能，我分享一个真实案例。XX口腔去年10月上线我们系统，3个月内客服转化率从18%提升到了31%。他们的王总上周还专门写了一封感谢信。我可以安排他们的负责人跟您分享一下实际使用体验..."),
            ("信任建立-专业背书", "开场白", ["信任", "专业"], "新客户对品牌缺乏信任", "展示资质和客户背书建立信任", "我们是行业内首家获得ISO认证的AI话术平台，目前服务了超过300家消费医疗机构。其中包括XX口腔、YY美容等知名品牌。最近还获得了行业创新大奖..."),
            ("需求确认-总结回放", "促成", ["确认", "总结"], "沟通接近尾声需确认需求", "总结客户痛点并确认是否准确", "好的，我帮您总结一下：您目前最大的痛点是新人培训周期太长，导致前3个月转化率很低。您期望通过AI话术系统，把新人上手时间从3个月缩短到1个月，对吧？如果我们能做到这一点，您觉得每月投入多少预算是合理的？"),
            ("场景切换-转介绍话术", "促成", ["转介绍", "裂变"], "已成交客户的转介绍", "利用客户满意度引导转介绍", "听您说对我们的服务很满意，太开心了！其实您身边有没有同行朋友也有类似的困扰？如果您愿意推荐，我们有专门的老带新计划，您和您的朋友都能享受额外3个月免费使用..."),
            ("危机处理-负面情绪", "售后", ["危机", "情绪"], "客户情绪激动需安抚", "先处理情绪再处理事情", "我非常理解您现在的感受，换做是我也会很生气。请您先喝杯水冷静一下，我向您保证，今天一定给您一个满意的答复。我现在就升级处理这个问题，10分钟内给您回复..."),
            ("深度需求-痛点放大", "异议处理", ["痛点", "深挖"], "客户未意识到问题严重性", "通过数据量化让客户感受痛点", "您说目前觉得转化率还行。但我帮您算个账：按您每天200条咨询量算，每提高1%的转化率，一个月就多200个客户。按客单价5000算，一年就是1200万额外收入。而我们系统年费才几万，投资回报率超过100倍..."),
            ("方案展示-结构化呈现", "促成", ["方案", "展示"], "需要清晰展示解决方案", "用三段式结构清晰呈现", "针对您的需求，我给您定制了三步走方案：第一步（第1周），AI话术库快速部署，导入您行业的300+标准话术。第二步（第2-4周），实战诊断+个性化优化，根据数据持续迭代。第三步（第2个月起），培训+演练巩固，确保全员达标..."),
            ("价值锚定-ROI计算", "异议处理", ["ROI", "价值"], "客户觉得投入产出不明确", "用具体数据演示投资回报", "我帮您算一下投资回报：系统年费36000元。您团队5个客服，每人每天处理50条咨询。如果转化率提升3%（行业平均提升幅度），每月多转化225个客户。客单价5000，月增收112.5万。36000除以112.5万，收回成本只需1天..."),
            ("季末冲刺-限时优惠", "促成", ["限时", "优惠"], "季末或节日促销场景", "制造紧迫感+附加价值", "本季度最后一周了！我特别为您争取到了一个特殊优惠包：年度合约直降20%，额外赠送价值8000元的定制话术服务。这个名额全国就5个，目前还剩2个。优惠今天24点截止，建议您尽快确认..."),
            ("回访激活-沉默客户", "复购", ["回访", "激活"], "长期未联系的沉默客户", "通过新价值唤醒客户兴趣", "您好，好久没联系了！最近我们系统做了一次大升级，新增了AI实时对话教练功能，很多老客户都反馈效果特别好。知道您之前对这方面一直很关注，想邀请您免费体验一周，看看新功能能不能帮到您..."),
            ("竞品拦截-预防流失", "竞品应对", ["拦截", "留存"], "客户提到在看竞品", "理解诉求+差异化+承诺", "理解您多方比较是很正常的。能告诉我您觉得XX产品哪些方面吸引您吗？我可以帮您做一个客观对比。同时，我们最近推出了一个客户保障计划：如果3个月内效果未达预期，我们全额退款加赔偿10%..."),
            ("团队说服-多角色沟通", "促成", ["团队", "决策"], "需要说服多个决策者", "针对不同角色用不同话术", "我理解这个决策需要多方评估。我准备了三份不同侧重点的资料：给老板看的是ROI和战略价值，给技术负责人看的是系统架构和安全性，给一线主管看的是实操效果和培训方案。我可以分别和他们沟通..."),
        ]
        scripts = []
        for i, (title, cat, tags, psych, strat, content) in enumerate(script_defs):
            s = Script(
                id=uuid4(), enterprise_id=ent.id,
                title=title, category=cat, tags=tags,
                status="published",
                psychology_layer=psych, strategy_layer=strat, content=content,
                version=1, difficulty=random.randint(1, 3), target_role="all",
                usage_count=random.randint(50, 300),
                conversion_rate=round(random.uniform(0.55, 0.92), 2),
                user_rating=round(random.uniform(3.5, 5.0), 1),
                lifecycle_stage="active",
                effectiveness_score=round(random.uniform(0.6, 0.95), 2),
                effectiveness_trend=random.choice(["rising", "stable", "stable"]),
                usage_contact_rate=round(random.uniform(0.15, 0.45), 2),
                source_type=random.choice(["manual", "manual", "flywheel_generated"]),
                created_by=admin.id,
                created_at=days_ago(random.randint(1, 60)),
            )
            session.add(s)
            scripts.append(s)
        await session.flush()
        print(f"[4/10] {len(scripts)}条话术创建完成。")

        # ── 4. 话术使用记录 (200条，跨7天) ──────────────────
        for _ in range(200):
            su = ScriptUsage(
                id=uuid4(),
                script_id=random.choice(scripts).id,
                user_id=random.choice(team).id,
                enterprise_id=ent.id,
                context={"source": random.choice(["chat", "recommend", "search"])},
                created_at=hours_ago(random.randint(0, 168)),
            )
            session.add(su)
        await session.flush()
        print("[5/10] 200条使用记录创建完成。")

        # ── 5. 痛点 (8条) ───────────────────────────────────
        pp_defs = [
            ("获客成本居高不下", "传统广告投放ROI持续下降，单个获客成本超过300元", 89, 72, 0.236, "rising", ["获客", "成本", "ROI"]),
            ("客服响应速度慢", "高峰期客户等待超过5分钟，流失率高达40%", 72, 68, 0.059, "stable", ["响应", "等待", "慢"]),
            ("话术缺乏标准化", "新人上手慢，不同客服转化率差距3倍以上", 65, 50, 0.3, "rising", ["标准化", "培训", "新人"]),
            ("客户需求理解偏差", "客服经常误判客户需求，推荐不匹配的产品", 45, 48, -0.063, "falling", ["需求", "误判", "理解"]),
            ("复购率低", "老客户二次消费率不足15%", 38, 30, 0.267, "rising", ["复购", "留存", "老客户"]),
            ("竞品抢客严重", "近3个月被竞品抢走的意向客户增长50%", 55, 42, 0.31, "rising", ["竞品", "流失", "抢客"]),
            ("售后满意度下降", "NPS评分从72降至58", 30, 35, -0.143, "falling", ["售后", "NPS", "满意度"]),
            ("线索质量参差不齐", "无效线索占比超40%，浪费客服资源", 42, 40, 0.05, "stable", ["线索", "质量", "无效"]),
        ]
        pain_points = []
        for name, desc, cur, prev, rate, trend, kw in pp_defs:
            pp = PainPoint(
                id=uuid4(), enterprise_id=ent.id,
                name=name, description=desc,
                mention_count_current=cur, mention_count_previous=prev,
                change_rate=rate, trend_label=trend,
                evidence_keywords=kw, source_type="manual",
                created_at=days_ago(random.randint(5, 30)),
            )
            session.add(pp)
            pain_points.append(pp)
        await session.flush()
        print("[6/10] 8个痛点创建完成。")

        # ── 6. 产品 (5个) ───────────────────────────────────
        prod_defs = [
            ("智能获客助手", "AI驱动的多渠道获客解决方案，降低获客成本30%", "P0", 156, 0.72, "获客成本痛点上升驱动"),
            ("AI客服机器人", "7x24小时智能客服，秒级响应，支持多轮对话", "P1", 89, 0.68, "响应速度痛点驱动"),
            ("千锤话术系统", "三层话术体系+AI实时推荐，提升转化率", "P0", 234, 0.85, "话术标准化+需求理解双驱"),
            ("智能质检平台", "AI自动质检全量对话，实时预警和分析", "P1", 67, 0.71, "客户需求理解偏差优化"),
            ("客户画像引擎", "多维度客户画像，精准匹配服务策略", "P2", 45, 0.63, "线索质量优化"),
        ]
        products = []
        for name, desc, pri, rec_cnt, hit, reason in prod_defs:
            p = Product(
                id=uuid4(), enterprise_id=ent.id,
                name=name, description=desc,
                dynamic_priority=pri,
                recommendation_count=rec_cnt,
                recommendation_hit_rate=hit,
                priority_reason=reason,
                created_at=days_ago(random.randint(30, 90)),
            )
            session.add(p)
            products.append(p)
        await session.flush()

        # ── 7. 服务 (5个) ───────────────────────────────────
        svc_defs = [
            ("话术定制服务", "根据企业业务定制专属话术库", 45, 0.82, False, None),
            ("团队培训服务", "线上+线下话术培训课程", 32, 0.78, False, None),
            ("数据分析报告", "月度/季度对话数据深度分析", 67, 0.85, True, "缺少实时数据监控场景"),
            ("AI陪练服务", "AI模拟客户实战演练，提升应变能力", 28, 0.73, False, None),
            ("竞品情报服务", "定期竞品话术分析报告", 18, 0.65, True, "痛点上升但无对应服务场景"),
        ]
        services = []
        for name, desc, cnt, eff, gap, gap_desc in svc_defs:
            s = ServiceItem(
                id=uuid4(), enterprise_id=ent.id,
                name=name, description=desc,
                usage_count=cnt, effectiveness=eff,
                has_scenario_gap=gap, gap_description=gap_desc,
                created_at=days_ago(random.randint(30, 90)),
            )
            session.add(s)
            services.append(s)
        await session.flush()
        print("[7/10] 5个产品 + 5个服务创建完成。")

        # ── 8. 诊断报告 (5条，使用三层诊断格式) ─────────────
        diag_conversations = [
            "客户：种植牙多少钱？\n客服：您好，欢迎咨询！我们是XX口腔连锁品牌。\n客户：就想问下价格\n客服：种植牙的价格从8000到30000不等，需要根据您的情况来定。方便留个电话，我让医生给您详细说明吗？\n客户：太贵了吧\n客服：价格确实要看具体方案，您先留个电话，我们免费给您做个口腔检查评估。",
            "客户：你们的护肤品怎么样？\n客服：您好，我们的护肤品非常好用的！\n客户：具体好在哪？\n客服：成分都是进口的，很多明星都在用。\n客户：嗯，我再看看吧\n客服：要不您先试用一下？我送您一套试用装。\n客户：不用了，谢谢",
            "客户：我想了解下你们的减肥项目\n客服：您好！请问您目前体重大概多少？想减多少？\n客户：160斤，想减到130\n客服：理解，减30斤的目标很明确。我们有三种方案：运动指导、饮食管理和医美辅助。根据您的情况，我建议先做个体质评估。很多跟您情况类似的客户，3个月就达标了。您看这周有空来做个评估吗？\n客户：好的，周六行吗？",
            "客户：你们的获客系统怎么收费？\n客服：您好！我们有三个版本：基础版3000/月、专业版8000/月、旗舰版20000/月。\n客户：差别在哪？\n客服：主要区别在于AI话术推荐精准度、支持的渠道数量和定制化程度。给您看个案例：XX诊所用专业版3个月，获客成本降低了40%。您目前的团队规模大概多少人？\n客户：10个客服\n客服：那专业版最合适，性价比最高。本月签约还能送3个月培训服务。",
            "客户：我要投诉！上次做的项目效果很差！\n客服：非常抱歉给您带来了不好的体验。能告诉我具体是哪个项目吗？\n客户：上个月做的热玛吉，一点效果都没有\n客服：我理解您的失望。热玛吉的效果通常在治疗后2-3个月才会完全显现。不过我先帮您预约一次免费复诊，让医生评估一下您目前的恢复情况，同时我给您申请一个VIP售后保障。\n客户：那行吧",
        ]
        diag_three_layer_templates = [
            {
                "psych_score": 62, "strat_score": 55, "script_score": 68,
                "psych_issues": [{"turn": 1, "issue": "未识别客户价格敏感心理", "suggested": "先共情再报价，降低防备心"}],
                "strat_issues": [{"turn": 3, "issue": "直接报价缺乏锚定策略", "current_strategy": "直接报价", "suggested_strategy": "先抛高价锚点再引导"}],
                "script_issues": [{"turn": 2, "issue": "开场白过于模板化", "original": "您好，欢迎咨询", "suggested": "结合客户关注点个性化问候"}],
                "plan": ["学习价格锚定技巧", "优化开场话术", "增加需求挖掘环节"],
            },
            {
                "psych_score": 42, "strat_score": 38, "script_score": 45,
                "psych_issues": [{"turn": 1, "issue": "未建立信任就推产品"}, {"turn": 3, "issue": "未察觉客户兴趣下降"}],
                "strat_issues": [{"turn": 2, "issue": "空洞的产品介绍，缺乏FABE法则", "current_strategy": "笼统夸赞", "suggested_strategy": "用FABE法则结构化呈现"}],
                "script_issues": [{"turn": 4, "issue": "强推试用让客户反感", "original": "要不您先试用一下", "suggested": "先解答疑虑再提供体验"}],
                "plan": ["学习FABE销售话术", "练习需求挖掘SPIN提问", "控制推销节奏"],
            },
            {
                "psych_score": 82, "strat_score": 78, "script_score": 85,
                "psych_issues": [{"turn": 2, "issue": "可以更深入挖掘减肥动机", "suggested": "追问为什么想减到130"}],
                "strat_issues": [],
                "script_issues": [{"turn": 3, "issue": "方案选项可以更个性化", "original": "三种方案", "suggested": "根据客户体重和时间预算推荐最适合的一种"}],
                "plan": ["增加动机挖掘话术", "强化个性化推荐能力"],
            },
            {
                "psych_score": 75, "strat_score": 80, "script_score": 72,
                "psych_issues": [{"turn": 1, "issue": "报价过早，应先了解预算", "suggested": "先探询预算范围再推荐版本"}],
                "strat_issues": [{"turn": 3, "issue": "案例使用得当，但缺少同行业对标", "suggested_strategy": "用同行业客户案例增强说服力"}],
                "script_issues": [{"turn": 4, "issue": "促成时限时优惠可以更具体", "original": "本月签约还能送", "suggested": "明确截止日期和剩余名额数量"}],
                "plan": ["优化报价节奏", "积累行业案例库", "完善促成话术"],
            },
            {
                "psych_score": 78, "strat_score": 72, "script_score": 80,
                "psych_issues": [{"turn": 1, "issue": "共情做得好，但可以更具体", "suggested": "复述客户的不满内容表示理解"}],
                "strat_issues": [{"turn": 2, "issue": "解释效果时间有教育意味，可能加重不满", "current_strategy": "直接解释", "suggested_strategy": "先认可感受再科普"}],
                "script_issues": [],
                "plan": ["强化投诉处理话术", "学习危机转化技巧"],
            },
        ]
        diag_reports = []
        for i, conv_text in enumerate(diag_conversations):
            tpl = diag_three_layer_templates[i]
            score = (tpl["psych_score"] + tpl["strat_score"] + tpl["script_score"]) // 3
            dr = DiagnosisReport(
                id=uuid4(), enterprise_id=ent.id, user_id=admin.id,
                conversation_text=conv_text,
                overall_score=score,
                result={
                    "overall_score": score,
                    "psychology_layer": {"score": tpl["psych_score"], "issues": tpl["psych_issues"]},
                    "strategy_layer": {"score": tpl["strat_score"], "issues": tpl["strat_issues"]},
                    "script_layer": {"score": tpl["script_score"], "issues": tpl["script_issues"]},
                    "improvement_plan": tpl["plan"],
                },
                created_at=days_ago(i * 3),
            )
            session.add(dr)
            diag_reports.append(dr)
        await session.flush()
        print("[8/10] 5条诊断报告创建完成。")

        # ── 8.5 优化任务 + 策略 ──────────────────────────────
        opt_task_defs = [
            {
                "title": "种植牙价格异议对话优化",
                "status": "strategies_generated",
                "priority": "P0",
                "diag_idx": 0,
                "root_causes": [
                    {"layer": "psychology", "issue": "未识别客户价格敏感心理", "turn": 1},
                    {"layer": "strategy", "issue": "直接报价缺乏锚定策略", "turn": 3},
                    {"layer": "script", "issue": "开场白过于模板化", "turn": 2},
                ],
                "strategies": [
                    {"priority": "P0", "problem": "直接报价导致客户价格焦虑", "root_cause_type": "script",
                     "solution": "采用价格锚定策略，先展示高端方案价值再引导到适合方案",
                     "current_script": "种植牙的价格从8000到30000不等", "suggested_script": "种植牙方案有很多选择，我们最受欢迎的高端方案在3万左右，不过根据您的情况，可能1万多的方案就能达到很好的效果",
                     "expected_impact": "预计减少30%价格异议", "risk_level": "low", "status": "adopted"},
                    {"priority": "P1", "problem": "开场白缺乏个性化", "root_cause_type": "script",
                     "solution": "根据客户来源和关注点定制开场白",
                     "current_script": "您好，欢迎咨询！我们是XX口腔连锁品牌", "suggested_script": "您好！看到您关注种植牙已经有一段时间了，很多客户跟您一样谨慎选择，这是对的",
                     "expected_impact": "提升首轮好感度", "risk_level": "low", "status": "adopted"},
                    {"priority": "P1", "problem": "缺少需求挖掘环节", "root_cause_type": "config",
                     "solution": "在报价前增加需求确认流程",
                     "current_script": None, "suggested_script": "在了解价格之前，方便我先了解下您的情况吗？比如缺牙多久了，目前有什么不便？这样我能推荐最适合您的方案",
                     "expected_impact": "提升需求匹配度", "risk_level": "low", "status": "pending"},
                ],
            },
            {
                "title": "护肤品咨询流失对话优化",
                "status": "strategies_generated",
                "priority": "P0",
                "diag_idx": 1,
                "root_causes": [
                    {"layer": "psychology", "issue": "未建立信任就推产品"},
                    {"layer": "psychology", "issue": "未察觉客户兴趣下降"},
                    {"layer": "strategy", "issue": "空洞的产品介绍"},
                    {"layer": "script", "issue": "强推试用让客户反感"},
                ],
                "strategies": [
                    {"priority": "P0", "problem": "产品介绍空洞无说服力", "root_cause_type": "script",
                     "solution": "使用FABE法则重构产品介绍话术",
                     "current_script": "成分都是进口的，很多明星都在用", "suggested_script": "我们的核心成分是法国进口的玻尿酸（Feature），渗透力是普通产品的3倍（Advantage），28天可以明显改善干燥细纹（Benefit），这是我们500位用户的对比图（Evidence）",
                     "expected_impact": "预计提升转化率15%", "risk_level": "low", "status": "adopted"},
                    {"priority": "P0", "problem": "未挖掘客户真实需求", "root_cause_type": "config",
                     "solution": "增加SPIN提问流程",
                     "current_script": None, "suggested_script": "方便问下您目前主要的肌肤困扰是什么？是干燥、暗沉还是细纹？平时用什么护肤品？",
                     "expected_impact": "减少需求误判", "risk_level": "low", "status": "pending"},
                    {"priority": "P1", "problem": "客户兴趣下降时继续推销", "root_cause_type": "script",
                     "solution": "识别客户犹豫信号，改为提供价值内容",
                     "current_script": "要不您先试用一下", "suggested_script": "完全理解，选择护肤品确实需要慎重。我发您一份皮肤类型自测表，您可以先了解自己的肤质，后续有问题随时找我",
                     "expected_impact": "降低客户反感率", "risk_level": "low", "status": "rejected"},
                ],
            },
            {
                "title": "减肥项目咨询话术优化",
                "status": "diagnosed",
                "priority": "P2",
                "diag_idx": 2,
                "root_causes": [
                    {"layer": "psychology", "issue": "可以更深入挖掘减肥动机"},
                    {"layer": "script", "issue": "方案选项可以更个性化"},
                ],
                "strategies": [],
            },
            {
                "title": "获客系统销售对话优化",
                "status": "strategies_generated",
                "priority": "P1",
                "diag_idx": 3,
                "root_causes": [
                    {"layer": "psychology", "issue": "报价过早，应先了解预算"},
                    {"layer": "strategy", "issue": "案例使用得当但缺少同行业对标"},
                    {"layer": "script", "issue": "促成时限时优惠不够具体"},
                ],
                "strategies": [
                    {"priority": "P0", "problem": "报价过早导致客户价格锚定在低价", "root_cause_type": "config",
                     "solution": "先通过提问了解客户规模和预算，再推荐合适版本",
                     "current_script": "我们有三个版本：基础版3000/月", "suggested_script": "为了推荐最合适您的方案，先了解下您团队的规模和目前获客预算大概在什么范围？",
                     "expected_impact": "提升客单价15%", "risk_level": "medium", "status": "pending"},
                    {"priority": "P1", "problem": "促成话术缺乏紧迫感", "root_cause_type": "script",
                     "solution": "增加具体截止日期和剩余名额",
                     "current_script": "本月签约还能送3个月培训服务", "suggested_script": "本月15号前签约还能送3个月培训服务，目前这个名额还剩最后3个，已经有7家同行在用了",
                     "expected_impact": "提升促成转化率", "risk_level": "low", "status": "pending"},
                ],
            },
        ]
        opt_tasks = []
        for odef in opt_task_defs:
            diag_report = diag_reports[odef["diag_idx"]]
            task = OptimizationTask(
                id=uuid4(), enterprise_id=ent.id,
                diagnosis_report_id=diag_report.id,
                title=odef["title"], status=odef["status"], priority=odef["priority"],
                classification={"overall_score": diag_report.overall_score},
                score_result=diag_report.result,
                root_causes=odef["root_causes"],
                created_by=admin.id,
                created_at=days_ago(odef["diag_idx"] * 3),
            )
            session.add(task)
            await session.flush()
            opt_tasks.append(task)

            for sdef in odef["strategies"]:
                strat = OptimizationStrategy(
                    id=uuid4(), task_id=task.id,
                    priority=sdef["priority"], problem=sdef["problem"],
                    root_cause_type=sdef["root_cause_type"], solution=sdef["solution"],
                    current_script=sdef.get("current_script"),
                    suggested_script=sdef.get("suggested_script"),
                    expected_impact=sdef.get("expected_impact"),
                    risk_level=sdef["risk_level"], status=sdef["status"],
                    adopted_at=days_ago(1) if sdef["status"] == "adopted" else None,
                    created_at=days_ago(odef["diag_idx"] * 3),
                )
                session.add(strat)
        await session.flush()
        print(f"[8.5/10] {len(opt_tasks)}个优化任务 + 策略创建完成。")

        # ── 8.6 飞轮事件 + 策略联动 ─────────────────────────
        flywheel_event_defs = [
            {
                "event_type": "diagnosis_completed", "trigger_type": "user_action",
                "trigger_data": {"report_id": str(diag_reports[0].id), "score": diag_reports[0].overall_score},
                "result_summary": {"overall_score": diag_reports[0].overall_score, "strategies_count": 3},
                "status": "completed", "days_ago": 12,
            },
            {
                "event_type": "pain_point_sense", "trigger_type": "manual",
                "trigger_data": {"time_window_days": 30},
                "result_summary": {"reports_analyzed": 5, "updates_applied": 3, "new_pain_points": 1},
                "status": "completed", "days_ago": 10,
            },
            {
                "event_type": "optimization_strategies_generated", "trigger_type": "user_action",
                "trigger_data": {"task_id": str(opt_tasks[0].id)},
                "result_summary": {"strategies_count": 3, "adopted": 2},
                "status": "completed", "days_ago": 8,
            },
            {
                "event_type": "strategy_status_changed", "trigger_type": "user_action",
                "trigger_data": {"strategy_action": "adopted"},
                "result_summary": {"status": "adopted"},
                "status": "completed", "days_ago": 7,
            },
            {
                "event_type": "diagnosis_completed", "trigger_type": "user_action",
                "trigger_data": {"report_id": str(diag_reports[1].id), "score": diag_reports[1].overall_score},
                "result_summary": {"overall_score": diag_reports[1].overall_score, "strategies_count": 3},
                "status": "completed", "days_ago": 6,
            },
            {
                "event_type": "cascade_reviewed", "trigger_type": "automatic",
                "trigger_data": {"cascade_trigger": "pain_point_rising"},
                "result_summary": {"actions_applied": 4},
                "status": "completed", "days_ago": 5,
            },
            {
                "event_type": "pain_point_sense", "trigger_type": "automatic",
                "trigger_data": {"time_window_days": 7},
                "result_summary": {"reports_analyzed": 3, "updates_applied": 2, "new_pain_points": 0},
                "status": "completed", "days_ago": 3,
            },
            {
                "event_type": "diagnosis_completed", "trigger_type": "user_action",
                "trigger_data": {"report_id": str(diag_reports[2].id), "score": diag_reports[2].overall_score},
                "result_summary": {"overall_score": diag_reports[2].overall_score},
                "status": "completed", "days_ago": 2,
            },
            {
                "event_type": "optimization_strategies_generated", "trigger_type": "user_action",
                "trigger_data": {"task_id": str(opt_tasks[1].id)},
                "result_summary": {"strategies_count": 3, "adopted": 1},
                "status": "completed", "days_ago": 1,
            },
            {
                "event_type": "strategy_status_changed", "trigger_type": "user_action",
                "trigger_data": {"strategy_action": "adopted"},
                "result_summary": {"status": "adopted"},
                "status": "completed", "days_ago": 0,
            },
        ]
        fw_events = []
        for edef in flywheel_event_defs:
            evt = FlywheelEvent(
                id=uuid4(), enterprise_id=ent.id,
                event_type=edef["event_type"], trigger_type=edef["trigger_type"],
                trigger_data=edef["trigger_data"], result_summary=edef["result_summary"],
                status=edef["status"],
                completed_at=days_ago(edef["days_ago"]),
                created_at=days_ago(edef["days_ago"]),
            )
            session.add(evt)
            fw_events.append(evt)
        await session.flush()

        cascade_defs = [
            {
                "event_idx": 1,
                "trigger_signal": {"type": "pain_point_rising", "pain_point": "获客成本居高不下", "change_rate": 0.236},
                "pain_point_actions": {"action": "update_trend", "details": "更新趋势为rising"},
                "product_actions": {"action": "reprioritize", "details": "智能获客助手升级为P0"},
                "service_actions": {"action": "flag_gap", "details": "竞品情报服务标记场景缺口"},
                "script_actions": {"action": "suggest_new", "details": "建议新增获客成本控制话术"},
                "status": "executed",
            },
            {
                "event_idx": 5,
                "trigger_signal": {"type": "diagnosis_trend", "avg_score_drop": 8, "common_issue": "需求挖掘不足"},
                "pain_point_actions": {"action": "create", "details": "新增痛点'需求挖掘能力不足'"},
                "product_actions": {},
                "service_actions": {"action": "boost", "details": "团队培训服务优先级提升"},
                "script_actions": {"action": "suggest_update", "details": "SPIN提问话术需要更新"},
                "status": "pending",
            },
        ]
        for cdef in cascade_defs:
            cascade = StrategyCascade(
                id=uuid4(), enterprise_id=ent.id,
                flywheel_event_id=fw_events[cdef["event_idx"]].id,
                trigger_signal=cdef["trigger_signal"],
                pain_point_actions=cdef.get("pain_point_actions", {}),
                product_actions=cdef.get("product_actions", {}),
                service_actions=cdef.get("service_actions", {}),
                script_actions=cdef.get("script_actions", {}),
                status=cdef["status"],
                reviewed_by=admin.id if cdef["status"] == "executed" else None,
                reviewed_at=days_ago(5) if cdef["status"] == "executed" else None,
                executed_at=days_ago(5) if cdef["status"] == "executed" else None,
                created_at=days_ago(10),
            )
            session.add(cascade)
        await session.flush()
        print(f"[8.6/10] {len(fw_events)}个飞轮事件 + {len(cascade_defs)}个策略联动创建完成。")

        # ── 9. 培训记录 (50条，跨7天) ───────────────────────
        train_categories = ["异议处理", "开场白", "竞品应对", "促成", "售后", "复购"]
        train_questions = [
            ('当客户说"你们的产品太贵了"时，以下哪种回应最有效？', [{"key":"A","text":"我们可以打折"},{"key":"B","text":"一分钱一分货"},{"key":"C","text":"您觉得贵是跟什么对比呢？"},{"key":"D","text":"这已经是最低价了"}], "C", "面对价格异议，先理解客户的参照系再做价值引导"),
            ("客户第一次咨询，以下哪个开场白最好？", [{"key":"A","text":"买不买都没关系"},{"key":"B","text":"结合客户关注点个性化问候"},{"key":"C","text":"直接介绍产品"},{"key":"D","text":"先发优惠券"}], "B", "个性化开场建立初步信任"),
            ("客户说竞品更好时，应该怎么做？", [{"key":"A","text":"贬低竞品"},{"key":"B","text":"承认竞品优势再引导差异化"},{"key":"C","text":"忽略不回应"},{"key":"D","text":"直接降价"}], "B", "承认竞品优势体现专业性，再引导差异化"),
            ("客户犹豫不决时，以下哪种做法最好？", [{"key":"A","text":"一直催促"},{"key":"B","text":"放弃跟进"},{"key":"C","text":"用限时优惠+社会证明推动"},{"key":"D","text":"威胁涨价"}], "C", "用合理的紧迫感和社会证明辅助决策"),
            ("处理客户投诉时，第一步应该？", [{"key":"A","text":"解释原因"},{"key":"B","text":"推卸责任"},{"key":"C","text":"先共情安抚情绪"},{"key":"D","text":"直接赔偿"}], "C", "先处理情绪再处理事情"),
        ]
        for _ in range(50):
            q_data = random.choice(train_questions)
            is_correct = random.random() < 0.7
            tr = TrainingRecord(
                id=uuid4(),
                user_id=random.choice(team).id,
                enterprise_id=ent.id,
                script_id=random.choice(scripts).id,
                question={"question": q_data[0], "options": q_data[1]},
                user_answer=q_data[2] if is_correct else random.choice(["A", "B", "C", "D"]),
                correct_answer=q_data[2],
                is_correct=is_correct,
                category=random.choice(train_categories),
                difficulty=random.randint(1, 3),
                explanation={"text": q_data[3]},
                created_at=hours_ago(random.randint(0, 168)),
            )
            session.add(tr)
        await session.flush()
        print("[9/10] 50条培训记录创建完成。")

        # ── 10. 渠道物料 (12条) ─────────────────────────────
        cm_defs = [
            ("douyin", "热玛吉真实体验｜从犹豫到惊艳", "video", {"views": 123000, "likes": 3456, "comments": 890}),
            ("douyin", "30岁抗衰怎么选？医生专业建议", "video", {"views": 151000, "likes": 5230, "comments": 1200}),
            ("douyin", "做完热玛吉7天/14天/30天效果对比", "video", {"views": 214000, "likes": 8901, "comments": 2300}),
            ("xhs", "做完热玛吉1个月后朋友以为我换了头", "image", {"views": 45000, "likes": 2340, "saves": 890}),
            ("xhs", "医美避坑指南｜选对机构比选对项目更重要", "image", {"views": 68000, "likes": 4120, "saves": 1560}),
            ("xhs", "素人改造vlog｜3个月逆袭记录", "video", {"views": 89000, "likes": 6700, "saves": 2100}),
            ("wechat", "星辰医美3月感恩季特惠", "article", {"reads": 8560, "shares": 326}),
            ("wechat", "消费医疗行业话术升级白皮书", "article", {"reads": 12300, "shares": 567}),
            ("wechat", "客户见证：从怀疑到信任的转变", "article", {"reads": 5600, "shares": 189}),
            ("baidu", "热玛吉多少钱一次？2026最新价格", "ad", {"impressions": 120000, "clicks": 8900, "conversions": 450}),
            ("baidu", "种植牙哪家好？全国口碑榜Top10", "ad", {"impressions": 95000, "clicks": 6700, "conversions": 320}),
            ("baidu", "减肥项目大全｜科学瘦身方案对比", "ad", {"impressions": 78000, "clicks": 5400, "conversions": 280}),
        ]
        for ch, title, mtype, metrics in cm_defs:
            cm = ChannelMaterial(
                id=uuid4(), enterprise_id=ent.id,
                channel=ch, title=title, content=f"{title}的详细内容描述",
                material_type=mtype, metrics=metrics,
                extracted_info={"brand_tone": "专业可信赖", "selling_points": ["效果显著", "安全可靠"], "keywords": title.split("｜")},
                tags=[ch, mtype], status="active",
                created_at=days_ago(random.randint(1, 30)),
            )
            session.add(cm)

        # ── 11. 模拟演练会话 (3条) ──────────────────────────
        sim_defs = [
            ("价格异议处理", "price_sensitive", 1, "completed", {"overall": 82, "dimensions": {"话术运用": 85, "沟通技巧": 80, "情绪管理": 78}}),
            ("竞品对比", "analytical", 2, "completed", {"overall": 76, "dimensions": {"话术运用": 78, "沟通技巧": 75, "情绪管理": 72}}),
            ("售后投诉", "angry", 3, "completed", {"overall": 88, "dimensions": {"话术运用": 90, "沟通技巧": 85, "情绪管理": 92}}),
        ]
        for scenario, ctype, diff, status, score in sim_defs:
            ss = SimulationSession(
                id=uuid4(), user_id=admin.id, enterprise_id=ent.id,
                scenario=scenario, customer_type=ctype, difficulty=diff,
                messages=[
                    {"role": "customer", "content": f"关于{scenario}的初始问题"},
                    {"role": "agent", "content": "您好，我来帮您解答..."},
                    {"role": "coach", "content": "处理得不错，注意把握节奏", "score": score["overall"]},
                ],
                score=score, status=status,
                completed_at=days_ago(random.randint(1, 7)),
                created_at=days_ago(random.randint(1, 7)),
            )
            session.add(ss)

        await session.commit()
        print("[10/10] 全部种子数据导入完成！")
        print("=" * 50)
        print("数据汇总：")
        print(f"  企业: 2 (千锤平台 + 千锤科技)")
        print(f"  超管: 1 (superadmin/kst@2026)")
        print(f"  用户: 5 (demo/demo123456 + 4个团队成员)")
        print(f"  话术: {len(scripts)}条 (status=published)")
        print(f"  使用记录: 200条 (覆盖最近7天)")
        print(f"  痛点: {len(pain_points)}个")
        print(f"  产品: {len(products)}个")
        print(f"  服务: {len(services)}个")
        print(f"  诊断报告: {len(diag_reports)}条 (三层诊断格式)")
        print(f"  优化任务: {len(opt_tasks)}个 (含策略)")
        print(f"  飞轮事件: {len(fw_events)}条")
        print(f"  策略联动: {len(cascade_defs)}条")
        print(f"  培训记录: 50条")
        print(f"  渠道物料: {len(cm_defs)}条")
        print(f"  模拟演练: 3条")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed())
