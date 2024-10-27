from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, Request, Form, HTTPException, Response, Cookie
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from jose import jwt,JWTError
from http import cookies

from app.models.models import User, Base, Bank, Transaction
from app.database import engine, get_db
from app.settings import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app = FastAPI()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
auth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
cookie = cookies.SimpleCookie()


async def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
            )
        return User(name=username)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
        )

async def get_current_user(token: str = Cookie(None)):
    token = cookie.get('access_token')
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Not authorized",
        )
    return verify_token(token.value)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register_user(request: Request, name: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.name == name))
        user = result.scalars().first()
        if user:
            raise HTTPException(status_code=400, detail="User already exists")

        hashed_password = await get_password_hash(password)
        new_user = User(name=name, hashed_password=hashed_password)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return templates.TemplateResponse("register.html", {
            "request": request,
            "message": "Registration successful!",
            "redirect": True  # Флаг для включения перенаправления
        })
    except Exception as e:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "message": f"An error occurred: {str(e)}"
        })

@app.get("/login", response_class=HTMLResponse)
async def get_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def log_in(response: Response, request: Request, name: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.name == name))
        user = result.scalars().first()
        if not user or not verify_password(password, user.hashed_password):
            return templates.TemplateResponse("login.html", {
                "request": request,
                "message": "Invalid credentials"
            })

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
                data={"sub": user.name}, expires_delta=access_token_expires
        )

        cookie['access_token'] = access_token

        return templates.TemplateResponse("login.html", {
            "request": request,
            "message": "Login successful!",
            "access_token": access_token,
            "redirect": True  # Флаг для включения перенаправления
        })
    except Exception as e:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "message": f"An error occurred: {str(e)}"
        })

# @app.get("/auth")
# async def read_auth(request: Request, current_user: User = Depends(get_current_user)):
#     return templates.TemplateResponse("auth.html", {
#             "request": request,
#             "message": "This is a protected route",
#             "redirect": True,
#         })

@app.get("/transaction", response_class=HTMLResponse)
async def transaction_form(request: Request, current_user: User = Depends(get_current_user)):
    token = cookie.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return templates.TemplateResponse("transaction.html", {
        "request": request, 
        "from_user": current_user.name,
    })

@app.post("/transaction", response_class=HTMLResponse)
async def create_transaction(request: Request, 
                            from_user: str = Form(...), 
                            to_user: str = Form(...), 
                            from_bank_name: str = Form(...), 
                            to_bank_name: str = Form(...), 
                            from_card_number: str = Form(...), 
                            to_card_number: str = Form(...),
                            transaction_amount: int = Form(...),
                            db: AsyncSession = Depends(get_db)):
    token = cookie.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token.value, SECRET_KEY, algorithms=[ALGORITHM])
        user_name: str = payload.get("sub")
        if user_name is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result_to = await db.execute(select(User).where(User.name == to_user))
    user_to = result_to.scalars().first()

    if not user_to or user_to == from_user:
        return templates.TemplateResponse("transaction.html", {
                "request": request,
                "message": "Invalid user send to"
            })

    from_bank = await db.execute(select(Bank).where(Bank.bank_name == from_bank_name))
    from_bank = from_bank.scalars().first()
    to_bank = await db.execute(select(Bank).where(Bank.bank_name == to_bank_name))
    to_bank = to_bank.scalars().first()

    if not from_bank or not to_bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    try:
        new_transaction = Transaction(
            from_user=from_user,
            to_user=user_to.name,
            from_bank=from_bank.id_bank,
            to_bank=to_bank.id_bank,
            from_card_number=from_card_number,
            to_card_number=to_card_number,
            transaction_amount=transaction_amount,
            transaction_time=datetime.utcnow(),
        )

        db.add(new_transaction)
        await db.commit()
        await db.refresh(new_transaction)

        return templates.TemplateResponse("transaction.html", {
            "request": request,
            "message": "Transaction created successfully!",
            "from_user": from_user
        })
    except Exception as e:
        return templates.TemplateResponse("transaction.html", {
            "request": request,
            "message": f"{str(e)}",
            "from_user": from_user
        })
