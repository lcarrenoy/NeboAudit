using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using NeboAudit.Api.Data;
using NeboAudit.Api.Services; // <-- Asegura la importación del servicio

var builder = WebApplication.CreateBuilder(args);

// 1. Registro del Contexto de Base de Datos
builder.Services.AddDbContext<NeboDbContext>(opt =>
    opt.UseSqlServer(builder.Configuration.GetConnectionString("NeboDb") ?? "Server=LAPTOP-Q3026NUM;Database=NeboAudit;Trusted_Connection=True;TrustServerCertificate=True;"));

// 2. Registro Explícito del Servicio del Ecosistema (Inyección de Dependencias)
builder.Services.AddScoped<TokenService>();

// 3. Configuración de Seguridad JWT
var jwtKey = builder.Configuration["Jwt:Key"] ?? "EstaEsUnaClaveSuperSecretaYFuerteDe32Bits!";
builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(opt =>
    {
        opt.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"] ?? "NeboAuditIssuer",
            ValidAudience = builder.Configuration["Jwt:Audience"] ?? "NeboAuditAudience",
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey))
        };
    });

builder.Services.AddAuthorization();
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();

// 4. Configuración de Swagger con candado de autenticación
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo { Title = "NeboAudit Platform API", Version = "v1" });
    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        In = ParameterLocation.Header,
        Description = "Escribe: Bearer {tu_token}",
        Name = "Authorization",
        Type = SecuritySchemeType.ApiKey,
        Scheme = "Bearer"
    });
    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "Bearer" }
            },
            Array.Empty<string>()
        }
    });
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c => c.RoutePrefix = "swagger");
}

app.UseAuthentication();
app.UseAuthorization();

// Permitir peticiones desde el ecosistema local (React, Python, etc.)
app.UseCors(x => x.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader());

app.MapControllers();
app.MapGet("/", () => Results.Redirect("/swagger")).AllowAnonymous();

app.Run();