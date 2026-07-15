using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Policy_Pilot_P2;
using Policy_Pilot_P2.Components;
using Policy_Pilot_P2.Services;
using System.Security.Claims;
using System.Threading.RateLimiting;
using TTUHSC.PAWS.Authentication.SSO;
using TTUHSC.PAWS.Template;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

builder.Services.AddRazorPages();
builder.Services.AddCascadingAuthenticationState();
builder.Services.AddAuthorization();

builder.Services.AddPAWSTemplate(
    builder.Configuration.GetSection(PAWSTemplateOptions.PAWSTemplate));

builder.Services.Configure<HscAuthOptions>(
    builder.Configuration.GetSection(HscAuthOptions.SectionName));

var authConfig = builder.Configuration.GetSection(HscAuthOptions.SectionName);
var authOptions = authConfig.Get<HscAuthOptions>() ?? new HscAuthOptions();

var pathBase = builder.Configuration.GetValue<string>(WebConstants.WebBasePathSettingsName) ?? "/";

builder.Services.AddAuthentication(options =>
{
    options.DefaultScheme = CookieAuthenticationDefaults.AuthenticationScheme;
    options.DefaultSignInScheme = CookieAuthenticationDefaults.AuthenticationScheme;
    options.DefaultChallengeScheme = HSCWebAuthenticationDefaults.AuthenticationScheme;
})
    .AddCookie(options =>
    {
        options.Cookie.HttpOnly = true;

        if (!string.IsNullOrWhiteSpace(pathBase) && pathBase != "/")
        {
            options.Cookie.Path = pathBase;
        }

        options.LoginPath = new PathString("/Account/Login");
        options.AccessDeniedPath = new PathString("/AccessDenied");
        options.LogoutPath = new PathString("/LogOut");
        options.Events = new CookieAuthenticationEvents
        {
            OnValidatePrincipal = async ctx =>
            {
                var userId = ctx.Principal?.FindFirstValue(ClaimTypes.NameIdentifier);
                if (userId == null)
                {
                    ctx.Response.StatusCode = StatusCodes.Status401Unauthorized;
                }

                await Task.CompletedTask;
            }
        };
    })
    .AddHSCWebAuthentication(options =>
    {
        options.ApiKey = authOptions.ApiKey;
        options.ApiSecret = authOptions.ApiSecret;
        options.AppIdentifier = authOptions.AppIdentifier;
        options.ExternalLoginCallback = new PathString("/ExternalLogIn");
    });

builder.Services.AddHttpClient<Gb10ChromaBackendService>();

builder.Services.AddRateLimiter(options => //server-level rate limiting
{
    options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(context =>
    {
        var key = context.Connection.RemoteIpAddress?.ToString() ?? "unknown";

        return RateLimitPartition.GetFixedWindowLimiter(
            key,
            _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 60,
                Window = TimeSpan.FromMinutes(1),
                QueueLimit = 0,
                AutoReplenishment = true
            });
    });

    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
});

var app = builder.Build();

// Check the remote GB10 retrieval backend and exit:
// dotnet run -- --ingest
if (args.Contains("--ingest"))
{
    using var scope = app.Services.CreateScope();

    var backend = scope.ServiceProvider.GetRequiredService<Gb10ChromaBackendService>();
    await backend.BuildIndexAsync();

    Console.WriteLine("Local ingestion skipped. The app uses the remote GB10 /retrieve-context vector database.");
    return;
}

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}

if (!string.IsNullOrWhiteSpace(pathBase) && pathBase != "/")
{
    app.UsePathBase(pathBase);
}

app.UseHttpsRedirection();
app.UseRouting();

app.UseAuthentication();
app.UseAuthorization();

// Files under wwwroot/Data are linked from the authenticated documents page.
// Keep normal assets public, but require sign-in for direct policy-document URLs.
app.Use(async (context, next) =>
{
    if (context.Request.Path.StartsWithSegments("/Data") &&
        context.User.Identity?.IsAuthenticated != true)
    {
        var returnUrl = context.Request.PathBase + context.Request.Path + context.Request.QueryString;
        var loginUrl = $"/Account/Login?returnUrl={Uri.EscapeDataString(returnUrl)}";
        context.Response.Redirect(loginUrl);
        return;
    }

    await next();
});

app.UseStaticFiles();
app.UseRateLimiter();
app.UseAntiforgery();

app.MapRazorPages();

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
