from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi import File, UploadFile
import uuid
from pydantic import BaseModel
from typing import List, Optional
import json

from src.ai_write_x.config.config import Config
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.tools.wx_publisher import pub2wx
from src.ai_write_x.utils import utils
from src.ai_write_x.utils import log


router = APIRouter(prefix="/api/articles", tags=["articles"])


class ArticleContentUpdate(BaseModel):
    content: str


class PublishRequest(BaseModel):
    article_paths: List[str]
    account_indices: List[int]
    platform: str = "wechat"


class ArticlePathRequest(BaseModel):
    path: str


class RetemplateRequest(BaseModel):
    path: str
    template_path: str


class HtmlImportRequest(BaseModel):
    html: str
    filename: str = ""
    action: str = "preview"
    title: str = ""
    template_name: str = ""
    template_category: str = "导入模板"


@router.get("/")
async def list_articles():
    """获取文章列表"""
    try:
        articles_dir = PathManager.get_article_dir()
        articles = []

        patterns = ["*.html", "*.md", "*.txt"]
        article_files = []

        for pattern in patterns:
            article_files.extend(articles_dir.glob(pattern))

        for file_path in article_files:
            stat = file_path.stat()
            title = file_path.stem.replace("_", "|")
            status = get_publish_status(title)
            meta = utils.load_article_meta(str(file_path))

            articles.append(
                {
                    "name": file_path.stem,
                    "path": str(file_path),
                    "title": title,
                    "format": file_path.suffix[1:].upper(),
                    "size": f"{stat.st_size / 1024:.2f} KB",
                    "create_time": datetime.fromtimestamp(stat.st_ctime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "status": status,
                    "use_template": meta.get("use_template", False),
                    "formatting_mode": meta.get("formatting_mode", "raw"),
                    "template_category": meta.get("template_category", ""),
                    "template_name": meta.get("template_name", ""),
                    "template_path": meta.get("template_path", ""),
                    "template_display": meta.get("template_display", "未记录模板"),
                }
            )

        articles.sort(key=lambda x: x["create_time"], reverse=True)
        return {"status": "success", "data": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content")
async def get_article_content(path: str):
    """获取文章内容 - 使用查询参数"""
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文章不存在")

    content = file_path.read_text(encoding="utf-8")
    return Response(content=content, media_type="text/plain; charset=utf-8")


@router.put("/content")
async def update_article_content(path: str, update: ArticleContentUpdate):
    """更新文章内容"""
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文章不存在")

    file_path.write_text(update.content, encoding="utf-8")
    return {"status": "success", "message": "文章已保存"}


@router.get("/preview")
async def preview_article(path: str):
    """安全预览文章 - 使用查询参数"""
    file_path = Path(path)
    if not file_path.exists():
        return HTMLResponse("<p>文章不存在</p>")

    content = file_path.read_text(encoding="utf-8")
    return HTMLResponse(
        content,
        headers={
            "Content-Security-Policy": "default-src 'self' 'unsafe-inline'; img-src 'self' data: https: http:; style-src 'self' 'unsafe-inline'"
        },
    )


@router.get("/media")
async def get_article_media(name: str):
    """读取一键优化后保存在本地的文章图片。"""
    from fastapi.responses import FileResponse
    from src.ai_write_x.utils.article_images import resolve_media_file

    try:
        file_path = resolve_media_file(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="图片不存在")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return FileResponse(file_path)


@router.post("/optimize-images")
async def optimize_images(request: ArticlePathRequest):
    """把文章中的外链和相对路径图片换成可预览的本地图片。"""
    from src.ai_write_x.utils.article_images import optimize_article_images

    file_path = Path(request.path)
    if not file_path.is_file() or file_path.suffix.lower() != ".html":
        raise HTTPException(status_code=400, detail="只能优化 HTML 文章中的图片")

    original = file_path.read_text(encoding="utf-8")
    updated, count = optimize_article_images(original, file_path.stem)
    if count:
        file_path.write_text(updated, encoding="utf-8")
    return {"status": "success", "replaced": count, "message": f"已优化 {count} 张图片"}


@router.post("/import-html")
async def import_html_article(request: HtmlImportRequest):
    """导入公众号 HTML：预览适配结果，或保存为文章/模板。"""
    from src.ai_write_x.utils.html_import import adapt_preview_html

    if not (request.html or "").strip():
        raise HTTPException(status_code=400, detail="HTML 内容为空")

    adapted = adapt_preview_html(request.html)
    title = (request.title or adapted["title"] or request.filename or "导入文章").strip()
    action = (request.action or "preview").strip()

    if action == "preview":
        return {
            "status": "success",
            "title": title,
            "article_html": adapted["article_html"],
            "template_html": adapted["template_html"],
        }

    if action == "article":
        article_dir = PathManager.get_article_dir()
        file_path = _unique_file(article_dir, utils.sanitize_filename(title), ".html")
        file_path.write_text(adapted["article_html"], encoding="utf-8")
        meta = {
            "use_template": False,
            "formatting_mode": "raw",
            "template_category": "",
            "template_name": "",
            "template_path": "",
            "template_display": "导入HTML",
        }
        utils.save_article_meta(str(file_path), meta)
        return {"status": "success", "message": f"已导入文章《{file_path.stem}》", "path": str(file_path)}

    if action == "template":
        category = (request.template_category or "导入模板").strip() or "导入模板"
        name = utils.sanitize_filename((request.template_name or title).strip() or "导入模板")
        template_dir = PathManager.get_template_dir() / category
        template_dir.mkdir(parents=True, exist_ok=True)
        file_path = _unique_file(template_dir, name, ".html")
        file_path.write_text(adapted["template_html"], encoding="utf-8")
        return {
            "status": "success",
            "message": f"已抽取模板 {category}/{file_path.stem}",
            "path": str(file_path),
        }

    raise HTTPException(status_code=400, detail="不支持的导入操作")


def _unique_file(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    index = 2
    while candidate.exists():
        candidate = directory / f"{stem}_{index}{suffix}"
        index += 1
    return candidate


@router.post("/retemplate")
async def retemplate_article(request: RetemplateRequest):
    """按当前文章内容填充到指定模板并保存。"""
    import asyncio
    from src.ai_write_x.core.base_framework import ContentResult, ContentType
    from src.ai_write_x.core.unified_workflow import UnifiedContentWorkflow
    from src.ai_write_x.utils.article_images import extract_article_text

    article_path = Path(request.path)
    template_path = Path(request.template_path)
    if not article_path.is_file():
        raise HTTPException(status_code=404, detail="文章不存在")
    if article_path.suffix.lower() != ".html":
        raise HTTPException(status_code=400, detail="只有 HTML 文章可以更换模板")
    if not template_path.is_file() or template_path.suffix.lower() != ".html":
        raise HTTPException(status_code=404, detail="模板不存在")

    original = article_path.read_text(encoding="utf-8")
    title, text = extract_article_text(original)
    if not text.strip():
        raise HTTPException(status_code=400, detail="文章没有可填充的正文")

    def fill():
        from src.ai_write_x.core.system_init import initialize_global_tools

        initialize_global_tools()
        config = Config.get_instance()
        previous = getattr(config, "forced_template_file", None)
        config.forced_template_file = str(template_path)
        try:
            workflow = UnifiedContentWorkflow()
            result = workflow._apply_template_formatting(
                ContentResult(
                    title=title or article_path.stem,
                    content=text,
                    summary="",
                    content_format="html",
                    content_type=ContentType.ARTICLE,
                )
            )
            return result.content, config.last_used_template or {}
        finally:
            config.forced_template_file = previous

    try:
        html, template_info = await asyncio.to_thread(fill)
    except Exception as exc:
        log.print_log(f"更换模板失败: {exc}", "error")
        raise HTTPException(status_code=500, detail=f"更换模板失败: {exc}")

    if not html or "<" not in html:
        raise HTTPException(status_code=500, detail="模板填充没有返回有效 HTML")

    article_path.write_text(html, encoding="utf-8")
    meta = utils.load_article_meta(str(article_path))
    meta.update(
        {
            "use_template": True,
            "formatting_mode": "template",
            "template_category": template_info.get("category", template_path.parent.name),
            "template_name": template_info.get("name", template_path.stem),
            "template_path": template_info.get("path", ""),
        }
    )
    meta["template_display"] = utils.format_template_display(meta)
    utils.save_article_meta(str(article_path), meta)
    return {"status": "success", "message": "已用新模板重新填充文章"}


@router.delete("/{article_path:path}")
async def delete_article(article_path: str):
    """删除文章"""
    file_path = Path(article_path)
    if file_path.exists():
        file_path.unlink()
        utils.delete_article_sidecars(article_path)
        return {"status": "success", "message": "文章已删除"}
    raise HTTPException(status_code=404, detail="文章不存在")


@router.post("/publish")
async def publish_articles(request: PublishRequest):
    """发布文章到平台"""
    try:
        config = Config.get_instance()
        credentials = config.wechat_credentials

        if not credentials:
            raise HTTPException(status_code=400, detail="未配置微信账号")

        success_count = 0
        fail_count = 0
        error_details = []
        warning_details = []
        format_publish = config.format_publish

        for article_path in request.article_paths:
            file_path = Path(article_path)
            if not file_path.exists():
                fail_count += 1
                error_details.append(f"{article_path}: 文件不存在")
                continue

            content = file_path.read_text(encoding="utf-8")

            ext = file_path.suffix.lower()

            try:
                if ext == ".html":
                    title, digest = utils.extract_html(content)
                elif ext == ".md":
                    title, digest = utils.extract_markdown_content(content)
                elif ext == ".txt":
                    title, digest = utils.extract_text_content(content)
                else:
                    fail_count += 1
                    error_details.append(f"{article_path}: 不支持的文件格式 {ext}")
                    continue
            except Exception as e:
                fail_count += 1
                error_details.append(f"{article_path}: 内容提取失败 - {str(e)}")
                continue

            if title is None:
                fail_count += 1
                error_details.append(f"{article_path}: 标题提取失败，无法发布")
                continue

            for account_index in request.account_indices:
                if account_index >= len(credentials):
                    continue

                cred = credentials[account_index]
                try:
                    article_to_publish = content
                    if ext != ".html" and format_publish:
                        article_to_publish = utils.get_format_article(ext, content)

                    message, _, success = pub2wx(
                        title=title,
                        digest=digest,
                        article=article_to_publish,
                        appid=cred["appid"],
                        appsecret=cred["appsecret"],
                        author=cred.get("author", ""),
                        cover_path=utils.get_cover_path(article_path),
                    )

                    if success:
                        success_count += 1
                        # 如果message包含权限回收提示,添加到warning_details
                        if message and "草稿箱" in message:
                            warning_details.append(f"{cred.get('author', '未命名')}: {message}")

                        save_publish_record(
                            article_path=article_path,
                            platform="wechat",
                            account_info={
                                "appid": cred["appid"],
                                "author": cred.get("author", ""),
                                "account_type": "wechat_official",
                            },
                            success=True,
                            error=message if "草稿箱" in message else None,
                        )
                    else:
                        fail_count += 1
                        save_publish_record(
                            article_path=article_path,
                            platform="wechat",
                            account_info={
                                "appid": cred["appid"],
                                "author": cred.get("author", ""),
                                "account_type": "wechat_official",
                            },
                            success=False,
                            error=message,
                        )

                except Exception as e:
                    fail_count += 1
                    error_msg = str(e)
                    save_publish_record(
                        article_path=article_path,
                        platform="wechat",
                        account_info={
                            "appid": cred["appid"],
                            "author": cred.get("author", ""),
                            "account_type": "wechat_official",
                        },
                        success=False,
                        error=error_msg,
                    )
                    error_details.append(f"{cred.get('author', '未命名')}: {error_msg}")

        return {
            "status": "success" if success_count > 0 else "error",
            "success_count": success_count,
            "fail_count": fail_count,
            "warning_details": warning_details,
            "error_details": error_details,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_publish_status(title: str) -> str:
    """获取文章发布状态"""
    records_file = PathManager.get_article_dir() / "publish_records.json"
    if not records_file.exists():
        return "unpublished"

    try:
        records = json.loads(records_file.read_text(encoding="utf-8"))
        article_records = records.get(title, [])

        if not article_records:
            return "unpublished"

        latest = max(article_records, key=lambda x: x.get("timestamp", ""))
        return "published" if latest.get("success") else "failed"
    except Exception:
        return "unpublished"


def save_publish_record(
    article_path: str, platform: str, account_info: dict, success: bool, error: Optional[str]
):
    """保存发布记录 - 新的通用格式"""
    records_file = PathManager.get_article_dir() / "publish_records.json"

    title = Path(article_path).stem.replace("_", "|")

    records = {}
    if records_file.exists():
        try:
            records = json.loads(records_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if title not in records:
        records[title] = []

    records[title].append(
        {
            "timestamp": datetime.now().isoformat(),
            "platform": platform,
            "success": success,
            "error": error,
            "account_info": account_info,
        }
    )

    records_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/platforms")
async def get_supported_platforms():
    """获取支持的发布平台列表"""
    config = Config.get_instance()

    platforms = []

    # 微信公众号
    wechat_credentials = config.wechat_credentials or []
    if wechat_credentials:
        platforms.append(
            {
                "id": "wechat",
                "name": "微信公众号",
                "icon": "wechat",
                "accounts": [
                    {
                        "index": idx,
                        "author": cred.get("author", "未命名"),
                        "appid": cred["appid"],
                        "full_info": f"{cred.get('author', '未命名')} ({cred['appid']})",
                    }
                    for idx, cred in enumerate(wechat_credentials)
                ],
            }
        )

    # 未来可扩展其他平台
    # if config.other_platform_credentials:
    #     platforms.append({...})

    return {"status": "success", "data": platforms}


@router.get("/publish-history/{article_path:path}")
async def get_publish_history(article_path: str):
    """获取文章发布历史"""
    records_file = PathManager.get_article_dir() / "publish_records.json"

    title = Path(article_path).stem.replace("_", "|")

    if not records_file.exists():
        return {"status": "success", "data": {"article_path": article_path, "records": []}}

    try:
        records = json.loads(records_file.read_text(encoding="utf-8"))
        article_records = records.get(title, [])

        sorted_records = sorted(article_records, key=lambda x: x.get("timestamp", ""), reverse=True)

        return {
            "status": "success",
            "data": {"article_path": article_path, "records": sorted_records},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ArticleDesign(BaseModel):
    article: str
    html: str
    css: str
    cover: Optional[str] = ""


@router.post("/design")
async def save_article_design(design: ArticleDesign):
    """保存文章设计(包括封面)"""
    try:
        article_path = Path(design.article)
        design_path = article_path.with_suffix(".design.json")

        design_data = {"html": design.html, "css": design.css, "cover": design.cover}  # 保存封面

        with open(design_path, "w", encoding="utf-8") as f:
            json.dump(design_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": "设计已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/design")
async def load_article_design(article: str):
    """加载文章设计(包括封面)"""
    try:
        article_path = Path(article)
        design_path = article_path.with_suffix(".design.json")

        if not design_path.exists():
            return {"html": "", "css": "", "cover": ""}

        with open(design_path, "r", encoding="utf-8") as f:
            design_data = json.load(f)

        return {
            "html": design_data.get("html", ""),
            "css": design_data.get("css", ""),
            "cover": design_data.get("cover", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-image")
async def upload_image(image: UploadFile = File(...)):
    """上传图片并返回路径"""
    try:
        # 获取图片保存目录
        image_dir = PathManager.get_image_dir()

        # 生成唯一文件名
        file_ext = Path(image.filename).suffix or ".jpg"
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = image_dir / unique_filename

        # 保存图片
        with open(file_path, "wb") as f:
            content = await image.read()
            f.write(content)

        # 返回相对路径(用于 HTML src 属性)
        relative_path = f"/images/{unique_filename}"

        return {"status": "success", "path": relative_path, "filename": unique_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images")
async def get_images():
    """获取已上传的图片列表"""
    try:
        image_dir = PathManager.get_image_dir()
        images = []

        # 支持的图片格式
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

        for file_path in image_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                images.append({"filename": file_path.name, "path": f"/images/{file_path.name}"})

        return images
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
