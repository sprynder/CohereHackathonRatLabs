import requests
import json

inputs = {"inputs":["saydie sc=ucks"]}

jsonData = json.dumps(inputs)

response = requests.post('http://ratlabsapi.h8gcaad5bvcvfnfv.eastus2.azurecontainer.io/sentiment', json=inputs)

print("Status code: ", response.status_code)
print("Printing Entire Post Request")
print(response.json())