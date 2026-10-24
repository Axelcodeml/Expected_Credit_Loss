# Frontend ECL

Interfaz Next.js para el servicio local de pérdida crediticia esperada.

## Requisitos

- Node.js 20.9 o superior.
- API FastAPI disponible en `http://localhost:8000`.
- `frontend/.env.local` con:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

El archivo de ejemplo está en la raíz del repositorio; cópielo con:

```powershell
Copy-Item ..\.env.example .env.local
```

## Desarrollo

```powershell
npm install
npm run dev
```

Abrir <http://localhost:3000>.

## Verificación

```powershell
npm run lint
npm run typecheck
npm run build
```

## Tipos de la API

El cliente usa tipos generados desde el OpenAPI real. Después de cambiar la API:

```powershell
Invoke-WebRequest http://localhost:8000/openapi.json -OutFile openapi.json
npm run generate:types
```

En Linux / macOS:

```bash
curl http://localhost:8000/openapi.json -o openapi.json
npm run generate:types
```

No editar `src/lib/api-types.ts` a mano.

## Estructura

- `src/app/`: páginas Cartera, Crédito individual, Modelo e Historial.
- `src/components/`: layout, carga, KPIs, gráficos, tabla, formulario e historial.
- `src/lib/api.ts`: cliente HTTP y descargas.
- `src/lib/api-types.ts`: contratos generados.
- `public/cartera_demo.csv`: muestra local generada por `scripts/make_sample.py`.

La muestra pública está ignorada por git. En un clon limpio, ejecutar desde la raíz:

```powershell
python scripts/make_sample.py
```

La documentación completa de instalación y operación está en el [README raíz](../README.md).
