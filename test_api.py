import requests
import time

url = "http://localhost:8000/api/generate"
data = {
    "jd_url": "https://elizabethnorman.com/jobs/data-strategy-manager-in-london-jid-72a3",
    "company_url": "https://elizabethnorman.com/about",
    "target_tone": "Strategic (Default)"
}

print("Starting generation...")
t0 = time.time()
try:
    with open("test.pdf", "rb") as f:
        files = {"resume": ("test.pdf", f, "application/pdf")}
        response = requests.post(url, data=data, files=files, timeout=120)
        
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
         res_json = response.json()
         print("Cover letter length:", len(res_json.get("cover_letter", "")))
    else:
         print("Response:", response.text)
except requests.exceptions.Timeout:
    print("API completely timed out after 120 seconds!")
except Exception as e:
    print("Error:", e)

print(f"Elapsed: {time.time() - t0:.2f}s")
