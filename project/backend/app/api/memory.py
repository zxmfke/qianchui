import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.memory import PainPoint, Product, ServiceItem, product_pain_points, service_products
from app.models.script import Script, script_pain_points, script_products, script_services
from app.models.user import User
from app.schemas.memory import (
    KnowledgeChainNode,
    KnowledgeChainResponse,
    PainPointCreate,
    PainPointResponse,
    ProductCreate,
    ProductResponse,
    ServiceItemCreate,
    ServiceItemResponse,
)

router = APIRouter(prefix="/api/memory", tags=["memory"])


# ── Pain Points ──────────────────────────────────────────

@router.get("/pain-points", response_model=list[PainPointResponse])
async def list_pain_points(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PainPoint)
        .where(PainPoint.enterprise_id == user.enterprise_id)
        .order_by(PainPoint.created_at.desc())
    )
    return [PainPointResponse.model_validate(p) for p in result.scalars().all()]


@router.post("/pain-points", response_model=PainPointResponse, status_code=status.HTTP_201_CREATED)
async def create_pain_point(
    body: PainPointCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pain_point = PainPoint(
        enterprise_id=user.enterprise_id,
        name=body.name,
        description=body.description,
        metadata_=body.metadata,
    )
    db.add(pain_point)
    await db.flush()
    return PainPointResponse.model_validate(pain_point)


# ── Products ─────────────────────────────────────────────

@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Product)
        .where(Product.enterprise_id == user.enterprise_id)
        .order_by(Product.created_at.desc())
    )
    products = result.scalars().all()
    return [ProductResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        pain_points=[PainPointResponse.model_validate(pp) for pp in p.pain_points],
        created_at=p.created_at,
    ) for p in products]


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = Product(
        enterprise_id=user.enterprise_id,
        name=body.name,
        description=body.description,
        metadata_=body.metadata,
    )
    db.add(product)
    await db.flush()

    for pp_id in body.pain_point_ids:
        await db.execute(
            product_pain_points.insert().values(product_id=product.id, pain_point_id=pp_id)
        )
    await db.flush()

    refreshed = await db.execute(
        select(Product).where(Product.id == product.id)
    )
    product = refreshed.scalar_one()

    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        pain_points=[PainPointResponse.model_validate(pp) for pp in product.pain_points],
        created_at=product.created_at,
    )


# ── Services ─────────────────────────────────────────────

@router.get("/services", response_model=list[ServiceItemResponse])
async def list_services(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ServiceItem)
        .where(ServiceItem.enterprise_id == user.enterprise_id)
        .order_by(ServiceItem.created_at.desc())
    )
    services = result.scalars().all()
    return [ServiceItemResponse(
        id=s.id,
        name=s.name,
        description=s.description,
        products=[ProductResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            pain_points=[PainPointResponse.model_validate(pp) for pp in p.pain_points],
            created_at=p.created_at,
        ) for p in s.products],
        created_at=s.created_at,
    ) for s in services]


@router.post("/services", response_model=ServiceItemResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    body: ServiceItemCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ServiceItem(
        enterprise_id=user.enterprise_id,
        name=body.name,
        description=body.description,
        metadata_=body.metadata,
    )
    db.add(service)
    await db.flush()

    for prod_id in body.product_ids:
        await db.execute(
            service_products.insert().values(service_id=service.id, product_id=prod_id)
        )
    await db.flush()

    refreshed = await db.execute(
        select(ServiceItem).where(ServiceItem.id == service.id)
    )
    service = refreshed.scalar_one()

    return ServiceItemResponse(
        id=service.id,
        name=service.name,
        description=service.description,
        products=[ProductResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            pain_points=[PainPointResponse.model_validate(pp) for pp in p.pain_points],
            created_at=p.created_at,
        ) for p in service.products],
        created_at=service.created_at,
    )


# ── Knowledge Chain ──────────────────────────────────────

@router.get("/knowledge-chain", response_model=KnowledgeChainResponse)
async def get_knowledge_chain(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pain_result = await db.execute(
        select(PainPoint)
        .where(PainPoint.enterprise_id == user.enterprise_id)
        .order_by(PainPoint.name)
    )
    pain_points = pain_result.scalars().all()

    chain_nodes = []
    for pp in pain_points:
        product_children = []
        for product in pp.products:
            service_children = []
            for svc in product.services:
                script_result = await db.execute(
                    select(Script)
                    .join(script_services, Script.id == script_services.c.script_id)
                    .where(
                        script_services.c.service_id == svc.id,
                        Script.enterprise_id == user.enterprise_id,
                    )
                    .limit(10)
                )
                scripts = script_result.scalars().all()
                script_children = [
                    KnowledgeChainNode(id=s.id, name=s.title, type="script")
                    for s in scripts
                ]
                service_children.append(
                    KnowledgeChainNode(id=svc.id, name=svc.name, type="service", children=script_children)
                )

            product_children.append(
                KnowledgeChainNode(id=product.id, name=product.name, type="product", children=service_children)
            )

        chain_nodes.append(
            KnowledgeChainNode(id=pp.id, name=pp.name, type="pain_point", children=product_children)
        )

    return KnowledgeChainResponse(pain_points=chain_nodes)
