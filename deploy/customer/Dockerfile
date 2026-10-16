FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY copilot/web/package*.json copilot/web/
RUN cd copilot/web && npm ci --ignore-scripts
COPY copilot/web/app-entry.js copilot/web/
RUN cd copilot/web && npx esbuild app-entry.js --bundle --format=iife --platform=browser --target=es2022 --minify --legal-comments=external --outfile=/compiled/app.js

FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY deploy/customer/package*.json deploy/customer/
RUN cd deploy/customer && npm ci --omit=dev --ignore-scripts
COPY copilot/web/package*.json copilot/web/
RUN cd copilot/web && npm ci --omit=dev --ignore-scripts
COPY copilot/web/client.js copilot/web/
COPY deploy/customer/*.mjs deploy/customer/
COPY deploy/customer/lookup.py deploy/customer/
COPY deploy/customer/public/ deploy/customer/public/
COPY --from=build /compiled/ deploy/customer/public/
COPY lookup_result.py engine.py profiles.py evidence.py live_guidance.py zenity_auth.py zenity_reader.py ./
COPY profiles/ profiles/
USER node
ENV NODE_ENV=production PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["node", "deploy/customer/server.mjs"]
