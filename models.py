import uuid
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl
from bson import ObjectId

# Helper para permitir que os modelos Pydantic trabalhem com o ObjectId do MongoDB
# VERSÃO CORRIGIDA PARA Pydantic v2+
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, _):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        # A nova versão do Pydantic espera que a função retorne um dicionário
        # em vez de modificar um argumento.
        return {"type": "string"}

class Modality(str, Enum):
    PRESENTIAL = "PRESENTIAL"
    ONLINE = "ONLINE"

# === Material Models ===
class MaterialBase(BaseModel):
    name: str = Field(..., min_length=3)
    url: HttpUrl

class Material(MaterialBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class MaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3)
    url: Optional[HttpUrl] = None


# === Course Models ===
class CourseBase(BaseModel):
    name: str = Field(..., min_length=3)
    credits: int = Field(..., ge=0)
    modality: Modality
    description: Optional[str] = None

class CourseCreate(CourseBase):
    pass # Não há campos extras além dos que já estão em CourseBase

class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3)
    credits: Optional[int] = Field(None, ge=0)
    modality: Optional[Modality] = None
    description: Optional[str] = None

class CourseInDB(CourseBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    materials: List[Material] = []
    classes: List[str] = []

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        
# === DTO for External API ===
class ClassDTO(BaseModel):
    id: str
    name: str
    semester: int
    year: int