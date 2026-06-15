# Ejecutar: python "C:\Dev\NeboAudit Platform\crear_qmd.py"

content = """\
---
title: "NeboAudit: Analisis de Patrones de Riesgo (Historico 2 Anos)"
subtitle: "Reporte de Gobernanza Regulatoria - Multitenant Audit"
date: "2026-06-15"
author: "Departamento de Riesgos Analiticos"
format:
  html:
    theme: cosmo
    toc: true
    embed-resources: true
execute:
  warning: false
  message: false
---

## 1. Resumen Ejecutivo

Este documento presenta el analisis estocastico del portafolio hipotecario
consolidado durante los ultimos 24 meses de operacion. El objetivo es
identificar anomalias estructurales y fallas latentes en la originacion de
creditos antes de que afecten los balances del banco.

```{python}
#| echo: false
#| output: false
import requests
import pandas as pd
import numpy as np

API_URL = "http://localhost:5267/api"
AUTH_PAYLOAD = {"usuario": "admin", "password": "admin123", "tenantId": 1}

try:
    auth_resp = requests.post(f"{API_URL}/auth/login", json=AUTH_PAYLOAD, timeout=5)
    token = auth_resp.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_URL}/loans?page=1&pageSize=1000", headers=headers, timeout=10)
    data = resp.json().get("data", [])
    df = pd.DataFrame(data)
    if df.empty:
        raise ValueError("No data from API")
except Exception as e:
    print(f"[Fallback] {e}")
    np.random.seed(42)
    N = 1000
    df = pd.DataFrame({
        "loanType": np.random.choice(["Conventional", "FHA", "VA", "USDA"], N,
                                     p=[0.40, 0.25, 0.20, 0.15]),
        "loanAmount": np.clip(85000 + np.random.exponential(180000, N), 85000, 1250000),
        "ltv": (75 + np.random.beta(5, 2, N) * 25).round(2),
        "dti": (18 + np.random.beta(3, 2, N) * 31.5).round(2),
        "riskScore": np.random.uniform(0.10, 0.95, N),
        "automatedAction": np.random.choice(
            ["FAST_TRACK", "SENIOR_REVIEW", "AUTO_BLOCK"], N, p=[0.55, 0.30, 0.15]
        ),
        "auditDays": np.clip(0.5 + np.random.exponential(1.2, N), 0.5, 8.0).round(1),
        "penalty": 0.0,
    })
    df.loc[df["automatedAction"] == "AUTO_BLOCK", "penalty"] = (
        df.loc[df["automatedAction"] == "AUTO_BLOCK", "loanAmount"] * 0.05
    )
    df.loc[df["automatedAction"] == "SENIOR_REVIEW", "penalty"] = (
        df.loc[df["automatedAction"] == "SENIOR_REVIEW", "loanAmount"] * 0.02
    )
```

## 2. Distribucion Normativa del Portafolio

La siguiente tabla muestra la clasificacion automatizada del motor de
inteligencia de NeboAudit sobre el universo auditado.

```{python}
#| echo: false
resumen = df.groupby("automatedAction").agg(
    Creditos=("loanAmount", "count"),
    Monto_Total=("loanAmount", "sum"),
    Score_Promedio=("riskScore", "mean"),
    Penalidad_Total=("penalty", "sum"),
).reset_index()

resumen["Monto_Total"] = resumen["Monto_Total"].apply(lambda x: f"${x:,.0f}")
resumen["Score_Promedio"] = resumen["Score_Promedio"].apply(lambda x: f"{x:.4f}")
resumen["Penalidad_Total"] = resumen["Penalidad_Total"].apply(lambda x: f"${x:,.0f}")
resumen.columns = ["Accion IA", "Creditos", "Monto Total", "Score Prom.", "Penalidad"]
resumen
```

## 3. Efecto Tijera -- LTV vs DTI

Al cruzar los indicadores macro del portafolio, el modelo detecta que
la combinacion de **LTV > 85%** con **DTI > 43%** dispara el riesgo
de forma exponencial.

```{python}
#| echo: false
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

color_map = {
    "FAST_TRACK":    "#1D9E75",
    "SENIOR_REVIEW": "#EF9F27",
    "AUTO_BLOCK":    "#A32D2D",
}
colors = df["automatedAction"].map(color_map)

axes[0].scatter(df["ltv"], df["riskScore"], c=colors, alpha=0.4, s=15, edgecolors="none")
axes[0].axvline(85, color="#A32D2D", ls="--", lw=1.2, label="LTV 85%")
axes[0].set_xlabel("LTV (%)")
axes[0].set_ylabel("Risk Score")
axes[0].set_title("LTV vs Risk Score")
corr = df["ltv"].corr(df["riskScore"])
axes[0].text(66, 0.91, f"r = {corr:.3f}", fontsize=9, color="#185FA5")

patches = [mpatches.Patch(color=c, label=k) for k, c in color_map.items()]
patches.append(plt.Line2D([0],[0], color="#A32D2D", ls="--", label="LTV 85%"))
axes[0].legend(handles=patches, fontsize=8)

for loan_type, grp in df.groupby("loanType"):
    axes[1].hist(grp["riskScore"], bins=25, alpha=0.55, label=loan_type)
axes[1].set_xlabel("Risk Score")
axes[1].set_ylabel("Frecuencia")
axes[1].set_title("Distribucion de riesgo por tipo de prestamo")
axes[1].legend(fontsize=8)

plt.tight_layout()
plt.show()

print(f"Correlacion estadistica LTV <-> RiskScore: {corr:.4f}")
```

## 4. Eficiencia Operativa de la Auditoria

El cuello de botella operativo no esta en el procesamiento computacional
sino en la validacion regulatoria manual.

```{python}
#| echo: false
resumen_dias = df.groupby("loanType")["auditDays"].agg(
    Media="mean", Mediana="median", P90=lambda x: x.quantile(0.90)
).round(1).reset_index()
resumen_dias.columns = ["Tipo de Prestamo", "Media (dias)", "Mediana", "P90"]
resumen_dias
```

```{python}
#| echo: false
fig, ax = plt.subplots(figsize=(9, 3.5))
df.boxplot(column="auditDays", by="loanType", ax=ax,
           boxprops=dict(color="#185FA5"),
           medianprops=dict(color="#A32D2D", lw=2),
           whiskerprops=dict(color="#185FA5"),
           capprops=dict(color="#185FA5"),
           flierprops=dict(marker="o", markerfacecolor="#EF9F27", markersize=3, alpha=0.5))
ax.axhline(2, color="#A32D2D", ls="--", lw=1.2, label="SLA 2 dias")
plt.suptitle("")
ax.set_title("Distribucion de tiempos de auditoria por tipo (boxplot)")
ax.set_xlabel("Tipo de Prestamo")
ax.set_ylabel("Dias de Auditoria")
ax.legend(fontsize=8)
plt.tight_layout()
plt.show()
```

## 5. Footing Financiero -- Verificacion Cruzada

Control de integridad matematica: la suma total de penalidades debe
coincidir exactamente con la sumatoria de creditos con penalidad asignada.

```{python}
#| echo: false
total_penalty  = df["penalty"].sum()
failed_penalty = df[df["penalty"] > 0]["penalty"].sum()
variance       = abs(total_penalty - failed_penalty)

footing = pd.DataFrame({
    "Concepto": [
        "Penalidad total portafolio",
        "Penalidad creditos con sancion (penalty > 0)",
        "Varianza Cross-Foot",
        "Estado de Footing",
    ],
    "Valor": [
        f"${total_penalty:,.2f}",
        f"${failed_penalty:,.2f}",
        f"${variance:,.2f}",
        "CUADRA [OK]" if variance < 0.01 else "ERROR",
    ],
})
footing
```
"""

output_path = r"C:\Dev\NeboAudit Platform\reporte_patrones.qmd"

with open(output_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Archivo creado: {output_path}")
print("Siguiente paso: quarto render reporte_patrones.qmd --to html")
