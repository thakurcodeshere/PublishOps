// ============================================================
// PublishOps — API Client
// ============================================================

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

import {
  dashboardStats,
  pipelineStages,
  topics,
  contentItems,
  scheduledPosts,
  analyticsData,
  recentActivity,
  pipelineRuns,
  platformRules,
  heatmapData,
  settingsData,
  topPerformers,
  upcomingSchedule,
} from './mockData';

async function apiRequest(endpoint, options = {}) {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) throw new Error(`API Error: ${res.status} ${res.statusText}`);
    return await res.json();
  } catch (error) {
    console.warn(`API call to ${endpoint} failed, using mock data:`, error.message);
    return null;
  }
}

// --- Dashboard ---
export async function fetchDashboardStats() {
  const data = await apiRequest('/dashboard/stats');
  return data || dashboardStats;
}

export async function fetchTopPerformers() {
  const data = await apiRequest('/dashboard/top-performers');
  return data || topPerformers;
}

export async function fetchUpcomingSchedule() {
  const data = await apiRequest('/dashboard/upcoming');
  return data || upcomingSchedule;
}

export async function fetchRecentActivity() {
  const data = await apiRequest('/dashboard/activity');
  return data || recentActivity;
}

// --- Pipeline ---
export async function fetchPipelineStatus() {
  const data = await apiRequest('/pipeline/status');
  return data || pipelineStages;
}

export async function fetchPipelineRuns() {
  const data = await apiRequest('/pipeline/runs');
  return data || pipelineRuns;
}

export async function triggerPipeline() {
  const data = await apiRequest('/pipeline/trigger', { method: 'POST' });
  return data || { status: 'triggered', message: 'Pipeline run initiated' };
}

// --- Topics ---
export async function fetchTopics(filters = {}) {
  const params = new URLSearchParams(filters).toString();
  const data = await apiRequest(`/topics?${params}`);
  return data || topics;
}

export async function updateTopicStatus(topicId, status) {
  const data = await apiRequest(`/topics/${topicId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
  return data || { id: topicId, status };
}

// --- Content ---
export async function fetchContent(filters = {}) {
  const params = new URLSearchParams(filters).toString();
  const data = await apiRequest(`/content?${params}`);
  return data || contentItems;
}

// --- Analytics ---
export async function fetchAnalytics(range = '30d') {
  const data = await apiRequest(`/analytics?range=${range}`);
  return data || analyticsData;
}

// --- Scheduler ---
export async function fetchScheduledPosts() {
  const data = await apiRequest('/scheduler/posts');
  return data || scheduledPosts;
}

export async function fetchHeatmapData() {
  const data = await apiRequest('/scheduler/heatmap');
  return data || heatmapData;
}

// --- Platforms ---
export async function fetchPlatformRules(platform) {
  const data = await apiRequest(`/platforms/${platform}`);
  return data || platformRules[platform];
}

export async function fetchAllPlatformRules() {
  const data = await apiRequest('/platforms');
  return data || platformRules;
}

// --- Settings ---
export async function fetchSettings() {
  const data = await apiRequest('/settings');
  return data || settingsData;
}

export async function updateSettings(section, values) {
  const data = await apiRequest(`/settings/${section}`, {
    method: 'PUT',
    body: JSON.stringify(values),
  });
  return data || { ...values, updated: true };
}
