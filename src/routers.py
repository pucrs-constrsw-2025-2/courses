from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Body, HTTPException, Query, status
import httpx

from database import course_collection
from models import (
    CourseCreate, CourseInDB, CourseUpdate, 
    Material, MaterialBase, MaterialUpdate,
    Modality, ClassDTO
)
from config import settings

router = APIRouter()

# === Helper para chamada à API externa ===
async def fetch_classes_from_api(class_ids: List[str], semester: Optional[int], year: Optional[int]) -> List[ClassDTO]:
    if not class_ids:
        return []
    
    params = {"ids": ",".join(class_ids)}
    if semester:
        params["semester"] = semester
    if year:
        params["year"] = year
        
    async with httpx.AsyncClient() as client:
        try:
            # Assumindo que a API externa tem um endpoint /classes/by-ids
            url = f"{settings.CLASSES_API_BASE_URL}/classes/by-ids"
            response = await client.get(url, params=params)
            response.raise_for_status()
            return [ClassDTO(**item) for item in response.json()]
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            # Em um app real, seria bom ter um log aqui
            print(f"Error fetching classes: {e}")
            return []


# === Course Endpoints ===
@router.post("/courses", response_model=CourseInDB, status_code=status.HTTP_201_CREATED)
async def create_course(course: CourseCreate):
    """Cria um novo curso."""
    course_dict = course.model_dump()
    result = await course_collection.insert_one(course_dict)
    new_course = await course_collection.find_one({"_id": result.inserted_id})
    return new_course

@router.get("/courses", response_model=List[CourseInDB])
async def list_courses(name: Optional[str] = None, modality: Optional[Modality] = None):
    """Lista cursos, com filtros opcionais por nome ou modalidade."""
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if modality:
        query["modality"] = modality.value
    
    courses = await course_collection.find(query).to_list(100)
    return courses

@router.get("/courses/{id}", response_model=CourseInDB)
async def get_course(id: str):
    """Busca um curso pelo seu ID."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail=f"Invalid ID: {id}")
    course = await course_collection.find_one({"_id": ObjectId(id)})
    if course is None:
        raise HTTPException(status_code=404, detail=f"Course with ID {id} not found")
    return course

@router.put("/courses/{id}", response_model=CourseInDB)
async def update_course(id: str, course: CourseCreate):
    """Atualiza um curso completamente (substituição)."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail=f"Invalid ID: {id}")
    
    update_result = await course_collection.replace_one({"_id": ObjectId(id)}, course.model_dump())
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Course with ID {id} not found")
    
    updated_course = await course_collection.find_one({"_id": ObjectId(id)})
    return updated_course

@router.patch("/courses/{id}", response_model=CourseInDB)
async def partial_update_course(id: str, course: CourseUpdate):
    """Atualiza parcialmente um curso."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail=f"Invalid ID: {id}")
        
    update_data = course.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_result = await course_collection.update_one(
        {"_id": ObjectId(id)}, {"$set": update_data}
    )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Course with ID {id} not found")
    
    updated_course = await course_collection.find_one({"_id": ObjectId(id)})
    return updated_course
    
@router.delete("/courses/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(id: str):
    """Deleta um curso."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail=f"Invalid ID: {id}")
    delete_result = await course_collection.delete_one({"_id": ObjectId(id)})
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Course with ID {id} not found")

# === Material Sub-resource Endpoints ===
@router.post("/courses/{id}/materials", response_model=Material, status_code=status.HTTP_201_CREATED)
async def add_material_to_course(id: str, material: MaterialBase):
    """Adiciona um novo material a um curso."""
    new_material = Material(**material.model_dump())

    # Converte o objeto do material para um dicionário pronto para o MongoDB
    material_dict = new_material.model_dump()
    material_dict['url'] = str(material_dict['url']) # CONVERTE A URL PARA STRING

    update_result = await course_collection.update_one(
        {"_id": ObjectId(id)},
        {"$push": {"materials": material_dict}} # USA O DICIONÁRIO CORRIGIDO
    )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Course with ID {id} not found")
    return new_material

@router.get("/courses/{id}/materials", response_model=List[Material])
async def get_materials_from_course(id: str, name: Optional[str] = None):
    """Lista os materiais de um curso, com filtro opcional por nome."""
    course = await get_course(id) # Reutiliza a função de busca
    materials = course.get("materials", [])
    if name:
        return [m for m in materials if name.lower() in m["name"].lower()]
    return materials

@router.get("/courses/{id}/materials/{material_id}", response_model=Material)
async def get_material_from_course(id: str, material_id: str):
    """Busca um material específico de um curso."""
    course = await get_course(id)
    for material in course["materials"]:
        if material["id"] == material_id:
            return material
    raise HTTPException(status_code=404, detail=f"Material with ID {material_id} not found in course {id}")

@router.put("/courses/{id}/materials/{material_id}", response_model=Material)
async def update_material_in_course(id: str, material_id: str, material: MaterialBase):
    """Atualiza um material de um curso completamente."""
    update_result = await course_collection.update_one(
        {"_id": ObjectId(id), "materials.id": material_id},
        {"$set": {"materials.$.name": material.name, "materials.$.url": str(material.url)}}
    )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Material or Course not found")
    return Material(id=material_id, **material.model_dump())

@router.patch("/courses/{id}/materials/{material_id}", response_model=Material)
async def partial_update_material_in_course(id: str, material_id: str, material: MaterialUpdate):
    """Atualiza um material de um curso parcialmente."""
    update_data = material.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # SE a url estiver sendo atualizada, converta-a para string
    if 'url' in update_data and update_data['url'] is not None:
        update_data['url'] = str(update_data['url'])

    mongo_update_fields = {f"materials.$.{key}": value for key, value in update_data.items()}

    update_result = await course_collection.update_one(
        {"_id": ObjectId(id), "materials.id": material_id},
        {"$set": mongo_update_fields}
    )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Material or Course not found")
    
    # Retorna o estado atualizado
    return await get_material_from_course(id, material_id)


@router.delete("/courses/{id}/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material_from_course(id: str, material_id: str):
    """Deleta um material de um curso."""
    update_result = await course_collection.update_one(
        {"_id": ObjectId(id)},
        {"$pull": {"materials": {"id": material_id}}}
    )
    if update_result.modified_count == 0:
        raise HTTPException(status_code=404, detail=f"Material or Course not found")

# === Class Sub-resource Endpoints ===

@router.get("/courses/{id}/classes", response_model=List[ClassDTO])
async def get_classes_from_course(id: str, semester: Optional[int] = Query(None), year: Optional[int] = Query(None)):
    """Busca as turmas de um curso, consultando uma API externa e aplicando filtros."""
    course = await get_course(id)
    class_ids = course.get("classes", [])
    
    # Chama o serviço externo para obter detalhes das turmas
    classes = await fetch_classes_from_api(class_ids, semester, year)
    return classes