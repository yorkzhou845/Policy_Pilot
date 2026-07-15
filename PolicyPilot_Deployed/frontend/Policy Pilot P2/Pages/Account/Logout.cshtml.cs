using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.Extensions.Options;
using TTUHSC.PAWS.Authentication.SSO;

namespace Policy_Pilot_P2.Pages.Account;

public class LogoutModel : PageModel
{
    private readonly HscAuthOptions _hscOptions;

    public LogoutModel(IOptions<HscAuthOptions> hscOptions)
    {
        _hscOptions = hscOptions.Value;
    }

    public async Task<IActionResult> OnGetAsync()
    {
        await SignOutAsync();
        return LocalRedirect(GetSignedOutUrl());
    }

    public async Task<IActionResult> OnPostAsync()
    {
        await SignOutAsync();
        return LocalRedirect(GetSignedOutUrl());
    }

    private async Task SignOutAsync()
    {
        await HttpContext.SignOutAsync(HSCWebAuthenticationDefaults.AuthenticationScheme, new AuthenticationProperties
        {
            RedirectUri = GetSignedOutUrl()
        });

        await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
    }

    private string GetSignedOutUrl()
    {
        var pathBase = HttpContext.Request.PathBase.HasValue
            ? HttpContext.Request.PathBase.Value!.TrimEnd('/')
            : string.Empty;

        return $"{pathBase}/LogOut";
    }
}
