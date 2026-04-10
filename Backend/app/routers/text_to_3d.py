"""이미지/3D 생성 API 라우터 - 이미지 생성, 3D 변환, 상태 조회, 이력 관리"""

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response, RedirectResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, async_session
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.generation import Generation
from app.schemas.generation import (
    GenerateRequest,
    GenerationResponse,
    GenerationStatusResponse,
    GenerationListResponse,
)
from app.services import llm_service, trellis_service, storage_service

router = APIRouter(prefix="/api/text-to-3d", tags=["이미지/3D 생성"])
logger = logging.getLogger(__name__)
settings = get_settings()


# ===== 백그라운드 작업 함수 =====

async def _background_generate_image(generation_id: int, prompt: str, image_bytes: Optional[bytes] = None, filename: str = "image.png"):
    """백그라운드에서 LLM 서버로 이미지 생성 또는 멀티뷰 전처리 요청"""
    async with async_session() as db:
        try:
            # 1) 상태를 'generating'으로 변경
            gen = await db.get(Generation, generation_id)
            if not gen:
                return
            gen.status = "generating"
            gen.updated_at = datetime.utcnow()
            await db.commit()

            # 2) LLM 서버에 이미지 생성/전처리 요청
            result = await llm_service.request_image_generation(prompt, image_bytes=image_bytes, filename=filename)

            if result["success"] and result["image_data"]:
                # 생성/전처리된 멀티뷰 이미지 저장
                if isinstance(result["image_data"], bytes):
                    image_path = storage_service.save_image(result["image_data"])
                else:
                    image_path = str(result["image_data"])

                gen.image_url = image_path
                gen.status = "image_done"
                logger.info(f"✅ [LLM] 멀티뷰 이미지 생성 완료 (ID: {generation_id}, 경로: {image_path})")
                
                # 3) 성공 시 다음 단계인 3D 변환 자동으로 실행 (이미지가 생성되었으므로)
                await db.commit()
                await _background_convert_3d(generation_id, image_path)
            else:
                gen.status = "failed"
                logger.error(f"이미지 생성/전처리 실패 (ID: {generation_id}): {result['error']}")
                gen.updated_at = datetime.utcnow()
                await db.commit()

        except Exception as e:
            logger.error(f"백그라운드 이미지 작업 오류 (ID: {generation_id}): {e}")
            gen = await db.get(Generation, generation_id)
            if gen:
                gen.status = "failed"
                gen.updated_at = datetime.utcnow()
                await db.commit()


async def _background_convert_3d(generation_id: int, image_path: str):
    """백그라운드에서 TRELLIS 서버로 3D 변환 요청"""
    async with async_session() as db:
        try:
            # 1) 상태를 'converting'으로 변경
            gen = await db.get(Generation, generation_id)
            if not gen:
                return
            gen.status = "converting"
            gen.updated_at = datetime.utcnow()
            await db.commit()

            # 2) 이미지 데이터 가져오기 (로컬 or GCS)
            image_bytes = storage_service.get_file_bytes(image_path)
            if not image_bytes:
                gen.status = "failed"
                gen.updated_at = datetime.utcnow()
                await db.commit()
                logger.error(f"3D 변환용 이미지를 찾을 수 없음: {image_path}")
                return

            # 3) TRELLIS 서버에 3D 변환 요청
            result = await trellis_service.request_3d_conversion_from_bytes(
                image_bytes, image_path.split("/")[-1]
            )

            if result["success"] and result["model_data"]:
                if isinstance(result["model_data"], bytes):
                    model_path = storage_service.save_3d_model(
                        result["model_data"],
                        extension=result.get("file_extension", ".glb"),
                    )
                else:
                    model_path = str(result["model_data"])

                gen.model_3d_url = model_path
                gen.status = "done"
                logger.info(f"✅ [Storage & DB] 3D 모델 파일 저장 완료 및 DB 업데이트 성공 (ID: {generation_id}, 파일경로: {model_path})")
            else:
                gen.status = "failed"
                logger.error(f"3D 변환 실패 (ID: {generation_id}): {result['error']}")

            gen.updated_at = datetime.utcnow()
            await db.commit()

        except Exception as e:
            logger.error(f"백그라운드 3D 변환 오류 (ID: {generation_id}): {e}")
            gen = await db.get(Generation, generation_id)
            if gen:
                gen.status = "failed"
                gen.updated_at = datetime.utcnow()
                await db.commit()


# ===== API 엔드포인트 =====

@router.post("/generate", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_image(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    prompt_text: str = Form(default=""),
    image: UploadFile = File(default=None),
):
    """텍스트 또는 이미지 기반 생성 요청

    - JSON(prompt_text) 또는 multipart(image + prompt_text) 모두 지원
    - 작업을 DB에 등록하고 즉시 응답 (202 Accepted)
    - 실제 생성은 백그라운드에서 비동기 처리
    - 상태는 `/api/text-to-3d/{id}/status`로 조회
    """
    if not prompt_text and (image is None or image.filename == ""):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="프롬프트 또는 이미지를 제공해주세요")

    # DB에 새 작업 등록
    generation = Generation(
        user_id=current_user.id,
        prompt_text=prompt_text or "(이미지 업로드)",
        status="pending",
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    if image and image.filename:
        # 이미지 업로드: LLM 서버로 보내서 멀티뷰 전처리 과정을 거침
        image_bytes = await image.read()
        logger.info(f"✅ [DB] 이미지 업로드 전처리 요청 저장 완료 (작업 ID: {generation.id}, 파일: '{image.filename}')")
        background_tasks.add_task(_background_generate_image, generation.id, prompt_text, image_bytes, image.filename)
    else:
        # 텍스트 프롬프트: LLM으로 이미지 생성 후 멀티뷰 생성
        logger.info(f"✅ [DB] 텍스트 생성 요청 저장 완료 (작업 ID: {generation.id}, 프롬프트: '{prompt_text}')")
        background_tasks.add_task(_background_generate_image, generation.id, prompt_text)

    return generation


@router.get("/{generation_id}/status", response_model=GenerationStatusResponse)
async def get_status(
    generation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """생성 작업 상태 조회"""
    gen = await db.get(Generation, generation_id)

    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다")

    return gen


@router.get("/{generation_id}/image")
async def get_image(
    generation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """생성된 이미지 조회"""
    gen = await db.get(Generation, generation_id)
    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다")

    if not gen.image_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="이미지가 아직 생성되지 않았습니다")

    # GCS 모드: 공개 URL로 리다이렉트
    if settings.is_cloud_storage:
        public_url = storage_service.get_public_url(gen.image_url)
        return RedirectResponse(url=public_url)

    # 로컬 모드: 파일 직접 서빙
    from fastapi.responses import FileResponse

    file_path = storage_service.get_file_path(gen.image_url)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="이미지 파일을 찾을 수 없습니다")

    return FileResponse(str(file_path), media_type="image/png")


@router.post("/{generation_id}/convert-3d", response_model=GenerationStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def convert_to_3d(
    generation_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """3D 모델 변환 요청

    - 이미지가 생성 완료된(image_done) 상태에서만 요청 가능
    - 실제 3D 변환은 백그라운드에서 비동기 처리
    """
    gen = await db.get(Generation, generation_id)
    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다")

    if gen.status != "image_done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"3D 변환은 이미지 생성이 완료된 후에만 가능합니다 (현재 상태: {gen.status})",
        )

    # 백그라운드에서 3D 변환 실행
    background_tasks.add_task(_background_convert_3d, gen.id, gen.image_url)

    return gen


@router.get("/{generation_id}/3d-status", response_model=GenerationStatusResponse)
async def get_3d_status(
    generation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """3D 변환 상태 조회"""
    gen = await db.get(Generation, generation_id)
    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다")

    return gen


@router.get("/{generation_id}/3d-model")
async def get_3d_model(
    generation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """3D 모델 파일 조회"""
    gen = await db.get(Generation, generation_id)
    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다")

    if not gen.model_3d_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="3D 모델이 아직 생성되지 않았습니다")

    # GCS 모드: 공개 URL로 리다이렉트
    if settings.is_cloud_storage:
        public_url = storage_service.get_public_url(gen.model_3d_url)
        return RedirectResponse(url=public_url)

    # 로컬 모드: 파일 직접 서빙
    from fastapi.responses import FileResponse

    file_path = storage_service.get_file_path(gen.model_3d_url)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="3D 모델 파일을 찾을 수 없습니다")

    # 파일 확장자에 따라 적절한 media_type 설정
    if str(file_path).endswith(".glb"):
        media_type = "model/gltf-binary"
    elif str(file_path).endswith(".ply"):
        media_type = "application/octet-stream"
    else:
        media_type = "application/octet-stream"

    return FileResponse(str(file_path), media_type=media_type)


@router.get("/history", response_model=GenerationListResponse)
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """내 생성 이력 조회 (최신순)"""
    result = await db.execute(
        select(Generation)
        .where(Generation.user_id == current_user.id)
        .order_by(desc(Generation.created_at))
    )
    generations = result.scalars().all()

    return GenerationListResponse(
        total=len(generations),
        items=generations,
    )


@router.delete("/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generation(
    generation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """생성물 삭제 (DB 레코드 + 관련 파일)"""
    gen = await db.get(Generation, generation_id)
    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다")

    # 관련 파일 삭제 (로컬 or GCS)
    if gen.image_url:
        storage_service.delete_file(gen.image_url)
    if gen.model_3d_url:
        storage_service.delete_file(gen.model_3d_url)

    # DB 레코드 삭제
    await db.delete(gen)
    await db.commit()
