# Multi-stage Dockerfile for React/Vite
# Stages: base -> development -> production

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
COPY package.json pnpm-lock.yaml* ./

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
FROM node:22-alpine as production

# Install lightweight HTTP server
RUN npm install -g serve

# Set environment
ENV NODE_ENV=production

WORKDIR /app

# Copy built application from build stage
COPY --from=build /app/dist ./dist

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

# Serve static files
CMD ["serve", "-s", "dist", "-l", "3000"]
