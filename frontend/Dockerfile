# Multi-stage Dockerfile for React/Vite
# Stages: base -> development -> build -> production

# ============================================================================
# Stage 1: Base
# ============================================================================
FROM node:22-alpine as base

# Set environment variables
ENV NODE_ENV=development

# Install pnpm
RUN npm install -g pnpm

# Create app directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install

# ============================================================================
# Stage 2: Development
# ============================================================================
FROM base as development

# Copy source code
COPY . .

# Expose port
EXPOSE 5173

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD wget --quiet --tries=1 --spider http://localhost:5173/ || exit 1

# Development server with HMR
CMD ["pnpm", "dev", "--host", "0.0.0.0"]

# ============================================================================
# Stage 3: Build
# ============================================================================
FROM base as build

# Copy source code
COPY . .

# Build application
RUN pnpm build

# ============================================================================
# Stage 4: Production
# ============================================================================
FROM nginx:alpine as production

# Set environment
ENV NODE_ENV=production

# Copy built application from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
