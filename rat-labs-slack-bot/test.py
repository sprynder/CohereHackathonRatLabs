import requests
import json

inputs = {"inputs":["Good morning everyone, I hope you had a chance to review the materials on plant propagation that I sent out last week. I'm going to give a quick overview of the process now, and then we'll move on to assigning individual tasks related to DNA sequencing.", "Sure thing, professor. I've been looking forward to learning more about plant propagation.", "Great! So, plant propagation is the process of creating new plants from existing ones. There are several methods we can use, including sexual reproduction, which involves the exchange of genetic material between two parent plants, and asexual reproduction, which involves the creation of a new plant from a single parent plant."]}

jsonData = json.dumps(inputs)
print(type(jsonData))


response = requests.post('http://ratlabapi.augxaneeh3a3aze4.southcentralus.azurecontainer.io/sentiment', json=jsonData)

print("Status code: ", response.status_code)
print("Printing Entire Post Request")
print(response.json())