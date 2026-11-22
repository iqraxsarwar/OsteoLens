# Independent hosting and privacy release handover

Prepared 22 November 2026. **No independent server has been provisioned, no permanent public URL has been assigned, and no public release has been approved.** The supplied Linux files are deployment templates, not a tested server installation.

## Open the current local application

On the project laptop, open <http://127.0.0.1:8000>. This address refers to the computer opening the link, so it will not give other people access. The existing local service must stay running. The previous `trycloudflare.com` URL is deliberately stopped.

## Recommended free route

Ask the university for a Linux VM and a university subdomain. This can provide a stable address and an institutional operator/contact arrangement without using the student's laptop. Availability, cost to the student, permitted research use and maintenance must be confirmed by university IT; none has been assumed.

Suggested initial capacity for this small CPU demo: 2 CPU cores, 8–12 GB RAM and 50 GB persistent storage. This is a provisioning estimate, not a measured concurrent-user guarantee. Linux x86-64 is the simplest migration target; ARM requires compatible Python/PyTorch packages and validation on that machine.

The server must support Python/PyTorch, the existing Chroma index, local Ollama/Qwen, an HTTPS reverse proxy, automatic service startup after reboot, restricted administrator access, patching, and a documented backup/log-retention policy. A free institutional subdomain is sufficient; buying a domain is not necessary.

If university hosting is unavailable, Oracle Always Free is a candidate, not an uptime guarantee. Its current documentation lists a total of 2 Ampere OCPUs and 12 GB RAM, with regional capacity limitations and possible reclamation of idle instances. Confirm the console's Always Free eligibility and account-wide quotas before creating anything; do not select paid resources or rely on expiring trial credits. The provider, region and international transfers also need review before launch. [Oracle's current limits](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

A static host alone cannot run the current Python model, Chroma and Ollama backend. A stable DNS name pointing at the laptop would still stop working when the laptop goes offline.

## Information needed from the host

- Server/provider, physical region and authorised administrator access. Never paste passwords or private SSH keys into chat.
- Stable public address and an assigned hostname, with permission to set DNS A/AAAA records.
- Whether the university or student operates the service and manages security incidents and rights requests.
- Provider/processor terms, subprocessors, logging, backups, retention, deletion and any overseas transfer mechanism. Server location alone does not establish the absence of overseas access or transfers.

## Prepared Linux deployment

Files are in `deploy/server/`: `osteolens.service`, `server.env.example`, and `Caddyfile.example`. Use a dedicated `osteolens` system user. Place the reviewed source under `/opt/osteolens`, writable runtime data under `/var/lib/osteolens`, and private configuration under `/etc/osteolens`. Give only the service account access to its configuration and runtime data; do not make these directories publicly readable or web-served.

1. Clone the reviewed source from <https://github.com/iqraxsarwar/OsteoLens>. Create a new Python environment **on the server** using the project's requirements and compatible CPU packages. Do not alter the laptop's environment. Record resolved server versions and compare them with the working environment before transferring the index; use Chroma 1.5.9 for the first migration to avoid an unintended database-format upgrade.
2. Build the frontend with the project's Node requirements and lockfile (`npm ci`, then `npm run build`). Leave `VITE_OSTEOLENS_API_URL` unset: the website and `/api` share one HTTPS origin. Do not expose Vite port 5173.
3. Transfer only the approved research artifacts: the unchanged `models/checkpoints/osteolens_btxrd_resnet18.pth`, a **consistent snapshot** of `backend/data/rag/` with its 638 chunks, the cached `all-MiniLM-L6-v2` embedding model, and the same Qwen model. Compare SHA-256 checksums of the checkpoint and copied artifacts. Obtain a consistent Chroma copy while no process is using the source index, during an agreed maintenance window; do not copy a live database blindly, re-ingest, or retrain. Do not copy private reports, credentials, browser profiles, logs or the entire user directory. Git excludes model and index files, so cloning alone is insufficient.
4. Put the embedding cache under `/var/lib/osteolens/cache/huggingface`. The unit enables offline Hugging Face loading and disables its telemetry; provision the required cache before startup. Keep Ollama listening on loopback only with `qwen2.5:0.5b`, and verify it locally. Its model storage and configuration belong to the new server; leave the working laptop configuration unchanged.
5. Complete the substantive privacy review and place the approved configuration at `/etc/osteolens/privacy-config.json`. Copy `server.env.example` to `/etc/osteolens/server.env`, replace the hostname, and generate a fresh random session secret of at least 32 characters into the referenced private file. Do not copy example approval fields or fabricate them. Personal uploads remain disabled after approval.
6. Install the supplied unit at `/etc/systemd/system/osteolens.service`. Prepare the writable directories and permissions, then run `systemd-analyze verify /etc/systemd/system/osteolens.service` on Linux. Check dependency readiness and service startup locally before opening public ingress. The unit uses one worker and restarts on failure; repeated failures stop retrying so an administrator can investigate.
7. Point the assigned DNS hostname at the server. Configure Caddy using the supplied template and validate with `caddy validate --config /etc/caddy/Caddyfile`. Allow public HTTPS/HTTP for serving and certificate issuance, restrict SSH to administrators, and block public access to ports 8000 and 11434. Review host, proxy and provider logs; access logging is not enabled in the supplied Caddy configuration. [Caddy HTTPS requirements](https://caddyserver.com/docs/automatic-https).
8. After review and validation, enable the application, Ollama and proxy services on boot. Reboot the **server** and verify the site recovers while the laptop is off. Set an operator-owned availability check and alert destination; do not collect visitor browsing analytics for this purpose.

No step above has been executed on a remote host yet. Linux unit/Caddy validation, capacity measurements, DNS/TLS, provider retention and reboot recovery remain server acceptance work.

## Public acceptance before announcing a URL

- English/Turkish privacy notice identifies the real controller, contact, purposes, recipients, legal grounds, retention and rights procedure.
- Homepage, 60-image library, one inference/Grad-CAM explanation, and one of 34 published report analyses work through the same HTTPS origin.
- The actual RAG page shows **638 chunks**, **qwen2.5:0.5b**, ready, and answers a custom research question with citations.
- Personal upload and legacy text endpoints reject requests; custom research questions use the bounded research endpoint. Personal PDF/TXT processing stays in the browser; no new visitor report or cookie is saved.
- Ollama, the API loopback port, private artifacts and administrator interfaces are not publicly accessible.
- HTTPS renewal, restart/reboot recovery, capacity limits, backups/restoration and log retention are checked on the chosen server.

See `PRIVACY_REVIEW.md` for the remaining legal and operational decisions. Passing technical checks does not certify legal compliance or establish the absence of past violations.
