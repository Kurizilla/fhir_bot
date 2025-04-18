from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import JSONResponse
import os
import requests
import json
import time
import vertexai
from vertexai.preview.language_models import TextGenerationModel

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


@app.get("/patologicos-personales")
def get_patologicos_personales(subject: str):
    entries = fetch_questionnaire_responses(subject)
    results = []

    for entry in entries:
        resource = entry.get("resource", {})
        patologicos_items = [
            item for item in resource.get("item", [])
            if item.get("text", "").lower() == "patológicos personales"
        ]

        if not patologicos_items:
            continue

        for item in patologicos_items:
            preguntas = extract_items_structure(item.get("item", []))
            results.append({
                "fecha": resource.get("authored", "Fecha desconocida"),
                "estado": resource.get("status", "Desconocido"),
                "doctor_id": resource.get("author", {}).get("reference", "").replace("Practitioner/", ""),
                "paciente_id": resource.get("subject", {}).get("reference", "").replace("Patient/", ""),
                "preguntas": preguntas
            })

    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron antecedentes patológicos personales")
    
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

@app.get("/condiciones")
def get_conditions(subject: str):
    print("🔍 Parámetro recibido:", subject)

    patient_id = subject.replace("Patient/", "")
    for candidate in [subject, patient_id]:
        print("➡️ Probando con subject:", candidate)

        response = requests.get(
            f"{FHIR_STORE_PATH}/Condition",
            headers=HEADERS,
            params={"subject": candidate}
        )

        print("🔄 URL generada:", response.url)
        print("📥 Status:", response.status_code)
        print("📦 Raw Response:", response.text[:1000])  # corta por si es muy largo

        if response.status_code == 200:
            json_data = response.json()
            entries = json_data.get("entry", [])
            print("🧾 Entries encontradas:", len(entries))

            results = []
            for entry in entries:
                resource = entry.get("resource", {})
                condition_name = resource.get("code", {}).get("coding", [{}])[0].get("display", "Desconocida")
                condition_code = resource.get("code", {}).get("coding", [{}])[0].get("code", "")
                verification_status = resource.get("verificationStatus", {}).get("coding", [{}])[0].get("display", "Desconocido")
                recorded_date = resource.get("recordedDate", "Fecha no disponible")

                results.append({
                    "condicion": condition_name,
                    "codigo": condition_code,
                    "fecha_registro": recorded_date,
                    "estado": verification_status
                })

            if results:
                return JSONResponse(content=results)

    raise HTTPException(status_code=404, detail="No se encontraron condiciones clínicas registradas")

@app.get("/observaciones")
def get_observaciones(subject: str):
    print("🧪 Observaciones - subject recibido:", subject)

    # Probamos con y sin el prefijo Patient/
    for candidate in [subject, subject.replace("Patient/", "")]:
        print("🔄 Probando con subject:", candidate)
        response = requests.get(
            f"{FHIR_STORE_PATH}/Observation",
            headers=HEADERS,
            params={"subject": candidate}
        )
        print("🌐 URL:", response.url)
        print("📥 Status code:", response.status_code)
        print("📦 Body:", response.text[:1000])

        if response.status_code == 200:
            data = response.json()
            entries = data.get("entry", [])
            print(f"✅ Entradas encontradas: {len(entries)}")

            results = []
            for entry in entries:
                resource = entry.get("resource", {})
                components = resource.get("component", [])
                for comp in components:
                    code = comp.get("code", {}).get("text", "Observación sin nombre")
                    valor = None
                    unidad = None

                    if "valueQuantity" in comp:
                        valor = comp["valueQuantity"].get("value", "Desconocido")
                        unidad = comp["valueQuantity"].get("unit", "")
                    elif "valueString" in comp:
                        valor = comp["valueString"]
                        unidad = ""

                    referencia = comp.get("referenceRange", [{}])[0]
                    referencia_baja = referencia.get("low", {}).get("value")
                    referencia_alta = referencia.get("high", {}).get("value")

                    results.append({
                        "observacion": code,
                        "valor": valor,
                        "unidad": unidad,
                        "rango_referencia": {
                            "min": referencia_baja,
                            "max": referencia_alta
                        },
                        "fecha": resource.get("effectiveDateTime", "Fecha no disponible"),
                        "paciente_id": resource.get("subject", {}).get("reference", "").replace("Patient/", "")
                    })

            if results:
                return JSONResponse(content=results)

    raise HTTPException(status_code=404, detail="No se encontraron observaciones registradas")

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
def get_alergias(subject: str):
    print("🔍 Entrando a /alergias con:", subject)

    patient_id = subject.replace("Patient/", "")
    print("🧪 Buscando alergias para el paciente:", patient_id)

    response = requests.get(
        f"{FHIR_STORE_PATH}/AllergyIntolerance",
        headers=HEADERS,
        params={"patient": patient_id}
    )

    print("📡 FHIR status:", response.status_code)
    if response.status_code != 200:
        print("❌ Error FHIR:", response.text)
        raise HTTPException(status_code=response.status_code, detail="No se pudo obtener alergias")

    entries = response.json().get("entry", [])
    print(f"🔢 Se encontraron {len(entries)} registros")

    if not entries:
        raise HTTPException(status_code=404, detail="No se encontraron alergias registradas")

    results = []
    for entry in entries:
        resource = entry.get("resource", {})
        print("📦 Entrada:", json.dumps(resource, indent=2)[:400])  # print parcial

        status = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")
        verification = resource.get("verificationStatus", {}).get("coding", [{}])[0].get("code", "")

        if status != "active" or verification != "confirmed":
            print("⛔️ Alergia omitida (no activa o no confirmada)")
            continue

        code = resource.get("code", {}).get("coding", [{}])[0]
        reaction = resource.get("reaction", [{}])[0]

        results.append({
            "alergia_a": code.get("display", "Desconocido"),
            "codigo": code.get("code", ""),
            "categoria": resource.get("category", []),
            "descripcion_reaccion": reaction.get("description", ""),
            "manifestacion": reaction.get("manifestation", [{}])[0].get("coding", [{}])[0].get("display", ""),
            "severidad": reaction.get("severity", ""),
            "criticalidad": resource.get("criticality", ""),
            "fecha_registro": resource.get("recordedDate", "Fecha no disponible"),
            "paciente_id": resource.get("patient", {}).get("reference", "").replace("Patient/", "")
        })

    if not results:
        print("📭 No se encontraron alergias activas y confirmadas")
        raise HTTPException(status_code=404, detail="No se encontraron alergias registradas")

    return JSONResponse(content=results)

@app.get("/medicamentos")
def get_medication_requests(subject: str):
    print("📡 FHIR request para MedicationRequest con subject:", subject)

    response = requests.get(
        f"{FHIR_STORE_PATH}/MedicationRequest",
        headers=HEADERS,
        params={"subject": subject}
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="No se pudo obtener la información de medicamentos")

    bundle = response.json()
    entries = bundle.get("entry", [])

    results = []
    for entry in entries:
        resource = entry.get("resource", {})
        medicamento = resource.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "Desconocido")
        status = resource.get("status", "Desconocido")
        intent = resource.get("intent", "Desconocido")
        paciente_id = resource.get("subject", {}).get("reference", "").replace("Patient/", "")

        # Obtener instrucciones de dosis
        instrucciones = []
        for di in resource.get("dosageInstruction", []):
            instrucciones.append(di.get("text", ""))

        # Obtener razones
        razones = [r.get("display", "") for r in resource.get("reasonReference", [])]

        results.append({
            "medicamento": medicamento,
            "estado": status,
            "intencion": intent,
            "instrucciones": instrucciones,
            "razones": razones,
            "paciente_id": paciente_id
        })

    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron recetas de medicamentos")

    return JSONResponse(content=results)

@app.get("/antecedentes_familiares")
def get_family_history(subject: str):
    print("🔍 Entrando a /antecedentes_familiares con:", subject)

    patient_id = subject.replace("Patient/", "")
    response = requests.get(
        f"{FHIR_STORE_PATH}/FamilyMemberHistory",
        headers=HEADERS,
        params={"patient": patient_id}
    )

    print("📡 FHIR status:", response.status_code)
    if response.status_code != 200:
        print("❌ Error en FHIR:", response.text)
        raise HTTPException(status_code=response.status_code, detail="No se pudo obtener antecedentes familiares")

    entries = response.json().get("entry", [])
    print(f"🧾 Registros encontrados: {len(entries)}")

    if not entries:
        raise HTTPException(status_code=404, detail="No se encontraron antecedentes familiares")

    results = []

    for entry in entries:
        resource = entry.get("resource", {})
        print("📦 Entrada:", json.dumps(resource, indent=2)[:500])

        if resource.get("status") != "completed":
            print("⛔️ Omitido (status no es completed)")
            continue

        relationship = resource.get("relationship", {}).get("coding", [{}])[0].get("display", "Relación desconocida")
        patient_ref = resource.get("patient", {}).get("reference", "").replace("Patient/", "")

        for condition in resource.get("condition", []):
            cond_info = condition.get("code", {}).get("coding", [{}])[0]
            results.append({
                "paciente_id": patient_ref,
                "relacion": relationship,
                "condicion": cond_info.get("display", "Condición desconocida").strip(),
                "codigo": cond_info.get("code", "").strip(),
                "contribuyo_a_la_muerte": condition.get("contributedToDeath", False)
            })

    if not results:
        print("📭 No se encontraron antecedentes válidos")
        raise HTTPException(status_code=404, detail="No se encontraron antecedentes familiares válidos")

    print("✅ Respuesta final:", results)
    return JSONResponse(content=results)


@app.get("/health")
def health():
    return {"status": "ok"}
