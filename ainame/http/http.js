const getBaseUrl = () => {
  if (typeof window !== "undefined" && window.location && window.location.hostname) {
    return `http://${window.location.hostname}:9000`;
  }
  return "http://127.0.0.1:9000";
};

const BASE_URL = getBaseUrl();

const request = (url, options = {}) => {
  const token = uni.getStorageSync("token");
  const method = (options.method || "GET").toUpperCase();
  const withAuth = options.auth !== false;
  const header = { ...(options.header || {}) };

  if (withAuth && token) {
    header.authorization = "Bearer " + token;
  }
  if (method !== "GET") {
    header["content-type"] = "application/json";
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method,
      data: options.data,
      header,
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data);
          return;
        }

        let errorMsg = "服务请求失败";
        if (res.data && Array.isArray(res.data.detail)) {
          errorMsg = res.data.detail[0].msg || "表单参数校验失败";
        } else if (res.data && typeof res.data.detail === "string") {
          errorMsg = res.data.detail;
        }

        uni.showToast({
          title: String(errorMsg),
          icon: "none",
          duration: 3000
        });
        reject(res.data);
      },
      fail: (err) => {
        uni.showToast({ title: "网络连接断开，请检查网络", icon: "none" });
        reject(err);
      }
    });
  });
};

const uploadFile = (url, filePath) => {
  const token = uni.getStorageSync("token");

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: BASE_URL + url,
      filePath,
      name: "file",
      header: token ? { authorization: "Bearer " + token } : {},
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(JSON.parse(res.data));
        } else {
          uni.showToast({ title: "文件上传失败", icon: "none" });
          reject(res);
        }
      },
      fail: (err) => {
        uni.showToast({ title: "网络异常，上传中断", icon: "none" });
        reject(err);
      }
    });
  });
};

const buildQuery = (params = {}) => {
  const query = Object.keys(params)
    .filter((key) => params[key] !== undefined && params[key] !== null && params[key] !== "")
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join("&");
  return query ? `?${query}` : "";
};

export default {
  getEmailCode: (email) => request("/auth/code?email=" + encodeURIComponent(email), { method: "GET", auth: false }),
  register: (data) => request("/auth/register", { method: "POST", data, auth: false }),
  login: (data) => request("/auth/login", { method: "POST", data, auth: false }),
  getInvitationSummary: () => request("/invitation/me", { method: "GET" }),
  generateName: (data) => request("/name/generate", { method: "POST", data }),
  feedbackName: (data) => request("/name/feedback", { method: "POST", data }),
  uploadKnowledge: (filePath) => uploadFile("/knowledge/upload", filePath),

  createApiKey: (name) => request("/api-key/create", { method: "POST", data: { name } }),
  getApiKeys: () => request("/api-key/list", { method: "GET" }),
  disableApiKey: (keyId) => request("/api-key/disable", { method: "POST", data: { key_id: keyId } }),
  enableApiKey: (keyId) => request("/api-key/enable", { method: "POST", data: { key_id: keyId } }),
  deleteApiKey: (keyId) => request("/api-key/delete", { method: "POST", data: { key_id: keyId } }),
  getApiKeyStats: () => request("/api-key/stats", { method: "GET" }),
  getApiKeyUsage: (params) => request("/api-key/usage" + buildQuery(params), { method: "GET" }),

  getAdminUsers: (params) => request("/admin/users" + buildQuery(params), { method: "GET" }),
  getAdminUsersOverview: () => request("/admin/users/overview", { method: "GET" }),
  getAdminUserDetail: (userId) => request(`/admin/users/${userId}/detail`, { method: "GET" }),
  createAdminUser: (data) => request("/admin/users", { method: "POST", data }),
  updateAdminUserRole: (userId, role) => request(`/admin/users/${userId}/role`, { method: "PATCH", data: { role } }),
  updateAdminUserSegment: (userId, user_segment) => request(`/admin/users/${userId}/segment`, { method: "PATCH", data: { user_segment } }),
  banAdminUser: (userId, data) => request(`/admin/users/${userId}/ban`, { method: "POST", data }),
  unbanAdminUser: (userId) => request(`/admin/users/${userId}/unban`, { method: "POST" }),
  addAdminBlacklist: (userId, reason) => request(`/admin/users/${userId}/blacklist`, { method: "POST", data: { reason } }),
  removeAdminBlacklist: (userId) => request(`/admin/users/${userId}/blacklist`, { method: "DELETE" }),
  getSensitiveWords: () => request("/admin/sensitive-words", { method: "GET" }),
  saveSensitiveWord: (data) => request("/admin/sensitive-words", { method: "POST", data }),
  disableSensitiveWord: (word) => request(`/admin/sensitive-words/${encodeURIComponent(word)}`, { method: "DELETE" }),
  getModerationRecords: (params) => request("/admin/moderation-records" + buildQuery(params), { method: "GET" }),
  reviewModerationRecord: (recordId, note) => request(`/admin/moderation-records/${recordId}/review`, { method: "POST", data: { note } }),
  getAdminActionLogs: (params) => request("/admin/action-logs" + buildQuery(params), { method: "GET" }),
  createCommunityPoll: (data) => request("/community/polls", { method: "POST", data }),
  getCommunityPolls: (params) => request("/community/polls" + buildQuery(params), { method: "GET" }),
  voteCommunityPoll: (pollId, optionId) => request(`/community/polls/${pollId}/vote`, { method: "POST", data: { option_id: optionId } }),
  getAdminCommunityPolls: (params) => request("/community/admin/polls" + buildQuery(params), { method: "GET" }),
  hideCommunityPoll: (pollId, reason) => request(`/community/admin/polls/${pollId}/hide`, { method: "POST", data: { reason } }),
  unhideCommunityPoll: (pollId) => request(`/community/admin/polls/${pollId}/unhide`, { method: "POST" })
};
