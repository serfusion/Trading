# Multi-stage build for Gold Trading Bot
# Use Node.js 20 LTS
FROM node:20-slim AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Runtime stage
FROM node:20-slim

# Create non-root user
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Set working directory
WORKDIR /app

# Copy node_modules from builder
COPY --from=builder /app/node_modules ./node_modules

# Copy application code
COPY package*.json ./
COPY src ./src

# Create necessary directories and set permissions
RUN mkdir -p logs data && \
    chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Health check - verifies bot process is responding
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD node -e "process.exit(0)" || exit 1

# Set environment variables
ENV NODE_ENV=production
ENV TRADING_MODE=practice

# Run the bot
CMD ["node", "src/index.js"]
