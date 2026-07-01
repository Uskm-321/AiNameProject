const getBaseUrl = () => {
  if (typeof window !== "undefined") {
    const port = window.location && window.location.port;
    if (["5173", "5174", "8080"].includes(port)) {
      return "/api";
    }

    const hostname = window.location && window.location.hostname;
    if (!hostname || hostname === "localhost") {
      return "http://127.0.0.1:8000";
    }
    if (hostname === "127.0.0.1") {
      return "http://127.0.0.1:8000";
    }
    return `http://${hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
};

const BASE_URL = getBaseUrl();
console.log("API BASE_URL =", BASE_URL);

const isAuthExpired = (statusCode, message) => {
  const text = String(message || "").toLowerCase();
  return (
    statusCode === 401 ||
    (
      statusCode === 403 &&
      (
        text.includes("token") ||
        text.includes("access") ||
        text.includes("过期") ||
        text.includes("登录")
      )
    )
  );
};

const redirectToLogin = () => {
  uni.removeStorageSync("token");
  uni.removeStorageSync("user");
  setTimeout(() => {
    uni.reLaunch({ url: "/pages/login/login" });
  }, 800);
};

const getErrorMessage = (res) => {
  let data = res && res.data;

  if (typeof data === "string") {
    try {
      data = JSON.parse(data);
    } catch (error) {
      return data || "服务请求失败";
    }
  }

  if (data && Array.isArray(data.detail)) {
    return data.detail[0].msg || "表单参数校验失败";
  }
  if (data && typeof data.detail === "string") {
    return data.detail;
  }
  if (data && typeof data.message === "string") {
    return data.message;
  }
  return "服务请求失败";
};

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

        const errorMsg = getErrorMessage(res);
        if (withAuth && isAuthExpired(res.statusCode, errorMsg)) {
          uni.showToast({
            title: "登录已过期，请重新登录",
            icon: "none",
            duration: 2000
          });
          redirectToLogin();
          reject(res.data);
          return;
        }

        uni.showToast({
          title: String(errorMsg),
          icon: "none",
          duration: 3000
        });
        reject(res.data);
      },
      fail: (err) => {
        console.error("request failed", BASE_URL + url, err);
        const reason = err && err.errMsg ? err.errMsg : "请求失败";
        uni.showToast({ title: `无法连接后端：${reason}`, icon: "none", duration: 4000 });
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
          return;
        }
        uni.showToast({ title: "文件上传失败", icon: "none" });
        reject(res);
      },
      fail: (err) => {
        console.error("upload failed", BASE_URL + url, err);
        const reason = err && err.errMsg ? err.errMsg : "上传失败";
        uni.showToast({ title: `无法连接后端：${reason}`, icon: "none", duration: 4000 });
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
  getBaseUrl,
  getEmailCode: (email) => request("/auth/code?email=" + encodeURIComponent(email), { method: "GET", auth: false }),
  register: (data) => request("/auth/register", { method: "POST", data, auth: false }),
  login: (data) => request("/auth/login", { method: "POST", data, auth: false }),
  getInvitationSummary: () => request("/invitation/me", { method: "GET" }),
  generateName: (data) => request("/name/generate", { method: "POST", data }),
  feedbackName: (data) => request("/name/feedback", { method: "POST", data }),
  generateVisual: (data) => request("/visual/generate", { method: "POST", data }),
  uploadKnowledge: (filePath) => uploadFile("/knowledge/upload", filePath),

  createApiKey: (name) => request("/api-key/create", { method: "POST", data: { name } }),
  getApiKeys: () => request("/api-key/list", { method: "GET" }),
  disableApiKey: (keyId) => request("/api-key/disable", { method: "POST", data: { key_id: keyId } }),
  enableApiKey: (keyId) => request("/api-key/enable", { method: "POST", data: { key_id: keyId } }),
  deleteApiKey: (keyId) => request("/api-key/delete", { method: "POST", data: { key_id: keyId } }),
  getApiKeyStats: () => request("/api-key/stats", { method: "GET" }),
  getApiKeyUsage: (params) => request("/api-key/usage" + buildQuery(params), { method: "GET" }),

  getPaymentPackages: () => request("/payments/packages", { method: "GET" }),
  createPayment: (data) => request("/payments/create", { method: "POST", data }),
  getPaymentOrder: (outTradeNo) => request(`/payments/orders/${encodeURIComponent(outTradeNo)}`, { method: "GET" }),
  syncPaymentOrder: (outTradeNo) => request(`/payments/orders/${encodeURIComponent(outTradeNo)}/sync`, { method: "POST" }),
  sandboxCompletePayment: (outTradeNo) => request(`/payments/orders/${encodeURIComponent(outTradeNo)}/sandbox-complete`, { method: "POST" }),

  getAdminUsers: (params) => request("/admin/users" + buildQuery(params), { method: "GET" }),
  updateAdminUserRole: (userId, role) => request(`/admin/users/${userId}/role`, { method: "PATCH", data: { role } }),
  updateAdminUserSegment: (userId, user_segment) => request(`/admin/users/${userId}/segment`, { method: "PATCH", data: { user_segment } }),
  banAdminUser: (userId, data) => request(`/admin/users/${userId}/ban`, { method: "POST", data }),
  unbanAdminUser: (userId) => request(`/admin/users/${userId}/unban`, { method: "POST" }),
  addAdminBlacklist: (userId, reason) => request(`/admin/users/${userId}/blacklist`, { method: "POST", data: { reason } }),
  removeAdminBlacklist: (userId) => request(`/admin/users/${userId}/blacklist`, { method: "DELETE" }),
  getSensitiveWords: () => request("/admin/sensitive-words", { method: "GET" }),
  saveSensitiveWord: (data) => request("/admin/sensitive-words", { method: "POST", data }),
  disableSensitiveWord: (word) => request(`/admin/sensitive-words/${encodeURIComponent(word)}`, { method: "DELETE" }),
  deleteSensitiveWord: (word) => request(`/admin/sensitive-words/${encodeURIComponent(word)}/remove`, { method: "DELETE" }),
  getModerationRecords: (params) => request("/admin/moderation-records" + buildQuery(params), { method: "GET" }),
  reviewModerationRecord: (recordId, note) => request(`/admin/moderation-records/${recordId}/review`, { method: "POST", data: { note } }),
  getAdminActionLogs: (params) => request("/admin/action-logs" + buildQuery(params), { method: "GET" }),

  createCommunityPoll: (data) => request("/community/polls", { method: "POST", data }),
  getCommunityPolls: (params) => request("/community/polls" + buildQuery(params), { method: "GET" }),
  voteCommunityPoll: (pollId, optionId) => request(`/community/polls/${pollId}/vote`, { method: "POST", data: { option_id: optionId } }),
  deleteCommunityPoll: (pollId) => request(`/community/polls/${pollId}`, { method: "DELETE" })
};
