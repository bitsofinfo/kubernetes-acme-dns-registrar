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

from core import CNAMEService


from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Form
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials, utils
from pydantic import BaseModel, BaseSettings

from core.logging import LogService
from core.settings import SmartSettings
from core.health import HealthcheckService

class AppSettings(SmartSettings):
    KADR_APP_NAME:str = "kubernetes-acme-dns-registrar"
    

logger = None
app = None
health_check_service = None

try:
    logger = LogService(__file__).logger

    app_settings = AppSettings()

    app = FastAPI()

    oauth2_token_url_security = HTTPBasic()
    
    health_check_service:HealthcheckService = HealthcheckService(app, [])

    CNAMEService()

except:
    logger.error(f"bootstrap() FastAPI error: {str(sys.exc_info()[:2])}")


