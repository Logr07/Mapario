# Databaze objektu k fotografovani

Mapova webova aplikace pro osobni evidenci vizualne zajimavych mist a budov. Umoznuje zakladat vlastni lokace, tridit je podle typu objektu, stavu, hodnoceni a pristupnosti, pripojovat fotodokumentaci a pracovat s nimi primo nad interaktivni mapou.

Projekt je rozdeleny na Vue frontend, Flask API a PostgreSQL/PostGIS databazi. Produkcni beh je pripraveny pres Docker Compose.

## Hlavni funkce

- registrace, prihlaseni, odhlaseni a zmena hesla
- soukrome lokace oddelene podle prihlaseneho uzivatele
- interaktivni mapa pres Leaflet s OpenStreetMap a Google satelitnim podkladem
- vyhledavani adres pres Photon/Komoot a podpora primeho zadani souradnic
- vytvareni, uprava, mazani a filtrovani lokalit
- kategorie, podtypy objektu, stav, hodnoceni a pristupnost
- oznacovani oblibenych lokalit
- nahravani, zobrazeni a mazani fotografii k jednotlivym lokalitam
- vlastni mapove ikony slozene ze stavu, hodnoceni, podtypu a oblibenosti
- CSRF ochrana, bezpecnostni HTTP hlavicky a zabezpecene session cookies

## Technologie

### Backend

- Python 3.12
- Flask 3
- Gunicorn
- psycopg 3
- PostgreSQL 16 s PostGIS
- pytest

### Frontend

- Vue 3
- Vite 6
- Leaflet
- leaflet.markercluster
- Nginx pro servirovani produkcniho buildu a proxy `/api`

## Struktura projektu

```text
.
├── backend/               # Flask aplikace, routy, repository, sluzby a security hooky
├── database/              # Postgres/PostGIS image a inicializacni SQL schema
├── frontend/              # Vue/Vite aplikace, komponenty, API klient a styly
├── tests/                 # pytest integracni a jednotkove testy
├── uploads/               # lokalni adresar pro nahrane fotky, neni verzovany
├── docker-compose.yml     # produkcne ladene slozeni db/backend/frontend
├── requirements.txt       # Python zavislosti
├── pytest.ini             # konfigurace testu
└── .env.example           # vzor konfigurace prostredi
```

## Rychle spusteni pres Docker

Predpoklady:

- Docker
- Docker Compose plugin

1. Pripravte konfiguraci:

```bash
cp .env.example .env
```

2. V souboru `.env` zmente alespon tyto hodnoty:

```env
POSTGRES_PASSWORD=replace-with-strong-database-password
DATABASE_URL=postgresql://lokality_app:replace-with-strong-database-password@db:5432/lokality_prod
FLASK_SECRET_KEY=replace-with-strong-flask-secret
PHOTON_USER_AGENT=mapa-bakalarka/1.0 (https://vase-domena.example)
```

3. Spustte aplikaci:

```bash
docker compose up --build
```

4. Otevrete frontend:

```text
http://localhost:5173
```

Sluzby jsou z hostitele dostupne pouze na loopback rozhrani:

- frontend: `http://127.0.0.1:5173`
- backend API: `http://127.0.0.1:5000/api`
- databaze: `127.0.0.1:5432`

Healthcheck API:

```bash
curl http://localhost:5173/api/health
```

Ocekavana odpoved:

```json
{"database":"ok","status":"ok"}
```

## Konfigurace

Aplikace nacita konfiguraci z promennych prostredi. Pro Docker Compose slouzi soubor `.env`.

| Promenna | Vychozi hodnota | Popis |
| --- | --- | --- |
| `POSTGRES_DB` | `interest_map` | Nazev databaze v PostgreSQL kontejneru |
| `POSTGRES_USER` | `interest_map` | Databazovy uzivatel |
| `POSTGRES_PASSWORD` | `change-me` | Heslo databazoveho uzivatele |
| `DATABASE_URL` | `postgresql://interest_map:change-me@localhost:5432/interest_map` | Connection string pro backend |
| `FLASK_SECRET_KEY` | `development-secret-change-me` | Klic pro Flask session; v produkci povinne zmenit |
| `UPLOAD_FOLDER` | `/app/uploads` | Adresar pro ulozene fotografie |
| `MAX_CONTENT_LENGTH` | `10485760` | Maximalni velikost requestu, vychozi 10 MB |
| `SESSION_COOKIE_NAME` | `__Host-mapa_session` | Nazev Flask session cookie |
| `SESSION_COOKIE_SECURE` | `true` | Pridava `Secure` atribut session cookie |
| `SECURITY_HEADERS_ENABLED` | `true` | Zapina bezpecnostni HTTP hlavicky |
| `HSTS_ENABLED` | `true` | Zapina HSTS hlavicku |
| `HSTS_MAX_AGE` | `31536000` | Doba platnosti HSTS v sekundach |
| `PHOTON_BASE_URL` | `https://photon.komoot.io` | Provider pro geokodovani |
| `PHOTON_USER_AGENT` | `mapa-bakalarka/0.1 (...)` | User-Agent posilany na Photon API |
| `PHOTON_TIMEOUT_SECONDS` | `8` | Timeout geokodovani |
| `VITE_API_BASE_URL` | `/api` | Base URL API pro frontend |
| `VITE_API_PROXY_TARGET` | `http://localhost:5000` | Cil proxy pri Vite vyvoji |
| `VITE_ALLOWED_HOSTS` | `true` | Volitelne povolene hosty pro Vite dev server |

V produkci doporucuji ponechat `SESSION_COOKIE_SECURE=true`, `SECURITY_HEADERS_ENABLED=true` a `HSTS_ENABLED=true`. Pro lokalni HTTP vyvoj mimo Docker muze byt potreba `SESSION_COOKIE_SECURE=false`.
Pokud vypnete `SESSION_COOKIE_SECURE`, zmente zaroven `SESSION_COOKIE_NAME` na hodnotu bez prefixu `__Host-`, napriklad `mapa_session`.

## Lokalni vyvoj bez kompletniho Compose stacku

Nejjednodussi je nechat databazi bezet v Dockeru a backend/frontend spustit lokalne.

### Databaze

```bash
docker compose up db
```

Pro backend bezici na hostiteli pouzijte connection string s `localhost`:

```bash
export DATABASE_URL=postgresql://lokality_app:replace-with-strong-database-password@localhost:5432/lokality_prod
```

Hodnoty musi odpovidat vasemu `.env`.

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_SECRET_KEY=local-development-secret
export UPLOAD_FOLDER=uploads
export SESSION_COOKIE_SECURE=false
export SESSION_COOKIE_NAME=mapa_session
export SECURITY_HEADERS_ENABLED=false
flask --app backend.wsgi run --host 0.0.0.0 --port 5000 --debug
```

API pak bezi na:

```text
http://localhost:5000/api
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite dev server bezi na:

```text
http://localhost:5173
```

Vite proxy smeruje `/api` na `http://localhost:5000`, pokud neni nastavena promenna `VITE_API_PROXY_TARGET`.

## Testy

Backend testy pouzivaji `pytest`. Cast testu vyzaduje dostupnou PostgreSQL/PostGIS databazi a promennou `DATABASE_URL`.

```bash
export DATABASE_URL=postgresql://lokality_app:replace-with-strong-database-password@localhost:5432/lokality_prod
python3 -m pytest
```

Pokud `DATABASE_URL` neni nastavena, integracni testy zavisle na databazi se preskoci.

Frontend build:

```bash
cd frontend
npm run build
```

## API prehled

Vsechny mutujici pozadavky pod `/api/` vyzaduji CSRF token v hlavicce `X-CSRF-Token`. Frontend ho ziskava automaticky z `/api/auth/csrf`.

### Autentizace

- `GET /api/auth/csrf` - vrati CSRF token
- `GET /api/auth/me` - vrati aktualni session
- `POST /api/auth/register` - vytvori ucet a rovnou prihlasi uzivatele
- `POST /api/auth/login` - prihlasi uzivatele
- `POST /api/auth/change-password` - zmeni heslo prihlaseneho uzivatele
- `POST /api/auth/logout` - odhlasi uzivatele

### Lokace

- `GET /api/locations` - seznam lokaci prihlaseneho uzivatele
- `GET /api/locations/:id` - detail lokace
- `POST /api/locations` - vytvoreni lokace
- `PUT /api/locations/:id` - uprava lokace
- `DELETE /api/locations/:id` - smazani lokace
- `PUT /api/locations/:id/favorite` - nastaveni nebo zruseni oblibenosti

Zakladni payload lokace:

```json
{
  "title": "Opuštěná tovární hala",
  "latitude": 50.087,
  "longitude": 14.421,
  "status": "unverified",
  "category": "industrial",
  "subcategory": "manufacturing",
  "rating": "3",
  "accessibility": "unknown"
}
```

### Fotografie

- `GET /api/locations/:location_id/photos` - seznam fotek k lokaci
- `POST /api/locations/:location_id/photos` - upload multipart pole `photo`
- `GET /api/locations/:location_id/photos/:photo_id/file` - soubor fotky
- `DELETE /api/locations/:location_id/photos/:photo_id` - smazani fotky

Podporovane formaty: JPG, PNG, WebP a GIF. Backend kontroluje priponu, MIME typ i magic bytes souboru.

### Geokodovani

- `GET /api/geocode?query=Praha` - vyhledani adresy nebo mista
- `GET /api/geocode/suggest?query=Pra` - naseptavani, pouziva stejnou sluzbu

Geokodovani je dostupne pouze prihlasenym uzivatelum. Backend vysledky cachuje v pameti po dobu 24 hodin a omezuje frekvenci volani na externi Photon API.

### Healthcheck

- `GET /api/health` - stav API a databazoveho spojeni

## Datovy model

Inicializacni schema je v `database/init.sql`.

- `users` - uzivatelske ucty a hash hesla
- `locations` - zaklad lokace, vlastnik, popis a PostGIS bod `geom`
- `points_of_interest` - stav, kategorie, podtyp, hodnoceni a pristupnost lokace
- `location_photos` - metadata nahranych fotografii
- `favorite_locations` - vazba uzivatel-lokace pro oblibene polozky

Databaze vynucuje povolene hodnoty pomoci `CHECK` constraintu a uchovava souradnice jako `geometry(Point, 4326)`.

## Bezpecnostni poznamky

- Hesla jsou ukladana jako solene hashe pres Werkzeug.
- Session cookie pouziva `HttpOnly`, `SameSite=Lax`, `Path=/` a podle konfigurace i `Secure`.
- Mutujici API pozadavky jsou chranene CSRF tokenem.
- Lokace i fotky se vzdy nacitaji pres vlastnictvi prihlaseneho uzivatele.
- Upload fotek pouziva `secure_filename`, kontrolu formatu a ochranu proti path traversal.
- Backend i nginx nastavuji bezpecnostni hlavicky vcetne CSP, `X-Frame-Options`, `Referrer-Policy` a HSTS.

## Udrzba

Zastaveni kontejneru:

```bash
docker compose down
```

Zastaveni vcetne smazani databazoveho volume:

```bash
docker compose down -v
```

Pozor: `docker compose down -v` smaze databazova data. Nahrane fotografie jsou mapovane do lokalniho adresare `uploads/`, ktery je ignorovany Gitem.
