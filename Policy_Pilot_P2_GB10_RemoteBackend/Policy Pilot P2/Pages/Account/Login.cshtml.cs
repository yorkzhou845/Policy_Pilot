using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using TTUHSC.PAWS.Authentication.SSO;

namespace Policy_Pilot_P2.Pages.Account;

public class LoginModel : PageModel
{
    public IActionResult OnGet(string? returnUrl = null)
    {
        var redirectUri = NormalizeLocalReturnUrl(returnUrl) ?? GetBaseUrl();

        return Challenge(new AuthenticationProperties
        {
            RedirectUri = redirectUri
        }, HSCWebAuthenticationDefaults.AuthenticationScheme);
    }

    private string GetBaseUrl()
    {
        var pathBase = HttpContext.Request.PathBase.HasValue
            ? HttpContext.Request.PathBase.Value!.TrimEnd('/')
            : string.Empty;

        return $"{pathBase}/";
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
