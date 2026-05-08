import uuid
import json
from loguru import logger
from typing import Optional
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form, Request, Response, BackgroundTasks
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache

from app.core.deps import get_current_user
from app.models.admin import AdminUser
from app.models.image import Image
from app.schemas.image import ImageUpdate, ImageResponse
from app.services.storage import storage
from app.services.zilliz_service import zilliz_service
from app.services.metadata_service import metadata_service
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter()

async def background_upsert_zilliz(image: Image, file_bytes: Optional[bytes] = None, mime_type: str = "image/jpeg"):
    try:
        text_to_embed = f"Title: {image.title}. Category: {image.category}. Tags: {', '.join(image.tags)}. Description: {image.description or ''}"
        
        if file_bytes is None:
            # This is an update. Re-use the existing embedding from Zilliz to save AI cost!
            logger.info("Updating embeddings to Zilliz.")
            embedding = zilliz_service.get_image_embedding(str(image.id))
            if not embedding:
                logger.warning(f"Could not find existing embedding for {image.id}. Skipping Zilliz update.")
                return
        else:
            # This is a new upload. Generate the multimodal embedding.
            logger.info("Uploading embedding to Zilliz.")
            embedding = await metadata_service.embed_multimodal(text_to_embed, file_bytes, mime_type)
        
        img_url = f"{settings.r2_public_url}/{image.image_key}" if settings.r2_public_url else image.image_key
        zilliz_service.upsert_image(
            image_id=str(image.id),
            title=image.title,
            category=image.category,
            tags=image.tags,
            image_url=img_url,
            text=text_to_embed,
            embedding=embedding
        )
    except Exception as e:
        logger.error(f"Background Zilliz upsert failed: {e}")

def background_delete_zilliz(image_id: str):
    zilliz_service.delete_image(image_id)

ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB

# ---------- Public Endpoints ----------

@router.get("/", summary="List all images")
@limiter.limit(settings.rate_limit_public)
@cache(namespace="images", expire=120)
async def list_images(
    request: Request,
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """Return a paginated list of images, optionally filtered by tag or category."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
    query_conditions = [Image.is_deleted == False]
    if tag:
        query_conditions.append(Image.tags == tag)
    if category and category != "all":
        query_conditions.append(Image.category == category)
        
    query = Image.find(*query_conditions)

    images = await query.skip(skip).limit(limit).sort("-created_at").to_list()
    total = await Image.find(*query_conditions).count()

    return {
        "images": [ImageResponse.from_doc(img) for img in images],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/{image_id}", summary="Get a single image")
@limiter.limit(settings.rate_limit_public)
@cache(namespace="images", expire=120)
async def get_image(request: Request, response: Response, image_id: PydanticObjectId):
    """Return a single image by its ID."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    image = await Image.get(image_id)
    if not image or image.is_deleted:
        raise HTTPException(status_code=404, detail="Image not found")
    return ImageResponse.from_doc(image)

# ---------- Protected Endpoints (Admin Only) ----------

@router.post("/batch", summary="Batch create multiple images", status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_admin)
async def create_batch_images(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    metadata: str = Form(...),
    _admin: AdminUser = Depends(get_current_user),
):
    """Batch upload up to 20 images with metadata."""
    if len(files) > 20:
        logger.warning(f"Batch upload rejected: {len(files)} files exceeds limit of 20.")
        raise HTTPException(status_code=400, detail="Cannot upload more than 20 files at once.")

    try:
        metadatas = json.loads(metadata)
    except Exception as e:
        logger.error(f"Failed to parse batch metadata JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid metadata format. Expected a JSON array.")

    if len(files) != len(metadatas):
        logger.warning(f"Metadata mismatch: {len(files)} files but {len(metadatas)} metadata entries.")
        raise HTTPException(status_code=400, detail="Number of files must match number of metadata entries.")

    await FastAPICache.clear(namespace="images")

    uploaded = []
    valid_categories = ["nature", "cars"]

    for idx, file in enumerate(files):
        if file.content_type not in ALLOWED_EXTENSIONS:
            logger.warning(f"Skipping {file.filename}: unsupported file type '{file.content_type}'.")
            continue

        file_bytes = await file.read()
        if len(file_bytes) > MAX_FILE_SIZE:
            logger.warning(f"Skipping {file.filename}: exceeds 15MB size limit.")
            continue

        meta = metadatas[idx]
        cat = meta.get("category", "").lower()
        if cat not in valid_categories:
            cat = "nature"

        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        object_key = f"{cat}/{unique_filename}"

        storage.upload_file(file_bytes, object_key, file.content_type)

        parsed_tags = meta.get("tags", [])
        if isinstance(parsed_tags, str):
            parsed_tags = [t.strip() for t in parsed_tags.split(",") if t.strip()]

        image = Image(
            title=meta.get("title", file.filename),
            description=meta.get("description", None),
            category=cat,
            image_key=object_key,
            tags=parsed_tags,
            rating=meta.get("rating", 0)
        )
        await image.insert()
        uploaded.append(image)

        # Sync to Zilliz in background with image bytes
        background_tasks.add_task(background_upsert_zilliz, image, file_bytes, file.content_type)

    logger.success(f"Batch upload complete: {len(uploaded)} images saved.")
    return [ImageResponse.from_doc(doc) for doc in uploaded]


@router.post("/", summary="Create an image entry", status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_admin)
async def create_image(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category: str = Form(...),
    tags: str = Form(""),
    file: UploadFile = File(...),
    _admin: AdminUser = Depends(get_current_user),
):
    """Create a new image document (admin only) and upload to R2."""
    await FastAPICache.clear(namespace="images")
    if file.content_type not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, and WebP are allowed.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 15MB.")

    valid_categories = ["nature", "cars"]
    if category.lower() not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of {valid_categories}.")

    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    object_key = f"{category.lower()}/{unique_filename}"
    
    storage.upload_file(file_bytes, object_key, file.content_type)
    
    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    image = Image(
        title=title,
        description=description,
        category=category.lower(),
        image_key=object_key,
        tags=parsed_tags,
    )
    await image.insert()
    
    # Sync to Zilliz in background with image bytes
    background_tasks.add_task(background_upsert_zilliz, image, file_bytes, file.content_type)
    
    return ImageResponse.from_doc(image)

@router.put("/{image_id}", summary="Update an image entry")
@limiter.limit(settings.rate_limit_admin)
async def update_image(
    request: Request,
    background_tasks: BackgroundTasks,
    image_id: PydanticObjectId,
    data: ImageUpdate,
    _admin: AdminUser = Depends(get_current_user),
):
    """Update an existing image document (admin only). Does not update the file itself."""
    await FastAPICache.clear(namespace="images")
    image = await Image.get(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        await image.set(update_data)
        
        # Sync to Zilliz in background (will download image bytes automatically)
        background_tasks.add_task(background_upsert_zilliz, image)

    return ImageResponse.from_doc(image)

@router.delete("/{image_id}", summary="Delete an image", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.rate_limit_admin)
async def delete_image(
    request: Request,
    background_tasks: BackgroundTasks,
    image_id: PydanticObjectId,
    _admin: AdminUser = Depends(get_current_user),
):
    """Soft-delete an image document (admin only). File remains in R2."""
    await FastAPICache.clear(namespace="images")
    image = await Image.get(image_id)
    if not image or image.is_deleted:
        raise HTTPException(status_code=404, detail="Image not found")
        
    image.is_deleted = True
    await image.save()
    
    # Sync to Zilliz in background
    background_tasks.add_task(background_delete_zilliz, str(image.id))
    
    return None
