using System;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.Extensions.Configuration;
using Microsoft.IdentityModel.Tokens;

namespace NeboAudit.Api.Services
{
    public class TokenService
    {
        private readonly IConfiguration _config;
        public TokenService(IConfiguration config) => _config = config;

        public string GenerateToken(string username, int tenantId)
        {
            var claims = new[]
            {
                new Claim(ClaimTypes.Name, username),
                new Claim("TenantId", tenantId.ToString()),
                new Claim(ClaimTypes.Role, username == "admin" ? "Administrator" : "Auditor")
            };

            // Usar una clave segura por defecto si no está en el appsettings
            var secretKey = _config["Jwt:Key"] ?? "EstaEsUnaClaveSuperSecretaYFuerteDe32Bits!";
            var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secretKey));
            var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

            var token = new JwtSecurityToken(
                issuer: _config["Jwt:Issuer"] ?? "NeboAuditIssuer",
                audience: _config["Jwt:Audience"] ?? "NeboAuditAudience",
                claims: claims,
                expires: DateTime.UtcNow.AddHours(8),
                signingCredentials: creds
            );

            return new JwtSecurityTokenHandler().WriteToken(token);
        }
    }
}