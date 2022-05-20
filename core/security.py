
from fastapi import FastAPI, Depends
from enum import Enum
from pydantic import BaseModel
from typing import Dict, List, Optional
from jose import JWTError, jwt
import uuid
from datetime import datetime, timedelta
import time
from .settings import SmartSettings
from .idp import IdpService
import sys
from .logging import LogService

logger = LogService(__file__).logger

class JWTSettings(SmartSettings):
    KADR_JWT_SECRET_KEY:str

class OAuth2GrantType(str, Enum):
    CLIENT_CREDENTIALS = 'client_credentials'

class OAuth2TokenType(str, Enum):
    BEARER = 'Bearer'

class OAuth2ErrorType(str, Enum):
    INVALID_REQUEST = 'invalid_request'
    INVALID_CLIENT = 'invalid_client'
    INVALID_GRANT = 'invalid_grant'
    INVALID_SCOPE = 'invalid_scope'
    UNAUTHORIZED_CLIENT = 'unauthorized_client'
    UNSUPPORTED_GRANT_TYPE = 'unsupported_grant_type'

    def __str__(self):
        str(self.value)

class OAuth2TokenClientCredentialsRequest(BaseModel):
    scope:Optional[str]
    grant_type:OAuth2GrantType = OAuth2GrantType.CLIENT_CREDENTIALS
    client_id:Optional[str]
    client_secret:Optional[str]

class OAuth2TokenResponse(BaseModel):
    access_token:str
    token_type:OAuth2TokenType
    expires_in:int # seconds
    refresh_token:Optional[str]
    scope:str

class OAuth2ErrorResponse(BaseModel):
    error:OAuth2ErrorType
    error_description:Optional[str]
    error_uri:Optional[str]

class JWTPayload(BaseModel):
    aud:List[str]  # audiences
    sub:str  # subject (i.e. the authorized principal)
    iss:str  # issuer identifier
    jti:Optional[str]  # unique id
    iat:Optional[int]   # issued at time (epoch)
    exp:Optional[int]  # expires at time (epoch)
    nbf:Optional[int]  # not before time (epoch)
    

class JWTService():
 
    def __init__(self):
        self.settings = JWTSettings()
        self.jwt_encoding_key = self.settings.get("KADR_JWT_SECRET_KEY")

    async def get_jwt_payload(self, subject_id:str, issuer_id:str, audiences:List[str]) -> JWTPayload:

        jwt_payload = JWTPayload(aud=audiences,sub=subject_id,iss=issuer_id)
        jwt_payload.jti = str(uuid.uuid4())
        jwt_payload.iat = int(time.time())
        jwt_payload.exp = int((datetime.now() + timedelta(minutes=60)).timestamp())
        jwt_payload.nbf = jwt_payload.iat

        return jwt_payload

    async def encode_jwt_payload(self, jwt_payload:JWTPayload) -> str:
        return jwt.encode(jwt_payload.dict(), self.jwt_encoding_key, algorithm="HS512")
        
    async def decode_validate_jwt_token(self, encoded_token:str, expected_issuer:str, expected_audience:str) -> JWTPayload:
        payload_dict = jwt.decode(encoded_token, self.jwt_encoding_key, \
                        algorithms="HS512", audience=expected_audience, \
                        issuer=expected_issuer, options={'verify_sub':False})
        return JWTPayload(**payload_dict)


class OAuth2Service():

    def __init__(self, idp_service:IdpService, jwt_service:JWTService):
        self.idp_service = idp_service
        self.jwt_service = jwt_service

    async def process_token_request(self, oauth2_token_payload:OAuth2TokenClientCredentialsRequest, 
                                          issuer_id:str, audiences:List[str]):
        try:
            # validate grant type
            try:
                OAuth2GrantType(oauth2_token_payload.grant_type) 
            except:
                logger.error(f"process_token_request() invalid grant_type passed or missing: {oauth2_token_payload.grant_type}")
                return OAuth2ErrorResponse(error=OAuth2ErrorType.INVALID_GRANT,error_description="Invalid grant_type or missing grant_type header")

            # authenticate the principal
            try:
                await self.idp_service.authenticate_principal(oauth2_token_payload.client_id, \
                                                              oauth2_token_payload.client_secret)
            except Exception as e:
                msg = str(sys.exc_info()[:2])
                logger.error(f"process_token_request() idp_service.authenticate_principal() {oauth2_token_payload.client_id}: {msg}")
                return OAuth2ErrorResponse(error=OAuth2ErrorType.UNAUTHORIZED_CLIENT,error_description=msg)

            jwt_payload:JWTPayload = await self.jwt_service.get_jwt_payload(subject_id=oauth2_token_payload.client_id,\
                                                                        issuer_id=issuer_id,\
                                                                        audiences=audiences)
            
            
            encoded_jwt_payload:str = await self.jwt_service.encode_jwt_payload(jwt_payload)
            expires_in:int = jwt_payload.exp - jwt_payload.iat

            logger.debug(f"process_token_request() success for: {oauth2_token_payload.client_id}")

            return OAuth2TokenResponse(access_token=encoded_jwt_payload,token_type=OAuth2TokenType.BEARER,expires_in=expires_in,scope="execute")

        except Exception as err:
            message = f"process_token_request() unexpected error: {str(sys.exc_info()[:2])}"
            logger.exception(message)
            return OAuth2ErrorResponse(error=OAuth2ErrorType.INVALID_REQUEST,error_description=message)