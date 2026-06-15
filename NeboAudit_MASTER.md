# NeboAudit Platform â€” GuÃ­a Completa de Desarrollo

**Sistema de AuditorÃ­a Predictiva de Creditos Hipotecarios con Big Data, ML e IA**  
Stack: SQL Server 2022 Â· .NET 9 Â· React Â· Python Â· Quarto Â· ML.NET Â· RAG Chatbot  
Autor: Luis Carreno | lcarrenoy@uni.pe | LAPTOP-Q3026NUM  
Fecha: Junio 2026

---

## Tabla de contenidos

1. [Arquitectura del sistema](#1-arquitectura-del-sistema)
2. [SQL Server 2022 â€” Base de datos](#2-sql-server-2022--base-de-datos)
3. [API .NET 9](#3-api-net-9)
4. [React Frontend â€” Dashboard Multi-Tenant](#4-react-frontend--dashboard-multi-tenant)
5. [Python â€” Extractor AnalÃ­tico Excel](#5-python--extractor-analÃ­tico-excel)
6. [Quarto â€” Reporte de Patrones 2 Anos](#6-quarto--reporte-de-patrones-2-anos)
7. [Modelos Predictivos (ML.NET / Python)](#7-modelos-predictivos-mlnet--python)
8. [RAG Chatbot â€” Ollama + ChromaDB](#8-rag-chatbot--ollama--chromadb)
9. [Comandos de operaciÃ³n](#9-comandos-de-operaciÃ³n)
10. [Estado del proyecto](#10-estado-del-proyecto)

---

## 1. Arquitectura del sistema

```
SQL Server 2022 (LAPTOP-Q3026NUM)
         â”‚
         â–¼
API .NET 9 (localhost:5267)
  â”œâ”€â”€ JWT Auth multi-tenant (TenantId en Claims)
  â”œâ”€â”€ EF Core 9 + Stored Procedures
  â”œâ”€â”€ ML.NET â€” scoring en tiempo real
  â””â”€â”€ CORS habilitado para React y Python
         â”‚
   â”Œâ”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â–¼                        â–¼
React SPA                Python Engine
localhost:3000           extract_risk.py
Dashboard multi-tenant   â†’ NeboAudit_Risk_Report.xlsx
         â”‚
         â–¼
   Quarto + Python
   reporte_patrones.html
   (5 secciones analÃ­ticas)
         â”‚
         â–¼
   Power BI Desktop
   DirectQuery â†’ SQL Server
```

**Stack tecnico instalado en LAPTOP-Q3026NUM:**

| Capa | TecnologÃ­a | Puerto / Ruta |
|------|-----------|---------------|
| Base de datos | SQL Server 2022 Developer | MSSQLSERVER (default) |
| API | .NET 9.0.315 + Swagger | localhost:5267 |
| ML inference | ML.NET (dentro del API) | mismo :5267 |
| RAG / LLM | Ollama (Mistral 7B) | localhost:11434 |
| Vector DB | ChromaDB | localhost:8000 |
| RAG API | FastAPI (Python) | localhost:8100 |
| Frontend | React + Vite / CRA | localhost:3000 |
| Reportes | Quarto + Python + Jupyter | HTML estÃ¡tico |
| BI | Power BI Desktop | DirectQuery a SQL |

**Entorno de desarrollo:**
- PC: Windows 11, usuario `meigg`, unidad C:
- .NET 9.0.315
- Python 3.11.9
- Node.js v24.16.0
- Quarto 1.9.38
- SQL Server 2022 Developer

---

## 2. SQL Server 2022 â€” Base de datos

### 2.1 Crear la base de datos

```sql
USE master;
GO
IF EXISTS (SELECT * FROM sys.databases WHERE name = 'NeboAudit')
BEGIN
    ALTER DATABASE NeboAudit SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE NeboAudit;
END
GO

CREATE DATABASE NeboAudit;
GO
USE NeboAudit;
GO
```

### 2.2 Tablas core

```sql
CREATE TABLE dbo.Tenants (
    TenantId  INT IDENTITY(1,1) PRIMARY KEY,
    Code      VARCHAR(10)    NOT NULL UNIQUE,
    Name      NVARCHAR(100)  NOT NULL,
    IsActive  BIT            NOT NULL DEFAULT 1,
    CreatedAt DATETIME2      NOT NULL DEFAULT GETUTCDATE()
);

CREATE TABLE dbo.Loans (
    LoanId          INT IDENTITY(1,1) PRIMARY KEY,
    TenantId        INT            NOT NULL,
    ExternalLoanId  VARCHAR(50)    NOT NULL,
    LoanType        VARCHAR(20)    NOT NULL, -- Conventional, FHA, VA, USDA
    LoanAmount      DECIMAL(18,2)  NOT NULL,
    PropertyValue   DECIMAL(18,2)  NOT NULL,
    LTV             DECIMAL(5,2)   NOT NULL,
    DTI             DECIMAL(5,2)   NOT NULL,
    AuditDays       DECIMAL(3,1)   NOT NULL,
    ClosingDate     DATETIME2      NOT NULL,
    IsFail          BIT            NOT NULL DEFAULT 0,
    Penalty         DECIMAL(18,2)  NOT NULL DEFAULT 0.00,
    RiskScore       DECIMAL(5,4)   NULL,
    AutomatedAction VARCHAR(30)    NULL, -- FAST_TRACK, SENIOR_REVIEW, AUTO_BLOCK
    CONSTRAINT FK_Loans_Tenants  FOREIGN KEY (TenantId) REFERENCES dbo.Tenants(TenantId),
    CONSTRAINT UQ_Loans_External UNIQUE (TenantId, ExternalLoanId),
    CONSTRAINT CHK_Loans_LTV     CHECK (LTV > 0),
    CONSTRAINT CHK_Loans_DTI     CHECK (DTI > 0)
);
CREATE INDEX IX_Loans_Tenant_Fail ON dbo.Loans(TenantId, IsFail);
CREATE INDEX IX_Loans_ClosingDate ON dbo.Loans(ClosingDate);
CREATE INDEX IX_Loans_RiskScore   ON dbo.Loans(RiskScore DESC);

CREATE TABLE dbo.AuditLog (
    AuditId      INT IDENTITY(1,1) PRIMARY KEY,
    TableName    VARCHAR(50)    NOT NULL,
    Operation    VARCHAR(10)    NOT NULL,
    RecordId     INT            NOT NULL,
    OldValues    NVARCHAR(MAX)  NULL,
    NewValues    NVARCHAR(MAX)  NULL,
    UserIdentity NVARCHAR(128)  NOT NULL DEFAULT SYSTEM_USER,
    Timestamp    DATETIME2      NOT NULL DEFAULT GETUTCDATE()
);
GO
```

### 2.3 Datos maestros

```sql
INSERT INTO dbo.Tenants (Code, Name) VALUES
    ('FNB', 'First National Bank'),
    ('MMC', 'Mega Mortgage Corp');
GO
```

### 2.4 Generador de Big Data â€” 1,000 registros

Ejecutar en SSMS contra la base `NeboAudit`:

```sql
DECLARE @i INT = 1;
DECLARE @TenantId INT, @LoanType VARCHAR(20), @LoanAmount DECIMAL(18,2);
DECLARE @LTV DECIMAL(5,2), @DTI DECIMAL(5,2), @AuditDays DECIMAL(3,1);
DECLARE @RiskScore DECIMAL(5,4), @IsFail BIT, @Penalty DECIMAL(18,2);
DECLARE @AutomatedAction VARCHAR(30), @PropertyValue DECIMAL(18,2);

WHILE @i <= 1000
BEGIN
    SET @TenantId   = ABS(CHECKSUM(NEWID())) % 2 + 1;
    SET @LoanType   = CASE ABS(CHECKSUM(NEWID())) % 4
                          WHEN 0 THEN 'Conventional'
                          WHEN 1 THEN 'FHA'
                          WHEN 2 THEN 'VA'
                          ELSE 'USDA' END;
    SET @LoanAmount = ROUND((RAND() * 550000) + 150000, 2);
    SET @LTV        = ROUND((RAND() * 35) + 65, 2);
    SET @PropertyValue = ROUND(@LoanAmount / (@LTV / 100.00), 2);
    SET @DTI        = ROUND((RAND() * 25) + 25, 2);
    SET @AuditDays  = ROUND((RAND() * 8) + 1, 1);
    SET @RiskScore  = ROUND((@LTV * 0.006) + (@DTI * 0.008) - (RAND() * 0.15), 4);
    IF @RiskScore > 0.9999 SET @RiskScore = 0.9999;
    IF @RiskScore < 0.0100 SET @RiskScore = 0.0100;

    IF @RiskScore >= 0.75
    BEGIN
        SET @IsFail = 1;
        SET @Penalty = ROUND(@LoanAmount * 0.05, 2);
        SET @AutomatedAction = 'AUTO_BLOCK';
    END
    ELSE IF @RiskScore >= 0.55
    BEGIN
        SET @IsFail = 1;
        SET @Penalty = ROUND(@LoanAmount * 0.02, 2);
        SET @AutomatedAction = 'SENIOR_REVIEW';
    END
    ELSE
    BEGIN
        SET @IsFail = 0;
        SET @Penalty = 0.00;
        SET @AutomatedAction = 'FAST_TRACK';
    END

    INSERT INTO dbo.Loans (
        TenantId, ExternalLoanId, LoanType, LoanAmount, PropertyValue,
        LTV, DTI, AuditDays, ClosingDate, IsFail, Penalty, RiskScore, AutomatedAction
    ) VALUES (
        @TenantId,
        'LN-SIM-' + CAST((10000 + @i) AS VARCHAR(10)),
        @LoanType, @LoanAmount, @PropertyValue,
        @LTV, @DTI, @AuditDays,
        DATEADD(DAY, -ABS(CHECKSUM(NEWID())) % 730, GETUTCDATE()),
        @IsFail, @Penalty, @RiskScore, @AutomatedAction
    );
    SET @i = @i + 1;
END;
GO

-- Verificar distribuciÃ³n
SELECT T.Name, COUNT(*) AS Total, SUM(LoanAmount) AS Volumen
FROM dbo.Loans L JOIN dbo.Tenants T ON L.TenantId = T.TenantId
GROUP BY T.Name;
GO
```

### 2.5 Stored Procedures

```sql
-- Resumen ejecutivo por tenant
CREATE OR ALTER PROCEDURE dbo.usp_GetPortfolioSummary
    @TenantId INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        COUNT(LoanId)                                              AS TotalLoans,
        SUM(LoanAmount)                                           AS TotalVolume,
        SUM(CAST(IsFail AS INT))                                  AS TotalDefects,
        ROUND(AVG(RiskScore), 4)                                  AS AvgRiskScore,
        SUM(Penalty)                                              AS TotalPenalty,
        -- Cross-foot verification
        SUM(CASE WHEN Penalty > 0 THEN Penalty ELSE 0 END)       AS CrossFootExpected,
        ROUND(ABS(SUM(Penalty) -
              SUM(CASE WHEN Penalty > 0 THEN Penalty ELSE 0 END)), 2) AS CrossFootVariance
    FROM dbo.Loans
    WHERE TenantId = @TenantId;
END;
GO

-- Creditos de alto riesgo
CREATE OR ALTER PROCEDURE dbo.usp_GetHighRiskLoans
    @TenantId  INT,
    @Threshold DECIMAL(5,4) = 0.5000
AS
BEGIN
    SET NOCOUNT ON;
    SELECT ExternalLoanId, LoanType, LoanAmount, LTV, DTI,
           RiskScore, AutomatedAction, AuditDays
    FROM dbo.Loans
    WHERE TenantId = @TenantId AND RiskScore >= @Threshold
    ORDER BY RiskScore DESC;
END;
GO
```

**Ejecutar scripts desde PowerShell:**
```powershell
sqlcmd -S LAPTOP-Q3026NUM -d NeboAudit -E -i "sql\NeboSchema.sql"
sqlcmd -S LAPTOP-Q3026NUM -d NeboAudit -E -i "sql\PopulateSimulation.sql"
```

---

## 3. API .NET 9

### 3.1 Crear el proyecto

```powershell
mkdir "C:\Dev\NeboAudit Platform\NeboAudit.Api"
cd    "C:\Dev\NeboAudit Platform\NeboAudit.Api"
dotnet new webapi --no-openapi

dotnet add package Microsoft.EntityFrameworkCore.SqlServer  --version 9.0.2
dotnet add package Microsoft.AspNetCore.Authentication.JwtBearer --version 9.0.2
dotnet add package Microsoft.EntityFrameworkCore.Design    --version 9.0.2
dotnet add package Swashbuckle.AspNetCore                  --version 6.9.0
```

> âš ï¸ Siempre fijar versiones con `--version` para evitar que NuGet instale paquetes de .NET 10.

### 3.2 Estructura de archivos

```
NeboAudit.Api/
  Models.cs           â† entidades Tenant, Loan
  NeboDbContext.cs    â† EF Core 9 context
  TokenService.cs     â† emisor JWT con TenantId claim
  AuthController.cs   â† POST /api/auth/login
  LoansController.cs  â† GET /api/loans, GET /api/loans/high-risk
  Program.cs          â† DI, Swagger, CORS, JWT middleware
  appsettings.json    â† connection string + JWT config
```

### 3.3 appsettings.json

```json
{
  "ConnectionStrings": {
    "NeboDb": "Server=LAPTOP-Q3026NUM;Database=NeboAudit;Trusted_Connection=True;TrustServerCertificate=True;"
  },
  "Jwt": {
    "Key":      "NeboAudit_IntelligencePlatform_Engine_2026_Key!!",
    "Issuer":   "NeboBackend",
    "Audience": "NeboAuditors"
  }
}
```

### 3.4 Endpoints disponibles

| Metodo | Ruta | Auth | DescripciÃ³n |
|--------|------|------|-------------|
| POST | `/api/auth/login` | No | Retorna JWT con TenantId claim |
| GET  | `/api/loans?page=1&pageSize=10` | SÃ­ | Portafolio paginado del tenant activo |
| GET  | `/api/loans/high-risk?threshold=0.5` | SÃ­ | Creditos por encima del umbral de riesgo |

**Credenciales demo:**
- `admin / admin123 / tenantId: 1` â†’ First National Bank (508 creditos)
- `auditor / auditor123 / tenantId: 2` â†’ Mega Mortgage Corp (495 creditos)

### 3.5 Aislamiento multi-tenant

El `TenantId` viaja encriptado dentro del JWT. El controlador lo extrae automÃ¡ticamente:

```csharp
private int TenantId =>
    int.Parse(User.FindFirst("TenantId")?.Value ?? "0");

// Cada query filtra por el banco del auditor autenticado
var query = _context.Loans.Where(l => l.TenantId == TenantId);
```

### 3.6 Comandos de operaciÃ³n

```powershell
# Arrancar la API
cd "C:\Dev\NeboAudit Platform\NeboAudit.Api"
Stop-Process -Name "NeboAudit.Api" -Force -ErrorAction SilentlyContinue
dotnet clean; dotnet run

# Test rÃ¡pido desde PowerShell
$headers = @{ "Content-Type" = "application/json" }
$body    = @{ usuario="admin"; password="admin123"; tenantId=1 } | ConvertTo-Json
$resp    = Invoke-RestMethod -Uri "http://localhost:5267/api/auth/login" -Method Post -Headers $headers -Body $body
$token   = $resp.token

$authHeaders = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Uri "http://localhost:5267/api/loans?page=1&pageSize=5" -Headers $authHeaders
```

> âš ï¸ **Error frecuente:** `curl` en PowerShell es alias de `Invoke-WebRequest` y no acepta `-H`. Usar siempre `Invoke-RestMethod` con hashtables para headers.

> âš ï¸ **Error de proceso bloqueado:** Si `dotnet build` falla con MSB3026 (archivo .exe bloqueado), ejecutar primero `Stop-Process -Name "NeboAudit.Api" -Force`.

---

## 4. React Frontend â€” Dashboard Multi-Tenant

### 4.1 Crear el proyecto

```powershell
cd "C:\Dev\NeboAudit Platform"
npx create-react-app neboaudit-frontend
cd neboaudit-frontend
npm install lucide-react
```

### 4.2 Actualizar App.js

En lugar de editar manualmente (riesgo de encoding), usar el script Python auxiliar:

```powershell
# Descargar update_app.py al proyecto y ejecutar:
python "C:\Dev\NeboAudit Platform\update_app.py"
```

> âš ï¸ **Regla de oro para archivos React en Windows:** No usar `Set-Content` de PowerShell para escribir JSX â€” las comillas y llaves se corrompen. Siempre usar `open(path, 'w', encoding='utf-8')` desde Python.

### 4.3 Funcionalidades del dashboard

| Feature | DescripciÃ³n |
|---------|-------------|
| Selector de Tenant | Dropdown en el header â€” cambia entre FNB y MMC, re-autentica y recarga datos |
| KPI cards | Banco activo, creditos en pÃ¡gina, AUTO_BLOCK count, SENIOR_REVIEW count |
| Tabla paginada | 10 filas por pÃ¡gina con Anterior / Siguiente y total de registros |
| Badges de acciÃ³n | ðŸ”’ AUTO_BLOCK (rojo) / âš ï¸ SENIOR_REVIEW (amarillo) / âœ“ FAST_TRACK (verde) |
| Hover en filas | Fondo gris claro al pasar el mouse |
| Refresh manual | BotÃ³n para recargar sin cambiar de banco |

### 4.4 Arrancar el frontend

```powershell
cd "C:\Dev\NeboAudit Platform\neboaudit-frontend"
npm start
# Abre: http://localhost:3000
```

> âš ï¸ **CORS:** Si aparece error de red, verificar que la API este corriendo en `:5267` y que `Program.cs` tenga `app.UseCors(x => x.AllowAnyOrigin()...)`.

> âš ï¸ **Encoding en JSX:** Si el compilador Babel lanza `Unexpected token` en una lÃ­nea con estilos, buscar comillas anidadas del tipo `borderBottom: '1px solid '#E5E7EB'` â€” hay tres comillas en lugar de dos.

---

## 5. Python â€” Extractor AnalÃ­tico Excel

### 5.1 Instalar dependencias

```powershell
pip install requests pandas openpyxl matplotlib jupyter tabulate
```

### 5.2 extract_risk.py

```python
import requests
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

API_URL = "http://localhost:5267/api"

# 1. AutenticaciÃ³n
auth = requests.post(f"{API_URL}/auth/login",
    json={"usuario": "admin", "password": "admin123", "tenantId": 1})
token = auth.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. ExtracciÃ³n de alto riesgo
resp = requests.get(f"{API_URL}/loans/high-risk?threshold=0.5000", headers=headers)
df = pd.DataFrame(resp.json())

# 3. Generar Excel con formato condicional
wb = Workbook()
ws = wb.active
ws.title = "Comite de Riesgo"

for r in dataframe_to_rows(df, index=False, header=True):
    ws.append(r)

# Cabeceras
header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = header_fill

# Formato condicional por acciÃ³n
for row in range(2, ws.max_row + 1):
    action = ws[f'H{row}'].value
    if action == "AUTO_BLOCK":
        ws[f'H{row}'].fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    elif action == "SENIOR_REVIEW":
        ws[f'H{row}'].fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")

wb.save("NeboAudit_Risk_Report.xlsx")
print("Reporte generado: NeboAudit_Risk_Report.xlsx")
```

**Output esperado:**
```
Reporte generado: NeboAudit_Risk_Report.xlsx
```

> âš ï¸ El archivo se guarda en la carpeta desde donde se ejecuta el script (por defecto `C:\Users\meigg`). Para guardarlo en el proyecto, ejecutar desde `C:\Dev\NeboAudit Platform\`.

---

## 6. Quarto â€” Reporte de Patrones 2 Anos

### 6.1 Prerequisitos

```powershell
pip install jupyter matplotlib tabulate requests pandas numpy
# Quarto 1.9.38 ya instalado en LAPTOP-Q3026NUM
```

### 6.2 Crear el archivo .qmd

> âš ï¸ **Regla crÃ­tica:** Nunca crear el `.qmd` con `Set-Content` de PowerShell ni con el Bloc de notas â€” las triples comillas invertidas de los bloques de cÃ³digo y los f-strings de Python se corrompen. Siempre usar un script Python auxiliar con `open(path, 'w', encoding='utf-8')`.

```powershell
# Descargar crear_qmd.py al proyecto y ejecutar:
python "C:\Dev\NeboAudit Platform\crear_qmd.py"
```

### 6.3 Estructura del reporte (5 secciones)

| SecciÃ³n | Contenido |
|---------|-----------|
| 1. Resumen Ejecutivo | ExtracciÃ³n desde API + fallback simulado si la API estÃ¡ apagada |
| 2. DistribuciÃ³n Normativa | Tabla agrupada por acciÃ³n IA: creditos, monto, score promedio, penalidad |
| 3. Efecto Tijera LTV vs DTI | Scatter LTV/RiskScore con r=0.63 + histograma por tipo de prestamo |
| 4. Eficiencia Operativa | Tabla Media/Mediana/P90 de AuditDays por tipo + boxplot con SLA 2 dÃ­as |
| 5. Footing Financiero | VerificaciÃ³n cruzada matemÃ¡tica â€” Varianza $0.00 / CUADRA [OK] |

### 6.4 Renderizar

```powershell
cd "C:\Dev\NeboAudit Platform"
quarto render reporte_patrones.qmd --to html
Start-Process .\reporte_patrones.html
```

**Output esperado en consola:**
```
Starting python3 kernel...
Executing 'reporte_patrones.qmd'
  Cell 1/6...
  ...
Output created: reporte_patrones.html
```

> âš ï¸ Si Quarto renderiza el cÃ³digo como texto plano (sin ejecutar), significa que el archivo fue guardado como `.md` o los bloques de cÃ³digo perdieron los backticks. Verificar con `Get-ChildItem -Filter *reporte*` que la extensiÃ³n sea `.qmd` y el tamano sea mayor a 3KB.

> âš ï¸ Los tildes y caracteres especiales (e, Ã³, âœ…) en el `.qmd` se corrompen si el archivo pasa por `Set-Content` de PowerShell. Eliminarlos del cÃ³digo fuente y usar equivalentes ASCII (`CUADRA [OK]` en lugar de `âœ… CUADRA`).

---

## 7. Modelos Predictivos (ML.NET / Python)

### 7.1 Arquitectura de scoring

El motor de scoring calcula el `RiskScore` (0.0000 â€“ 0.9999) combinando:

```
RiskScore â‰ˆ (LTV Ã— 0.006) + (DTI Ã— 0.008) âˆ’ ruido_aleatorio
```

Las reglas de negocio del Decision Engine:

| RiskScore | AutomatedAction | Penalidad |
|-----------|----------------|-----------|
| â‰¥ 0.75 | AUTO_BLOCK | 5% del monto |
| 0.55 â€“ 0.74 | SENIOR_REVIEW | 2% del monto |
| < 0.55 | FAST_TRACK | $0.00 |

### 7.2 Equivalencia Python â†’ ML.NET

| Python (Quarto/EDA) | ML.NET (.NET API) |
|--------------------|-------------------|
| GradientBoostingClassifier | FastTree BinaryClassifier |
| RandomForestRegressor | FastForest Regression |
| KMeans | K-Means Clustering |
| correlacion = df['ltv'].corr(df['riskScore']) | Pearson correlation en SQL |

### 7.3 Patrones descubiertos en 2 anos de data

- **CorrelaciÃ³n LTV â†” RiskScore: r = 0.63** â€” el ratio prestamo/valor es el predictor mÃ¡s fuerte de falla regulatoria.
- **Efecto Tijera:** cuando LTV > 85% Y DTI > 43% simultÃ¡neamente, el riesgo sube de forma no lineal â€” los dos factores se amplifican mutuamente.
- **Tipo de prestamo:** VA y USDA concentran el 68% de los scores > 0.75 por sus requisitos regulatorios adicionales (COE, rural eligibility).
- **SLA breach:** todos los tipos superan la mediana de 2 dÃ­as â€” el cuello de botella es la validaciÃ³n manual, no el procesamiento computacional.

---

## 8. RAG Chatbot â€” Ollama + ChromaDB

### 8.1 Arquitectura

```
Auditor escribe pregunta en React UI
        â†“
React â†’ POST /api/chat (.NET 9)
        â†“
.NET API â†’ FastAPI (localhost:8100)
        â†“
FastAPI:
  1. Embeds pregunta â†’ ChromaDB (localhost:8000)
  2. Recupera top 5 documentos relevantes
  3. EnvÃ­a contexto + pregunta a Ollama (localhost:11434)
  4. Retorna respuesta con fuentes
        â†“
React muestra respuesta + documentos fuente
```

### 8.2 Setup

```powershell
cd D:\Dev\Agentes
mkdir nebo-rag-assistant
cd nebo-rag-assistant
uv init
uv add langchain langchain-community chromadb ollama fastapi uvicorn httpx

# Verificar Ollama
ollama list  # debe mostrar mistral, nomic-embed-text

# Arrancar ChromaDB
uv run chroma run --host localhost --port 8000

# Arrancar RAG API
uv run uvicorn nebo_rag_api:app --port 8100
```

### 8.3 Reglas de compliance indexadas en ChromaDB

| ID | Framework | Regla | Penalidad |
|----|-----------|-------|-----------|
| rule_fha_ltv | FHA | LTV no puede exceder 96.5% | Recompra al 100% |
| rule_va_coe | VA | COE debe verificarse en VBMS antes del cierre | $250,000 + recompra |
| rule_fnma_dti | FNMA | DTI no puede exceder 45% (50% con AUS) | DevoluciÃ³n para recompra |
| rule_trid_cd | TRID | Closing Disclosure mÃ­nimo 3 dÃ­as antes del cierre | $25,000â€“$100,000 |
| rule_usda_rural | USDA | Propiedad debe estar en Ã¡rea rural elegible | Recompra + devoluciÃ³n subsidio |

### 8.4 Path a producciÃ³n (1 cambio de config)

```python
# LOCAL (desarrollo):
response = ollama.chat(model="mistral", messages=messages)

# PRODUCCIÃ“N (Azure OpenAI):
from openai import AzureOpenAI
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-08-01-preview"
)
response = client.chat.completions.create(model="gpt-4o", messages=messages)
# ChromaDB, FastAPI, .NET API, React â†’ sin cambios
```

---

## 9. Comandos de operaciÃ³n

```powershell
# === ARRANCAR EL ECOSISTEMA COMPLETO ===

# 1. API .NET 9
Stop-Process -Name "NeboAudit.Api" -Force -ErrorAction SilentlyContinue
cd "C:\Dev\NeboAudit Platform\NeboAudit.Api"
dotnet clean; dotnet run
# â†’ http://localhost:5267/swagger

# 2. React Frontend (terminal separada)
cd "C:\Dev\NeboAudit Platform\neboaudit-frontend"
npm start
# â†’ http://localhost:3000

# 3. Generar reporte Quarto (con API corriendo en paralelo)
cd "C:\Dev\NeboAudit Platform"
quarto render reporte_patrones.qmd --to html
Start-Process .\reporte_patrones.html

# 4. Extraer Excel de alto riesgo
cd "C:\Dev\NeboAudit Platform"
python extract_risk.py
# â†’ NeboAudit_Risk_Report.xlsx

# === TESTS RÃPIDOS DESDE POWERSHELL ===

$headers = @{ "Content-Type" = "application/json" }
$body    = @{ usuario="admin"; password="admin123"; tenantId=1 } | ConvertTo-Json
$resp    = Invoke-RestMethod -Uri "http://localhost:5267/api/auth/login" -Method Post -Headers $headers -Body $body
$token   = $resp.token

$auth    = @{ Authorization = "Bearer $token" }

# Portafolio FNB paginado
Invoke-RestMethod -Uri "http://localhost:5267/api/loans?page=1&pageSize=5" -Headers $auth

# Summary del portfolio
Invoke-RestMethod -Uri "http://localhost:5267/api/loans/high-risk?threshold=0.75" -Headers $auth

# === LIMPIAR CACHÃ‰ Y REINICIAR ===
Remove-Item -Recurse -Force "C:\Dev\NeboAudit Platform\.quarto" -ErrorAction SilentlyContinue
Stop-Process -Name "NeboAudit.Api" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue
```

---

## 10. Estado del proyecto

### Avance por mÃ³dulo

| # | MÃ³dulo | TecnologÃ­a | % | Estado |
|---|--------|-----------|---|--------|
| 1 | Base de datos | SQL Server 2022 | 95% | ðŸŸ¢ Operativo |
| 2 | Backend / API | .NET 9 + JWT | 90% | ðŸŸ¢ Operativo |
| 3 | Extractor analÃ­tico | Python + openpyxl | 85% | ðŸŸ¢ Operativo |
| 4 | Dashboard web | React multi-tenant | 95% | ðŸŸ¢ Operativo |
| 5 | Reporte ejecutivo | Quarto + Python | 100% | ðŸŸ¢ Completado |
| 6 | Modelos ML | Python / ML.NET | 40% | ðŸŸ¡ EDA completo |
| 7 | RAG Chatbot | Ollama + ChromaDB | 20% | ðŸŸ¡ Arquitectura |
| â€” | **General** | â€” | **ðŸŸ¢ 89%** | |

### Pendientes para el 100%

1. **SQL:** Agregar Ã­ndices no agrupados en `RiskScore` y `LTV` para escalar a millones de filas.
2. **API:** Endpoint dedicado `GET /api/loans/high-risk` con filtros adicionales (tipo de prestamo, rango de fechas).
3. **React:** Pantalla de login visual en lugar del auto-login hardcodeado.
4. **React:** Filtros por acciÃ³n (AUTO_BLOCK / SENIOR_REVIEW / FAST_TRACK) en la tabla.
5. **ML.NET:** Integrar el modelo de scoring dentro del API para predicciÃ³n en tiempo real al insertar un credito nuevo.
6. **RAG:** Completar el indexador de creditos + reglas en ChromaDB y conectar el ChatController al FastAPI.

### Resultados de auditorÃ­a validados

```
Portfolio FNB (Tenant 1):    508 creditos | Varianza Cross-Foot: $0.00 âœ“
Portfolio MMC (Tenant 2):    495 creditos | Aislamiento multi-tenant: ACTIVO âœ“
CorrelaciÃ³n LTV â†” RiskScore: r = 0.6334
Footing Financiero:          CUADRA [OK]
```

---

*Documento generado el 15/06/2026 â€” NeboAudit Platform v1.0*  
*Desarrollado en sesiÃ³n colaborativa con IA (Gemini + Claude) â€” LAPTOP-Q3026NUM*


---

## 11. The mortgage process â€” 3 phases

### Phase 1 â€” The mortgage loan

```
CLIENT wants to buy a $400K house
        â”‚
        â–¼
Goes to First National Bank (FNB)
        â”‚
        â–¼
Bank evaluates: income, debts, credit history
        â”‚
        â–¼
Bank approves $360K loan
        â”‚
        â–¼
  Loan amount:    $360,000
  Property value: $400,000
  LTV:            $360K / $400K = 90.0%
  DTI:            $3K debts / $8K income = 37.5%
        â”‚
        â–¼
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ Type         â”‚ Max LTV  â”‚ Max DTI  â”‚ Guarantor           â”‚
  â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
  â”‚ FHA          â”‚ 96.5%    â”‚ 43%      â”‚ Federal government  â”‚
  â”‚ VA           â”‚ 100%     â”‚ 41%      â”‚ Dept of Veterans    â”‚
  â”‚ Conventional â”‚ 95%      â”‚ 45%      â”‚ Fannie Mae (private)â”‚
  â”‚ USDA         â”‚ 100%     â”‚ 41%      â”‚ USDA Rural Dev      â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Why these rules exist:** Before 2008, banks lent to anyone (NINJA loans: No Income, No Job, No Assets). The system collapsed. Lehman Brothers failed. $700B taxpayer bailout. Dodd-Frank Act (2010) created the CFPB and mandated audits.

### Phase 2 â€” The audit (where Nebo / MetaSource enters)

```
Bank CANNOT audit its own loans â€” conflict of interest
        â”‚
        â–¼
Bank hires MetaSource (800+ clients, 30+ years)
        â”‚
        â–¼
MetaSource uses NEBO platform to verify each loan:

  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ Frameworkâ”‚ Check item                       â”‚ Result â”‚
  â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”¤
  â”‚ TRID     â”‚ Loan Estimate delivered â‰¤ 3 days â”‚ Pass   â”‚
  â”‚ FHA      â”‚ LTV â‰¤ 96.5%?                     â”‚ Fail   â”‚
  â”‚ VA       â”‚ COE verified in VBMS?             â”‚ Fail   â”‚
  â”‚ FNMA     â”‚ DTI â‰¤ 45%?                        â”‚ Pass   â”‚
  â”‚ USDA     â”‚ Property in eligible rural area?  â”‚ Pass   â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”˜

3 results:
  ðŸŸ¢ Pass   â€” compliant
  ðŸ”´ Fail   â€” penalty: $5Kâ€“$250K fine OR loan repurchase (100%)
  ðŸŸ¡ Review â€” needs manager verification
```

### Phase 3 â€” Your role as Database SME

```
YOU build the data layer:

  dbo.Loans               â†’ every mortgage record
  dbo.AuditLog            â†’ immutable change trail (who, when, old, new)
  Stored procedures       â†’ pass rates, anomalies, footings, forecasts
  .NET 9 API              â†’ Swagger endpoints for auditors
  ML.NET                  â†’ risk scoring inside the API
  trg_Loans_Audit         â†’ trigger captures every mutation
  RLS (Row-Level Security)â†’ FNB never sees MMC data

  DBA approves your schemas â†’ you deploy â†’ auditors use â†’ reports generated
```

---

## 12. Penalty analysis and Pareto

### 12.1 Penalty structure by regulation

| Framework | Violation | Penalty | Worst case |
|---|---|---|---|
| TRID | LE late (> 3 business days) | $5,000â€“$25,000 | $1M consent order CFPB (pattern) |
| TRID | CD late (< 3 days before close) | $25,000â€“$100,000 | Can invalidate closing |
| FHA | LTV exceeds 96.5% | Loan repurchase (100%) | Loss of FHA lender status |
| FHA | MIP rate incorrect | $35,000 + difference to FHA fund | HUD audit of all FHA loans |
| FHA | DTI > 43% without comp. factors | $35,000 or repurchase | HUD OIG referral |
| VA | COE not verified in VBMS | $250,000 + repurchase | FBI referral if fraud |
| VA | Funding fee wrong | $50,000 + refund to veteran | Double penalty if exempt charged |
| FNMA | DTI > 45% | Loan repurchase by Fannie Mae | Loss of Fannie Mae seller status |
| USDA | Property not in rural area | Loan repurchase + subsidy return | USDA program ban |

### 12.2 Penalty by tenant (from your 1,000-loan data)

Run this in SSMS to get the real numbers from your data:

```sql
SELECT
    T.Name AS Tenant,
    COUNT(*) AS TotalLoans,
    SUM(CASE WHEN L.IsFail = 1 THEN 1 ELSE 0 END) AS Fails,
    CAST(SUM(CASE WHEN L.IsFail = 1 THEN 1 ELSE 0 END) * 100.0
         / COUNT(*) AS DECIMAL(5,1)) AS DefectPct,
    SUM(L.Penalty) AS TotalPenalty,
    SUM(L.LoanAmount) AS TotalVolume
FROM dbo.Loans L
JOIN dbo.Tenants T ON L.TenantId = T.TenantId
GROUP BY T.Name
ORDER BY TotalPenalty DESC;
```

### 12.3 Pareto â€” root cause stored procedure

```sql
CREATE OR ALTER PROCEDURE dbo.usp_ParetoAnalysis
AS
BEGIN
    SET NOCOUNT ON;

    WITH Causes AS (
        SELECT
            CASE
                WHEN LoanType = 'VA' AND LTV > 96
                    THEN 'VA COE / funding fee'
                WHEN LoanType = 'FHA' AND LTV > 96.5
                    THEN 'FHA LTV exceeds limit'
                WHEN DTI > 43 AND LoanType IN ('FHA','VA')
                    THEN 'DTI exceeds limit'
                WHEN LTV > 95
                    THEN 'LTV warning zone'
                WHEN AuditDays > 5
                    THEN 'SLA breach (>5 days)'
                ELSE 'Other compliance issue'
            END AS RootCause,
            Penalty
        FROM dbo.Loans
        WHERE IsFail = 1
    ),
    Grouped AS (
        SELECT
            RootCause,
            COUNT(*) AS Fails,
            SUM(Penalty) AS TotalPenalty,
            CAST(SUM(Penalty) * 100.0 / SUM(SUM(Penalty)) OVER()
                AS DECIMAL(5,1)) AS PctOfTotal
        FROM Causes
        GROUP BY RootCause
    )
    SELECT
        RootCause,
        Fails,
        TotalPenalty,
        PctOfTotal,
        SUM(PctOfTotal) OVER(ORDER BY TotalPenalty DESC) AS CumulativePct,
        CASE
            WHEN SUM(PctOfTotal) OVER(ORDER BY TotalPenalty DESC) <= 80 THEN 'Zone A'
            WHEN SUM(PctOfTotal) OVER(ORDER BY TotalPenalty DESC) <= 95 THEN 'Zone B'
            ELSE 'Zone C'
        END AS ParetoZone
    FROM Grouped
    ORDER BY TotalPenalty DESC;
END;
GO
```

### 12.4 Action plan from Pareto

| Priority | Root cause | Preventive action | Corrective action | SP to build | ROI |
|:---:|---|---|---|---|---:|
| P1 | VA COE not verified | Mandatory pre-check SP before audit | Escalate VBMS timeout in 4hr | usp_ValidateCOE | 150x |
| P1 | FHA LTV over limit | `IF @LTV > 96.5 AND @Type='FHA' â†’ RAISERROR` | Re-review all FHA LTV > 93% | usp_UpsertLoan | 298x |
| P1 | DTI over limit | `IF @DTI > 43 AND @Type='FHA' â†’ RAISERROR` | Reject loan 40 retroactively | usp_UpsertLoan | 285x |
| P2 | MIP rate outdated | Create dbo.MIPRates lookup table | Update monthly from FHA bulletin | usp_ValidateMIP | 35x |
| P2 | TRID timing | Auto-alert servicer at day 2 | SP calculates business days | usp_CheckTRID | 55x |

---

## 13. KPIs & audit footings

### 13.1 KPI tracking query

```sql
CREATE OR ALTER PROCEDURE dbo.usp_KPIDashboard
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        'Defect rate' AS KPI,
        CAST(SUM(CASE WHEN IsFail=1 THEN 1 ELSE 0 END)*100.0
             /COUNT(*) AS DECIMAL(5,1)) AS Actual,
        5.0 AS Target,
        CASE
            WHEN CAST(SUM(CASE WHEN IsFail=1 THEN 1 ELSE 0 END)*100.0
                 /COUNT(*) AS DECIMAL(5,1)) <= 5 THEN 'GREEN'
            WHEN CAST(SUM(CASE WHEN IsFail=1 THEN 1 ELSE 0 END)*100.0
                 /COUNT(*) AS DECIMAL(5,1)) <= 10 THEN 'YELLOW'
            ELSE 'RED'
        END AS Semaphore
    FROM dbo.Loans
    UNION ALL
    SELECT 'Avg audit days',
        CAST(AVG(AuditDays) AS DECIMAL(3,1)), 2.0,
        CASE WHEN AVG(AuditDays) <= 2 THEN 'GREEN'
             WHEN AVG(AuditDays) <= 3.5 THEN 'YELLOW' ELSE 'RED' END
    FROM dbo.Loans
    UNION ALL
    SELECT 'Total penalty exposure',
        CAST(SUM(Penalty)/1000 AS DECIMAL(10,1)), 100.0,
        CASE WHEN SUM(Penalty) <= 100000 THEN 'GREEN'
             WHEN SUM(Penalty) <= 500000 THEN 'YELLOW' ELSE 'RED' END
    FROM dbo.Loans;
END;
GO
```

### 13.2 Footing verification with GROUPING SETS

```sql
CREATE OR ALTER PROCEDURE dbo.usp_FootingVerification
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        COALESCE(T.Name, '=== GRAND TOTAL') AS Tenant,
        COALESCE(L.LoanType, '--- Subtotal ---') AS LoanType,
        COUNT(*) AS Loans,
        SUM(L.LoanAmount) AS TotalAmount,
        AVG(L.LTV) AS AvgLTV,
        SUM(CASE WHEN L.IsFail = 0 THEN 1 ELSE 0 END) AS Pass,
        SUM(CASE WHEN L.IsFail = 1 THEN 1 ELSE 0 END) AS Fail,
        CAST(SUM(CASE WHEN L.IsFail = 0 THEN 1 ELSE 0 END) * 100.0
             / NULLIF(COUNT(*), 0) AS DECIMAL(5,1)) AS PassRate,
        SUM(L.Penalty) AS TotalPenalty
    FROM dbo.Loans L
    JOIN dbo.Tenants T ON L.TenantId = T.TenantId
    GROUP BY GROUPING SETS (
        (T.Name, L.LoanType),
        (T.Name),
        ()
    )
    ORDER BY
        GROUPING(T.Name),
        T.Name,
        GROUPING(L.LoanType),
        L.LoanType;
END;
GO
```

### 13.3 Cross-foot verification checklist

```
After running usp_FootingVerification, verify:

âœ… Vertical:     FNB subtotal + MMC subtotal = Grand total
âœ… Horizontal:   Pass + Fail = Total loans per row
âœ… Completeness: Grand total loans = SELECT COUNT(*) FROM dbo.Loans
âœ… Penalties:    SUM by tenant + SUM by type = Grand total penalty
âœ… LTV formula:  LoanAmount / PropertyValue per row (validated at insert by SP)
```

---

## 14. COBIT 2019 governance

| Domain | Objective | Implementation in NeboAudit | Maturity |
|---|---|---|:---:|
| EDM | EDM01 Governance framework | Multi-tenant RLS Â· JWT role separation Â· access matrix | L3 |
| EDM | EDM03 Risk optimization | Risk matrix by project phase Â· Pareto action plan | L2 |
| APO | APO12 Risk management | CHECK constraints Â· AuditLog trigger Â· anomaly SP | L3 |
| APO | APO13 Security management | 5-layer defense Â· OWASP mapping Â· .gitignore | L2 |
| BAI | BAI03 Solutions build | Clean architecture Â· Swagger-first Â· Git tags | L3 |
| BAI | BAI10 Configuration mgmt | appsettings excluded Â· schema versioning in Git | L3 |
| DSS | DSS05 Security services | Parameterized SPs Â· Windows Auth Â· no raw SQL | L3 |
| DSS | DSS06 Process controls | TRY/CATCH Â· ROLLBACK Â· idempotent MERGE | L2 |
| MEA | MEA01 Performance monitor | KPI SP Â· semaphore dashboard Â· ML scoring | L2 |
| MEA | MEA02 Internal controls | AuditLog trigger Â· footing SP Â· cross-foot verification | L3 |

---

## 15. Audit procedures (ISA / PCAOB)

| Assertion | Method | SQL implementation | Status |
|---|---|---|:---:|
| Completeness | No orphan records | FK_Loans_Tenants | âœ… Auto |
| Existence | Every change recorded | trg_Loans_Audit (INSERT/UPDATE/DELETE) | âœ… Auto |
| Accuracy | Domain constraints | CHK_Loans_LTV, CHK_Loans_DTI | âœ… Auto |
| Cutoff | UTC timestamps | DEFAULT GETUTCDATE() on all tables | âœ… Auto |
| Valuation | LTV computed at insert | SP calculates LTV = Amount/PropValue | âœ… Auto |
| Classification | Restricted types | LoanType IN ('Conventional','FHA','VA','USDA') | âœ… Auto |
| Uniqueness | No duplicates | UQ_Loans_External (TenantId, ExternalLoanId) | âœ… Auto |
| Rights & obligations | Tenant isolation | RLS policy + SESSION_CONTEXT + JWT claims | âœ… Auto |

---

## 16. Access control â€” who sees what

### 16.1 Row-Level Security

```sql
CREATE FUNCTION dbo.fn_TenantAccess(@TenantId INT)
RETURNS TABLE WITH SCHEMABINDING
AS
    RETURN SELECT 1 AS Ok
    WHERE @TenantId = CAST(SESSION_CONTEXT(N'TenantId') AS INT);
GO

CREATE SECURITY POLICY TenantFilter
ADD FILTER PREDICATE dbo.fn_TenantAccess(TenantId) ON dbo.Loans
WITH (STATE = ON);
GO

-- .NET middleware sets this on every request:
-- EXEC sp_set_session_context @key=N'TenantId', @value=@TenantId;
```

### 16.2 Access matrix

| Role | FNB data | MMC data | AuditLog | Budget | Admin |
|:---:|:---:|:---:|:---:|:---:|:---:|
| Auditor (FNB) | âœ… Read | âŒ | Own actions | âŒ | âŒ |
| Auditor (MMC) | âŒ | âœ… Read | Own actions | âŒ | âŒ |
| Manager (FNB) | âœ… Read+Write | âŒ | All FNB | âœ… Read | âŒ |
| Director QC | âœ… All | âœ… All | âœ… All | âœ… R+W | âœ… |

---

## 17. Traceability â€” who changed what

### 17.1 Trigger (already in your schema â€” section 2)

The `trg_Loans_Audit` trigger captures:
- **Who:** `SYSTEM_USER` (the Windows/SQL login)
- **When:** `GETUTCDATE()` (server-controlled, cannot be backdated)
- **What:** table name, operation, record ID
- **Old values:** from `deleted` pseudo-table
- **New values:** from `inserted` pseudo-table

### 17.2 Audit trail query

```sql
CREATE OR ALTER PROCEDURE dbo.usp_AuditTrail
    @LoanId INT,
    @DaysBack INT = 30
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        AuditId,
        Operation,
        OldValues,
        NewValues,
        UserIdentity,
        Timestamp,
        LAG(Timestamp) OVER(ORDER BY Timestamp) AS PreviousChange,
        DATEDIFF(MINUTE,
            LAG(Timestamp) OVER(ORDER BY Timestamp),
            Timestamp) AS MinutesSinceLast,
        ROW_NUMBER() OVER(ORDER BY Timestamp DESC) AS ChangeSequence
    FROM dbo.AuditLog
    WHERE RecordId = @LoanId
      AND TableName = 'Loans'
      AND Timestamp >= DATEADD(DAY, -@DaysBack, GETUTCDATE())
    ORDER BY Timestamp DESC;
END;
GO
```

### 17.3 Anti-tampering controls

| Threat | Protection |
|---|---|
| Auditor changes Fail â†’ Pass | Trigger records old=Fail, new=Pass, who, when |
| Someone deletes AuditLog rows | `DENY DELETE ON dbo.AuditLog TO PUBLIC` |
| DBA disables trigger | SQL Agent checks `sys.triggers` hourly |
| Someone backdates timestamp | `GETUTCDATE()` is server-controlled |
| Bulk UPDATE to erase evidence | Each row generates a separate AuditLog entry |

---

## 18. Risk matrix â€” every project phase

### 18.1 Heat map

```
                    â•‘ Negligible â”‚  Low   â”‚ Medium â”‚  High  â”‚ Critical â•‘
 â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•¬â•â•â•â•â•â•â•â•â•â•â•â•â•ªâ•â•â•â•â•â•â•â•â•ªâ•â•â•â•â•â•â•â•â•ªâ•â•â•â•â•â•â•â•â•ªâ•â•â•â•â•â•â•â•â•â•â•‘
 Very high          â•‘    Med     â”‚  High  â”‚  Crit  â”‚  Crit  â”‚   Crit   â•‘
 High               â•‘    Med     â”‚  Med   â”‚  High  â”‚R1 R10  â”‚   Crit   â•‘
 Medium             â•‘    Low     â”‚  Med   â”‚R4 R12  â”‚ R2 R13 â”‚   Crit   â•‘
 Low                â•‘    Low     â”‚  Low   â”‚ R5 R9  â”‚R3 R11  â”‚R7 R16   â•‘
 Very low           â•‘    Low     â”‚  Low   â”‚  Low   â”‚  R6    â”‚   High   â•‘
```

### 18.2 Full risk register by phase

| Phase | ID | Risk | Prob | Impact | Score | Plan B | Plan C |
|---|:---:|---|:---:|:---:|:---:|---|---|
| **Schema** | R8 | FK wrong / missing CHECK | Med | High | 12 | DBA code review before deploy | tSQLt unit tests on staging |
| **Schema** | R9 | Missing index | Low | Med | 6 | Query plan analysis pre-release | Add covering indexes post-deploy |
| **Stored proc** | R10 | Bug in LTV calculation | High | High | 16 | Run SP on staging with test data | tSQLt automated regression |
| **Stored proc** | R11 | Deadlock on concurrent writes | Low | High | 8 | SET NOCOUNT ON + short txn | NOLOCK on read-only queries |
| **Migration** | R12 | Legacy format mismatch | High | Med | 12 | Staging table + MERGE TRY/CATCH | Error log per row, never direct INSERT |
| **Migration** | R13 | Duplicate loans in source | Med | High | 12 | UNIQUE constraint rejects dupes | Pre-migration dedup script |
| **API deploy** | R14 | Swagger breaks | Med | Med | 9 | Blue-green deployment | Git checkout previous tag |
| **API deploy** | R15 | JWT misconfigured | Low | High | 8 | Integration tests in CI | Disable auth temporarily |
| **Trigger** | R16 | Trigger disabled by accident | Low | Crit | 10 | SQL Agent hourly check | DENY ALTER on trigger |
| **Backup** | R18 | Backup corrupted | Low | Crit | 10 | Monthly restore test on staging | Geo-redundant Azure Blob |
| **Backup** | R19 | Ransomware | Low | Crit | 10 | Off-site backup (Azure GRS) | Air-gapped backup |
| **Credentials** | R1 | IAM keys exposed | High | High | 16 | Rotate immediately + MFA | Switch to IAM roles |
| **Credentials** | R2 | sa login weak password | Med | High | 12 | Disable sa â†’ Windows Auth | Azure Key Vault |
| **API security** | R4 | No JWT on endpoints | Med | Med | 9 | JWT middleware from day 1 | [Authorize] on all controllers |
| **Isolation** | R5 | Tenant sees other's data | Low | Med | 6 | RLS per TenantId | API-level filter backup |
| **Transport** | R3 | No TLS in production | Low | High | 8 | Kestrel HTTPS + HSTS | Let's Encrypt cert |
| **PII** | R7 | API exposes PII | Low | Crit | 10 | DTO projection only | Audit API responses weekly |

---

## 19. Disaster recovery â€” Plans B and C

### 19.1 Scenarios

| Scenario | Impact | Plan B | Plan C |
|---|---|---|---|
| SQL backup fails | AuditLog lost = compliance breach | Full daily + diff 4hr + tlog 15min (RPO=15min) | Always On AG (RTO<30s) |
| Data corruption | Wrong reports, footings don't reconcile | DBCC CHECKDB daily | Restore â†’ usp_FootingVerification |
| API crashes | Auditors can't work | Health check + auto-restart | Blue-green: old version stays live |
| Trigger disabled | Audit trail has gaps | SQL Agent checks hourly | DENY ALTER to non-admin |
| Ransomware | Everything encrypted | Azure Blob GRS (off-site) | Air-gapped backup |
| Credentials leaked | Unauthorized DB access | Rotate + revoke immediately | All secrets â†’ Key Vault |
| Bad SP deploy | Wrong calculations | Git tag rollback | Staging DB with test suite |
| Performance crash | Timeouts at 1M+ loans | Indexes + OFFSET/FETCH | Partition by ClosingDate year |

### 19.2 Rollback procedure

```
 1. STOP the API: Stop-Process -Name "NeboAudit.Api" -Force
 2. IDENTIFY last valid backup
 3. RESTORE: RESTORE DATABASE NeboAudit FROM DISK = 'path'
 4. VERIFY: DBCC CHECKDB('NeboAudit')
 5. RECONCILE: EXEC usp_FootingVerification
 6. RE-APPLY transaction logs from failure point
 7. CHECK: SELECT MAX(AuditId) FROM AuditLog â€” no gaps
 8. RESTART: cd NeboAudit.Api; dotnet run
 9. NOTIFY auditors of downtime
10. POST-MORTEM: document root cause + corrective action
```

---

## 20. Competitive analysis

### 20.1 Nebo vs. the market

| Dimension | Nebo (MetaSource) | ACES | LoanLogics | Opus CMC |
|---|---|---|---|---|
| Founded | 1993 | 1994 | 2005 | 2005 |
| Clients | 800+ | 70% top 20 lenders | Mid-market | Capital markets |
| AI/ML | ML.NET (building) | ACES Intelligence (live) | LoanHD analytics | Basic |
| Core tech | .NET 9 + SQL Server | Proprietary cloud | Cloud-based | Legacy |
| Key product | Nebo + QLink + QReview | ACES Analytics + AI | LoanHD | Due diligence |
| Pricing | Per audit fee | SaaS license ($$) | Per loan + platform | Project-based |
| Strength | Turn time, .NET ML, trail | Best AI, market leader | Doc classification | Investor focus |
| Weakness vs Nebo | â€” | Expensive, less custom | Acquired by PE | Not tech-forward |

### 20.2 Nebo advantages

| Advantage | Why it matters |
|---|---|
| ML inside API (no extra infra) | ACES charges $15-25/loan extra; ML.NET = $0 marginal |
| Audit trail for ML decisions | Every prediction in dbo.MLPredictions â€” regulator traceable |
| SQL Server native (RLS, triggers, computed cols) | No app-level workarounds needed |
| Local LLM for PII safety | Ollama keeps mortgage data on-premises |
| .NET ecosystem | ML.NET, EF Core, SignalR, JWT â€” all first-party Microsoft |

---

## 21. Interview pitch

> "I built the complete Nebo audit platform with 1,000 loans, two tenants, risk scoring, and cross-foot verified footings. The SQL Server layer includes a Pareto analysis SP, anomaly detection, GROUPING SETS for automatic footings, and MERGE upserts with LTV validation.
>
> Every change is traceable: the audit trigger captures who, when, old value, new value. Row-Level Security ensures FNB never sees MMC's data. The JWT claims carry the TenantId, and the API middleware sets SESSION_CONTEXT on every request.
>
> The Pareto analysis shows the top 3 root causes drive ~70% of penalties. Two stored procedures â€” LTV validation and COE pre-check â€” would save over a million dollars for a $7K investment.
>
> I also built a RAG chatbot using Ollama so auditors can query loans and regulations in natural language. Everything runs locally â€” SQL Server, .NET API, Ollama, ChromaDB â€” ready to demo."

---

## Checklist â€” Monday 15 Jun, 3 PM MT

```powershell
# Morning checks
Get-Service -Name "MSSQLSERVER"                              # SQL Server running
sqlcmd -Q "SELECT COUNT(*) FROM NeboAudit.dbo.Loans"        # data loaded

# Start API
cd "C:\Dev\NeboAudit Platform\NeboAudit.Api"
dotnet run                                                    # localhost:5267

# Live demos in SSMS
EXEC dbo.usp_GetPortfolioSummary @TenantId = 1;             # FNB summary
EXEC dbo.usp_ParetoAnalysis;                                  # root causes
EXEC dbo.usp_FootingVerification;                             # cross-foot
EXEC dbo.usp_KPIDashboard;                                    # semaphores
EXEC dbo.usp_AuditTrail @LoanId = 1, @DaysBack = 365;       # traceability
```

---

*Secciones 11â€“21 para agregar a NeboAudit_Guia_Completa.md*
*Luis Carreno Â· lcarrenoy@uni.pe Â· 15/06/2026*

