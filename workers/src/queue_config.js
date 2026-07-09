/**
 * PublishOps — Shared Queue Configuration
 * =========================================
 * Central configuration for all BullMQ queues, Redis connection,
 * priority constants, and graceful shutdown handling.
 */
import { Queue, QueueEvents } from "bullmq";
import IORedis from "ioredis";
import dotenv from "dotenv";
import { createLogger, format, transports } from "winston";

dotenv.config();

// ---------------------------------------------------------------------------
// Logger
// ---------------------------------------------------------------------------
const LOG_LEVEL = process.env.WORKER_LOG_LEVEL || "info";

export const logger = createLogger({
  level: LOG_LEVEL,
  format: format.combine(
    format.timestamp({ format: "YYYY-MM-DD HH:mm:ss.SSS" }),
    format.errors({ stack: true }),
    format.printf(({ timestamp, level, message, stack, ...meta }) => {
      const metaStr = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : "";
      const stackStr = stack ? `\n${stack}` : "";
      return `${timestamp} [${level.toUpperCase().padEnd(5)}] ${message}${metaStr}${stackStr}`;
    })
  ),
  transports: [new transports.Console()],
});

// ---------------------------------------------------------------------------
// Redis Connection
// ---------------------------------------------------------------------------
const REDIS_HOST = process.env.REDIS_HOST || "localhost";
const REDIS_PORT = parseInt(process.env.REDIS_PORT || "6379", 10);

export const redisConnection = {
  host: REDIS_HOST,
  port: REDIS_PORT,
  maxRetriesPerRequest: null,  // Required by BullMQ
  enableReadyCheck: false,
  retryStrategy(times) {
    const delay = Math.min(times * 200, 5000);
    logger.warn(`Redis connection retry #${times}, next attempt in ${delay}ms`);
    return delay;
  },
};

/**
 * Create a new IORedis client for direct Redis operations.
 */
export function createRedisClient() {
  const client = new IORedis(REDIS_PORT, REDIS_HOST, {
    maxRetriesPerRequest: null,
    enableReadyCheck: false,
    retryStrategy(times) {
      return Math.min(times * 200, 5000);
    },
  });
  client.on("error", (err) => logger.error("Redis client error", { error: err.message }));
  return client;
}

// ---------------------------------------------------------------------------
// Priority Constants
// ---------------------------------------------------------------------------
export const Priority = Object.freeze({
  CRITICAL: 1,
  HIGH: 3,
  NORMAL: 5,
  LOW: 10,
});

// ---------------------------------------------------------------------------
// Queue Definitions
// ---------------------------------------------------------------------------
export const QUEUE_NAMES = Object.freeze({
  UPLOAD: "upload-queue",
  COMMENT: "comment-queue",
  EDIT: "edit-queue",
});

/**
 * Default job options per queue.
 */
export const DEFAULT_JOB_OPTIONS = Object.freeze({
  [QUEUE_NAMES.UPLOAD]: {
    attempts: 3,
    backoff: { type: "exponential", delay: 5000 },
    removeOnComplete: { age: 86400, count: 500 },    // Keep 24h or last 500
    removeOnFail: { age: 604800, count: 1000 },      // Keep 7d or last 1000
    priority: Priority.HIGH,
  },
  [QUEUE_NAMES.COMMENT]: {
    attempts: 3,
    backoff: { type: "exponential", delay: 3000 },
    removeOnComplete: { age: 43200, count: 200 },    // Keep 12h or last 200
    removeOnFail: { age: 259200, count: 500 },        // Keep 3d or last 500
    priority: Priority.NORMAL,
  },
  [QUEUE_NAMES.EDIT]: {
    attempts: 2,
    backoff: { type: "exponential", delay: 4000 },
    removeOnComplete: { age: 43200, count: 200 },
    removeOnFail: { age: 259200, count: 500 },
    priority: Priority.NORMAL,
  },
});

// ---------------------------------------------------------------------------
// Queue Instances
// ---------------------------------------------------------------------------
const queues = new Map();

/**
 * Get or create a Queue instance.
 * @param {string} name - Queue name from QUEUE_NAMES
 * @returns {Queue}
 */
export function getQueue(name) {
  if (!queues.has(name)) {
    const queue = new Queue(name, { connection: redisConnection });
    queue.on("error", (err) => logger.error(`Queue "${name}" error`, { error: err.message }));
    queues.set(name, queue);
  }
  return queues.get(name);
}

// ---------------------------------------------------------------------------
// Backend API Client
// ---------------------------------------------------------------------------
export const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";

// ---------------------------------------------------------------------------
// Graceful Shutdown
// ---------------------------------------------------------------------------
const shutdownCallbacks = [];

/**
 * Register a callback to run during graceful shutdown.
 * @param {Function} cb - Async function to call on shutdown
 */
export function onShutdown(cb) {
  shutdownCallbacks.push(cb);
}

async function gracefulShutdown(signal) {
  logger.info(`Received ${signal} — starting graceful shutdown`);

  const timeout = setTimeout(() => {
    logger.error("Graceful shutdown timed out after 30s — forcing exit");
    process.exit(1);
  }, 30000);

  try {
    // Run all registered shutdown callbacks
    await Promise.allSettled(
      shutdownCallbacks.map((cb) => cb())
    );

    // Close all queues
    for (const [name, queue] of queues) {
      logger.info(`Closing queue: ${name}`);
      await queue.close();
    }

    logger.info("Graceful shutdown complete");
    clearTimeout(timeout);
    process.exit(0);
  } catch (err) {
    logger.error("Error during graceful shutdown", { error: err.message });
    clearTimeout(timeout);
    process.exit(1);
  }
}

process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
process.on("SIGINT", () => gracefulShutdown("SIGINT"));

process.on("unhandledRejection", (reason) => {
  logger.error("Unhandled promise rejection", { reason: String(reason) });
});

process.on("uncaughtException", (err) => {
  logger.error("Uncaught exception — shutting down", { error: err.message, stack: err.stack });
  process.exit(1);
});
