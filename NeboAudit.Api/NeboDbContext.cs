using Microsoft.EntityFrameworkCore;
using NeboAudit.Api.Models;

namespace NeboAudit.Api.Data
{
    public class NeboDbContext : DbContext
    {
        public NeboDbContext(DbContextOptions<NeboDbContext> options) : base(options) { }

        public DbSet<Tenant> Tenants { get; set; }
        public DbSet<Loan> Loans { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);
            
            // Mapeo preciso para evitar pérdida de decimales en auditorías de riesgo
            modelBuilder.Entity<Loan>().Property(p => p.LoanAmount).HasPrecision(18, 2);
            modelBuilder.Entity<Loan>().Property(p => p.PropertyValue).HasPrecision(18, 2);
            modelBuilder.Entity<Loan>().Property(p => p.LTV).HasPrecision(5, 2);
            modelBuilder.Entity<Loan>().Property(p => p.DTI).HasPrecision(5, 2);
            modelBuilder.Entity<Loan>().Property(p => p.AuditDays).HasPrecision(3, 1);
            modelBuilder.Entity<Loan>().Property(p => p.Penalty).HasPrecision(18, 2);
            modelBuilder.Entity<Loan>().Property(p => p.RiskScore).HasPrecision(5, 4);
        }
    }
}