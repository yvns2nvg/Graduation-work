"""다운로드 API 라우터 - 3D 모델 파일 다운로드 (로컬 + GCS 지원)"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.generation import Generation
from app.services import storage_service

router = APIRouter(prefix="/api/shoes", tags=["다운로드"])
settings = get_settings()


@router.get("/{generation_id}/download")
async def download_3d_model(
    generation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """3D 모델 파일 다운로드

    - 브라우저에서 파일 다운로드 다이얼로그가 뜸
    - Content-Disposition: attachment 헤더 포함
    """
    gen = await db.get(Generation, generation_id)
    if not gen or gen.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다")

    if gen.status != "done" or not gen.model_3d_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="3D 모델이 아직 완성되지 않았습니다",
        )

    # 다운로드 파일명 설정 (프롬프트 일부를 파일명에 포함)
    prompt_slug = gen.prompt_text[:30].replace(" ", "_").replace("/", "_")
    # 확장자 추출
    if "." in gen.model_3d_url:
        extension = "." + gen.model_3d_url.rsplit(".", 1)[-1]
    else:
        extension = ".glb"
    download_filename = f"shoe_{gen.id}_{prompt_slug}{extension}"

    # GCS 모드: 파일 데이터를 GCS에서 가져와서 Response로 반환
    if settings.is_cloud_storage:
        file_bytes = storage_service.get_file_bytes(gen.model_3d_url)
        if not file_bytes:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="3D 모델 파일을 찾을 수 없습니다")

        return Response(
            content=file_bytes,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"'
            },
        )

    # 로컬 모드: FileResponse로 직접 서빙
    file_path = storage_service.get_file_path(gen.model_3d_url)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="3D 모델 파일을 찾을 수 없습니다")

    return FileResponse(
        path=str(file_path),
        filename=download_filename,
        media_type="application/octet-stream",
    )
