# Public research demo

The production React build and FastAPI API are served from the same origin. Run `npm ci` and `npm run build`; FastAPI serves `dist/` automatically. Never publish the development server or the existing private report store directly.

## Required runtime

Use the existing Python environment with `backend/requirements.txt` and `backend/rag-requirements.txt`, the unchanged ResNet-18 checkpoint, the existing 638-chunk Chroma index, and Ollama with `qwen2.5:0.5b`. Model weights and runtime data are excluded from Git. A fresh clone alone does not include them. Follow `backend/README.md` for index setup on a different machine; rebuilding may produce a different chunk count. Do not rebuild the working local index when deploying this workspace.

## Public mode

Set `OSTEOLENS_PUBLIC_MODE=1`, `OSTEOLENS_PUBLIC_ORIGIN` to the exact HTTPS website origin, and a cryptographically random `OSTEOLENS_SESSION_SECRET` of at least 32 characters (or `OSTEOLENS_SESSION_SECRET_FILE`). Use a separate `OSTEOLENS_REPORT_DATA_DIR` for public uploads. Start **one Uvicorn worker** on a loopback port behind an HTTPS reverse proxy. The report and model concurrency guards are process-local; multiple workers are not supported by this demo deployment.

Public mode separates uploads by signed, secure, HttpOnly browser cookies; checks Origin on mutations; limits API requests and concurrent POSTs; limits public upload storage; and removes public reports older than 24 hours during periodic request-triggered cleanup. It never removes the pre-existing local reports. Cookies are not user accounts: losing a cookie loses access to its reports. Storage is not encrypted. Use only public or synthetic documents.

Configure the reverse proxy to cap request bodies at 21 MiB and trust forwarded client addresses only from that proxy. Ollama and the backend must not expose ports directly to the internet. Public demo controls are not a clinical or enterprise security certification.

## Free hosting constraint

A static host cannot run the current Python/PyTorch/Chroma/Ollama stack. As checked on 21 November 2026, Hugging Face's documentation requires a paid plan for new Docker/Gradio Spaces even though CPU Basic has no hourly charge: https://huggingface.co/docs/hub/spaces-overview . No paid service has been selected.

A Cloudflare Quick Tunnel can provide a temporary free HTTPS demo URL while this computer is running. It is not independent hosting, has no uptime guarantee, and its URL changes after restarting: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/ . A permanent independent site requires a suitable server/account (for example university infrastructure).

## Start and stop this Windows workspace

The configured environment and verified portable Cloudflare helper are already present on the owner's computer. From a PowerShell terminal in the project directory:

```powershell
.\deploy\Start-PublicDemo.ps1
```

Keep that terminal running. It prints the new HTTPS URL. The current URL and process IDs are also recorded in `deploy/runtime/public-demo.json` (excluded from Git). Closing VS Code is safe only if it does not close the terminal running the launcher. The demo initially started by Codex runs in the background.

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

## Acceptance checks

1. Open the public HTTPS URL in a fresh browser, switch English/Türkçe and reload.
2. Check 60 radiographs, filtering, real ResNet-18 inference and the Grad-CAM explanation.
3. Analyse one of the 34 attributed public report excerpts.
4. Confirm RAG displays 638 chunks, `qwen2.5:0.5b` and ready; ask a question and inspect actual citations.
5. In another browser session confirm the first visitor's reports are not listed or retrievable.
6. Confirm network requests use the public HTTPS origin, never localhost or port 8001.
