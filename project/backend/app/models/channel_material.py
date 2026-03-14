"""渠道物料数据模型

用于存储各渠道（抖音、小红书、微信、百度等）的营销物料，
支持 AI 提取品牌调性、核心卖点、风格关键词等信息。
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ChannelMaterial(TimestampMixin, Base):
    """渠道物料表"""

    __tablename__ = "channel_materials"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False
    )
    # 渠道类型: douyin/xhs/wechat/baidu/kuaishou/weibo/other
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    # 物料标题
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # 物料内容/描述
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 原始 URL（可选）
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 物料类型: video/image/article/ad/other
    material_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # 渠道指标: views, likes, comments, shares 等
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    # AI 提取的信息: brand_tone, selling_points, keywords, style 等
    extracted_info: Mapped[dict] = mapped_column(JSON, default=dict)
    # 标签列表
    tags: Mapped[list] = mapped_column(JSON, default=list)
    # 状态: active/archived，默认 active
    status: Mapped[str] = mapped_column(String(20), default="active")
