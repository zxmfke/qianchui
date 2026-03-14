"""渠道物料 API 请求/响应模型"""

from pydantic import BaseModel, Field


class ChannelMaterialCreate(BaseModel):
    """创建物料请求体"""

    channel: str = Field(..., description="douyin/xhs/wechat/baidu/kuaishou/weibo/other")
    title: str = Field(..., min_length=1)
    content: str = Field(default="")
    source_url: str | None = None
    material_type: str = Field(default="video")
    tags: list[str] = Field(default_factory=list)


class ChannelMaterialUpdate(BaseModel):
    """更新物料请求体"""

    title: str | None = None
    content: str | None = None
    source_url: str | None = None
    material_type: str | None = None
    metrics: dict | None = None
    tags: list[str] | None = None
    status: str | None = None
