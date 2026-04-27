import os
import re
import logging
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db  # 你的数据库连接
from apscheduler.schedulers.background import BackgroundScheduler



# 自动扫描所有目录用 os.walk 递归遍历 uploads 下所有文件夹， about/news/robot 等，还有根目录的图片。
# URL 格式完全匹配生成的 URL 是 /uploads/news/xxx.png
# 支持视频清理正则同时匹配 <img> 和 <video> 标签，ALLOWED_EXTENSIONS 里加上了 mp4/avi/mov，视频也能一起清理。
# 可排除目录EXCLUDE_DIRS 可以加不想清理的文件夹，比如 videos 目录不想删，就加进去，脚本会自动跳过。

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("image_cleaner")

# ======================【配置项】======================
# 根上传目录
UPLOAD_ROOT = "/uploads"
# 只清理这些后缀（可按需加）
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "mp4", "avi", "mov"}
# 排除不清理的文件夹（比如 videos 不想删就加这里）
EXCLUDE_DIRS = {"videos"}


# ======================================================


def extract_images_from_html(html: str):
    """从富文本中提取所有 img/video 的 src URL"""
    if not html:
        return []

    # 匹配 img 标签
    img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
    # 匹配 video 标签
    video_pattern = re.compile(r'<video[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)

    imgs = img_pattern.findall(html)
    videos = video_pattern.findall(html)

    return imgs + videos


def get_all_used_images(db: Session):
    """从所有业务表中提取正在使用的图片/视频 URL"""
    used_resources = set()

    # ======================【你要修改的部分】======================
    # 示例：根据你的业务表添加
    # 1. 产品表（robot）
    products = db.execute(text("SELECT detail FROM product")).fetchall()
    for p in products:
        used_resources.update(extract_images_from_html(p.detail))

    # 2. 新闻表（news）
    news = db.execute(text("SELECT content FROM news")).fetchall()
    for n in news:
        used_resources.update(extract_images_from_html(n.content))

    # 3. 行业表（industry）
    industries = db.execute(text("SELECT content FROM industry")).fetchall()
    for i in industries:
        used_resources.update(extract_images_from_html(i.content))

    # 4. 解决方案表（solution）
    solutions = db.execute(text("SELECT content FROM solution")).fetchall()
    for s in solutions:
        used_resources.update(extract_images_from_html(s.content))

    # 5. 关于我们（about）
    about = db.execute(text("SELECT content FROM about")).fetchall()
    for a in about:
        used_resources.update(extract_images_from_html(a.content))
    # =============================================================

    return used_resources


def get_all_local_resources():
    """递归扫描 uploads 目录下所有文件，生成完整 URL"""
    all_resources = set()

    for root, dirs, files in os.walk(UPLOAD_ROOT):
        # 排除不需要扫描的目录
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            ext = file.split(".")[-1].lower()
            if ext in ALLOWED_EXTENSIONS:
                # 本地完整路径
                full_path = os.path.join(root, file)
                # 转换成 URL 格式（/uploads/xxx/yyy.png）
                url_path = full_path.replace(UPLOAD_ROOT, "").replace("\\", "/")
                url_path = f"{UPLOAD_ROOT}{url_path}"
                all_resources.add(url_path)

    return all_resources


def clean_unused_resources():
    """清理未使用的图片/视频（主函数）"""
    logger.info(f"【资源清理任务】开始执行 → {datetime.now()}")

    # 1. 获取数据库连接
    db: Session = next(get_db())

    # 2. 获取正在使用的资源
    used_resources = get_all_used_images(db)
    logger.info(f"正在使用的资源数量：{len(used_resources)}")

    # 3. 获取本地所有资源
    local_resources = get_all_local_resources()
    logger.info(f"本地资源数量：{len(local_resources)}")

    # 4. 找出未使用的
    unused = local_resources - used_resources
    logger.info(f"未使用资源数量：{len(unused)}")

    # 5. 删除文件
    delete_count = 0
    for resource_url in unused:
        try:
            # 把 URL 转成真实路径
            file_path = resource_url.replace(UPLOAD_ROOT, "")
            file_path = os.path.join(UPLOAD_ROOT, file_path.lstrip("/"))

            if os.path.exists(file_path):
                os.remove(file_path)
                delete_count += 1
                logger.info(f"已删除：{file_path}")
        except Exception as e:
            logger.error(f"删除失败：{resource_url} → {str(e)}")

    logger.info(f"【资源清理任务】执行完成，共删除 {delete_count} 个资源\n")
    return delete_count


# ======================【定时任务】======================
def start_resource_clean_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

    # 每周一凌晨 3 点执行（生产环境推荐）
    scheduler.add_job(clean_unused_resources, "cron", day_of_week=1, hour=3)

    # 测试用：每分钟执行一次（打开即可测试）
    # scheduler.add_job(clean_unused_resources, "interval", minutes=1)

    scheduler.start()
    logger.info("✅ 资源定时清理任务已启动")