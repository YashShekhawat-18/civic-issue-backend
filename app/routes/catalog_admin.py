"""Create / edit / deactivate departments and categories.

The list routes (GET /departments and GET /categories) already exist from Phase 3.
These extra routes use the same URL prefixes.
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_roles
from app.core.responses import success_response
from app.models.user import Role
from app.schemas.admin import CategoryCreate, CategoryUpdate, DepartmentCreate, DepartmentUpdate
from app.services import catalog_admin_service

admin_only = Depends(require_roles(Role.ADMIN))

departments_router = APIRouter(prefix="/departments", tags=["Departments"])
categories_router = APIRouter(prefix="/categories", tags=["Categories"])


# ---------- departments ----------

@departments_router.post("", status_code=201, summary="Create a department (admin)")
async def create_department(data: DepartmentCreate, admin: dict = admin_only):
    department = await catalog_admin_service.create_department(actor=admin, data=data)
    return success_response("Department created", department, status_code=201)


@departments_router.get("/{department_id}", summary="One department")
async def get_department(department_id: str, current_user: dict = Depends(get_current_user)):
    return success_response("Department fetched", await catalog_admin_service.get_department(department_id, current_user))


@departments_router.patch("/{department_id}", summary="Edit a department (admin)")
async def update_department(department_id: str, data: DepartmentUpdate, admin: dict = admin_only):
    department = await catalog_admin_service.update_department(actor=admin, department_id=department_id, data=data)
    return success_response("Department updated", department)


@departments_router.delete("/{department_id}", summary="Deactivate a department (admin)")
async def deactivate_department(department_id: str, admin: dict = admin_only):
    department = await catalog_admin_service.deactivate_department(actor=admin, department_id=department_id)
    return success_response("Department deactivated", department)


# ---------- categories ----------

@categories_router.post("", status_code=201, summary="Create a category (admin)")
async def create_category(data: CategoryCreate, admin: dict = admin_only):
    category = await catalog_admin_service.create_category(actor=admin, data=data)
    return success_response("Category created", category, status_code=201)


@categories_router.get("/{category_id}", summary="One category")
async def get_category(category_id: str, current_user: dict = Depends(get_current_user)):
    return success_response("Category fetched", await catalog_admin_service.get_category(category_id, current_user))


@categories_router.patch("/{category_id}", summary="Edit a category (admin)")
async def update_category(category_id: str, data: CategoryUpdate, admin: dict = admin_only):
    category = await catalog_admin_service.update_category(actor=admin, category_id=category_id, data=data)
    return success_response("Category updated", category)


@categories_router.delete("/{category_id}", summary="Deactivate a category (admin)")
async def deactivate_category(category_id: str, admin: dict = admin_only):
    category = await catalog_admin_service.deactivate_category(actor=admin, category_id=category_id)
    return success_response("Category deactivated", category)
