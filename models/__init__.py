# models/__init__.py
from .home_model import HomeImage
from .service_model import ServiceContent
from .about_model import AboutUs
from .file_model import FileRecord
from .news_model import News
from .industry_model import Industry
from .solution_model import Solution
from .category_model import Category
from .product_model import RobotProduct, SportProduct


__all__ = [
    "HomeImage",
    "ServiceContent",
    "AboutUs",
    "FileRecord",
    "News",
    "Industry",
    "Solution",
    "Category"
    ,"RobotProduct", "SportProduct"
]