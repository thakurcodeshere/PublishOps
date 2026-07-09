/**
 * PublishOps — Upload Worker
 * ===========================
 * Processes jobs from the 'upload-queue'.
 * Handles platform-specific uploads, OAuth token refresh, rate limit detection,
 * and reports status back to the FastAPI backend.
 */
import { Worker, UnrecoverableError } from "bullmq";
import axios from "axios";
import {
  redisConnection,
  QUEUE_NAMES,
  BACKEND_URL,
  logger,
  onShutdown,
  getQueue,
  DEFAULT_JOB_OPTIONS,
} from "./queue_config.js";

const CONCURRENCY = parseInt(process.env.WORKER_CONCURRENCY || "3", 10);
const DEAD_LETTER_QUEUE = "upload-dead-letter";

// ---------------------------------------------------------------------------
// Platform-specific upload handlers
// ---------------------------------------------------------------------------

/**
 * Refresh OAuth token for a platform before uploading.
 * @param {string} platform
 * @param {object} credentials
 * @returns {Promise<string>} Fresh access token
 */
async function refreshOAuthToken(platform, credentials) {
  logger.info(`Refreshing OAuth token for ${platform}`);
  const resp = await axios.post(`${BACKEND_URL}/api/v1/auth/refresh-token`, {
    platform,
    refresh_token: credentials.refresh_token,
  });
  return resp.data.access_token;
}

/**
 * Upload to YouTube via the backend proxy.
 */
async function uploadToYouTube(job, accessToken) {
  const { content_id, title, description, tags, video_url, thumbnail_url, privacy_status } = job.data;
  logger.info(`Uploading to YouTube: "${title}"`, { content_id });

  const resp = await axios.post(
    `${BACKEND_URL}/api/v1/platforms/youtube/upload`,
    {
      content_id,
      title,
      description,
      tags: tags || [],
      video_url,
      thumbnail_url,
      privacy_status: privacy_status || "public",
      access_token: accessToken,
    },
    { timeout: 300000 }  // 5 min timeout for large uploads
  );

  return { platform: "youtube", platform_post_id: resp.data.video_id, url: resp.data.url };
}

/**
 * Upload to TikTok via the backend proxy.
 */
async function uploadToTikTok(job, accessToken) {
  const { content_id, caption, video_url, sounds, hashtags } = job.data;
  logger.info(`Uploading to TikTok: content_id=${content_id}`);

  const resp = await axios.post(
    `${BACKEND_URL}/api/v1/platforms/tiktok/upload`,
    {
      content_id,
      caption,
      video_url,
      sounds: sounds || [],
      hashtags: hashtags || [],
      access_token: accessToken,
    },
    { timeout: 180000 }
  );

  return { platform: "tiktok", platform_post_id: resp.data.post_id, url: resp.data.url };
}

/**
 * Upload to Instagram via the backend proxy.
 */
async function uploadToInstagram(job, accessToken) {
  const { content_id, caption, media_urls, media_type, hashtags } = job.data;
  logger.info(`Uploading to Instagram (${media_type}): content_id=${content_id}`);

  const resp = await axios.post(
    `${BACKEND_URL}/api/v1/platforms/instagram/upload`,
    {
      content_id,
      caption,
      media_urls: media_urls || [],
      media_type: media_type || "reel",
      hashtags: hashtags || [],
      access_token: accessToken,
    },
    { timeout: 180000 }
  );

  return { platform: "instagram", platform_post_id: resp.data.media_id, url: resp.data.url };
}

/**
 * Upload to Twitter/X via the backend proxy.
 */
async function uploadToTwitter(job, accessToken) {
  const { content_id, text, media_urls, reply_to } = job.data;
  logger.info(`Uploading to Twitter/X: content_id=${content_id}`);

  const resp = await axios.post(
    `${BACKEND_URL}/api/v1/platforms/twitter/upload`,
    {
      content_id,
      text,
      media_urls: media_urls || [],
      reply_to,
      access_token: accessToken,
    },
    { timeout: 60000 }
  );

  return { platform: "twitter", platform_post_id: resp.data.tweet_id, url: resp.data.url };
}

/**
 * Upload to LinkedIn via the backend proxy.
 */
async function uploadToLinkedIn(job, accessToken) {
  const { content_id, text, media_urls, media_type, document_url } = job.data;
  logger.info(`Uploading to LinkedIn: content_id=${content_id}`);

  const resp = await axios.post(
    `${BACKEND_URL}/api/v1/platforms/linkedin/upload`,
    {
      content_id,
      text,
      media_urls: media_urls || [],
      media_type: media_type || "text_post",
      document_url,
      access_token: accessToken,
    },
    { timeout: 120000 }
  );

  return { platform: "linkedin", platform_post_id: resp.data.post_id, url: resp.data.url };
}

const PLATFORM_HANDLERS = {
  youtube: uploadToYouTube,
  tiktok: uploadToTikTok,
  instagram: uploadToInstagram,
  twitter: uploadToTwitter,
  linkedin: uploadToLinkedIn,
};

// ---------------------------------------------------------------------------
// Job Processor
// ---------------------------------------------------------------------------

async function processUpload(job) {
  const { platform, content_id, credentials } = job.data;

  if (!platform || !PLATFORM_HANDLERS[platform]) {
    throw new UnrecoverableError(`Unknown platform: ${platform}`);
  }
  if (!content_id) {
    throw new UnrecoverableError("Missing content_id in job data");
  }

  logger.info(`Processing upload job ${job.id}`, {
    platform,
    content_id,
    attempt: job.attemptsMade + 1,
  });

  // Report status: uploading
  await axios.post(`${BACKEND_URL}/api/v1/posts/${content_id}/status`, {
    status: "uploading",
    platform,
    attempt: job.attemptsMade + 1,
  }).catch((err) => logger.warn("Failed to report upload status", { error: err.message }));

  try {
    // Refresh OAuth token
    let accessToken;
    try {
      accessToken = await refreshOAuthToken(platform, credentials || {});
    } catch (tokenErr) {
      logger.error(`OAuth token refresh failed for ${platform}`, { error: tokenErr.message });
      throw new Error(`Token refresh failed: ${tokenErr.message}`);
    }

    // Update progress
    await job.updateProgress(30);

    // Execute platform-specific upload
    const handler = PLATFORM_HANDLERS[platform];
    const result = await handler(job, accessToken);

    await job.updateProgress(90);

    // Report success to backend
    await axios.post(`${BACKEND_URL}/api/v1/posts/${content_id}/status`, {
      status: "published",
      platform,
      platform_post_id: result.platform_post_id,
      url: result.url,
    });

    // Queue follow-up jobs: comment engagement (2 min delay) + edit (3 min delay)
    const commentQueue = getQueue(QUEUE_NAMES.COMMENT);
    await commentQueue.add(
      `comment-${content_id}-${platform}`,
      {
        content_id,
        platform,
        platform_post_id: result.platform_post_id,
        credentials,
      },
      {
        ...DEFAULT_JOB_OPTIONS[QUEUE_NAMES.COMMENT],
        delay: 120000, // 2 minutes
      }
    );

    const editQueue = getQueue(QUEUE_NAMES.EDIT);
    await editQueue.add(
      `edit-${content_id}-${platform}`,
      {
        content_id,
        platform,
        platform_post_id: result.platform_post_id,
        credentials,
      },
      {
        ...DEFAULT_JOB_OPTIONS[QUEUE_NAMES.EDIT],
        delay: 180000, // 3 minutes
      }
    );

    await job.updateProgress(100);
    logger.info(`Upload complete: ${platform}/${result.platform_post_id}`, { content_id });

    return result;
  } catch (err) {
    // Rate limit detection
    if (err.response && err.response.status === 429) {
      const retryAfter = parseInt(err.response.headers["retry-after"] || "60", 10);
      logger.warn(`Rate limited by ${platform} — retry after ${retryAfter}s`, { content_id });

      // Report rate limit to backend
      await axios.post(`${BACKEND_URL}/api/v1/posts/${content_id}/status`, {
        status: "rate_limited",
        platform,
        retry_after_seconds: retryAfter,
      }).catch(() => {});

      // BullMQ's Worker.RateLimitError equivalent: throw with delay
      const rateLimitError = new Error(`Rate limited by ${platform}`);
      rateLimitError.rateLimitDelay = retryAfter * 1000;
      throw rateLimitError;
    }

    // Non-retryable errors
    if (err.response && err.response.status >= 400 && err.response.status < 500 && err.response.status !== 429) {
      logger.error(`Non-retryable error from ${platform}: ${err.response.status}`, {
        content_id,
        error: err.response.data,
      });
      throw new UnrecoverableError(`${platform} returned ${err.response.status}: ${JSON.stringify(err.response.data)}`);
    }

    // Retryable errors
    logger.error(`Upload to ${platform} failed (will retry)`, {
      content_id,
      error: err.message,
      attempt: job.attemptsMade + 1,
    });
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Dead Letter Queue Handler
// ---------------------------------------------------------------------------
async function moveToDeadLetter(job, err) {
  logger.error(`Job ${job.id} exhausted all retries — moving to dead letter queue`, {
    content_id: job.data.content_id,
    platform: job.data.platform,
    error: err.message,
  });

  const dlq = getQueue(DEAD_LETTER_QUEUE);
  await dlq.add(`dlq-${job.id}`, {
    original_job_id: job.id,
    original_queue: QUEUE_NAMES.UPLOAD,
    data: job.data,
    error: err.message,
    failed_at: new Date().toISOString(),
    attempts: job.attemptsMade,
  });

  // Report permanent failure to backend
  await axios.post(`${BACKEND_URL}/api/v1/posts/${job.data.content_id}/status`, {
    status: "failed",
    platform: job.data.platform,
    error: err.message,
    permanent: true,
  }).catch((reportErr) => logger.warn("Failed to report permanent failure", { error: reportErr.message }));
}

// ---------------------------------------------------------------------------
// Worker Initialization
// ---------------------------------------------------------------------------

const worker = new Worker(QUEUE_NAMES.UPLOAD, processUpload, {
  connection: redisConnection,
  concurrency: CONCURRENCY,
  limiter: {
    max: 10,
    duration: 60000,  // Max 10 jobs per minute
  },
  settings: {
    backoffStrategy: (attemptsMade) => {
      // Exponential backoff: 5s, 25s, 125s
      return Math.min(5000 * Math.pow(5, attemptsMade - 1), 300000);
    },
  },
});

worker.on("completed", (job, result) => {
  logger.info(`Job ${job.id} completed`, {
    platform: result.platform,
    platform_post_id: result.platform_post_id,
  });
});

worker.on("failed", async (job, err) => {
  if (job && job.attemptsMade >= (job.opts.attempts || 3)) {
    await moveToDeadLetter(job, err);
  } else {
    logger.warn(`Job ${job?.id} failed (attempt ${job?.attemptsMade}/${job?.opts?.attempts || 3})`, {
      error: err.message,
    });
  }
});

worker.on("error", (err) => {
  logger.error("Worker error", { error: err.message });
});

worker.on("stalled", (jobId) => {
  logger.warn(`Job ${jobId} stalled — will be re-processed`);
});

// Register graceful shutdown
onShutdown(async () => {
  logger.info("Closing upload worker...");
  await worker.close();
});

logger.info(`Upload worker started (concurrency=${CONCURRENCY})`);
