using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.Extensions.Options;
using TTUHSC.PAWS.Authentication.SSO;

namespace Policy_Pilot_P2.Pages;

public class ExternalLogInModel : PageModel
{
    private readonly HscAuthOptions _hscOptions;

    public ExternalLogInModel(IOptions<HscAuthOptions> hscOptions)
    {
        _hscOptions = hscOptions.Value;
    }

    public async Task<IActionResult> OnGetAsync(string? returnUrl = null)
    {
        // TTUHSC SSO returns here. Convert the HSC identity into the local app cookie.
        var result = await HttpContext.AuthenticateAsync(HSCWebAuthenticationDefaults.AuthenticationScheme);

        if (!result.Succeeded || result.Principal is null)
        {
            return RedirectToPage("/Account/Login", new { returnUrl });
        }

        await HttpContext.SignInAsync(
            CookieAuthenticationDefaults.AuthenticationScheme,
            result.Principal,
            new AuthenticationProperties
            {
                IsPersistent = false,
                ExpiresUtc = DateTimeOffset.UtcNow.AddHours(_hscOptions.CookieLifetimeHours)
            });

        return LocalRedirect(NormalizeLocalReturnUrl(returnUrl) ?? GetDefaultReturnUrl());
    }

    private string GetDefaultReturnUrl()
    {
        var pathBase = HttpContext.Request.PathBase.HasValue
            ? HttpContext.Request.PathBase.Value!.TrimEnd('/')
            : string.Empty;

        var defaultUrl = string.IsNullOrWhiteSpace(_hscOptions.DefaultUrl)
            ? "/"
            : _hscOptions.DefaultUrl;

        if (!defaultUrl.StartsWith('/'))
        {
            defaultUrl = "/";
        }

        return $"{pathBase}{defaultUrl}";
    }

    private static string? NormalizeLocalReturnUrl(string? returnUrl)
    {
        if (string.IsNullOrWhiteSpace(returnUrl))
        {
            return null;
        }

        if (!returnUrl.StartsWith('/') || returnUrl.StartsWith("//") || returnUrl.StartsWith("/\\"))
        {
            return null;
        }

        return Uri.TryCreate(returnUrl, UriKind.Absolute, out _) ? null : returnUrl;
    }
}
