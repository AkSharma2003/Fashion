from app.core.db import SessionLocal
from app.modules.auth.repository import (RoleRepository, StaffUserRepository)

def test_role_repository():
    db = SessionLocal()
    
    try:
        repo=RoleRepository(db)
        roles=repo.list_active_roles()
        assert isinstance(roles,list)
    finally:
        db.close()
        
def test_staff_user_repository():
    db = SessionLocal()
    
    try:
        repo=StaffUserRepository(db)
        users=repo.get_active_staff_users()
        assert isinstance(users,list)
    finally:
        db.close()

