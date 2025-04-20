from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import JSONResponse
import os
import requests
import json
import time
import vertexai
from vertexai.preview.language_models import TextGenerationModel
from vertexai.preview.generative_models import GenerativeModel
from datetime import datetime
from fastapi import Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from models.response_models import (
    AllergyEntry,
    MedicamentoEntry,
    CondicionEntry,
    ObservacionEntry,
    FamilyHistoryEntry,
    PreguntaRespuesta,
    CuestionarioRespuesta,
    ResumenDisponibilidad,
    CuestionarioResumenIA,
)

from utils.fhir_utils import (
    access_fhir,
    extract_patient_data,
    extract_questionnaire_section,
    extract_conditions,
    extract_observaciones,
    extract_allergies,
    extract_medications,
    extract_disponibilidad_resumen,
    extract_banderas_rojas,
    extract_family_history,
)
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

parameters_medlm = {
    "candidate_count": 1,
    "max_output_tokens": 1000,
    "temperature": 0.1,
    "top_k": 40,
    "top_p": 0.80,
}

def initialize_vertex_ai():
    vertexai.init(project=os.getenv("MEDLM_PROJECT"), location="us-central1")


app = FastAPI()

FHIR_STORE_PATH = "https://api-qa.fhir.goes.gob.sv/v1/r4/"
HEADERS = {
    "Accept": "application/json",
    "GS-APIKEY": os.getenv("GS_APIKEY")
}

print("🔐 Loaded API Key:", HEADERS["GS-APIKEY"])  # Solo para debug temporal


@app.get("/patient", response_model=Dict)
def get_patient(patient_id: str):
    resource = access_fhir("Patient", patient_id)
    return extract_patient_data(resource)

@app.get("/prevention", response_model=List[CuestionarioRespuesta])
def get_prevention(patient: str):
    return extract_questionnaire_section(patient, "variables prevención")

@app.get("/patologicos-personales", response_model=List[CuestionarioRespuesta])
def get_patologicos_personales(patient: str):
    return extract_questionnaire_section(patient, "patológicos personales")

@app.get("/determinants", response_model=List[CuestionarioRespuesta])
def get_determinants(patient: str):
    return extract_questionnaire_section(patient, "determinantes socioambientales")

@app.get("/condiciones", response_model=List[CondicionEntry])
def get_conditions(patient: str):
    return extract_conditions(patient)

@app.get("/observaciones", response_model=List[ObservacionEntry])
def get_observaciones(patient: str):
    return extract_observaciones(patient)

@app.post("/medlm_query")
def medlm_query(payload: dict = Body(...)):
    prompt = payload.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Falta el campo 'prompt'.")

    initialize_vertex_ai()
    model = TextGenerationModel.from_pretrained("medlm-medium")

    for attempt in range(3):
        try:
            result = model.predict(prompt=prompt, **parameters_medlm)
            return {"response": result.text}
        except Exception as e:
            wait = 0.5 * (2**attempt)
            time.sleep(wait)
            if attempt == 2:
                raise HTTPException(status_code=500, detail="Error interno al usar MedLM")

@app.get("/alergias", response_model=List[AllergyEntry])
def get_alergias(patient: str):
    return extract_allergies(patient)

@app.get("/medicamentos", response_model=List[MedicamentoEntry])
def get_medications(patient: str):
    return extract_medications(patient)

@app.get("/disponibilidad_recursos", response_model=ResumenDisponibilidad)
def disponibilidad_recursos(patient_id: str = Query(..., description="ID del paciente")):
    return extract_disponibilidad_resumen(patient_id)

@app.get("/banderas_rojas", response_model=CuestionarioResumenIA)
def banderas_rojas(patient_id: str = Query(..., description="ID del paciente")):
    return extract_banderas_rojas(patient_id)

@app.get("/antecedentes_familiares", response_model=List[FamilyHistoryEntry])
def get_family_history(patient: str):
    return extract_family_history(patient)

@app.get("/health")
def health():
    return {"status": "ok"}
