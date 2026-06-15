-- ========================================================
-- NeboAudit Platform — Database Schema & Core Architecture
-- Target: SQL Server 2022 (LAPTOP-Q3026NUM)
-- ========================================================

USE master;
GO
if exists (select * from sys.databases where name='NeboAudit')
begin
    alter database NeboAudit set single_user with rollback immediate;
    drop database NeboAudit;
end
GO

CREATE DATABASE NeboAudit;
GO
USE NeboAudit;
GO

-- 2.1 Tablas Base del Sistema Multi-Tenant
CREATE TABLE dbo.Tenants (
    TenantId INT IDENTITY(1,1) PRIMARY KEY,
    Code VARCHAR(10) NOT NULL UNIQUE,
    Name NVARCHAR(100) NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE()
);

CREATE TABLE dbo.Loans (
    LoanId INT IDENTITY(1,1) PRIMARY KEY,
    TenantId INT NOT NULL,
    ExternalLoanId VARCHAR(50) NOT NULL,
    LoanType VARCHAR(20) NOT NULL, -- Conventional, FHA, VA, USDA
    LoanAmount DECIMAL(18,2) NOT NULL,
    PropertyValue DECIMAL(18,2) NOT NULL,
    LTV DECIMAL(5,2) NOT NULL,
    DTI DECIMAL(5,2) NOT NULL,
    AuditDays DECIMAL(3,1) NOT NULL,
    ClosingDate DATETIME2 NOT NULL,
    IsFail BIT NOT NULL DEFAULT 0,
    Penalty DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    RiskScore DECIMAL(5,4) NULL,
    AutomatedAction VARCHAR(30) NULL, -- FAST_TRACK, SENIOR_REVIEW, AUTO_BLOCK
    CONSTRAINT FK_Loans_Tenants FOREIGN KEY (TenantId) REFERENCES dbo.Tenants(TenantId),
    CONSTRAINT UQ_Loans_External UNIQUE (TenantId, ExternalLoanId),
    CONSTRAINT CHK_Loans_LTV CHECK (LTV > 0),
    CONSTRAINT CHK_Loans_DTI CHECK (DTI > 0)
);
CREATE INDEX IX_Loans_Tenant_Fail ON dbo.Loans(TenantId, IsFail);
CREATE INDEX IX_Loans_ClosingDate ON dbo.Loans(ClosingDate);

CREATE TABLE dbo.ComplianceRules (
    RuleId VARCHAR(50) PRIMARY KEY,
    Framework VARCHAR(20) NOT NULL, -- TRID, FHA, VA, FNMA, USDA
    Description NVARCHAR(50) NOT NULL,
    BasePenalty DECIMAL(18,2) NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1
);

CREATE TABLE dbo.AuditLog (
    AuditId INT IDENTITY(1,1) PRIMARY KEY,
    TableName VARCHAR(50) NOT NULL,
    Operation VARCHAR(10) NOT NULL,
    RecordId INT NOT NULL,
    OldValues NVARCHAR(MAX) NULL,
    NewValues NVARCHAR(MAX) NULL,
    UserIdentity NVARCHAR(128) NOT NULL DEFAULT SYSTEM_USER,
    Timestamp DATETIME2 NOT NULL DEFAULT GETUTCDATE()
);
GO

-- 2.2 Inserción de Datos Maestros y Simulaciones
INSERT INTO dbo.Tenants (Code, Name) VALUES ('FNB', 'First National Bank'), ('MMC', 'Mega Mortgage Corp');

INSERT INTO dbo.ComplianceRules (RuleId, Framework, Description, BasePenalty) VALUES
('RULE_FHA_LTV', 'FHA', 'FHA LTV maximum boundary constraint 96.5%', 15000.00),
('RULE_FNMA_DTI', 'FNMA', 'Fannie Mae DTI hard cap ceiling limit 45%', 25000.00),
('RULE_VA_COE', 'VA', 'Certificate of Eligibility verification process', 50000.00);

-- Semilla de Pruebas (Portafolio Base)
INSERT INTO dbo.Loans (TenantId, ExternalLoanId, LoanType, LoanAmount, PropertyValue, LTV, DTI, AuditDays, ClosingDate, IsFail, Penalty, RiskScore, AutomatedAction)
VALUES 
(1, 'LN-2026-001', 'FHA', 320000.00, 330000.00, 96.97, 38.50, 1.5, '2026-03-15', 1, 335000.00, 0.9240, 'AUTO_BLOCK'),
(1, 'LN-2026-002', 'Conventional', 450000.00, 500000.00, 90.00, 46.20, 3.2, '2026-04-20', 1, 240000.00, 0.7850, 'SENIOR_REVIEW'),
(2, 'LN-2026-003', 'VA', 280000.00, 280000.00, 100.00, 32.10, 0.8, '2026-05-12', 0, 0.00, 0.1210, 'FAST_TRACK');
GO

-- 2.3 Stored Procedures de Control Financiero y Auditoría Cross-Foot
CREATE OR ALTER PROCEDURE dbo.usp_GetPortfolioSummary
    @TenantId INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT 
        COUNT(LoanId) AS TotalLoans,
        SUM(LoanAmount) AS TotalPortfolioVolume,
        SUM(CAST(IsFail AS INT)) AS TotalDefects,
        ROUND(AVG(RiskScore), 4) AS AverageRiskScore,
        SUM(Penalty) AS TotalPenaltyExposure,
        -- Verificación matemática estricta Cross-Foot
        ROUND(SUM(CASE WHEN IsFail = 1 THEN Penalty ELSE 0 END), 2) AS CrossFootExpected,
        ROUND(ABS(SUM(Penalty) - SUM(CASE WHEN IsFail = 1 THEN Penalty ELSE 0 END)), 2) AS CrossFootVariance
    FROM dbo.Loans
    WHERE TenantId = @TenantId;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_GetHighRiskLoans
    @TenantId INT,
    @Threshold DECIMAL(5,4) = 0.5000
AS
BEGIN
    SET NOCOUNT ON;
    SELECT 
        ExternalLoanId, LoanType, LoanAmount, LTV, DTI, RiskScore, AutomatedAction
    FROM dbo.Loans
    WHERE TenantId = @TenantId AND RiskScore >= @Threshold
    ORDER BY RiskScore DESC;
END;
GO