
---

## 11. The mortgage process — 3 phases

### Phase 1 — The mortgage loan

```
CLIENT wants to buy a $400K house
        │
        ▼
Goes to First National Bank (FNB)
        │
        ▼
Bank evaluates: income, debts, credit history
        │
        ▼
Bank approves $360K loan
        │
        ▼
  Loan amount:    $360,000
  Property value: $400,000
  LTV:            $360K / $400K = 90.0%
  DTI:            $3K debts / $8K income = 37.5%
        │
        ▼
  ┌──────────────┬──────────┬──────────┬─────────────────────┐
  │ Type         │ Max LTV  │ Max DTI  │ Guarantor           │
  ├──────────────┼──────────┼──────────┼─────────────────────┤
  │ FHA          │ 96.5%    │ 43%      │ Federal government  │
  │ VA           │ 100%     │ 41%      │ Dept of Veterans    │
  │ Conventional │ 95%      │ 45%      │ Fannie Mae (private)│
  │ USDA         │ 100%     │ 41%      │ USDA Rural Dev      │
  └──────────────┴──────────┴──────────┴─────────────────────┘
```

**Why these rules exist:** Before 2008, banks lent to anyone (NINJA loans: No Income, No Job, No Assets). The system collapsed. Lehman Brothers failed. $700B taxpayer bailout. Dodd-Frank Act (2010) created the CFPB and mandated audits.

### Phase 2 — The audit (where Nebo / MetaSource enters)

```
Bank CANNOT audit its own loans — conflict of interest
        │
        ▼
Bank hires MetaSource (800+ clients, 30+ years)
        │
        ▼
MetaSource uses NEBO platform to verify each loan:

  ┌──────────┬──────────────────────────────────┬────────┐
  │ Framework│ Check item                       │ Result │
  ├──────────┼──────────────────────────────────┼────────┤
  │ TRID     │ Loan Estimate delivered ≤ 3 days │ Pass   │
  │ FHA      │ LTV ≤ 96.5%?                     │ Fail   │
  │ VA       │ COE verified in VBMS?             │ Fail   │
  │ FNMA     │ DTI ≤ 45%?                        │ Pass   │
  │ USDA     │ Property in eligible rural area?  │ Pass   │
  └──────────┴──────────────────────────────────┴────────┘

3 results:
  🟢 Pass   — compliant
  🔴 Fail   — penalty: $5K–$250K fine OR loan repurchase (100%)
  🟡 Review — needs manager verification
```

### Phase 3 — Your role as Database SME

```
YOU build the data layer:

  dbo.Loans               → every mortgage record
  dbo.AuditLog            → immutable change trail (who, when, old, new)
  Stored procedures       → pass rates, anomalies, footings, forecasts
  .NET 9 API              → Swagger endpoints for auditors
  ML.NET                  → risk scoring inside the API
  trg_Loans_Audit         → trigger captures every mutation
  RLS (Row-Level Security)→ FNB never sees MMC data

  DBA approves your schemas → you deploy → auditors use → reports generated
```

---

## 12. Penalty analysis and Pareto

### 12.1 Penalty structure by regulation

| Framework | Violation | Penalty | Worst case |
|---|---|---|---|
| TRID | LE late (> 3 business days) | $5,000–$25,000 | $1M consent order CFPB (pattern) |
| TRID | CD late (< 3 days before close) | $25,000–$100,000 | Can invalidate closing |
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

### 12.3 Pareto — root cause stored procedure

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
| P1 | FHA LTV over limit | `IF @LTV > 96.5 AND @Type='FHA' → RAISERROR` | Re-review all FHA LTV > 93% | usp_UpsertLoan | 298x |
| P1 | DTI over limit | `IF @DTI > 43 AND @Type='FHA' → RAISERROR` | Reject loan 40 retroactively | usp_UpsertLoan | 285x |
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

✅ Vertical:     FNB subtotal + MMC subtotal = Grand total
✅ Horizontal:   Pass + Fail = Total loans per row
✅ Completeness: Grand total loans = SELECT COUNT(*) FROM dbo.Loans
✅ Penalties:    SUM by tenant + SUM by type = Grand total penalty
✅ LTV formula:  LoanAmount / PropertyValue per row (validated at insert by SP)
```

---

## 14. COBIT 2019 governance

| Domain | Objective | Implementation in NeboAudit | Maturity |
|---|---|---|:---:|
| EDM | EDM01 Governance framework | Multi-tenant RLS · JWT role separation · access matrix | L3 |
| EDM | EDM03 Risk optimization | Risk matrix by project phase · Pareto action plan | L2 |
| APO | APO12 Risk management | CHECK constraints · AuditLog trigger · anomaly SP | L3 |
| APO | APO13 Security management | 5-layer defense · OWASP mapping · .gitignore | L2 |
| BAI | BAI03 Solutions build | Clean architecture · Swagger-first · Git tags | L3 |
| BAI | BAI10 Configuration mgmt | appsettings excluded · schema versioning in Git | L3 |
| DSS | DSS05 Security services | Parameterized SPs · Windows Auth · no raw SQL | L3 |
| DSS | DSS06 Process controls | TRY/CATCH · ROLLBACK · idempotent MERGE | L2 |
| MEA | MEA01 Performance monitor | KPI SP · semaphore dashboard · ML scoring | L2 |
| MEA | MEA02 Internal controls | AuditLog trigger · footing SP · cross-foot verification | L3 |

---

## 15. Audit procedures (ISA / PCAOB)

| Assertion | Method | SQL implementation | Status |
|---|---|---|:---:|
| Completeness | No orphan records | FK_Loans_Tenants | ✅ Auto |
| Existence | Every change recorded | trg_Loans_Audit (INSERT/UPDATE/DELETE) | ✅ Auto |
| Accuracy | Domain constraints | CHK_Loans_LTV, CHK_Loans_DTI | ✅ Auto |
| Cutoff | UTC timestamps | DEFAULT GETUTCDATE() on all tables | ✅ Auto |
| Valuation | LTV computed at insert | SP calculates LTV = Amount/PropValue | ✅ Auto |
| Classification | Restricted types | LoanType IN ('Conventional','FHA','VA','USDA') | ✅ Auto |
| Uniqueness | No duplicates | UQ_Loans_External (TenantId, ExternalLoanId) | ✅ Auto |
| Rights & obligations | Tenant isolation | RLS policy + SESSION_CONTEXT + JWT claims | ✅ Auto |

---

## 16. Access control — who sees what

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
| Auditor (FNB) | ✅ Read | ❌ | Own actions | ❌ | ❌ |
| Auditor (MMC) | ❌ | ✅ Read | Own actions | ❌ | ❌ |
| Manager (FNB) | ✅ Read+Write | ❌ | All FNB | ✅ Read | ❌ |
| Director QC | ✅ All | ✅ All | ✅ All | ✅ R+W | ✅ |

---

## 17. Traceability — who changed what

### 17.1 Trigger (already in your schema — section 2)

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
| Auditor changes Fail → Pass | Trigger records old=Fail, new=Pass, who, when |
| Someone deletes AuditLog rows | `DENY DELETE ON dbo.AuditLog TO PUBLIC` |
| DBA disables trigger | SQL Agent checks `sys.triggers` hourly |
| Someone backdates timestamp | `GETUTCDATE()` is server-controlled |
| Bulk UPDATE to erase evidence | Each row generates a separate AuditLog entry |

---

## 18. Risk matrix — every project phase

### 18.1 Heat map

```
                    ║ Negligible │  Low   │ Medium │  High  │ Critical ║
 ═══════════════════╬════════════╪════════╪════════╪════════╪══════════║
 Very high          ║    Med     │  High  │  Crit  │  Crit  │   Crit   ║
 High               ║    Med     │  Med   │  High  │R1 R10  │   Crit   ║
 Medium             ║    Low     │  Med   │R4 R12  │ R2 R13 │   Crit   ║
 Low                ║    Low     │  Low   │ R5 R9  │R3 R11  │R7 R16   ║
 Very low           ║    Low     │  Low   │  Low   │  R6    │   High   ║
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
| **Credentials** | R2 | sa login weak password | Med | High | 12 | Disable sa → Windows Auth | Azure Key Vault |
| **API security** | R4 | No JWT on endpoints | Med | Med | 9 | JWT middleware from day 1 | [Authorize] on all controllers |
| **Isolation** | R5 | Tenant sees other's data | Low | Med | 6 | RLS per TenantId | API-level filter backup |
| **Transport** | R3 | No TLS in production | Low | High | 8 | Kestrel HTTPS + HSTS | Let's Encrypt cert |
| **PII** | R7 | API exposes PII | Low | Crit | 10 | DTO projection only | Audit API responses weekly |

---

## 19. Disaster recovery — Plans B and C

### 19.1 Scenarios

| Scenario | Impact | Plan B | Plan C |
|---|---|---|---|
| SQL backup fails | AuditLog lost = compliance breach | Full daily + diff 4hr + tlog 15min (RPO=15min) | Always On AG (RTO<30s) |
| Data corruption | Wrong reports, footings don't reconcile | DBCC CHECKDB daily | Restore → usp_FootingVerification |
| API crashes | Auditors can't work | Health check + auto-restart | Blue-green: old version stays live |
| Trigger disabled | Audit trail has gaps | SQL Agent checks hourly | DENY ALTER to non-admin |
| Ransomware | Everything encrypted | Azure Blob GRS (off-site) | Air-gapped backup |
| Credentials leaked | Unauthorized DB access | Rotate + revoke immediately | All secrets → Key Vault |
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
 7. CHECK: SELECT MAX(AuditId) FROM AuditLog — no gaps
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
| Weakness vs Nebo | — | Expensive, less custom | Acquired by PE | Not tech-forward |

### 20.2 Nebo advantages

| Advantage | Why it matters |
|---|---|
| ML inside API (no extra infra) | ACES charges $15-25/loan extra; ML.NET = $0 marginal |
| Audit trail for ML decisions | Every prediction in dbo.MLPredictions — regulator traceable |
| SQL Server native (RLS, triggers, computed cols) | No app-level workarounds needed |
| Local LLM for PII safety | Ollama keeps mortgage data on-premises |
| .NET ecosystem | ML.NET, EF Core, SignalR, JWT — all first-party Microsoft |

---

## 21. Interview pitch

> "I built the complete Nebo audit platform with 1,000 loans, two tenants, risk scoring, and cross-foot verified footings. The SQL Server layer includes a Pareto analysis SP, anomaly detection, GROUPING SETS for automatic footings, and MERGE upserts with LTV validation.
>
> Every change is traceable: the audit trigger captures who, when, old value, new value. Row-Level Security ensures FNB never sees MMC's data. The JWT claims carry the TenantId, and the API middleware sets SESSION_CONTEXT on every request.
>
> The Pareto analysis shows the top 3 root causes drive ~70% of penalties. Two stored procedures — LTV validation and COE pre-check — would save over a million dollars for a $7K investment.
>
> I also built a RAG chatbot using Ollama so auditors can query loans and regulations in natural language. Everything runs locally — SQL Server, .NET API, Ollama, ChromaDB — ready to demo."

---

## Checklist — Monday 15 Jun, 3 PM MT

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

*Secciones 11–21 para agregar a NeboAudit_Guia_Completa.md*
*Luis Carreño · lcarrenoy@uni.pe · 15/06/2026*
