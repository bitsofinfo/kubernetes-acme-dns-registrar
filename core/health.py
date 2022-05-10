from typing import Optional, Dict, List
from fastapi import FastAPI, Depends
from fastapi_health import health
from pydantic import BaseModel
from abc import ABC, abstractmethod

class HealthcheckResult(BaseModel):
    success:bool = False
    message:str 
    details:Optional[object]

class HealthcheckParticipant(ABC):
    @abstractmethod
    def get_check_health_functions(self) -> List[callable]:
        pass

class HealthcheckService():

    async def success_handler(self, **results):
        return results

    async def failure_handler(self, **results):
        return results 

    def __init__(self, app:FastAPI, participants:List[HealthcheckParticipant]):

        conditions:List[callable] = []
        for p in participants:
            conditions.extend(p.get_check_health_functions())

        print(conditions)

        app.add_api_route("/health", health(conditions, \
                                     success_handler=self.success_handler, \
                                     failure_handler=self.failure_handler))
