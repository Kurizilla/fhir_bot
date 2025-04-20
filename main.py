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


@app.get("/patient")
def get_patient(patient_id: str):
    resource = access_fhir("Patient", patient_id)
    return JSONResponse(content=extract_patient_data(resource))


@app.get("/prevention")
def get_prevention(patient: str):
    return JSONResponse(content=extract_questionnaire_section(patient, "variables prevención"))

@app.get("/patologicos-personales")
def get_patologicos_personales(patient: str):
    return JSONResponse(content=extract_questionnaire_section(patient, "patológicos personales"))

@app.get("/determinants")
def get_determinants(patient: str):
    return JSONResponse(content=extract_questionnaire_section(patient, "determinantes socioambientales"))

@app.get("/condiciones")
def get_conditions(patient: str):
    results = extract_conditions(patient)
    return JSONResponse(content=results)

@app.get("/observaciones")
def get_observaciones(patient: str):
    results = extract_observaciones(patient)
    return JSONResponse(content=results)

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
            return JSONResponse(content={"response": result.text})
        except Exception as e:
            wait = 0.5 * (2**attempt)
            time.sleep(wait)
            if attempt == 2:
                raise HTTPException(status_code=500, detail="Error interno al usar MedLM")

@app.get("/alergias")
def get_alergias(patient: str):
    return JSONResponse(content=extract_allergies(patient))

@app.get("/medicamentos")
def get_medications(patient: str):
    return JSONResponse(content=extract_medications(patient))

@app.get("/disponibilidad_recursos")
def disponibilidad_recursos(patient_id: str = Query(..., description="ID del paciente")):
    resumen = extract_disponibilidad_resumen(patient_id)
    return JSONResponse(content=resumen)

@app.get("/banderas_rojas")
def banderas_rojas(patient_id: str = Query(..., description="ID del paciente")):
    resumen = extract_banderas_rojas(patient_id)
    return JSONResponse(content=resumen)


@app.get("/antecedentes_familiares")
def get_family_history(patient: str):
    return JSONResponse(content=extract_family_history(patient))


@app.get("/health")
def health():
    return {"status": "ok"}
