import requests
import json

inputs = {"inputs":[
"Hey everyone, just a reminder that the team meeting is at 10am tomorrow in the conference room.",
"Can someone please send me the budget proposal that was sent out last week?",
"I'd like to propose a new project to the team. Who is available to discuss this with me in a meeting tomorrow?",
"Great job on the presentation yesterday, team! I received a lot of positive feedback.",
"Please make sure to submit your time sheets by the end of the day today.",
"I just wanted to share some updates on the sales numbers for Q2. We exceeded our targets by 10%!",
"Does anyone have any ideas for the company's holiday party? I'm looking for suggestions.",
"I'm getting reports of some issues with the new software rollout. Can someone investigate and report back to the team?",
"I'd like to schedule a meeting with the HR team to discuss the new benefits package. Who is available on Friday at 2pm?",
"I'm going to be out of the office for the rest of the week for a family emergency. Can someone please follow up on the Johnson account in my absence?",
"Great news! The new marketing campaign has resulted in a 20% increase in website traffic.",
"Can someone please send me the latest version of the project timeline?",
"I'm looking for volunteers to help with the charity fundraiser next month. Please let me know if you're interested in helping out.",
"I'd like to schedule a team building activity for next week. Any suggestions?",
"Please make sure to review the updated company policies that were sent out yesterday."
],
"query": "des règles"}

jsonData = json.dumps(inputs)

response = requests.post('http://ratlabsapi.h8gcaad5bvcvfnfv.eastus.azurecontainer.io/search', json=inputs)

print("Status code: ", response.status_code)
print("Printing Entire Post Request")
print(response.json())