import requests
import yaml

url = "localhost/openapi.json"

response = requests.get(url)
response.raise_for_status()

openapi_schema = response.json()

with open("openapi_contract.yaml", "w") as file:
    yaml.dump(openapi_schema, file, sort_keys=False)

print("OpenAPI contract updated successfully.")