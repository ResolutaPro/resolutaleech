import requests

url = "https://d300.userdrive.org:8443/d/3sj4nat42as5ln2377llftr5gbdfsw22kuaye5aw5t2n75ffobyskn3atr2m563gfoqqaghd/Onda.De.Viol%C3%AAncia.2025.720p.Dub.Filmesmp4.vip.mp4"

try:
    r = requests.head(url, timeout=10, allow_redirects=True)
    print(f"Status: {r.status_code}")
    print(f"Size: {r.headers.get('Content-Length', 'N/A')}")
    print(f"Type: {r.headers.get('Content-Type', 'N/A')}")
except Exception as e:
    print(f"Erro: {e}")
