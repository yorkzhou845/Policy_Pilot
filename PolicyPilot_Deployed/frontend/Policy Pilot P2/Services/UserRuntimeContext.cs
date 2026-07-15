namespace Policy_Pilot_P2.Services;

public sealed class UserRuntimeContext
{
    public string CurrentDateTimeLocal { get; set; } = string.Empty;

    public string CurrentDateIsoUtc { get; set; } = string.Empty;

    public string TimeZone { get; set; } = string.Empty;

    public string Location { get; set; } = "Lubbock";
}
