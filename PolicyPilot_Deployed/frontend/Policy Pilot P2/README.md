dotnet user-secrets set "HSCWebAuthentication:ApiKey" "YOUR_HSC_API_KEY"
dotnet user-secrets set "HSCWebAuthentication:ApiSecret" "YOUR_HSC_API_SECRET"
dotnet user-secrets set "HSCWebAuthentication:AppIdentifier" "policyagent"
dotnet user-secrets set "HSCWebAuthentication:CookieLifetimeHours" "8"
dotnet user-secrets set "HSCWebAuthentication:DefaultUrl" "/"
# Policy Pilot P2

Policy Pilot P2 is a Blazor Server application for answering questions about Texas Tech University Health Sciences Center operating policies.

The app uses:

- ASP.NET Core / Blazor Server
- TTUHSC PAWS template
- TTUHSC SSO authentication
- Remote GB-10 Ollama generation endpoint
- Remote GB10 retrieval endpoint
- Python bridge under `App_Data/GB10_Chroma`

---

# Important Setup Rules

Do **not** commit these folders:

```text
publish/
publish-output/
bin/
obj/
.vs/
```

Do **not** commit real authentication keys or backend API keys.

Real secrets should be stored in:

- User Secrets for local development
- Environment variables for production

---

# Configuration Overview

The app requires configuration for:

1. TTUHSC SSO authentication
2. Remote GB-10 generation
3. Remote GB10 retrieval
4. Python bridge execution

Do **not** rely on `launchSettings.json` in production.

`launchSettings.json` is only for local development.

---

# TTUHSC SSO Authentication

This project uses TTUHSC SSO authentication through the three-field `HSCWebAuthentication` configuration pattern.

The required settings are:

```text
HSCWebAuthentication:ApiKey
HSCWebAuthentication:ApiSecret
HSCWebAuthentication:AppIdentifier
```

This project does **not** use `AppToken`.

The configured external login callback path is:

```text
/ExternalLogIn
```

In `appsettings.json`, keep placeholder values only:

```json
"HSCWebAuthentication": {
  "ApiKey": "",
  "ApiSecret": "",
  "AppIdentifier": ""
}
```

Do **not** put real SSO values in `appsettings.json`.

---

## Local SSO Setup With User Secrets

From the project folder, run:

```powershell
cd "C:\Users\yourname\source\repos\Repo\Repo\Policy_Pilot_P2_Publish\Policy Pilot P2"

dotnet user-secrets set "HSCWebAuthentication:ApiKey" "YOUR_API_KEY"
dotnet user-secrets set "HSCWebAuthentication:ApiSecret" "YOUR_API_SECRET"
dotnet user-secrets set "HSCWebAuthentication:AppIdentifier" "policyagent"
```

Use `policyagent` only if that is the correct application identifier for this deployment.

Verify the saved values:

```powershell
dotnet user-secrets list
```

---

## Production SSO Setup

In production, configure the SSO values as environment variables:

```text
HSCWebAuthentication__ApiKey=...
HSCWebAuthentication__ApiSecret=...
HSCWebAuthentication__AppIdentifier=...
```

Use double underscores `__` for production environment variables.

Do **not** use colons `:` in production environment variable names.

Do **not** rely on `launchSettings.json` in production.

---

# Python Bridge Configuration

The Blazor app runs `App_Data/GB10_Chroma/backend_bridge.py` through Python.

By default, the app uses the Python command from the server PATH:

- Windows: `python`
- Linux: `python3`

If the server uses a specific Python executable, set this environment variable:

```text
POLICY_PILOT_PYTHON=C:\Path\To\python.exe
```

The Python executable must have the required package from `App_Data/GB10_Chroma/requirements.txt` available.

---

# Production Configuration

The deployed app requires these environment variables:

```text
ASPNETCORE_ENVIRONMENT=Production

HSCWebAuthentication__ApiKey=...
HSCWebAuthentication__ApiSecret=...
HSCWebAuthentication__AppIdentifier=...

GB10_OLLAMA_HOST=...
GB10_GEN_MODEL=...
GB10_OLLAMA_API_KEY=...
DB10_RETRIEVE_CONTEXT_URL=...
```

Optional:

```text
POLICY_PILOT_PYTHON=C:\Path\To\python.exe
```

Restart the app, IIS app pool, or server after setting production environment variables.

---

# Local Development Setup

Use this section when running the app locally with:

```powershell
dotnet run
```

---

## 1. Go to the Project Folder

Open PowerShell and go to the project folder.

Example:

```powershell
cd "C:\Users\yourname\source\repos\Repo\Repo\Policy_Pilot_P2_Publish\Policy Pilot P2"
```

Replace `yourname` with your own Windows username.

---

## 2. Clean Old Build and Output Folders

Run this before building if you previously created a `publish` folder inside the project:

```powershell
Remove-Item -Recurse -Force ".\publish" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\bin" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\obj" -ErrorAction SilentlyContinue
```

Do not keep a `publish` folder inside the project while running `dotnet build`, because Blazor may try to compile files inside it.

---

## 3. Confirm Python Access

The app will use `python` from PATH unless `POLICY_PILOT_PYTHON` is set.

Check Python from PowerShell:

```powershell
python --version
python -m pip install -r ".\App_Data\GB10_Chroma\requirements.txt"
```

If Python is not on PATH, set `POLICY_PILOT_PYTHON` to an existing Python executable before running the app.

---

## 4. Set Local Authentication Secrets

Run:

```powershell
dotnet user-secrets set "HSCWebAuthentication:ApiKey" "YOUR_API_KEY"
dotnet user-secrets set "HSCWebAuthentication:ApiSecret" "YOUR_API_SECRET"
dotnet user-secrets set "HSCWebAuthentication:AppIdentifier" "policyagent"
```

Then verify:

```powershell
dotnet user-secrets list
```

---

## 5. Build and Run Locally

Run:

```powershell
dotnet build
dotnet run
```

Then open the local URL shown in the terminal.

---

# What Developers Do After Pulling From Git

After pulling the repo, each developer should run:

```powershell
cd "C:\Users\yourname\source\repos\Repo\Repo\Policy_Pilot_P2_Publish\Policy Pilot P2"

Remove-Item -Recurse -Force ".\publish" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\bin" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\obj" -ErrorAction SilentlyContinue

python -m pip install -r ".\App_Data\GB10_Chroma\requirements.txt"

dotnet user-secrets set "HSCWebAuthentication:ApiKey" "YOUR_API_KEY"
dotnet user-secrets set "HSCWebAuthentication:ApiSecret" "YOUR_API_SECRET"
dotnet user-secrets set "HSCWebAuthentication:AppIdentifier" "policyagent"

dotnet build
dotnet run
```

If Python is not on PATH, set `POLICY_PILOT_PYTHON` to the full path of an existing Python executable.

---

# Final Production Publish Setup

Use this section when creating the final deployable production folder.

Production should not use the raw source folder.

Production should use a separate output folder named:

```text
publish-output
```

This folder is created **outside** the project folder to avoid Blazor build errors.

---

## 1. Go to the Project Folder

Open PowerShell and go to the project folder.

Example:

```powershell
cd "C:\Users\yourname\source\repos\Repo\Repo\Policy_Pilot_P2_Publish\Policy Pilot P2"
```

---

## 2. Clean Old Output Folders

Run:

```powershell
Remove-Item -Recurse -Force ".\publish" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "..\publish-output" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\bin" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\obj" -ErrorAction SilentlyContinue
```

---

## 3. Publish the .NET App Outside the Project Folder

Run:

```powershell
dotnet clean
dotnet publish -c Release -o "..\publish-output"
```

This creates:

```text
Policy_Pilot_P2_Publish\publish-output
```

Do **not** use:

```powershell
dotnet publish -c Release -o ".\publish"
```

because creating `publish` inside the project folder can cause Blazor build errors later.

---

## 4. Configure Production Environment Variables

On the production server, configure:

```text
ASPNETCORE_ENVIRONMENT=Production

HSCWebAuthentication__ApiKey=...
HSCWebAuthentication__ApiSecret=...
HSCWebAuthentication__AppIdentifier=...

GB10_OLLAMA_HOST=...
GB10_GEN_MODEL=...
GB10_OLLAMA_API_KEY=...
DB10_RETRIEVE_CONTEXT_URL=...
```

Optional, if Python is not available through the normal server PATH:

```text
POLICY_PILOT_PYTHON=C:\Path\To\python.exe
```

Restart the app, IIS app pool, or server after setting production environment variables.

---

## 5. Deploy the Full `publish-output` Folder

Deploy the entire `publish-output` folder.

The deployed folder must include:

```text
publish-output\App_Data\GB10_Chroma
publish-output\Policy Pilot P2.dll
publish-output\wwwroot
```

Do **not** deploy only the `.dll`.

---

# Production Deployment Summary

For production, run:

```powershell
cd "C:\Users\yourname\source\repos\Repo\Repo\Policy_Pilot_P2_Publish\Policy Pilot P2"

Remove-Item -Recurse -Force ".\publish" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "..\publish-output" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\bin" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\obj" -ErrorAction SilentlyContinue

dotnet clean
dotnet publish -c Release -o "..\publish-output"
```

Then deploy:

```text
Policy_Pilot_P2_Publish\publish-output
```

---

# `.gitignore` Requirements

Make sure `.gitignore` includes:

```gitignore
# Python cache
__pycache__/
**/__pycache__/
*.pyc
**/*.pyc

# Build output
bin/
obj/
publish/
**/publish/
publish-output/
**/publish-output/

# Visual Studio
.vs/
*.user
*.suo
*.csproj.user

# Logs
*.log

# OS files
.DS_Store
Thumbs.db
```

---

# Build Commands

For local development:

```powershell
Remove-Item -Recurse -Force ".\publish" -ErrorAction SilentlyContinue
dotnet build
dotnet run
```

For production publish:

```powershell
dotnet clean
dotnet publish -c Release -o "..\publish-output"
```

---

# Deployment Notes

The production server still needs:

- .NET runtime / hosting support
- Production environment variables configured
- Python available on the server PATH, or `POLICY_PILOT_PYTHON` pointed to an existing Python executable
- Required Python package from `App_Data/GB10_Chroma/requirements.txt` available to that Python executable
- Network access to the GB-10 generation endpoint
- Network access to the GB10 retrieval endpoint
- TTUHSC SSO configuration values

The production app should use environment variables for keys and backend URLs.

Do not rely on `launchSettings.json` in production.

---

# Authentication Troubleshooting

If the app throws:

```text
The 'AppIdentifier' option must be provided.
```

then `HSCWebAuthentication:AppIdentifier` is missing or empty.

For local development, run:

```powershell
dotnet user-secrets set "HSCWebAuthentication:AppIdentifier" "policyagent"
```

For production, set:

```text
HSCWebAuthentication__AppIdentifier=policyagent
```

If the app repeatedly redirects to login, verify that the configured callback path matches the app code:

```text
/ExternalLogIn
```

Also verify that the TTUHSC SSO registration allows the deployed application URL.

---

# Disclaimer

This app provides AI-assisted policy summaries.

It is not the official policy source.

Users should verify answers against the cited TTUHSC policy documents.


---

# GB10 Remote Backend Deployment

This version is structured so the Blazor web app does not start Python locally.
The Python policy backend should run on the GB10 server as a small HTTP service.
The Blazor app calls that service through `GB10Backend:BaseUrl`.

## Web app settings

Local development:

```powershell
setx GB10_BACKEND_BASE_URL "http://66.230.43.54:8090"
setx GB10_BACKEND_API_KEY "YOUR_BACKEND_API_KEY_IF_CONFIGURED"
```

Production environment variables:

```text
GB10Backend__BaseUrl=http://66.230.43.54:8090
GB10Backend__ApiKey=YOUR_BACKEND_API_KEY_IF_CONFIGURED
```

Do not commit the real backend API key.

## GB10 server setup

Copy the files in `App_Data/GB10_Chroma` to a directory on GB10, then run:

```bash
cd ~/policy-pilot-backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Set the GB10 runtime environment variables on the server:

```bash
export GB10_OLLAMA_HOST="http://127.0.0.1:11434"
export GB10_OLLAMA_API_KEY="YOUR_OLLAMA_API_KEY_IF_REQUIRED"
export GB10_GEN_MODEL="llama3.1:8b"
export GB10_GUARD_MODEL="llama-guard3:8b"
export DB10_RETRIEVE_CONTEXT_URL="http://127.0.0.1:8085/retrieve-context"
export POLICY_PILOT_BACKEND_API_KEY="YOUR_BACKEND_API_KEY"
```

Start the backend manually for testing:

```bash
source .venv/bin/activate
uvicorn backend_server:app --host 0.0.0.0 --port 8090
```

Health check:

```bash
curl http://127.0.0.1:8090/health
```

Answer test:

```bash
curl -X POST http://127.0.0.1:8090/answer \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: YOUR_BACKEND_API_KEY" \
  -d '{"question":"What is OP 01.01?","runtimeContext":{"Location":"Lubbock"}}'
```

For production, create a systemd service such as `/etc/systemd/system/policy-pilot-backend.service`.

```ini
[Unit]
Description=Policy Pilot GB10 Backend
After=network.target

[Service]
User=yorzhou
WorkingDirectory=/home/yorzhou/policy-pilot-backend
Environment="GB10_OLLAMA_HOST=http://127.0.0.1:11434"
Environment="GB10_GEN_MODEL=llama3.1:8b"
Environment="GB10_GUARD_MODEL=llama-guard3:8b"
Environment="DB10_RETRIEVE_CONTEXT_URL=http://127.0.0.1:8085/retrieve-context"
Environment="GB10_OLLAMA_API_KEY=YOUR_OLLAMA_API_KEY_IF_REQUIRED"
Environment="POLICY_PILOT_BACKEND_API_KEY=YOUR_BACKEND_API_KEY"
ExecStart=/home/yorzhou/policy-pilot-backend/.venv/bin/uvicorn backend_server:app --host 0.0.0.0 --port 8090
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now policy-pilot-backend
sudo systemctl status policy-pilot-backend --no-pager
journalctl -u policy-pilot-backend -f
```
