/**
 * PublishOps — Comment Worker
 * =============================
 * Processes jobs from the 'comment-queue'.
 * Triggered 2 min after upload. Monitors comments for 30 minutes,
 * generates Claude-powered replies, and pins the first self-comment.
 *
 * Reply cadence:
 *   - First 10 min: 2-3 replies
 *   - After 10 min: 1 reply per 5-10 min
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

const CONCURRENCY = parseInt(process.env.WORKER_CONCURRENCY || "5", 10);

// Comment engagement configuration
const ENGAGEMENT_WINDOW_MS = 30 * 60 * 1000;  // 30 minutes
const EARLY_PHASE_MS = 10 * 60 * 1000;        // First 10 minutes
const EARLY_PHASE_REPLIES = 3;                  // 2-3 replies in early phase
const LATE_PHASE_INTERVAL_MS = 7 * 60 * 1000; // ~7 min between replies (5-10 min avg)
const POLL_INTERVAL_MS = 30 * 1000;            // Check for new comments every 30s

/**
 * Sleep helper.
 */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Generate a Claude-powered reply for a comment.
 */
async function generateReply(contentId, platform, comment) {
  const resp = await axios.post(`${BACKEND_URL}/api/v1/engagement/generate-reply`, {
    content_id: contentId,
    platform,
    comment_id: comment.id,
    comment_text: comment.text,
    comment_author: comment.author,
    comment_sentiment: comment.sentiment || "neutral",
  }, { timeout: 30000 });

  return resp.data.reply_text;
}

/**
 * Post a reply to a comment on the platform.
 */
async function postReply(platform, platformPostId, commentId, replyText, accessToken) {
  const resp = await axios.post(`${BACKEND_URL}/api/v1/platforms/${platform}/comment`, {
    post_id: platformPostId,
    parent_comment_id: commentId,
    text: replyText,
    access_token: accessToken,
  }, { timeout: 30000 });

  return resp.data;
}

/**
 * Pin the first self-comment on a post.
 */
async function pinFirstComment(platform, platformPostId, commentId, accessToken) {
  try {
    await axios.post(`${BACKEND_URL}/api/v1/platforms/${platform}/pin-comment`, {
      post_id: platformPostId,
      comment_id: commentId,
      access_token: accessToken,
    }, { timeout: 15000 });
    logger.info(`Pinned first comment on ${platform}/${platformPostId}`);
  } catch (err) {
    logger.warn(`Failed to pin comment on ${platform} — may not be supported`, {
      error: err.message,
    });
  }
}

/**
 * Fetch new comments from the platform.
 */
async function fetchComments(platform, platformPostId, sinceTimestamp, accessToken) {
  const resp = await axios.get(`${BACKEND_URL}/api/v1/platforms/${platform}/comments`, {
    params: {
      post_id: platformPostId,
      since: sinceTimestamp,
      access_token: accessToken,
    },
    timeout: 15000,
  });

  return resp.data.comments || [];
}

/**
 * Refresh OAuth token before engagement.
 */
async function refreshToken(platform, credentials) {
  const resp = await axios.post(`${BACKEND_URL}/api/v1/auth/refresh-token`, {
    platform,
    refresh_token: credentials.refresh_token,
  }, { timeout: 10000 });
  return resp.data.access_token;
}

// ---------------------------------------------------------------------------
// Job Processor
// ---------------------------------------------------------------------------

async function processComment(job) {
  const { content_id, platform, platform_post_id, credentials } = job.data;

  if (!content_id || !platform || !platform_post_id) {
    throw new UnrecoverableError("Missing required fields: content_id, platform, platform_post_id");
  }

  logger.info(`Starting comment engagement for ${platform}/${platform_post_id}`, { content_id });

  // Refresh token
  let accessToken;
  try {
    accessToken = await refreshToken(platform, credentials || {});
  } catch (err) {
    throw new Error(`Token refresh failed for comment worker: ${err.message}`);
  }

  // Post initial self-comment (hook/CTA)
  let selfCommentId;
  try {
    const initialComment = await axios.post(`${BACKEND_URL}/api/v1/engagement/generate-first-comment`, {
      content_id,
      platform,
    }, { timeout: 30000 });

    const selfCommentResult = await postReply(
      platform,
      platform_post_id,
      null,  // No parent — top-level comment
      initialComment.data.text,
      accessToken,
    );
    selfCommentId = selfCommentResult.comment_id;

    // Pin the first comment
    if (selfCommentId) {
      await pinFirstComment(platform, platform_post_id, selfCommentId, accessToken);
    }

    logger.info(`Posted and pinned initial comment on ${platform}/${platform_post_id}`, { content_id });
  } catch (err) {
    logger.warn("Failed to post initial self-comment", { error: err.message, content_id });
  }

  await job.updateProgress(10);

  // Track engagement metrics
  const startTime = Date.now();
  let totalReplies = 0;
  let earlyPhaseReplies = 0;
  let lastReplyTime = 0;
  let lastPollTimestamp = new Date(startTime - 60000).toISOString(); // Start from 1 min before
  const repliedCommentIds = new Set();

  // Engagement loop: monitor for 30 minutes
  while (Date.now() - startTime < ENGAGEMENT_WINDOW_MS) {
    const elapsed = Date.now() - startTime;
    const isEarlyPhase = elapsed < EARLY_PHASE_MS;

    try {
      // Fetch new comments
      const comments = await fetchComments(platform, platform_post_id, lastPollTimestamp, accessToken);
      lastPollTimestamp = new Date().toISOString();

      // Filter out already-replied and self-comments
      const newComments = comments.filter(
        (c) => !repliedCommentIds.has(c.id) && c.id !== selfCommentId
      );

      if (newComments.length > 0) {
        logger.info(`Found ${newComments.length} new comments on ${platform}/${platform_post_id}`, { content_id });

        // Determine if we should reply based on cadence
        let shouldReply = false;
        if (isEarlyPhase && earlyPhaseReplies < EARLY_PHASE_REPLIES) {
          shouldReply = true;
        } else if (!isEarlyPhase) {
          const timeSinceLastReply = Date.now() - lastReplyTime;
          shouldReply = timeSinceLastReply >= LATE_PHASE_INTERVAL_MS || lastReplyTime === 0;
        }

        if (shouldReply && newComments.length > 0) {
          // Pick the best comment to reply to (highest engagement potential)
          const bestComment = newComments[0]; // Backend sorts by relevance

          try {
            // Generate AI reply
            const replyText = await generateReply(content_id, platform, bestComment);

            // Post reply
            await postReply(platform, platform_post_id, bestComment.id, replyText, accessToken);

            repliedCommentIds.add(bestComment.id);
            totalReplies++;
            lastReplyTime = Date.now();

            if (isEarlyPhase) {
              earlyPhaseReplies++;
            }

            logger.info(`Replied to comment by ${bestComment.author} on ${platform}`, {
              content_id,
              total_replies: totalReplies,
              phase: isEarlyPhase ? "early" : "late",
            });
          } catch (replyErr) {
            logger.warn("Failed to generate or post reply", {
              error: replyErr.message,
              comment_id: bestComment.id,
            });
          }
        }
      }
    } catch (fetchErr) {
      logger.warn("Failed to fetch comments", { error: fetchErr.message, platform });
    }

    // Update progress based on elapsed time
    const progress = Math.min(10 + Math.floor((elapsed / ENGAGEMENT_WINDOW_MS) * 90), 99);
    await job.updateProgress(progress);

    // Wait before next poll
    await sleep(POLL_INTERVAL_MS);
  }

  // Report engagement summary to backend
  try {
    await axios.post(`${BACKEND_URL}/api/v1/posts/${content_id}/engagement-summary`, {
      platform,
      platform_post_id,
      total_replies: totalReplies,
      early_phase_replies: earlyPhaseReplies,
      duration_minutes: 30,
      comments_monitored: repliedCommentIds.size,
    });
  } catch (err) {
    logger.warn("Failed to report engagement summary", { error: err.message });
  }

  await job.updateProgress(100);

  logger.info(`Comment engagement complete for ${platform}/${platform_post_id}`, {
    content_id,
    total_replies: totalReplies,
  });

  return {
    content_id,
    platform,
    total_replies: totalReplies,
    comments_monitored: repliedCommentIds.size,
  };
}

// ---------------------------------------------------------------------------
// Worker Initialization
// ---------------------------------------------------------------------------

const worker = new Worker(QUEUE_NAMES.COMMENT, processComment, {
  connection: redisConnection,
  concurrency: CONCURRENCY,
});

worker.on("completed", (job, result) => {
  logger.info(`Comment job ${job.id} completed`, {
    platform: result.platform,
    total_replies: result.total_replies,
  });
});

worker.on("failed", (job, err) => {
  logger.error(`Comment job ${job?.id} failed`, {
    error: err.message,
    attempt: job?.attemptsMade,
  });
});

worker.on("error", (err) => {
  logger.error("Comment worker error", { error: err.message });
});

onShutdown(async () => {
  logger.info("Closing comment worker...");
  await worker.close();
});

logger.info(`Comment worker started (concurrency=${CONCURRENCY})`);
