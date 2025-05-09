# app/models/response_models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union

class AllergyEntry(BaseModel):
    alergia_a: str
    codigo: Optional[str] = None
    categoria: Optional[List[str]] = []
    descripcion_reaccion: Optional[str] = None
    manifestacion: Optional[str] = None
    severidad: Optional[str] = None
    criticalidad: Optional[str] = None
    fecha_registro: str
    estado_clinico: Optional[str] = None
    estado_verificacion: Optional[str] = None
    paciente_id: str

class MedicamentoEntry(BaseModel):
    medicamento: str
    estado: str
    intencion: str
    instrucciones: Optional[List[str]] = []
    razones: Optional[List[str]] = []
    paciente_id: str

class CondicionEntry(BaseModel):
    condicion: str
    codigo: Optional[str] = None
    fecha_registro: str
    estado: Optional[str] = None

class ObservacionEntry(BaseModel):
    observacion: str
    valor: Optional[Union[str, float]] = None
    unidad: Optional[str] = None
    rango_referencia: Dict[str, Optional[float]] = Field(default_factory=lambda: {"min": None, "max": None})
    fecha: str
    paciente_id: str

class FamilyHistoryEntry(BaseModel):
    paciente_id: str
    relacion: str
    condicion: str
    codigo: Optional[str] = None
    contribuyo_a_la_muerte: bool

class PreguntaRespuesta(BaseModel):
    pregunta: str
    respuestas: List[str]

class CuestionarioRespuesta(BaseModel):
    fecha: str
    estado: str
    doctor_id: str
    paciente_id: str
    preguntas: List[PreguntaRespuesta]

class ResumenDisponibilidad(BaseModel):
    patient_id: str
    nombre: str
    genero: str
    edad: str
    recursos_disponibles: Dict[str, List[str]]

class CuestionarioResumenIA(BaseModel):
    cuestionario_resumen: str
