# 09: Docker compose and the latency measurement

**What to build:** The developer runs `docker compose up` and gets the API and the Streamlit UI, with the data directory mounted as a volume and settings read from environment variables. If the index is missing, the API fails at startup with a clear message. A latency script sends a list of questions to the running `/ask` and reports median and p95 latency, overall and per stage, along with the hardware it ran on.

**Blocked by:** 01 (Tracer bullet: ask a question, get a cited answer)

**Status:** ready-for-agent

- [ ] The compose file defines two services, `api` and `ui`. The UI reaches the API by service name, and the API has a health check using `GET /health`
- [ ] Neither the PDFs nor the index are baked into an image. The data directory is a mounted volume
- [ ] All settings, including `GROQ_API_KEY` and `COURSE_QA_LLM_PROVIDER`, come from environment variables (loaded from `.env`), with a committed `.env.example` file and no secrets in git
- [ ] With `COURSE_QA_LLM_PROVIDER=ollama`, the `api` container can reach an Ollama server (on the host or as an optional compose service)
- [ ] The latency script paces its requests to stay within Groq's free-tier rate limits and retries on rate-limit errors; rate-limited waits are excluded from the reported latency and counted separately
- [ ] The latency report records the LLM provider and model alongside the hardware
- [ ] The API exits at startup with a clear message naming the missing index when it isn't there
- [ ] The latency script takes a split (Test Split by default), sends each question to `/ask`, and reports median and p95 for `total` and each `timings_ms` stage
- [ ] The latency report records the CPU, RAM, OS and whether it ran inside Docker
- [ ] The README explains how to ingest, start the services and run the latency script
