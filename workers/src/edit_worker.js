/**
 * PublishOps — Edit Worker
 * =========================
 * Processes jobs from the 'edit-queue'.
 * Triggered 3 min after upload. Makes minor caption edits (fix typo, add emoji)
 * to signal freshness to the platform algorithm.
 */
import { Worker, UnrecoverableError } from "bullmq";
import axios from "axios";
import {
  redisConnection,
  QUEUE_NAMES,
  BACKEND_URL,
  logger,
  onShutdown,
} from "./queue_config.js";

const CONCURRENCY = parseInt(process.env.WORKER_CONCURRENCY || "2", 10);

/**
 * Refresh OAuth token before editing.
 */
async function refreshToken(platform, credentials) {
  const resp = await axios.post(`${BACKEND_URL}/api/v1/auth/refresh-token`, {
    platform,
    refresh_token: credentials.refresh_token,
  }, { timeout: 10000 });
  return resp.data.access_token;
}

/**
 * Generate a minor edit for the caption/description.
 * The backend uses Claude to produce a subtle, natural-looking edit.
 */
async function generateEdit(contentId, platform) {
  const resp = await axios.post(`${BACKEND_URL}/api/v1/engagement/generate-edit`, {
    content_id: contentId,
    platform,
    edit_types: ["fix_typo", "add_emoji", "adjust_hashtag", "tweak_cta"],
  }, { timeout: 30000 });

  return resp.data;
}

/**
 * Apply the edit to the published post via the platform API.
 */
async function applyEdit(platform, platformPostId, editData, accessToken) {
  const resp = await axios.post(`${BACKEND_URL}/api/v1/platforms/${platform}/edit`, {
    post_id: platformPostId,
    updated_caption: editData.updated_caption,
    updated_title: editData.updated_title,
    updated_tags: editData.updated_tags,
    edit_type: editData.edit_type,
    access_token: accessToken,
  }, { timeout: 30000 });

  return resp.data;
}

// ---------------------------------------------------------------------------
// Job Processor
// ---------------------------------------------------------------------------

async function processEdit(job) {
  const { content_id, platform, platform_post_id, credentials } = job.data;

  if (!content_id || !platform || !platform_post_id) {
    throw new UnrecoverableError("Missing required fields: content_id, platform, platform_post_id");
  }

  logger.info(`Processing edit for ${platform}/${platform_post_id}`, {
    content_id,
    attempt: job.attemptsMade + 1,
  });

  // Refresh token
  let accessToken;
  try {
    accessToken = await refreshToken(platform, credentials || {});
  } catch (err) {
    throw new Error(`Token refresh failed for edit worker: ${err.message}`);
  }

  await job.updateProgress(20);

  // Generate edit
  let editData;
  try {
    editData = await generateEdit(content_id, platform);
  } catch (err) {
    if (err.response && err.response.status === 404) {
      logger.info(`No edit needed for ${content_id} on ${platform} — skipping`, { content_id });
      return { content_id, platform, status: "skipped", reason: "no_edit_needed" };
    }
    throw err;
  }

  if (!editData || !editData.updated_caption) {
    logger.info(`Edit generation returned empty for ${content_id} — skipping`);
    return { content_id, platform, status: "skipped", reason: "empty_edit" };
  }

  await job.updateProgress(50);

  // Apply edit to platform
  let editResult;
  try {
    editResult = await applyEdit(platform, platform_post_id, editData, accessToken);
    logger.info(`Edit applied to ${platform}/${platform_post_id}`, {
      content_id,
      edit_type: editData.edit_type,
    });
  } catch (err) {
    // Rate limit
    if (err.response && err.response.status === 429) {
      const retryAfter = parseInt(err.response.headers["retry-after"] || "120", 10);
      logger.warn(`Rate limited by ${platform} during edit — retry in ${retryAfter}s`);
      const rateLimitError = new Error(`Rate limited by ${platform}`);
      rateLimitError.rateLimitDelay = retryAfter * 1000;
      throw rateLimitError;
    }

    // Platform doesn't support editing
    if (err.response && err.response.status === 405) {
      logger.info(`${platform} does not support post editing — skipping`);
      return { content_id, platform, status: "skipped", reason: "editing_not_supported" };
    }

    // Non-retryable
    if (err.response && err.response.status >= 400 && err.response.status < 500) {
      throw new UnrecoverableError(`${platform} returned ${err.response.status} during edit`);
    }

    throw err;
  }

  await job.updateProgress(80);

  // Report edit to backend
  try {
    await axios.post(`${BACKEND_URL}/api/v1/posts/${content_id}/edit-applied`, {
      platform,
      platform_post_id,
      edit_type: editData.edit_type,
      changes: editData.changes_summary,
    });
  } catch (err) {
    logger.warn("Failed to report edit to backend", { error: err.message });
  }

  await job.updateProgress(100);

  return {
    content_id,
    platform,
    status: "edited",
    edit_type: editData.edit_type,
    platform_post_id,
  };
}

// ---------------------------------------------------------------------------
// Worker Initialization
// ---------------------------------------------------------------------------

const worker = new Worker(QUEUE_NAMES.EDIT, processEdit, {
  connection: redisConnection,
  concurrency: CONCURRENCY,
});

worker.on("completed", (job, result) => {
  logger.info(`Edit job ${job.id} completed`, {
    platform: result.platform,
    status: result.status,
    edit_type: result.edit_type,
  });
});

worker.on("failed", (job, err) => {
  logger.error(`Edit job ${job?.id} failed`, {
    error: err.message,
    attempt: job?.attemptsMade,
  });
});

worker.on("error", (err) => {
  logger.error("Edit worker error", { error: err.message });
});

onShutdown(async () => {
  logger.info("Closing edit worker...");
  await worker.close();
});

logger.info(`Edit worker started (concurrency=${CONCURRENCY})`);
