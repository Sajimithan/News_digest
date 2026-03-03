# ── Frontend — React + Vite → Nginx ──────────────────────────────────────────

# ── Stage 1: Build ───────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer cache friendly)
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source and build
# Override outDir: vite.config.ts uses '../frontend/dist' for the local monorepo layout,
# but inside Docker the working dir is /app so we write directly to /app/dist instead.
COPY . .
RUN npx tsc --noEmit && npx vite build --outDir dist

# ── Stage 2: Serve with Nginx ─────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Replace default nginx config with our proxy-aware one
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the Vite build output
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
