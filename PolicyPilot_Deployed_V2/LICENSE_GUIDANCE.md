# Licensing Guidance

No project-wide license is granted by this repository template.

Before publishing:

1. Confirm in writing that you may redistribute the remaining original source code and architecture.
2. Confirm that no copied code, visual assets, prompts, sample data, or documentation remains subject to employer restrictions.
3. Choose a project license only for material you have the authority to license.
4. Keep third-party dependency notices and license terms intact. Installing a dependency does not transfer ownership of that dependency.
5. Do not describe third-party frameworks, models, or libraries as your own work.
6. Review the licenses and acceptable-use terms of the Ollama models you choose. Model licenses differ and are separate from the Ollama software license.
7. Do not publish real policy documents unless their redistribution is authorized.

This file is publication guidance, not legal advice and not an open-source license.

## Direct dependency license review

The direct dependencies selected for this template currently identify the following licenses in their official project metadata or repositories:

| Dependency | Reported license |
|---|---|
| ASP.NET Core / Blazor | MIT |
| FastAPI | MIT |
| Uvicorn | BSD |
| pypdf | BSD-style, commonly identified as BSD-3-Clause |
| python-docx | MIT |
| python-dotenv | BSD |

Recheck the exact versions installed from `requirements.txt`, including all transitive dependencies from `uvicorn[standard]`, before distribution. The Ollama software license and each downloaded model's license must also be reviewed separately.
