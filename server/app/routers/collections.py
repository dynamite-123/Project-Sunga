from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Collection, Record, Share
from ..schemas import CollectionCreate, CollectionResponse, RecordResponse, CollectionUpdate, MessageResponse, SharedCollectionResponse
from ..oauth2 import get_current_user

router = APIRouter(
    prefix='/collections',
    tags=['collections']
)

@router.post("/", response_model=CollectionResponse)
async def create_collection(
    collection: CollectionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new collection"""
    db_collection = Collection(
        name=collection.name,
        description=collection.description,
        user_id=current_user.id
    )
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)
    return db_collection

@router.get("/", response_model=List[CollectionResponse])
async def get_all_collections(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all collections under a user"""
    collections = db.query(Collection).filter(Collection.user_id == current_user.id).all()
    return collections

@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific collection by ID"""
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return collection

@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: str,
    collection: CollectionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a collection"""
    db_collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()
    
    if not db_collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    db_collection.name = collection.name
    db_collection.description = collection.description
    db.commit()
    db.refresh(db_collection)
    return db_collection

@router.patch("/{collection_id}", response_model=CollectionResponse)
async def update_collection_partial(
    collection_id: str,
    collection_update: CollectionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Partially update a collection"""
    db_collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()
    
    if not db_collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Update only the fields that are provided
    if collection_update.name is not None:
        db_collection.name = collection_update.name
    if collection_update.description is not None:
        db_collection.description = collection_update.description
        
    db.commit()
    db.refresh(db_collection)
    return db_collection

@router.get("/{collection_id}/records", response_model=List[RecordResponse])
async def get_records_from_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all records from a collection"""
    # Verify collection belongs to user
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    records = db.query(Record).filter(Record.collection_id == collection_id).all()
    return records

@router.put("/{collection_id}/records/{record_id}", response_model=MessageResponse)
async def add_record_to_collection(
    collection_id: str,
    record_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add a record to a collection"""
    # Verify collection belongs to user
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Verify record belongs to user
    record = db.query(Record).filter(
        Record.id == record_id,
        Record.user_id == current_user.id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    record.collection_id = collection_id
    db.commit()
    
    return {"message": "Record added to collection successfully"}

@router.delete("/{collection_id}/records/{record_id}", response_model=MessageResponse)
async def remove_record_from_collection(
    collection_id: str,
    record_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove a record from a collection (sets collection_id to null)"""
    # Verify collection belongs to user
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Verify record belongs to user and is in this collection
    record = db.query(Record).filter(
        Record.id == record_id,
        Record.user_id == current_user.id,
        Record.collection_id == collection_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found in this collection")
    
    record.collection_id = None
    db.commit()
    
    return {"message": "Record removed from collection successfully"}

@router.delete("/{collection_id}", response_model=MessageResponse)
async def delete_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a collection"""
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Remove collection_id from all records in this collection
    db.query(Record).filter(Record.collection_id == collection_id).update(
        {"collection_id": None}
    )
    
    # Delete the collection
    db.delete(collection)
    db.commit()
    
    return {"message": "Collection deleted successfully"}

@router.get("/share/{share_token}", response_model=SharedCollectionResponse)
async def access_shared_collection(
    share_token: str,
    db: Session = Depends(get_db)
):
    """Access a collection via secure share token (no auth required)"""
    
    # Find the share
    share = db.query(Share).filter(
        Share.share_token == share_token,
        Share.is_active == True,
        Share.collection_id.isnot(None)
    ).first()
    
    if not share:
        raise HTTPException(status_code=404, detail="Invalid or expired share link")
    
    # Get the collection
    collection = db.query(Collection).filter(Collection.id == share.collection_id).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Get records in collection
    records = db.query(Record).filter(Record.collection_id == share.collection_id).all()
    
    return {
        "collection": {
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "created_at": collection.created_at
        },
        "records": [
            {
                "id": record.id,
                "filename": record.filename,
                "content": record.content,
                "created_at": record.created_at
            } for record in records
        ]
    }
