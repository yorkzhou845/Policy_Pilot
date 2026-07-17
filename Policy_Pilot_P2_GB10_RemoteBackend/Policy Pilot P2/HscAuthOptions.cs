namespace Policy_Pilot_P2;

public class HscAuthOptions
{
    // This section name matches the manager-provided appsettings example.
    public const string SectionName = "HSCWebAuthentication";

    public string ApiKey { get; set; } = string.Empty;
    public string ApiSecret { get; set; } = string.Empty;
    public string AppIdentifier { get; set; } = string.Empty;
    public int CookieLifetimeHours { get; set; } = 8;
    public string DefaultUrl { get; set; } = "/";
}
