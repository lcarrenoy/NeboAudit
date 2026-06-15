using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using NeboAudit.Api.Data;

namespace NeboAudit.Api.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize]
    public class LoansController : ControllerBase
    {
        private readonly NeboDbContext _context;
        public LoansController(NeboDbContext context) => _context = context;

        // Aislamiento Multi-Tenant basado en los claims del token JWT
        private int TenantId => int.Parse(User.FindFirst("TenantId")?.Value ?? "0");

        [HttpGet]
        public async Task<IActionResult> GetLoans([FromQuery] int page = 1, [FromQuery] int pageSize = 10)
        {
            var query = _context.Loans.Where(l => l.TenantId == TenantId);
            var totalRows = await query.CountAsync();
            
            var data = await query
                .OrderByDescending(l => l.LoanId)
                .Skip((page - 1) * pageSize)
                .Take(pageSize)
                .ToListAsync();

            return Ok(new {
                Data = data,
                Page = page,
                PageSize = pageSize,
                TotalRows = totalRows,
                TotalPages = (int)Math.Ceiling((double)totalRows / pageSize)
            });
        }

        [HttpGet("high-risk")]
        public async Task<IActionResult> GetHighRisk([FromQuery] decimal threshold = 0.5000m)
        {
            var highRiskLoans = await _context.Loans
                .Where(l => l.TenantId == TenantId && l.RiskScore >= threshold)
                .OrderByDescending(l => l.RiskScore)
                .ToListAsync();

            return Ok(highRiskLoans);
        }
    }
}