# Share OsteoLens with a doctor or supervisor

Reviewers need only a web browser and an HTTPS website link. They do not need VS Code, Python, Ollama, the source code or a local installation. **No shareable service is currently running.** `http://127.0.0.1:8000` opens only on the project laptop; sending that address will not work for someone else.

## Available routes

1. **A scheduled, temporary review:** after completing the operator/provider privacy review, run the existing `deploy/Start-PublicDemo.ps1` on the project laptop and share the HTTPS URL it prints. Keep the laptop awake, connected, and the launcher running throughout the review. The link changes when restarted; it is not a permanent website. A hard-to-guess tunnel URL is not authentication, so use published or synthetic material for the review and do not describe it as confidential access.
2. **Review whenever they want:** deploy the complete app to a university or suitable cloud server, assign a stable hostname and configure HTTPS and service startup. See `SERVER_HOSTING.md`. The university route is the first choice under the current free-only budget. The server and privacy arrangements still need to be supplied and reviewed.
3. **Immediate review while those details are pending:** share your screen in a meeting while opening the local site. This allows a demonstration now without publishing the unfinished service. It is not an independently accessible website.

The public launcher checks the privacy-review configuration. Do not replace missing facts with placeholder approvals to get a URL. Required decisions include the actual operator, approved privacy contact, processing grounds for visitor technical data and research-chat text, provider/transfer/retention arrangements and any past personal-report processing. Browser-only documents reduce server collection but do not certify overall KVKK compliance.

## Suggested invitation after a working URL exists

> Please review OsteoLens, my Graduation Project 1 research prototype, at [insert tested HTTPS URL]. No installation is required. Please use the included published cases or synthetic documents for evaluation, and do not put patient identifiers or confidential report text in the research chatbot. I would appreciate feedback on usability, the accuracy and limitations of cited answers, the heatmap explanation, and the report workflow. This is an educational prototype, not a clinical diagnostic service. [For a temporary tunnel: the site will be available during our agreed review session.]

## Five-minute review

- Choose English or Türkçe.
- Open a case and run image analysis. Compare the source label, model result and Grad-CAM explanation; the heatmap is not a tumour boundary.
- In the main RAG assistant, write a custom question and inspect the linked citations.
- In Medical Report Analyser, choose one of 34 published examples, analyse it and ask its RAG assistant a custom question.
- Choose **My own report · on device** and open a synthetic text-containing PDF/TXT. Ask a question, inspect verbatim page-referenced passages, then clear the report. This mode is local text retrieval, not Qwen generation. Scanned/encrypted PDFs are unsupported.
- Note unclear wording, unsupported statements or source mismatches. Send feedback privately to the project owner without patient information. Do not post personal reports in GitHub issues.

The source repository is <https://github.com/iqraxsarwar/OsteoLens>. A source-code link is useful for technical review but does not replace the live website link.
