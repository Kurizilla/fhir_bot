# app/models/response_models.py

from pydantic import BaseModel
from typing import List, Optional, Dict

class AllergyEntry(BaseModel):
    alergia_a: str
    codigo: str
    categoria: List[str]
    descripcion_reaccion: Optional[str]
    manifestacion: Optional[str]
    severidad: Optional[str]
    criticalidad: Optional[str]
    fecha_registro: str
    estado_clinico: Optional[str]
    estado_verificacion: Optional[str]
    paciente_id: str

class MedicamentoEntry(BaseModel):
    medicamento: str
    estado: str
    intencion: str
    instrucciones: List[str]
    razones: List[str]
    paciente_id: str

class CondicionEntry(BaseModel):
    condicion: str
    codigo: str
    fecha_registro: str
    estado: str

class ObservacionEntry(BaseModel):
    observacion: str
    valor: Optional[str]
    unidad: Optional[str]
    rango_referencia: Dict[str, Optional[float]]
    fecha: str
    paciente_id: str

class FamilyHistoryEntry(BaseModel):
    paciente_id: str
    relacion: str
    condicion: str
    codigo: str
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
