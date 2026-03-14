import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runtime import AgentRuntime
from app.api.deps import get_current_user
from app.database import async_session_factory, get_db
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    conversations = result.scalars().all()
    out: list[ConversationResponse] = []
    for c in conversations:
        msg_count = len(c.messages) if c.messages else 0
        last_msg = c.messages[-1].content[:80] if c.messages else None
        resp = ConversationResponse.model_validate(c)
        resp.message_count = msg_count
        resp.last_message = last_msg
        out.append(resp)
    return out


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = Conversation(
        user_id=user.id,
        enterprise_id=user.enterprise_id,
        title=body.title or "新对话",
    )
    db.add(conversation)
    await db.flush()
    return ConversationResponse.model_validate(conversation)


@router.post("/{conversation_id}/messages", response_model=dict)
async def send_message(
    conversation_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "对话不存在", "message_en": "Conversation not found"})

    runtime = AgentRuntime(db)
    response = await runtime.process_message(
        user_input=body.content,
        conversation_id=conversation_id,
        user_id=str(user.id),
        enterprise_id=str(user.enterprise_id),
    )

    return response


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "对话不存在", "message_en": "Conversation not found"})

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == uuid.UUID(conversation_id))
        .order_by(Message.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    messages = msg_result.scalars().all()
    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{conversation_id}/stream")
async def stream_conversation(
    conversation_id: str,
    body: MessageCreate,
    user: User = Depends(get_current_user),
):
    async def _generate():
        async with async_session_factory() as session:
            result = await session.execute(
                select(Conversation).where(
                    Conversation.id == uuid.UUID(conversation_id),
                    Conversation.user_id == user.id,
                )
            )
            if not result.scalar_one_or_none():
                yield f"data: {json.dumps({'type': 'error', 'message': '对话不存在', 'message_en': 'Conversation not found'})}\n\n"
                return

            runtime = AgentRuntime(session)
            async for chunk in runtime.process_message_stream(
                user_input=body.content,
                conversation_id=conversation_id,
                user_id=str(user.id),
                enterprise_id=str(user.enterprise_id),
            ):
                yield chunk

            await session.commit()

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
