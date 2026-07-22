"""Face OSINT v3 - age/gender/emotion, multi-engine reverse search, face compare."""
import os, re, asyncio
from pathlib import Path
import httpx
from utils.config import REQUEST_TIMEOUT

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

async def detect_faces(image_path: str) -> dict:
    path = str(Path(image_path).resolve())
    result = {"file": path, "faces": [], "face_count": 0, "demographics": []}
    if not Path(path).exists():
        result["error"] = "File not found"
        return result
    try:
        from deepface import DeepFace
        faces = DeepFace.extract_faces(img_path=path, detector_backend="mtcnn", enforce_detection=False)
        if faces and len(faces) > 0:
            result["face_count"] = len(faces)
            for idx, face in enumerate(faces):
                area = face.get("area", 0)
                confidence = face.get("confidence", 0)
                facial_area = face.get("facial_area", {})
                result["faces"].append({"index": idx, "confidence": round(float(confidence), 4), "facial_area": facial_area})
            try:
                analysis = DeepFace.analyze(img_path=path, actions=["age","gender","emotion","race"], detector_backend="mtcnn", enforce_detection=False, silent=True)
                if isinstance(analysis, list):
                    for a in analysis[:result["face_count"]]:
                        result["demographics"].append({
                            "age": a.get("age"), "gender": a.get("dominant_gender"),
                            "emotion": a.get("dominant_emotion"), "race": a.get("dominant_race"),
                        })
            except: pass
    except ImportError: result["error"] = "DeepFace not installed"
    except Exception as e: result["error"] = str(e)
    return result


async def compare_faces(img1: str, img2: str) -> dict:
    try:
        from deepface import DeepFace
        r = DeepFace.verify(img1_path=img1, img2_path=img2, detector_backend="mtcnn", enforce_detection=False, silent=True)
        return {"match": r.get("verified",False), "distance": round(float(r.get("distance",0)),4),
                "threshold": r.get("threshold",0), "model": r.get("model","")}
    except Exception as e: return {"error": str(e)}


async def yandex_reverse_search(image_path: str) -> dict:
    result = {"file": image_path, "results": [], "source": "Yandex"}
    if not Path(image_path).exists(): result["error"] = "File not found"; return result
    try:
        with open(image_path, "rb") as f: file_data = f.read()
        mime = "image/" + Path(image_path).suffix.lower().lstrip(".")
        files = {"upfile": (Path(image_path).name, file_data, mime)}
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers={"User-Agent":UA}, verify=False) as c:
            r = await c.post("https://yandex.com/images/search", files=files, data={"rpt":"imageview"}, follow_redirects=True)
            if r.status_code == 200:
                result["results_url"] = str(r.url)
                urls = re.findall(r'https?://[^"\']*img_url=[^"\']+', r.text)
                for u in urls[:20]:
                    try:
                        parsed = httpx.URL(u)
                        actual = dict(parsed.params).get("img_url","")
                        if actual:
                            result["results"].append({"url":actual,"source":"Yandex"})
                    except: continue
                links = re.findall(r'https?://[^"\'\s]+', r.text)
                for link in links[:30]:
                    domain = re.sub(r'^www\.','', httpx.URL(link).host or "")
                    if domain and domain not in ("yandex.com","yastatic.net",""):
                        if not any(rr["url"]==link for rr in result["results"]):
                            result["results"].append({"url":link,"source":domain})
    except Exception as e: result["error"] = str(e)
    return result


async def google_lens_search(image_path: str) -> dict:
    result = {"file": image_path, "results": [], "source": "Google Lens"}
    try:
        boundary = "----PrOSINTBoundary"
        with open(image_path, "rb") as f: data = f.read()
        body = f'--{boundary}\r\nContent-Disposition: form-data; name="encoded_image"; filename="{Path(image_path).name}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + data + f'\r\n--{boundary}--\r\n'.encode()
        headers = {"User-Agent": UA, "Content-Type": f"multipart/form-data; boundary={boundary}"}
        async with httpx.AsyncClient(timeout=30, headers=headers, verify=False, follow_redirects=True) as c:
            r = await c.post("https://lens.google.com/v3/upload", content=body)
            if r.status_code in (200, 302):
                result["results_url"] = str(r.url)
                if r.status_code == 200:
                    urls = re.findall(r'https?://[^\s"\'<>]+', r.text)
                    result["results"] = [{"url": u, "source": "Google Lens"} for u in urls if len(u)>20 and "google" not in u][:20]
    except Exception as e: result["error"] = str(e)
    return result


async def tineye_search(image_url: str) -> dict:
    result = {"source": "TinEye", "results": []}
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA}, verify=False) as c:
            r = await c.get(f"https://tineye.com/search?url={image_url}")
            if r.status_code == 200:
                urls = re.findall(r'https?://[^\s"\'<>]+', r.text)
                result["results"] = [{"url": u, "source": "TinEye"} for u in urls if "tineye" not in u and len(u)>30][:15]
    except: pass
    return result


async def face_search(image_path: str) -> dict:
    face_data = await detect_faces(image_path)
    if not face_data.get("faces"):
        return {"file": image_path, "faces_detected": 0, "detection_details": face_data, "reverse_search": {"error": "No faces"}}
    yandex_task = yandex_reverse_search(image_path)
    google_task = google_lens_search(image_path)
    yandex, google = await asyncio.gather(yandex_task, google_task)
    return {"file": image_path, "faces_detected": face_data["face_count"], "detection_details": face_data,
            "reverse_search_yandex": yandex, "reverse_search_google": google}
