from fastapi import APIRouter
from app.api.routes import health, admin_users, admin_bases, chat, ingestion, payroll
from dotenv import load_dotenv

load_dotenv()

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(payroll.router, prefix="/payroll", tags=["payroll"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin-users"])
api_router.include_router(admin_bases.router, prefix="/admin/bases", tags=["admin-bases"])
