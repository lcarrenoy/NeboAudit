USE NeboAudit;
GO
EXEC dbo.usp_GetPortfolioSummary @TenantId = 1;
GO
SELECT AutomatedAction, COUNT(*) AS Loans, CAST(AVG(RiskScore) AS DECIMAL(5,4)) AS AvgScore, SUM(Penalty) AS TotalPenalty, SUM(LoanAmount) AS TotalVolume FROM dbo.Loans GROUP BY AutomatedAction ORDER BY AvgScore DESC;
GO
SELECT TOP 10 ExternalLoanId, LoanType, LoanAmount, LTV, DTI, RiskScore, AutomatedAction, Penalty FROM dbo.Loans ORDER BY RiskScore DESC;
GO
SELECT T.Name, COUNT(*) AS Loans, SUM(CASE WHEN L.IsFail=1 THEN 1 ELSE 0 END) AS Fails, CAST(SUM(CASE WHEN L.IsFail=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) AS DECIMAL(5,1)) AS DefectPct, SUM(L.Penalty) AS Penalties FROM dbo.Loans L JOIN dbo.Tenants T ON L.TenantId=T.TenantId GROUP BY T.Name;
GO
