import requests

url = "http://localhost:8080/webhook/set/meubot"
headers = {
    "apikey": "1234",
    "Content-Type": "application/json"
}
payload = {
    "enabled": True,
    "url": "http://api:8000/webhook",
    "webhook_by_events": False,
    "events": ["MESSAGES_UPSERT"]
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())


#http://host.docker.internal:8000/webhook