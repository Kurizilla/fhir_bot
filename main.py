from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import requests

app = FastAPI()

FHIR_STORE_PATH = "https://api-dev.fhir.goes.gob.sv/v1/r4"
HEADERS = {
    "Accept": "application/json",
    "GS-APIKEY": os.getenv("GS_APIKEY")
}


def access_fhir(resource_type: str, resource_id: str):
    resource_url = f"{FHIR_STORE_PATH}/{resource_type}/{resource_id}"
    response = requests.get(resource_url, headers=HEADERS)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Error al obtener {resource_type}/{resource_id}")
    return response.json()


def fetch_questionnaire_responses(subject: str):
    response = requests.get(
        f"{FHIR_STORE_PATH}/QuestionnaireResponse",
        headers=HEADERS,
        params={"subject": subject}
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error al obtener datos FHIR")
    return response.json().get("entry", [])


def extract_items_structure(item_list, prefix=""):
    results = []
    for item in item_list:
        text = item.get("text", "Pregunta desconocida")
        full_text = f"{prefix}{text}" if prefix else text
        answers = [str(answer.get(list(answer.keys())[0])) for answer in item.get("answer", [])]
        if answers:
            results.append({"pregunta": full_text, "respuestas": answers})
        if "item" in item:
            results.extend(extract_items_structure(item["item"], prefix=full_text + " -> "))
    return results


def extract_patient_data(resource):
    nombre = resource.get("name", [{}])[0].get("text", "Desconocido")
    contacto = [
        {"value": t.get("value", ""), "system": t.get("system", "")}
        for t in resource.get("telecom", []) if t.get("value")
    ]
    documentos = [
        {
            "value": i.get("value", ""),
            "display": i.get("type", {}).get("coding", [{}])[0].get("display", "Desconocido")
        }
        for i in resource.get("identifier", []) if i.get("value")
    ]
    direccion = resource.get("address", [{}])[0] if resource.get("address") else {}

    return {
        "nombre": nombre,
        "contacto": contacto,
        "documentos": documentos,
        "genero": resource.get("gender", "Desconocido"),
        "fecha_de_nacimiento": resource.get("birthDate", "Desconocida"),
        "direccion": direccion,
        "activo": resource.get("active", False)
    }


@app.get("/patient")
def get_patient(patient_id: str):
    resource = access_fhir("Patient", patient_id)
    return JSONResponse(content=extract_patient_data(resource))


@app.get("/prevention")
def get_prevention(subject: str):
    entries = fetch_questionnaire_responses(subject)
    results = []
    for entry in entries:
        resource = entry.get("resource", {})
        prevention_items = [item for item in resource.get("item", []) if item.get("text", "").lower() == "variables prevención"]
        if not prevention_items:
            continue
        for item in prevention_items:
            preguntas = extract_items_structure(item.get("item", []))
            results.append({
                "fecha": resource.get("authored", "Fecha desconocida"),
                "estado": resource.get("status", "Desconocido"),
                "doctor_id": resource.get("author", {}).get("reference", "").replace("Practitioner/", ""),
                "paciente_id": resource.get("subject", {}).get("reference", "").replace("Patient/", ""),
                "preguntas": preguntas
            })
    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron variables de prevención")
    return JSONResponse(content=results)


@app.get("/determinants")
def get_determinants(subject: str):
    entries = fetch_questionnaire_responses(subject)
    results = []
    for entry in entries:
        resource = entry.get("resource", {})
        determinant_items = [item for item in resource.get("item", []) if item.get("text", "").lower() == "determinantes socioambientales"]
        if not determinant_items:
            continue
        for item in determinant_items:
            preguntas = extract_items_structure(item.get("item", []))
            results.append({
                "fecha": resource.get("authored", "Fecha desconocida"),
                "estado": resource.get("status", "Desconocido"),
                "doctor_id": resource.get("author", {}).get("reference", "").replace("Practitioner/", ""),
                "paciente_id": resource.get("subject", {}).get("reference", "").replace("Patient/", ""),
                "preguntas": preguntas
            })
    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron determinantes socioambientales")
    return JSONResponse(content=results)


@app.get("/health")
def health():
    return {"status": "ok"}