from fastapi import HTTPException
import requests
from datetime import datetime
import os
import vertexai
from vertexai.preview.generative_models import GenerativeModel


parameters_medlm = {
    "candidate_count": 1,
    "max_output_tokens": 1000,
    "temperature": 0.1,
    "top_k": 40,
    "top_p": 0.80,
}

def initialize_vertex_ai():
    vertexai.init(project=os.getenv("MEDLM_PROJECT"), location="us-central1")


def gemini_query(prompt: str):
    try:
        initialize_vertex_ai()
        model = GenerativeModel("gemini-2.0-flash-001")
        response = model.generate_content(prompt)
        
        if hasattr(response, "text"):
            return response.text
        elif hasattr(response, "candidates"):
            return response.candidates[0].content.parts[0].text
        else:
            return "Respuesta desconocida de Gemini."

    except Exception as e:
        print("❌ Error al usar Gemini:", str(e))
        return "No se pudo generar resumen."

FHIR_STORE_PATH = "https://api-qa.fhir.goes.gob.sv/v1/r4/"
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

def fetch_questionnaire_responses(patient: str):
    response = requests.get(
        f"{FHIR_STORE_PATH}/QuestionnaireResponse",
        headers=HEADERS,
        params={"patient": patient}
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

def extract_questionnaire_section(patient: str, section_name: str):
    entries = fetch_questionnaire_responses(patient)
    results = []

    for entry in entries:
        resource = entry.get("resource", {})
        section_items = [
            item for item in resource.get("item", [])
            if item.get("text", "").lower() == section_name.lower()
        ]

        if not section_items:
            continue

        for item in section_items:
            preguntas = extract_items_structure(item.get("item", []))
            results.append({
                "fecha": resource.get("authored", "Fecha desconocida"),
                "estado": resource.get("status", "Desconocido"),
                "doctor_id": resource.get("author", {}).get("reference", "").replace("Practitioner/", ""),
                "paciente_id": resource.get("patient", {}).get("reference", "").replace("Patient/", ""),
                "preguntas": preguntas
            })

    if not results:
        raise HTTPException(status_code=404, detail=f"No se encontraron respuestas en el cuestionario para: {section_name}")

    return results

def extract_conditions(patient: str):
    patient_id = patient.replace("Patient/", "")
    for candidate in [patient, patient_id]:
        response = requests.get(
            f"{FHIR_STORE_PATH}/Condition",
            headers=HEADERS,
            params={"patient": candidate}
        )
        if response.status_code == 200:
            entries = response.json().get("entry", [])
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
            return results
    raise HTTPException(status_code=404, detail="No se encontraron condiciones clínicas registradas")

def extract_observaciones(patient: str):
    for candidate in [patient, patient.replace("Patient/", "")]:
        response = requests.get(
            f"{FHIR_STORE_PATH}/Observation",
            headers=HEADERS,
            params={"patient": candidate}
        )
        if response.status_code == 200:
            entries = response.json().get("entry", [])
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
                        "paciente_id": resource.get("patient", {}).get("reference", "").replace("Patient/", "")
                    })
            return results
    raise HTTPException(status_code=404, detail="No se encontraron observaciones registradas")

def extract_allergies(patient: str):
    patient_id = patient.replace("Patient/", "")
    print(f"🔑 Headers: {HEADERS}")
    response = requests.get(
        f"{FHIR_STORE_PATH}/AllergyIntolerance",
        headers=HEADERS,
        params={"patient": patient_id}
    )

    print("📥 FHIR response status:", response.status_code)
    print("📥 FHIR response body:", response.text)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="No se pudo obtener alergias")

    entries = response.json().get("entry", [])
    results = []
    for entry in entries:
        resource = entry.get("resource", {})
        status = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")
        verification = resource.get("verificationStatus", {}).get("coding", [{}])[0].get("code", "")
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
            "estado_clinico": status,
            "estado_verificacion": verification,
            "paciente_id": resource.get("patient", {}).get("reference", "").replace("Patient/", "")
        })
    
    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron alergias registradas")
    
    return results


def extract_medications(patient: str):
    response = requests.get(
        f"{FHIR_STORE_PATH}/MedicationRequest",
        headers=HEADERS,
        params={"patient": patient}
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="No se pudo obtener la información de medicamentos")

    entries = response.json().get("entry", [])
    results = []
    for entry in entries:
        resource = entry.get("resource", {})
        medicamento = resource.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "Desconocido")
        status = resource.get("status", "Desconocido")
        intent = resource.get("intent", "Desconocido")
        paciente_id = resource.get("patient", {}).get("reference", "").replace("Patient/", "")
        instrucciones = [di.get("text", "") for di in resource.get("dosageInstruction", [])]
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
    return results

def extract_family_history(patient: str):
    patient_id = patient.replace("Patient/", "")
    response = requests.get(
        f"{FHIR_STORE_PATH}/FamilyMemberHistory",
        headers=HEADERS,
        params={"patient": patient_id}
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="No se pudo obtener antecedentes familiares")

    entries = response.json().get("entry", [])
    results = []

    for entry in entries:
        resource = entry.get("resource", {})
        if resource.get("status") != "completed":
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
        raise HTTPException(status_code=404, detail="No se encontraron antecedentes familiares válidos")

    return results

def flatten_items(items, prefix=""):
    results = []
    for item in items:
        text = item.get("text", "Pregunta desconocida")
        full_text = f"{prefix}{text}" if prefix else text
        answers = item.get("answer", [])
        if answers:
            for ans in answers:
                value = next(iter(ans.values()), "")
                results.append(f"{full_text}: {value}")
        if "item" in item:
            results.extend(flatten_items(item["item"], prefix=full_text + " -> "))
    return results

def extract_disponibilidad_resumen(patient_id: str):
    resumen = {
        "patient_id": patient_id,
        "nombre": "Desconocido",
        "genero": "Desconocido",
        "edad": "Desconocida",
        "recursos_disponibles": {}
    }

    try:
        paciente = access_fhir("Patient", patient_id)
        resumen["nombre"] = paciente.get("name", [{}])[0].get("text", "Desconocido")
        resumen["genero"] = paciente.get("gender", "Desconocido")
        fecha_nacimiento = paciente.get("birthDate")
        if fecha_nacimiento:
            birth_date = datetime.strptime(fecha_nacimiento, "%Y-%m-%d")
            edad = (datetime.today() - birth_date).days // 365
            resumen["edad"] = f"{edad} años"
    except Exception as e:
        print(f"❌ Error obteniendo paciente: {e}")
        raise HTTPException(status_code=404, detail="No se encontró el recurso Patient o error en datos")

    try:
        resumen["recursos_disponibles"]["condiciones"] = [c["condicion"] for c in extract_conditions(f"Patient/{patient_id}")]
    except Exception as e:
        print(f"❌ Error en condiciones: {e}")
    
    try:
        resumen["recursos_disponibles"]["observaciones"] = [o["observacion"] for o in extract_observaciones(f"Patient/{patient_id}")]
    except Exception as e:
        print(f"❌ Error en observaciones: {e}")

    try:
        resumen["recursos_disponibles"]["alergias"] = extract_allergies(f"Patient/{patient_id}")
    except Exception as e:
        print(f"❌ Error en alergias: {e}")

    try:
        resumen["recursos_disponibles"]["medicamentos"] = [m["medicamento"] + f" ({m['estado']})" for m in extract_medications(f"Patient/{patient_id}")]
    except Exception as e:
        print(f"❌ Error en medicamentos: {e}")

    print("📦 Resumen generado:", resumen)
    return resumen


def extract_banderas_rojas(patient_id: str):
    entries = fetch_questionnaire_responses(f"Patient/{patient_id}")
    sorted_entries = sorted(entries, key=lambda e: e.get("resource", {}).get("authored", ""), reverse=True)
    latest_items = sorted_entries[0].get("resource", {}).get("item", []) if sorted_entries else []
    flatten_respuestas = flatten_items(latest_items) if latest_items else []
    observaciones = extract_observaciones(f"Patient/{patient_id}")
    observaciones_texto = [f"{o['observacion']}: {o['valor']} {o['unidad']}".strip() for o in observaciones]
    if not flatten_respuestas and not observaciones_texto:
        return {"cuestionario_resumen": "No se encontraron respuestas válidas ni observaciones clínicas."}
    texto_entrada = "\n".join(flatten_respuestas[:60])
    if observaciones_texto:
        texto_entrada += "\n\nAdemás, se registraron estas observaciones clínicas:\n" + "\n".join(observaciones_texto[:20])
    prompt = f"""A continuación se listan respuestas a un cuestionario clínico:

{texto_entrada}

Tu tarea es detectar y resumir únicamente las *banderas rojas* (hábitos de riesgo, enfermedades, condiciones crónicas o valores clínicos fuera de rango). No repitas todo. Sé conciso y directo."""
    resumen = gemini_query(prompt)
    return {"cuestionario_resumen": resumen}

def extract_dietary_habits(patient_id: str):
    clean_patient_id = patient_id.replace("Patient/", "")
    response = requests.get(
        f"{FHIR_STORE_PATH}/QuestionnaireResponse",
        headers=HEADERS,
        params={"subject": f"Patient/{clean_patient_id}"}
    )

    if response.status_code != 200:
        raise Exception("No se pudo obtener el QuestionnaireResponse")

    questionnaire_responses = response.json().get("entry", [])
    results = {
        "come_verduras": None,
        "frecuencia_verduras": None,
        "come_frutas": None,
        "frecuencia_frutas": None
    }

    for entry in questionnaire_responses:
        resource = entry.get("resource", {})
        items = resource.get("item", [])

        for section in items:
            if section.get("linkId") == "10001":  # Sección: Variables prevención
                for question in section.get("item", []):
                    link_id = question.get("linkId")

                    # Verduras
                    if link_id == "10021":
                        results["come_verduras"] = True
                        for subquestion in question.get("item", []):
                            if subquestion.get("linkId") == "10022":
                                answer = subquestion.get("answer", [{}])[0]
                                results["frecuencia_verduras"] = answer.get("valueInteger")

                    # Frutas
                    if link_id == "10023":
                        results["come_frutas"] = True
                        for subquestion in question.get("item", []):
                            if subquestion.get("linkId") == "10024":
                                answer = subquestion.get("answer", [{}])[0]
                                results["frecuencia_frutas"] = answer.get("valueInteger")

    return results


def extract_smoking_data(patient_id: str):
    clean_patient_id = patient_id.replace("Patient/", "")
    response = requests.get(
        f"{FHIR_STORE_PATH}/QuestionnaireResponse",
        headers=HEADERS,
        params={"subject": f"Patient/{clean_patient_id}"}
    )

    if response.status_code != 200:
        raise Exception("No se pudo obtener el QuestionnaireResponse")

    questionnaire_responses = response.json().get("entry", [])
    results = {
        "fuma": None,
        "anios_fumando": None,
        "cigarros_por_anio": None
    }

    for entry in questionnaire_responses:
        resource = entry.get("resource", {})
        items = resource.get("item", [])

        for section in items:
            if section.get("linkId") == "10001":  # Variables prevención
                for question in section.get("item", []):
                    if question.get("linkId") == "10012":  # ¿Fuma?
                        # Caso 2: viene valueBoolean directamente
                        fuma_answer = question.get("answer", [])
                        if fuma_answer and "valueBoolean" in fuma_answer[0]:
                            results["fuma"] = fuma_answer[0]["valueBoolean"]
                        else:
                            # Caso 3: evaluar existencia de subitems
                            subitems = question.get("item", [])
                            link_ids_presentes = [item.get("linkId") for item in subitems]

                            if "10013" in link_ids_presentes and "10104" in link_ids_presentes:
                                results["fuma"] = True  # aunque los answers estén vacíos

                            # Extraer valores de subitems
                            for subq in subitems:
                                if subq.get("linkId") == "10013":
                                    for ans in subq.get("answer", []):
                                        if "valueString" in ans:
                                            results["cigarros_por_anio"] = ans["valueString"]
                                if subq.get("linkId") == "10104":
                                    for ans in subq.get("answer", []):
                                        if "valueInteger" in ans:
                                            results["anios_fumando"] = ans["valueInteger"]

    return results

def extract_bmi(patient_id: str):
    clean_patient_id = patient_id.replace("Patient/", "")
    response = requests.get(
        f"{FHIR_STORE_PATH}/Observation",
        headers=HEADERS,
        params={"subject": f"Patient/{clean_patient_id}"}
    )

    if response.status_code != 200:
        raise Exception("No se pudo obtener el recurso Observation")

    entries = response.json().get("entry", [])
    bmi_observations = []

    for entry in entries:
        obs = entry.get("resource", {})
        codings = obs.get("code", {}).get("coding", [])

        for coding in codings:
            code = coding.get("code", "").lower()
            display = coding.get("display", "").lower()
            system = coding.get("system", "").lower()

            if code == "imc" or "masa corporal" in display or "body mass index" in display:
                bmi_observations.append(obs)
                break  # ya lo encontramos, no necesitamos ver más codings

    if not bmi_observations:
        return {"imc": None}

    latest = sorted(
        bmi_observations,
        key=lambda o: o.get("effectiveDateTime", ""),
        reverse=True
    )[0]

    imc_value = latest.get("valueQuantity", {}).get("value")

    if imc_value is None:
        for comp in latest.get("component", []):
            value_str = comp.get("valueString", "")
            try:
                imc_value = float(value_str.split()[0])
            except (ValueError, IndexError):
                imc_value = None

    return {"imc": imc_value}

import json

def extract_diabetes_status(patient_id: str):
    clean_patient_id = patient_id.replace("Patient/", "")
    response = requests.get(
        f"{FHIR_STORE_PATH}/QuestionnaireResponse",
        headers=HEADERS,
        params={"subject": f"Patient/{clean_patient_id}"}
    )

    if response.status_code != 200:
        raise Exception("No se pudo obtener el QuestionnaireResponse")

    questionnaire_responses = response.json().get("entry", [])
    results = {
        "diabetes": None,
        "tipo_diabetes": None
    }

    for entry in questionnaire_responses:
        resource = entry.get("resource", {})
        items = resource.get("item", [])

        for section in items:
            if section.get("linkId") == "10301":  # Patológicos personales
                for question in section.get("item", []):
                    if question.get("linkId") == "10302":  # ¿Tiene diabetes?
                        subitems = question.get("item", [])

                        if subitems and len(subitems) > 0:
                            results["diabetes"] = True  # ✅ PRIORIDAD MÁXIMA
                            for subq in subitems:
                                if subq.get("linkId") == "10303":  # ¿Sabe qué tipo?
                                    for ans in subq.get("answer", []):
                                        if "valueString" in ans:
                                            results["tipo_diabetes"] = ans["valueString"]
                            return results  # ✅ TERMINAMOS AQUÍ SI HAY SUBPREGUNTAS

                        # Solo si NO hay subpreguntas, se evalúa valueBoolean
                        answer = question.get("answer", [])
                        if answer and "valueBoolean" in answer[0]:
                            results["diabetes"] = answer[0]["valueBoolean"]

    return results




