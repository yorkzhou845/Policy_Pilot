# Authentication Integration Notes

This version follows the TTUHSC core-application pattern provided by the manager.

## Configuration fields

The app reads three values from the `HSCWebAuthentication` section:

```text
HSCWebAuthentication:ApiKey
HSCWebAuthentication:ApiSecret
HSCWebAuthentication:AppIdentifier
```

No `AppToken` value is configured in this version because the provided TTUHSC example uses only these three fields.

## Runtime flow

- `/Account/Login` challenges `HSCWebAuthenticationDefaults.AuthenticationScheme`.
- TTUHSC SSO redirects back to `/ExternalLogIn`.
- `/ExternalLogIn` authenticates the HSC SSO identity and issues the local cookie.
- `/Account/Logout` signs out of the local cookie and the HSC SSO scheme, then redirects to `/LogOut`.

## Local secrets

Set these with User Secrets from the project folder:

```powershell
dotnet user-secrets set "HSCWebAuthentication:ApiKey" "YOUR_API_KEY"
dotnet user-secrets set "HSCWebAuthentication:ApiSecret" "YOUR_API_SECRET"
dotnet user-secrets set "HSCWebAuthentication:AppIdentifier" "policyagent"
```

Use server environment variables with double underscores for the published deployment.
