import requests, json

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjdlZTRjMWM0NzA4NWFlNzRkYjA1Yzc2NjgwZTc1ZmMzNGNjNTg5MjRlMzE3ZGM1MTQxNTU4Y2U2ZGM2YTliMWVkMzE1ZGE3MTE2MDE5NzFhIn0.eyJhdWQiOiI4ZGU0MmI5NS1iOWEyLTQ2YmItOTJjYi1lMWE0ZmY2MTJiMmQiLCJqdGkiOiI3ZWU0YzFjNDcwODVhZTc0ZGIwNWM3NjY4MGU3NWZjMzRjYzU4OTI0ZTMxN2RjNTE0MTU1OGNlNmRjNmE5YjFlZDMxNWRhNzExNjAxOTcxYSIsImlhdCI6MTc3MzE1OTQxNywibmJmIjoxNzczMTU5NDE3LCJleHAiOjE5MzA3ODA4MDAsInN1YiI6IjcxNjY0NTgiLCJncmFudF90eXBlIjoiIiwiYWNjb3VudF9pZCI6Mjk1OTE1MDYsImJhc2VfZG9tYWluIjoiYW1vY3JtLnJ1IiwidmVyc2lvbiI6Miwic2NvcGVzIjpbInB1c2hfbm90aWZpY2F0aW9ucyIsImZpbGVzIiwiY3JtIiwiZmlsZXNfZGVsZXRlIiwibm90aWZpY2F0aW9ucyJdLCJoYXNoX3V1aWQiOiI3NTUwNTQ1MC0yOWFjLTRiNDItYmJiYS05NTJlM2M4MTQ3YWUiLCJhcGlfZG9tYWluIjoiYXBpLWIuYW1vY3JtLnJ1In0.DMgs897BxCbNsma7mdGEah2mwqeKwYd-csw7AxygfQcyqbRO62OimFuex0lKrQLAo4QoIAwqJszWwWOhO7ai0FhfeT0LP5gAu9deDZ-yVTSTzBkyR2ZwVNFTgi-kbzZO9n3byP1LCO00oaQY0C927u7n8P8SnDYaKhV6Vrw_pKRC2CjkXVrjgGi9tL3778ycKls1lknBSFcWrVssMfhL-O55EvWW5rYFXe94qiY9_ox_rUW0Csf6kIXemIdkjXa6Gz1LLHW7ZRBDGKYR7Vy0mMzk7Pjb1JxqR-9yC-Rja1FbRzoQEiG3lNgZWtPCot3a-vJI8FMHczOvU06YPFjO6A"
DOMAIN = "kiviclub.amocrm.ru"
headers = {"Authorization": f"Bearer {TOKEN}"}

# Воронки
r = requests.get(f"https://{DOMAIN}/api/v4/leads/pipelines", headers=headers)
print("=== PIPELINES ===")
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# Пользователи
r = requests.get(f"https://{DOMAIN}/api/v4/users", headers=headers)
print("=== USERS ===")
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

result = {}

r = requests.get(f"https://{DOMAIN}/api/v4/leads/pipelines", headers=headers)
result["pipelines"] = r.json()

r = requests.get(f"https://{DOMAIN}/api/v4/users", headers=headers)
result["users"] = r.json()

with open("amo_ids.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("Сохранено в amo_ids.json")