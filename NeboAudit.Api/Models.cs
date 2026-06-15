using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace NeboAudit.Api.Models
{
    [Table("Tenants")]
    public class Tenant
    {
        [Key]
        public int TenantId { get; set; }
        public string Code { get; set; } = null!;
        public string Name { get; set; } = null!;
        public bool IsActive { get; set; }
        public DateTime CreatedAt { get; set; }
    }

    [Table("Loans")]
    public class Loan
    {
        [Key]
        public int LoanId { get; set; }
        public int TenantId { get; set; }
        public string ExternalLoanId { get; set; } = null!;
        public string LoanType { get; set; } = null!; // Conventional, FHA, VA, USDA
        public decimal LoanAmount { get; set; }
        public decimal PropertyValue { get; set; }
        public decimal LTV { get; set; }
        public decimal DTI { get; set; }
        public decimal AuditDays { get; set; }
        public DateTime ClosingDate { get; set; }
        public bool IsFail { get; set; }
        public decimal Penalty { get; set; }
        public decimal? RiskScore { get; set; }
        public string? AutomatedAction { get; set; } // FAST_TRACK, SENIOR_REVIEW, AUTO_BLOCK

        [ForeignKey("TenantId")]
        public Tenant? Tenant { get; set; }
    }
}