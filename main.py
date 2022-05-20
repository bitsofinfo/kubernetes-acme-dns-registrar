import asyncio
import concurrent.futures
import copy
import os
import sys
from datetime import datetime, timedelta
from os.path import exists
from random import randint
from typing import Dict, List, Optional
from wsgiref.validate import validator
from xml.dom import ValidationErr
from xmlrpc.client import Boolean
import json

from core.security import *
from core.idp import *

from core import RegistrarService


from fastapi import FastAPI, Depends, Form
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials, utils

from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_404_NOT_FOUND

from pydantic import BaseModel, BaseSettings

from core.logging import LogService
from core.settings import SmartSettings
from core.health import HealthcheckService


import asyncio
class AppSettings(SmartSettings):
    KADR_APP_NAME:str = "kubernetes-acme-dns-registrar"
    KADR_OAUTH2_TOKEN_BASIC_AUTH_ENABLED:bool = True
    

logger = None
app = None
health_check_service = None
registrar_service = None


try:
    logger = LogService(__file__).logger

    app_settings = AppSettings()

    app = FastAPI()

    oauth2_token_url_security = HTTPBasic()
    
    jwt_service:JWTService = JWTService()
    idp_service:IdpService = DefaultIdpService()
    oauth2_service = OAuth2Service(jwt_service=jwt_service,idp_service=idp_service)
    registrar_service = RegistrarService()
    registrar_service.start()

    health_check_service:HealthcheckService = HealthcheckService(app, [registrar_service])

except:
    logger.error(f"bootstrap() FastAPI error: {str(sys.exc_info()[:2])}")




async def get_authorized_principal(request:Request) -> AuthorizedPrincipal:
    """
    Protects API endpoints, expects valid JWT Bearer tokens
    
    Note this is called from within FastAPI internals
    via the depends() mechanism. Any exception thrown
    here will be handled and marshalled to JSON by the 
    framework.. vs us doing it
    """
    try:
        authorization:str = request.headers.get("Authorization")
        scheme, param = utils.get_authorization_scheme_param(authorization)

        if not authorization or scheme.lower() != "bearer":
            raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
        request_audience = request.url.path
        if '/' in request_audience:
            parts = request_audience.split('/')
            request_audience = parts[0]
            if not request_audience and len(parts) > 1:
                request_audience = parts[1]
            request_audience = f"/{request_audience}/"
    
        # validate and decode the JWT payload from the token 
        jwt_payload:JWTPayload = await jwt_service.decode_validate_jwt_token(param, \
                expected_audience=f"{app_settings.KADR_APP_NAME}:{request_audience}", \
                expected_issuer=app_settings.KADR_APP_NAME)

        # lookup the principal
        authorized_principal:AuthorizedPrincipal = await idp_service.get_authorized_principal(jwt_payload.sub)

        return authorized_principal

    except Exception as e:
        error_id = str(uuid.uuid4())
        status_code = HTTP_500_INTERNAL_SERVER_ERROR
        headers = {"X-KADR-ERROR-ID": error_id}
        detail = str(sys.exc_info()[:2])

        if isinstance(e,HTTPException):
            status_code = e.status_code
            detail += " " + e.detail

        if isinstance(e,JWTError):
            status_code = HTTP_401_UNAUTHORIZED

        if isinstance(e,AuthorizedPrincipalNotFoundError):
            status_code = HTTP_401_UNAUTHORIZED

        message = f"get_authorized_principal() error: {status_code} {detail} {error_id}"
        #logger.exception(message)
        
        raise HTTPException(
                status_code=status_code,
                detail=detail,
                headers=headers
            )

@app.get("/registrations")
async def get_registrations(invoking_principal:AuthorizedPrincipal=Depends(get_authorized_principal)):
    return await get_registrations(None,invoking_principal)

@app.get("/registrations/{name:path}")
async def get_registrations(name:Optional[str], \
                            invoking_principal:AuthorizedPrincipal=Depends(get_authorized_principal)):
    
    try:
        if not name:
            return await registrar_service.get_registration_store().get_all()
        else:

            registration = await registrar_service.get_registration_store().get_by_name(name)

            if not registration:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=f"{name} not found",
                    headers=None
                )

            return {name:registration}

    except HTTPException as e:
        raise e

    except Exception as e:
        error_id = str(uuid.uuid4())
        status_code = HTTP_500_INTERNAL_SERVER_ERROR
        headers = {"X-KADR-ERROR-ID": error_id}
        detail = str(sys.exc_info()[:2])
        logger.exception("get_registrations() unexpected error: {detail}")

        raise HTTPException(
            status_code=status_code,
            detail=detail,
            headers=headers
        )


def get_security_gate():
    """
    Returns a security gating function that should return 
    a set of basic auth credentials, or nothing if the 
    basic auth is not enabled. 
    """
    if app_settings.KADR_OAUTH2_TOKEN_BASIC_AUTH_ENABLED:
        return oauth2_token_url_security 
    else:
        return (lambda: None)
    


@app.post("/oauth2/token")
async def oauth2_token(scope:str=Form(...),\
                       grant_type:str=Form(...),\
                       client_id:Optional[str]=Form(None),\
                       client_secret:Optional[str]=Form(None), \
                       ba_credentials: HTTPBasicCredentials = Depends(get_security_gate())\
            ):
    """
    Handles OAuth2 client_credentials grant POSTs to get a token

    Note the client can must POST an form encoded body containing grant_type and scope
    which are required. 

    Depending on the AppSettings property KADR_OAUTH2_TOKEN_BASIC_AUTH_ENABLED
    if enabled, the client_id and client_secret must be passed as a Basic auth string. 

    if not enabled, the client_id and client_secret will be expected in the form body. 
    """

    try:
        # if BA enabled, transfer the values
        if (ba_credentials):
            client_id = ba_credentials.username
            client_secret = ba_credentials.password

        # formalize to a payload for the ClientCredentials request
        oauth2_token_payload:OAuth2TokenClientCredentialsRequest = \
            OAuth2TokenClientCredentialsRequest(scope=scope,grant_type=OAuth2GrantType(grant_type),\
                                                client_id=client_id,client_secret=client_secret)

        # let the oauth2servce handle processing of the request
        return await oauth2_service.process_token_request(oauth2_token_payload=oauth2_token_payload, \
                                issuer_id=app_settings.KADR_APP_NAME, \
                                audiences=[f"{app_settings.KADR_APP_NAME}:/registrations/"])  
                                              
    except Exception as err:
        message = f"oauth2_token() unexpected error: {str(sys.exc_info()[:2])}"
        logger.exception(message)
        return OAuth2ErrorResponse(error=OAuth2ErrorType.INVALID_REQUEST,error_description=message)


async def get_authorized_principal(request:Request) -> AuthorizedPrincipal:
    """
    Protects API endpoints, expects valid JWT Bearer tokens
    
    Note this is called from within FastAPI internals
    via the depends() mechanism. Any exception thrown
    here will be handled and marshalled to JSON by the 
    framework.. vs us doing it
    """
    try:
        authorization:str = request.headers.get("Authorization")
        scheme, param = utils.get_authorization_scheme_param(authorization)

        if not authorization or scheme.lower() != "bearer":
            raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"}
                )

        # validate and decode the JWT payload from the token 
        jwt_payload:JWTPayload = await jwt_service.decode_validate_jwt_token(param, \
                expected_audience=f"{app_settings.KADR_APP_NAME}:{request.url.path}", \
                expected_issuer=app_settings.KADR_APP_NAME)

        # lookup the principal
        authorized_principal:AuthorizedPrincipal = await idp_service.get_authorized_principal(jwt_payload.sub)

        return authorized_principal

    except Exception as e:
        error_id = str(uuid.uuid4())
        status_code = HTTP_500_INTERNAL_SERVER_ERROR
        headers = {"X-KADR-ERROR-ID": error_id}
        detail = str(sys.exc_info()[:2])

        if isinstance(e,HTTPException):
            status_code = e.status_code
            detail += " " + e.detail

        if isinstance(e,JWTError):
            status_code = HTTP_401_UNAUTHORIZED

        if isinstance(e,AuthorizedPrincipalNotFoundError):
            status_code = HTTP_401_UNAUTHORIZED

        message = f"get_authorized_principal() error: {status_code} {detail} {error_id}"
        #logger.exception(message)
        
        raise HTTPException(
                status_code=status_code,
                detail=detail,
                headers=headers
            )
