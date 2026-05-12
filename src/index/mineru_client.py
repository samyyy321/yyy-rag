import io
import time
import zipfile
from pathlib import Path

import requests
from loguru import logger

from src.core.config import get_settings


settings = get_settings()


async def parse_document(file_path: str) -> str:
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.MINERU_TOKEN}",
    }
    logger.info(f"MinerU解析请求头: {headers}")
    # 1. 申请上传 URL
    data = {
        "files": [
            {"name": file_path.name}
        ],
        "model_version": settings.MINERU_MODEL_VERSION,
    }

    logger.info(f"开始解析文档: {file_path.name}")

    response = requests.post(
        f"{settings.MINERU_API_URL}/file-urls/batch",
        headers=headers,
        json=data,
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()

    if result["code"] != 0:
        raise RuntimeError(f"申请上传地址失败: {result['msg']}")

    batch_id = result["data"]["batch_id"]
    upload_url = result["data"]["file_urls"][0]

    logger.info(f"获取上传地址成功: batch_id={batch_id}")

    # 2. 上传文件
    with open(file_path, "rb") as f:
        response = requests.put(
            upload_url,
            data=f,
            timeout=60,
        )

    response.raise_for_status()

    logger.info(f"文件上传成功: {file_path.name}")

    # 3. 等待解析
    while True:
        response = requests.get(
            f"{settings.MINERU_API_URL}/extract-results/batch/{batch_id}",
            headers={
                "Authorization": f"Bearer {settings.MINERU_TOKEN}"
            },
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        item = result["data"]["extract_result"][0]

        state = item["state"]
        logger.info(f"MinerU解析状态: {state}")

        if state == "done":
            zip_url = item["full_zip_url"]
            break

        if state == "failed":
            error = item.get("err_msg", "未知错误")
            logger.error(f"MinerU解析失败: {error}")
            raise RuntimeError(f"MinerU解析失败: {error}")

        time.sleep(settings.MINERU_POLL_INTERVAL)

    # 4. 下载结果
    logger.info("解析完成，开始下载结果")

    response = requests.get(
        zip_url,
        timeout=60,
    )
    response.raise_for_status()

    # 5. 读取 full.md
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        for name in z.namelist():
            if name.endswith("full.md"):
                markdown = z.read(name).decode("utf-8")
                logger.info(
                    f"Markdown提取成功: {file_path.name}, "
                    f"长度={len(markdown)}"
                )
                return markdown

    raise RuntimeError("MinerU解析结果中没有找到 full.md")