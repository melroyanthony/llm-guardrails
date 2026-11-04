## Core Patterns

### config.py (Cognita-style singleton with validation)

```python
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation (Cognita pattern)."""

    # Database
    database_url: str = ""  # Required — load from DATABASE_URL env var

    @field_validator("database_url")
    @classmethod
    def database_url_must_be_set(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must be set — never hardcode credentials")
        return v

    # App
    debug: bool = False
    log_level: str = "info"
    environment: str = "development"  # development | staging | production
    secret_key: str = ""

    @field_validator("secret_key")
    @classmethod
    def secret_key_required(cls, v: str, info) -> str:
        """Reject empty secret_key in non-development environments."""
        env = info.data.get("environment", "development")
        if not v and env != "development":
            raise ValueError("SECRET_KEY must be set in staging/production (set SECRET_KEY env var)")
        if not v:
            # Generate a random key for development — never a fixed placeholder
            import secrets
            return secrets.token_urlsafe(32)
        return v

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",  # Allow undefined env vars
    )


# Singleton - instantiated once at module load
settings = Settings()
```

### main.py

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
```

### database.py

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings

async_engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_use_lifo=True,
)

async_session = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_db():
    async with async_session() as session:
        yield session
```

### SQLModel Pattern (Base, Create, Public, Table)

```python
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from pydantic import field_validator

class ItemBase(SQLModel):
    """Shared fields for all Item schemas."""
    name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=0)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()

class ItemCreate(ItemBase):
    """Fields required to create an Item."""
    pass

class ItemUpdate(SQLModel):
    """Fields that can be updated (all optional)."""
    name: str | None = None
    quantity: int | None = None

class ItemPublic(ItemBase):
    """Fields returned to clients."""
    id: int
    created_at: datetime

class Item(ItemBase, table=True):
    """Database table definition."""
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    location_id: int = Field(foreign_key="location.id")
    location: "Location" = Relationship(back_populates="items")
```

### Router Pattern

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_db
from app.models.item import Item, ItemCreate, ItemPublic, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/", response_model=list[ItemPublic])
async def list_items(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
):
    """List all items with pagination."""
    stmt = select(Item).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=ItemPublic, status_code=status.HTTP_201_CREATED)
async def create_item(
    item: ItemCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new item."""
    db_item = Item.model_validate(item)
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item

@router.get("/{item_id}", response_model=ItemPublic)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single item by ID."""
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.patch("/{item_id}", response_model=ItemPublic)
async def update_item(
    item_id: int,
    item_update: ItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an item."""
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an item."""
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
```

### Health Endpoints

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_db

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/live")
async def liveness():
    """Liveness probe - is the process running?"""
    return {"status": "ok"}

@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe - can we serve traffic?"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}
```

### Feature Module Pattern (Cognita-inspired)

For complex features, organize as self-contained modules:

```
app/modules/inventory/
├── __init__.py          # Export router
├── router.py            # API endpoints
├── service.py           # Business logic
├── schemas.py           # Request/response models
└── dependencies.py      # Module-specific deps
```

```python
# app/modules/inventory/__init__.py
from .router import router

__all__ = ["router"]
```

```python
# app/modules/inventory/service.py
from sqlmodel.ext.asyncio.session import AsyncSession

class InventoryService:
    """Business logic for inventory operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stock_level(self, item_id: int) -> int:
        """Calculate current stock from movements."""
        # Business logic here
        pass

    async def record_movement(self, item_id: int, quantity: int, type: str) -> None:
        """Record stock in/out movement."""
        # Business logic here
        pass
```

```python
# app/modules/inventory/router.py
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_db
from .service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])

def get_service(db: AsyncSession = Depends(get_db)) -> InventoryService:
    return InventoryService(db)

@router.get("/{item_id}/stock")
async def get_stock(
    item_id: int,
    service: InventoryService = Depends(get_service),
):
    return {"stock": await service.get_stock_level(item_id)}
```

```python
# app/main.py - Register module
from app.modules.inventory import router as inventory_router

app.include_router(inventory_router, prefix="/api/v1")
```

