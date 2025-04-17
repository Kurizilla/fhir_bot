import os
import requests

# Ensure that GS_APIKEY is loaded correctly
if not os.getenv("GS_APIKEY"):
    print("Error: GS_APIKEY is not set. Make sure direnv is loaded.")
    exit(1)

# Base URL for the FHIR Store
FHIR_STORE_PATH = "https://api-dev.fhir.goes.gob.sv/v1/r4"

# Headers including API key from environment variables
HEADERS = {
    "Accept": "application/json",
    "GS-APIKEY": os.getenv("GS_APIKEY"),
}

def access_fhir(resource_type: str, resource_id: str):
    """Access a FHIR resource via Apigee."""
    resource_url = f"{FHIR_STORE_PATH}/{resource_type}/{resource_id}"
    response = requests.get(resource_url, headers=HEADERS)

    if response.status_code != 200:
        print(f"Error: Failed to fetch {resource_type}/{resource_id}")
        print(f"Status Code: {response.status_code}")
        print("Response:", response.text)
        return None
    
    return response.json()

# Test the function with a Patient resource
if __name__ == "__main__":
    resource_type = "Patient"
    resource_id = "f3749563-bdcf-4c97-81a0-8b072a8ec4d3"
    
    print(f"Fetching {resource_type} with ID {resource_id}...\n")
    result = access_fhir(resource_type, resource_id)

    if result:
        print("FHIR Resource Response:")
        print(result)
