# Public research demo

**Currently blocked:** the previous public tunnel is stopped. Complete the substantive review in [PRIVACY_REVIEW.md](PRIVACY_REVIEW.md) before restarting. Both the launcher and a public-mode backend enforce the review configuration; personal uploads remain disabled permanently in this version.

The production React build and FastAPI API are served from the same origin. Run `npm ci` and `npm run build`; FastAPI serves `dist/` automatically. Never publish the development server or the existing private report store directly.

## Required runtime

Use the existing Python environment with `backend/requirements.txt` and `backend/rag-requirements.txt`, the unchanged ResNet-18 checkpoint, the existing 638-chunk Chroma index, and Ollama with `qwen2.5:0.5b`. Model weights and runtime data are excluded from Git. A fresh clone alone does not include them. Follow `backend/README.md` for index setup on a different machine; rebuilding may produce a different chunk count. Do not rebuild the working local index when deploying this workspace.

## Public mode

Set `OSTEOLENS_PUBLIC_MODE=1`, `OSTEOLENS_PUBLIC_ORIGIN` to the exact HTTPS website origin, and a cryptographically random `OSTEOLENS_SESSION_SECRET` of at least 32 characters (or `OSTEOLENS_SESSION_SECRET_FILE`). Keep any legacy public report store separate from the local private store. New uploads are disabled. Start **one Uvicorn worker** on a loopback port behind an HTTPS reverse proxy. The report and model concurrency guards are process-local; multiple workers are not supported by this demo deployment.

The privacy middleware blocks legacy report upload/read/question/association routes and unrestricted chat before reading request bodies. Published examples use allowlisted IDs and are not saved. Guided research questions accept no arbitrary text/history. No new session cookie is created. A verified legacy cookie is used only for owner-scoped erasure of old uploads. The old retention cleanup remains a fallback; it is not a comprehensive disposal programme.

Public mode checks Origin, applies request/concurrency limits, uses brief keyed IP hashes in memory for throttling and suppresses Uvicorn access logs. Responses use no-referrer, no-store and a restrictive content security policy. Review infrastructure/provider logs separately. Never expose Ollama directly. These controls are not a clinical, legal or enterprise security certification.

Create `deploy/runtime/privacy-config.json` only after the responsible operator completes the review; use `deploy/privacy-config.example.json` as the schema. Do not invent an operator, contact, legal basis or transfer arrangement to bypass the gate. The configuration is Git-ignored. Notice fields are displayed to visitors.

## Free hosting constraint

A static host cannot run the current Python/PyTorch/Chroma/Ollama stack. As checked on 21 November 2026, Hugging Face's documentation requires a paid plan for new Docker/Gradio Spaces even though CPU Basic has no hourly charge: https://huggingface.co/docs/hub/spaces-overview . No paid service has been selected.

A Cloudflare Quick Tunnel can provide a temporary free HTTPS demo URL while this computer is running. It is not independent hosting, has no uptime guarantee, and its URL changes after restarting: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/ . A permanent independent site requires a suitable server/account (for example university infrastructure).

## Start and stop this Windows workspace

The configured environment and verified portable Cloudflare helper are already present on the owner's computer. From a PowerShell terminal in the project directory:

```powershell
.\deploy\Start-PublicDemo.ps1
```

Keep that terminal running. It prints the new HTTPS URL. The current URL and process IDs are also recorded in `deploy/runtime/public-demo.json` (excluded from Git). Closing VS Code is safe only if it does not close the terminal running the launcher. The earlier background demo has been stopped for privacy review.

Alternatively, run Python directly without changing PowerShell's script policy:

```powershell
& "$env:USERPROFILE\OsteoLens-rag-env\Scripts\python.exe" .\deploy\start_public_demo.py --cloudflared "..\OsteoLens-work\tools\cloudflared.exe"
```

To stop the background demo or an existing launcher before restarting:

```powershell
.\deploy\Stop-PublicDemo.ps1
```

The stop script checks the launcher's process identity and stops only its process tree. It does not stop the separate local API on port 8000 or Ollama. After stopping, use the start command to obtain a new URL. Keep the computer awake and connected to the internet; this is a temporary public demo, not an independently hosted production service.

On a different computer, provide the configured Python environment and the [official Cloudflare executable](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/) using the scripts' `-Python` and `-Cloudflared` parameters. The helper is excluded from Git.

## Acceptance checks after an approved release

1. Verify English/Türkçe notices and the approved controller/contact details.
2. Confirm there is no personal file picker or free-text assistant input.
3. Confirm direct upload and old chat API calls return 403 before body parsing.
4. Analyse one of the 34 published examples; confirm no saved user report or persistent report session appears.
5. Verify X-ray inference and guided RAG with citations and unchanged model/index.
6. Check legacy erasure cannot affect another browser's data, and validate the broader deletion procedure separately.
7. Confirm no third-party font/analytics requests and no reflected request content in errors.
8. Review actual provider routing, contracts, logging and retention before opening the service to users.
