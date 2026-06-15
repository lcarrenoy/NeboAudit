Clear-Host
$ErrorActionPreference = "SilentlyContinue"

# Escaneo dinamico de la arquitectura de archivos real de NeboAudit Platform
$Rutas = @{
    "SQL_Procs"      = (Get-ChildItem -Path ".\" -Filter "*.sql" -Recurse -File | Select-Object -First 1 -ExpandProperty FullName)
    "API_Program"    = (Get-ChildItem -Path ".\" -Filter "Program.cs" -Recurse -File | Select-Object -First 1 -ExpandProperty FullName)
    "Frontend_API"   = (Get-ChildItem -Path ".\" -Filter "api.js" -Recurse -File | Select-Object -First 1 -ExpandProperty FullName)
    "Python_Script"  = (Get-ChildItem -Path ".\" -Filter "crear_qmd.py" -Recurse -File | Select-Object -First 1 -ExpandProperty FullName)
    "Quarto_Config"  = (Get-ChildItem -Path ".\" -Filter "reporte_patrones.qmd" -Recurse -File | Select-Object -First 1 -ExpandProperty FullName)
    "Quarto_HTML"    = (Get-ChildItem -Path ".\" -Filter "NeboAudit_FULL_Report.html" -Recurse -File | Select-Object -First 1 -ExpandProperty FullName)
    "PowerBI_File"   = (Get-ChildItem -Path ".\" -Filter "*Riesgo.pbix" -Recurse -File | Select-Object -First 1 -ExpandProperty FullName)
}

function Escribir-Header ($Texto) {
    Write-Host "`n=========================================================================" -ForegroundColor Cyan
    Write-Host "  $Texto" -ForegroundColor Cyan
    Write-Host "=========================================================================" -ForegroundColor Cyan
}

$EstadoAPI = if (Get-NetTCPConnection -LocalPort 5267 -State Listen 2>$null) { "ACTIVE" } else { "DOWN" }
$EstadoReact = if (Get-NetTCPConnection -LocalPort 3000 -State Listen 2>$null) { "ACTIVE" } else { "DOWN" }
$EstadoQuarto = if ($Rutas.Quarto_HTML) { "RENDER OK" } else { "MISSING" }
$EstadoPBI = if (Get-Process -Name "PBIDesktop" 2>$null) { "OPEN" } else { "OFFLINE" }

Escribir-Header "1. CUADRO DE CONTROL LOCAL (NEBOAUDIT PLATFORM)"
$Mask = "{0,-22} | {1,-10} | {2,-25}"
Write-Host ($Mask -f "Proceso / Capa", "Estado", "Ruta / URL Local") -ForegroundColor Yellow
Write-Host "------------------------------------------------------------------------"
Write-Host ($Mask -f "Backend .NET API (OAS)", $EstadoAPI, "http://localhost:5267/swagger")
Write-Host ($Mask -f "React Frontend", $EstadoReact, "http://localhost:3000")
Write-Host ($Mask -f "Power BI Scoring", $EstadoPBI, "NeboAudit_Riesgo.pbix")
Write-Host ($Mask -f "Reporte Quarto FULL", $EstadoQuarto, "docs/NeboAudit_FULL_Report.html")

Escribir-Header "2. CHECKLIST DE ENTREGABLES MAPPED"
$MaskChk = "{0,-5} | {1,-15} | {2,-12} | {3,-25}"
Write-Host ($MaskChk -f "CHK", "Modulo", "Estado", "Archivo") -ForegroundColor Yellow
Write-Host "------------------------------------------------------------------------"

# Obtenemos nombre real del archivo SQL mapeado
$SqlName = if ($Rutas.SQL_Procs) { Split-Path $Rutas.SQL_Procs -Leaf } else { "Script_Estructura.sql" }

$Componentes = @(
    @("SQL_Procs", "DB SQL (Schema)", $SqlName),
    @("API_Program", "API Core", "Program.cs"),
    @("Frontend_API", "Frontend Core", "api.js"),
    @("Python_Script", "Python Engine", "crear_qmd.py"),
    @("Quarto_Config", "Quarto Layout", "reporte_patrones.qmd"),
    @("Quarto_HTML", "Quarto Analytics", "NeboAudit_FULL_Report.html"),
    @("PowerBI_File", "Power BI Scoring", "NeboAudit_Riesgo.pbix")
)

foreach ($Comp in $Componentes) {
    $Status = if ($Rutas[$Comp[0]]) { "100%" } else { "MISSING" }
    $ChkBox = if ($Status -eq "100%") { "[X]" } else { "[ ]" }
    Write-Host ($MaskChk -f $ChkBox, $Comp[1], $Status, $Comp[2])
}

Escribir-Header "3. LINKS DE PRESENTACION PUBLICA Y DOCUMENTACION"
$LinksPresentacion = @{
    "Portal_Web"      = "https://lcarrenoy.github.io/nebo-frontend"
    "Quarto_FULL_Doc" = "https://lcarrenoy.github.io/NeboAudit-Core/docs/NeboAudit_FULL_Report.html"
    "Swagger_JSON"    = "http://localhost:5267/swagger/v1/swagger.json"
    "API_Railway"     = "https://nebo-api.up.railway.app/swagger"
    "PowerBI_Web"     = "https://app.powerbi.com/view?r=TU_LINK_PUBLICO_NEBO_AQUI"
    "GitHub_Repo"     = "https://github.com/lcarrenoy/NeboAudit"
}
$MaskLinks = "{0,-15} | {1,-50}"
foreach ($Llave in $LinksPresentacion.Keys) { Write-Host ($MaskLinks -f $Llave, $LinksPresentacion[$Llave]) -ForegroundColor Green }
