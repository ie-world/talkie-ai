from pydantic import BaseModel
from typing import Literal

class LearningRequest(BaseModel):
    type: Literal["word", "sentence"]

class LearningResponse(BaseModel):
    result: str