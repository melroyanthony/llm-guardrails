# MongoDB Patterns

For NoSQL use cases, use MongoDB with async drivers.

## Version Matrix

| Package | Version | Notes |
|---------|---------|-------|
| MongoDB | 7.x | Latest stable |
| Motor | 3.6.x | Async driver for MongoDB |
| Beanie | 1.26.x | Async ODM (Pydantic-based) |

## When to Use MongoDB vs PostgreSQL

| Use Case | Recommendation |
|----------|----------------|
| Relational data with joins | PostgreSQL |
| Document-oriented data | MongoDB |
| Flexible schema / rapid iteration | MongoDB |
| Complex transactions | PostgreSQL |
| Time-series / logs | MongoDB |
| Geospatial queries | Either (both support) |

## Project Structure

```
backend/
├── app/
│   ├── database.py          # MongoDB connection
│   ├── models/              # Beanie documents
│   │   ├── __init__.py
│   │   └── {entity}.py
│   └── ...
```

## Beanie Setup

### database.py

```python
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models import Item, Location, Staff  # Import all documents

client: AsyncIOMotorClient | None = None


async def init_db():
    """Initialize MongoDB connection and Beanie."""
    global client
    client = AsyncIOMotorClient(settings.mongodb_url)

    await init_beanie(
        database=client[settings.mongodb_db],
        document_models=[
            Item,
            Location,
            Staff,
        ],
    )


async def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
```

### Beanie Document Model

```python
from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from typing import Optional


class Item(Document):
    """Item document in MongoDB."""

    name: Indexed(str)  # Creates index on name
    quantity: int = Field(ge=0)
    location_id: Indexed(str)  # Reference to Location
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "items"  # Collection name
        indexes = [
            [("location_id", 1), ("name", 1)],  # Compound index
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Lettuce",
                "quantity": 100,
                "location_id": "loc_123",
            }
        }


# Pydantic models for API
class ItemCreate(BaseModel):
    name: str
    quantity: int = Field(ge=0)
    location_id: str


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = Field(ge=0, default=None)


class ItemPublic(BaseModel):
    id: str
    name: str
    quantity: int
    location_id: str
    created_at: datetime

    @classmethod
    def from_document(cls, doc: Item) -> "ItemPublic":
        return cls(
            id=str(doc.id),
            name=doc.name,
            quantity=doc.quantity,
            location_id=doc.location_id,
            created_at=doc.created_at,
        )
```

### Router with Beanie

```python
from fastapi import APIRouter, HTTPException, status
from beanie import PydanticObjectId

from app.models.item import Item, ItemCreate, ItemUpdate, ItemPublic

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=list[ItemPublic])
async def list_items(
    location_id: str | None = None,
    limit: int = 20,
    skip: int = 0,
):
    """List items with optional location filter."""
    query = Item.find()

    if location_id:
        query = query.find(Item.location_id == location_id)

    items = await query.skip(skip).limit(limit).to_list()
    return [ItemPublic.from_document(item) for item in items]


@router.post("/", response_model=ItemPublic, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate):
    """Create a new item."""
    db_item = Item(**item.model_dump())
    await db_item.insert()
    return ItemPublic.from_document(db_item)


@router.get("/{item_id}", response_model=ItemPublic)
async def get_item(item_id: str):
    """Get a single item by ID."""
    item = await Item.get(PydanticObjectId(item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemPublic.from_document(item)


@router.patch("/{item_id}", response_model=ItemPublic)
async def update_item(item_id: str, item_update: ItemUpdate):
    """Update an item."""
    item = await Item.get(PydanticObjectId(item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = item_update.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await item.update({"$set": update_data})

    return ItemPublic.from_document(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str):
    """Delete an item."""
    item = await Item.get(PydanticObjectId(item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await item.delete()
```

## Docker Compose with MongoDB

```yaml
services:
  mongo:
    image: mongo:7
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER:-app}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:-secret}
      MONGO_INITDB_DATABASE: ${MONGO_DB:-app}
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    environment:
      MONGODB_URL: mongodb://${MONGO_USER:-app}:${MONGO_PASSWORD:-secret}@mongo:27017
      MONGODB_DB: ${MONGO_DB:-app}
    depends_on:
      mongo:
        condition: service_healthy

volumes:
  mongo_data:
```

## Aggregation Pipelines

```python
async def get_inventory_summary(location_id: str) -> dict:
    """Get inventory summary using aggregation."""
    pipeline = [
        {"$match": {"location_id": location_id}},
        {
            "$group": {
                "_id": None,
                "total_items": {"$sum": 1},
                "total_quantity": {"$sum": "$quantity"},
                "avg_quantity": {"$avg": "$quantity"},
            }
        },
    ]

    result = await Item.aggregate(pipeline).to_list()
    return result[0] if result else {}
```

## Testing with MongoDB

```python
import pytest
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from app.models import Item, Location


@pytest.fixture
async def mongo_client():
    """Mock MongoDB client for testing."""
    client = AsyncMongoMockClient()

    await init_beanie(
        database=client["test_db"],
        document_models=[Item, Location],
    )

    yield client

    # Cleanup
    await client.drop_database("test_db")
```

## When to Choose

**PostgreSQL recommended** for:
- Relational data with complex joins (e.g., inventory management)
- Strong consistency requirements (stock levels, transactions)
- Complex analytical queries and reporting

**MongoDB recommended** for:
- Flexible schema requirements
- Document-centric data (logs, user activity, content)
- Rapid prototyping with evolving data models
