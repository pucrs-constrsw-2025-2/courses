from fastapi import FastAPI
from routers import router as course_router

app = FastAPI(
    title="Courses API",
    description="API para gerenciar cursos, materiais e turmas.",
    version="1.0.0"
)

# Inclui o roteador de cursos
app.include_router(course_router, tags=["Courses"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Courses API!"}