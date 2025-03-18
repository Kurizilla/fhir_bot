import functions_framework
import requests
import google.auth
from google.auth.transport.requests import Request
from flask import jsonify, request

# Definir URLs de las APIs de FHIR
FHIR_PATIENT_API_URL = "https://healthcare.googleapis.com/v1/projects/g-stg-gsv000-tlmd-erp-prj-6fe2/locations/us-east1/datasets/stg-medicalpractice/fhirStores/mp-fhir/fhir/Patient"
FHIR_QUESTIONNAIRE_RESPONSE_API_URL = "https://healthcare.googleapis.com/v1/projects/g-stg-gsv000-tlmd-erp-prj-6fe2/locations/us-east1/datasets/stg-medicalpractice/fhirStores/mp-fhir/fhir/QuestionnaireResponse"

# Obtener credenciales automáticamente desde Google
credentials, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-healthcare"])

def get_access_token():
    credentials.refresh(Request())
    return credentials.token

def extract_patient_data(resource):
    """
    Extrae la información relevante de un paciente y la devuelve en el formato solicitado.
    """
    nombre = resource.get("name", [{}])[0].get("text", "Desconocido")
    contacto = [{"value": t.get("value", ""), "system": t.get("system", "")} for t in resource.get("telecom", []) if t.get("value")]
    documentos = [{"value": i.get("value", ""), "display": i.get("type", {}).get("coding", [{}])[0].get("display", "Desconocido")} for i in resource.get("identifier", []) if i.get("value")]
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

def extract_determinants(entry):
    """
    Extrae únicamente los determinantes socioambientales del recurso QuestionnaireResponse.
    """
    resource = entry.get("resource", {})
    socio_items = [item for item in resource.get("item", []) if item.get("text", "").lower() == "determinantes socioambientales"]

    if not socio_items:
        return None
    
    parsed_questions = []
    def extract_items(items, prefix=""):
        for item in items:
            question = prefix + item.get("text", "Pregunta desconocida")
            if "answer" in item:
                answers = [str(answer[list(answer.keys())[0]]) for answer in item["answer"]]
                parsed_questions.append(f"{question}: {', '.join(answers)}")
            if "item" in item:
                extract_items(item["item"], prefix=question + " -> ")
    
    for socio_item in socio_items:
        extract_items(socio_item.get("item", []))
    
    doctor_id = resource.get("author", {}).get("reference", "").replace("Practitioner/", "")
    patient_id = resource.get("subject", {}).get("reference", "").replace("Patient/", "")
    
    return {
        "questions": parsed_questions,
        "doctor": doctor_id,
        "patient": patient_id,
        "date": resource.get("authored", "Fecha desconocida"),
        "status": resource.get("status", "Desconocido")
    }

@functions_framework.http
def format_fhir_patient(request):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    patient_id = request.args.get("patient_id")
    if not patient_id:
        return jsonify({"error": "Se requiere el parámetro 'patient_id'"}), 400
    response = requests.get(f"{FHIR_PATIENT_API_URL}/{patient_id}", headers=headers)
    if response.status_code != 200:
        return jsonify({"error": "No se pudo obtener la información del paciente"}), response.status_code
    patient_data = extract_patient_data(response.json())
    return jsonify(patient_data)

@functions_framework.http
def format_fhir_socioenvironmental_determinants(request):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    subject = request.args.get("subject")
    if not subject:
        return jsonify({"error": "Se requiere el parámetro 'subject'"}), 400
    response = requests.get(FHIR_QUESTIONNAIRE_RESPONSE_API_URL, headers=headers, params={"subject": subject})
    if response.status_code != 200:
        return jsonify({"error": "No se pudo obtener la respuesta de FHIR"}), response.status_code
    data = response.json()
    socio_data = [extract_determinants(entry) for entry in data.get("entry", [])]
    socio_data = [entry for entry in socio_data if entry]
    if not socio_data:
        return jsonify({"error": "No se encontraron determinantes socioambientales"}), 404
    return jsonify(socio_data)
