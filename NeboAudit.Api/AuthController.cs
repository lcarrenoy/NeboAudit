using Microsoft.AspNetCore.Mvc;
using NeboAudit.Api.Services;

namespace NeboAudit.Api.Controllers
{
    [ApiController]
    [Route("api/auth")]
    public class AuthController : ControllerBase
    {
        private readonly TokenService _tokenService;
        public AuthController(TokenService tokenService) => _tokenService = tokenService;

        [HttpPost("login")]
        public IActionResult Login([FromBody] LoginRequest request)
        {
            if ((request.Usuario == "admin" && request.Password == "admin123") || 
                (request.Usuario == "auditor" && request.Password == "auditor123"))
            {
                var token = _tokenService.GenerateToken(request.Usuario, request.TenantId);
                return Ok(new { Token = token, Expiration = DateTime.UtcNow.AddHours(8) });
            }

            return Unauthorized(new { Message = "Credenciales de auditoría inválidas." });
        }
    }

    public class LoginRequest
    {
        public string Usuario { get; set; } = null!;
        public string Password { get; set; } = null!;
        public int TenantId { get; set; }
    }
}