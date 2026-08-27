"""JWT auth with api_key fallback."""
from __future__ import annotations
import os, time
from typing import Optional
from fastapi import Depends, HTTPException, Header, Request
try:
    import jwt  # PyJWT
    _has_jwt=True
except: _has_jwt=False

SECRET=os.getenv("JWT_SECRET") or os.getenv("KITE_API_SECRET") or "dev-secret-change-me"
API_KEY=os.getenv("API_KEY","")
ALGO="HS256"

def create_token(sub: str, exp_min: int=60)->str:
    if not _has_jwt: return f"dummy-{sub}"
    payload={"sub":sub,"exp":int(time.time())+exp_min*60,"iat":int(time.time())}
    return jwt.encode(payload, SECRET, algorithm=ALGO)

def verify_token(token: str)->Optional[dict]:
    if not _has_jwt: return {"sub":"user"} if token else None
    try: return jwt.decode(token, SECRET, algorithms=[ALGO])
    except: return None

async def jwt_or_api_key(request: Request, authorization: Optional[str]=Header(None), x_api_key: Optional[str]=Header(None)):
    # allow api_key fallback
    if API_KEY and (x_api_key==API_KEY or request.query_params.get("api_key")==API_KEY):
        return {"sub":"api_key"}
    if not authorization: raise HTTPException(401,"Missing Authorization")
    token=authorization.replace("Bearer ","").strip()
    data=verify_token(token)
    if not data: raise HTTPException(401,"Invalid token")
    return data

def protect_premium(depends=Depends(jwt_or_api_key)): return depends
