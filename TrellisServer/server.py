"""
TRELLIS Mock 서버 (포트 8002)

현재: 주석 처리된 실제 TRELLIS 코드 + 로그만 출력하는 더미 응답
나중에: 주석 해제하면 실제 3D 변환 동작
"""

import logging
import io
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse

# ===== 실제 TRELLIS 사용 시 주석 해제 =====
# from PIL import Image
# from trellis.pipelines import TrellisImageTo3DPipeline
# from trellis.utils import render_utils
# import trimesh
# pipeline = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
# pipeline.cuda()
# ===========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TRELLIS] %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="TRELLIS 3D Server")


@app.get("/health")
async def health():
    logger.info("헬스 체크 요청 받음")
    return {"status": "ok"}


@app.post("/convert")
async def convert(image: UploadFile = File(...)):
    image_bytes = await image.read()

    logger.info("=" * 50)
    logger.info("3D 변환 요청 수신")
    logger.info(f"  파일명     : {image.filename}")
    logger.info(f"  Content-Type: {image.content_type}")
    logger.info(f"  파일 크기  : {len(image_bytes):,} bytes ({len(image_bytes)/1024:.1f} KB)")
    logger.info("=" * 50)

    # ===== 실제 TRELLIS 변환 코드 (주석 해제 시 동작) =====
    # pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    # logger.info(f"  이미지 해상도: {pil_image.size}")
    #
    # outputs = pipeline.run(
    #     pil_image,
    #     seed=1,
    #     sparse_structure_sampler_params={"steps": 12, "cfg_strength": 7.5},
    #     slat_sampler_params={"steps": 12, "cfg_strength": 3.0},
    # )
    #
    # glb = outputs["mesh"][0].export_glb()
    # logger.info("3D 변환 완료 - GLB 파일 반환")
    # return Response(content=glb, media_type="application/octet-stream",
    #     headers={"Content-Disposition": "attachment; filename=output.glb"})
    # =====================================================

    # 현재: 더미 응답 반환
    logger.info("더미 응답 반환 (실제 변환 미실행)")
    return JSONResponse(content={
        "success": True,
        "message": "TRELLIS 서버가 요청을 받았습니다 (Mock 모드)",
        "filename": image.filename,
        "size_bytes": len(image_bytes),
    })
