from fastapi import APIRouter, Depends, HTTPException,Query
from sqlalchemy.orm import Session
from ..dependencies.db import get_db
from ..models.core import User,Profile
from ..schemas.user import UserCreate, UserUpdate,ProfileCreate,ProfileUpdate,UserResponse,ProfileResponse

router = APIRouter(prefix="/users",tags=["users"])

@router.get("",response_model=list[UserResponse])
async def get_users(ids:list[int]=Query(None),db:Session=Depends(get_db)):
    query=db.query(User)
    if ids:
        query=query.filter(User.id.in_(ids))
    return query.all()
    
@router.get("/{user_id}",response_model=ProfileResponse)
async def get_user(user_id:int,db:Session=Depends(get_db)):
    user=db.query(Profile).filter(Profile.id==user_id).first()
    if not user:
        raise HTTPException(status_code=404,detail="User not found")
    return user