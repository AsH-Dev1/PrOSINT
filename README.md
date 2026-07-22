# PrOSINT — OSINT Multi-Source Investigation Platform

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-3.0-orange.svg)]()

**PrOSINT** es una plataforma de investigación OSINT multi-fuente con 25+ módulos, CLI interactiva, interfaz web con visualización de grafos, y base de datos SQLite para gestión de casos.

## 🚀 Instalación

```bash
git clone https://github.com/usuario/PrOSINT
cd PrOSINT
pipx install -e .

# Twitter/X lookup (opcional)
pipx runpip prosint install snscrape

# Reconocimiento facial (opcional, requiere ~2GB)
pipx runpip prosint install deepface tf-keras
```

## ⚙️ Configuración

```bash
cp .env.example .env
# Edita .env con tus API keys (opcionales - el sistema funciona sin ellas)
```

| Variable | Descripción | Obligatoria |
|----------|-------------|-------------|
| `SHODAN_API_KEY` | Shodan para IP/banners/CVEs | No |
| `HIBP_API_KEY` | Have I Been Pwned para brechas | No |

## 🖥️ Uso rápido

```bash
prosint webui              # Interfaz web → http://127.0.0.1:8000
prosint --help              # Todos los comandos disponibles
```

---

## 📋 Todos los comandos

### 🔍 Búsqueda de Personas

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `prosint search "Nombre"` | 44+ fuentes (MX/LATAM/Global) con links cliqueables | `prosint search "Leo Messi"` |
| `prosint username @nick` | 138 plataformas con detección agresiva | `prosint username @torvalds` |
| `prosint dorks "nombre"` | Google Dorks con resultados reales | `prosint dorks "John Smith"` |
| `prosint person email` | Email + username cross-reference | `prosint person user@test.com` |
| `prosint pii CURP/SSN` | Búsqueda inversa de PII (CURP, SSN, phone) | `prosint pii ABCD920101HDFRRR01` |

### 📧 Email & Contacto

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `prosint email user@test.com` | Validación + HIBP + Gravatar + linked accounts | `prosint email --accounts user@test.com` |
| `prosint phone +525512345678` | 10 apps + carrier 30 países + VoIP detection | `prosint phone +34612345678` |
| `prosint breaches email` | Psbdmp + XposedOrNot + BreachDirectory | `prosint breaches user@test.com` |
| `prosint leaks email` | Paste sites + leak databases | `prosint leaks user@test.com` |

### 🌐 Dominios & Redes

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `prosint domain ejemplo.com` | WHOIS + DNS records | `prosint domain google.com` |
| `prosint subdomain ejemplo.com` | Subdominios (crt.sh + OTX + rapiddns) | `prosint subdomain tesla.com` |
| `prosint harvest ejemplo.com` | Emails + hosts (6 buscadores + DNSDumpster) | `prosint harvest github.com` |
| `prosint network 8.8.8.8` | GeoIP + Shodan + Censys + SecurityTrails + AbuseIPDB | `prosint network --ports 1.2.3.4` |
| `prosint web https://site.com` | Tech stack + Wayback Machine | `prosint web https://example.com` |

### 🎯 Redes Sociales & Gaming

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `prosint twitter @user` | Perfil + tweets recientes (snscrape) | `prosint twitter --timeline @jack` |
| `prosint telegram @user` | Perfil + avatar + miembros + mensajes | `prosint telegram @durov` |
| `prosint discord username` | IDs + badges + linked accounts | `prosint discord username` |

### 🖼️ Imagen & Reconocimiento Facial

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `prosint face foto.jpg` | Edad/género/emoción/raza + Google Lens + Yandex | `prosint face foto.jpg` |
| `prosint compare a.jpg b.jpg` | Comparación facial 1:1 (¿misma persona?) | `prosint compare a.jpg b.jpg` |
| `prosint metadata archivo` | EXIF + PDF + DOCX + XLSX | `prosint metadata foto.jpg` |

### 📊 Negocios & Finanzas

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `prosint company Microsoft` | LinkedIn + Glassdoor + Crunchbase + WHOIS + BuiltWith | `prosint company "Tesla Motors"` |
| `prosint crypto 1A1z...` | BTC/ETH balance + explorers + OFAC sanctions | `prosint crypto 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa` |

### 🗺️ Geolocalización

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `prosint geoint 8.8.8.8` | IP → dirección real (OpenStreetMap) | `prosint geoint 8.8.8.8` |
| `prosint geoint AA:BB:CC:DD:EE:FF` | WiFi BSSID lookup (WiGLE) | `prosint geoint AA:BB:CC:DD:EE:FF` |
| `prosint geoint 40.7,-74.0` | Reverse geocoding lat/lon → dirección | `prosint geoint 40.7,-74.0` |

### 📁 Documentos & Automatización

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `prosint docs "query"` | Google Docs + Pastebin + Scribd + SlideShare | `prosint docs "company report"` |
| `prosint full target` | Todos los módulos relevantes a la vez | `prosint full ejemplo.com` |

### 🧠 Investigación Avanzada (Graph Engine)

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `prosint investigate target --depth 2` | Grafo recursivo con SQLite (guarda caso) | `prosint investigate user@test.com` |
| `prosint cases` | Listar todos los casos guardados | `prosint cases` |
| `prosint graph-view <case_id>` | Ver grafo de un caso | `prosint graph-view abc12345` |

---

## 🏗️ Arquitectura

```
PrOSINT/
├── core/                  # 25+ módulos OSINT
│   ├── domain.py          # WHOIS + DNS
│   ├── subdomain.py       # Enumeración de subdominios
│   ├── network.py         # IP, Shodan, Censys, SecurityTrails
│   ├── email.py           # Email validation, HIBP, Gravatar
│   ├── username.py        # Búsqueda en 138 plataformas
│   ├── phone.py           # 10 apps, carrier 30 países
│   ├── people.py          # WebMii/Pipl/directorios + Discord
│   ├── person.py          # Correlación email + username
│   ├── pii.py             # Búsqueda inversa CURP/SSN
│   ├── face.py            # DeepFace edad/género + Google Lens
│   ├── dorks.py           # Google Dorks + DuckDuckGo
│   ├── harvester.py       # theHarvester + 6 buscadores
│   ├── leaks.py           # Psbdmp + XposedOrNot
│   ├── breaches.py        # Breach search multi-source
│   ├── accounts.py        # Linked accounts discovery
│   ├── company.py         # LinkedIn, Glassdoor, Crunchbase
│   ├── crypto.py          # BTC/ETH + OFAC sanctions
│   ├── twitter_intel.py   # snscrape tweets
│   ├── telegram_intel.py  # Telegram profile scraping
│   ├── geoint.py          # WiFi lookup + reverse geocoding
│   ├── web.py             # Tech stack + Wayback Machine
│   ├── metadata.py        # EXIF + PDF + DOCX + XLSX
│   ├── graph_engine.py    # Entity graph + SQLite
│   ├── identity.py        # Fuzzy matching + clustering
│   └── pipeline.py        # Recursive transform engine
├── utils/
│   ├── config.py          # .env loader
│   ├── output.py          # Rich terminal formatting
│   ├── report.py          # HTML/JSON/CSV/Markdown reports
│   ├── http_helper.py     # httpx + curl fallback
│   └── cache.py           # Request caching
├── cli/
│   └── main.py            # Typer CLI (25+ comandos)
├── web/
│   ├── app.py             # FastAPI application
│   ├── routes.py          # 30+ API endpoints
│   ├── templates/
│   │   └── index.html     # SPA dashboard
│   └── static/
│       └── app.js         # 25 render functions + vis.js graph
├── data/
│   └── sites.json         # 138 plataformas con URLs
├── .env.example           # Template de API keys
├── pyproject.toml         # Build config
└── requirements.txt       # Dependencies
```

---

## 🔌 APIs opcionales (modelo Shodan)

El sistema funciona **al 100% sin API keys**. Si configuras alguna en `.env`, se usa automáticamente.

| API | Variable `.env` | Qué aporta |
|-----|----------------|-----------|
| Shodan | `SHODAN_API_KEY` | Banners, CVEs, IoT detection |
| HIBP | `HIBP_API_KEY` | Búsqueda de brechas por email |

---

## 🎨 Web UI

```bash
prosint webui
```

Panel interactivo con:
- **Dashboard** con Quick Search (auto-detecta tipo de target)
- **26 paneles** en sidebar
- **Graph View** con visualización interactiva (vis.js)
- **Cases** con gestión de investigaciones guardadas (SQLite)
- **Export** HTML/JSON/CSV desde cada panel
- Dark theme profesional

---

## ⚠️ Disclaimer

Esta herramienta es solo para **investigaciones autorizadas** y **OSINT ético**:
- Pruebas de seguridad autorizadas
- Investigaciones de ciberseguridad con consentimiento
- Verificación de fugas de datos propias
- Búsqueda de personas con fines legítimos y legales

El uso indebido de esta herramienta puede violar leyes de privacidad. El autor no se hace responsable del uso no autorizado.

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE)
