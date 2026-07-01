<template>
  <view class="page">
    <view class="topbar">
      <view>
        <view class="title">管理员工作台</view>
        <view class="subtitle">{{ currentUser.email || 'ADMIN' }}</view>
      </view>
      <view class="top-actions">
        <button class="ghost-btn" size="mini" @click="goApp">起名页</button>
        <button class="danger-btn mini" size="mini" @click="logout">退出</button>
      </view>
    </view>

    <view class="stats-grid">
      <view class="stat">
        <text class="stat-label">用户总数</text>
        <text class="stat-value">{{ usersTotal }}</text>
      </view>
      <view class="stat">
        <text class="stat-label">封禁用户</text>
        <text class="stat-value">{{ bannedCount }}</text>
      </view>
      <view class="stat">
        <text class="stat-label">黑名单</text>
        <text class="stat-value">{{ blacklistedCount }}</text>
      </view>
      <view class="stat">
        <text class="stat-label">待巡查</text>
        <text class="stat-value">{{ pendingReviewCount }}</text>
      </view>
    </view>

    <scroll-view class="tabs" scroll-x>
      <view
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab', activeTab === tab.key ? 'active' : '']"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </view>
    </scroll-view>

    <view v-if="activeTab === 'users'" class="panel">
      <view class="toolbar">
        <input class="search" v-model="userQuery.keyword" placeholder="搜索邮箱或用户名" confirm-type="search" @confirm="loadUsers" />
        <picker :range="segmentOptions" @change="onSegmentFilter">
          <view class="filter">{{ userQuery.user_segment || '全部画像' }}</view>
        </picker>
        <picker :range="statusOptions" @change="onStatusFilter">
          <view class="filter">{{ userQuery.status || '全部状态' }}</view>
        </picker>
        <button class="primary-btn compact" size="mini" @click="loadUsers">查询</button>
      </view>

      <view class="table">
        <view class="table-head user-grid">
          <text>用户</text>
          <text>画像</text>
          <text>状态</text>
          <text>操作</text>
        </view>
        <view v-for="user in users" :key="user.id" class="table-row user-grid">
          <view class="user-cell">
            <text class="strong">{{ user.username }}</text>
            <text class="muted">{{ user.email }}</text>
            <text class="muted">ID {{ user.id }} · {{ user.role }}</text>
          </view>
          <view class="stack">
            <picker :range="['B', 'C']" @change="e => changeSegment(user, ['B', 'C'][e.detail.value])">
              <view class="chip">{{ user.user_segment }}</view>
            </picker>
            <picker :range="['USER', 'ADMIN']" @change="e => changeRole(user, ['USER', 'ADMIN'][e.detail.value])">
              <view class="link-btn">{{ user.role === 'ADMIN' ? '管理员' : '设为管理员' }}</view>
            </picker>
          </view>
          <view class="stack">
            <text :class="['status', user.status === 'ACTIVE' ? 'ok' : 'blocked']">{{ user.status }}</text>
            <text v-if="user.blacklisted" class="status blocked">BLACKLIST</text>
          </view>
          <view class="actions">
            <button v-if="user.status === 'ACTIVE'" class="warn-btn mini" size="mini" @click="banUser(user)">封禁</button>
            <button v-else class="primary-btn mini" size="mini" @click="unbanUser(user)">解封</button>
            <button v-if="!user.blacklisted" class="danger-btn mini" size="mini" @click="blacklistUser(user)">拉黑</button>
            <button v-else class="ghost-btn mini" size="mini" @click="removeBlacklist(user)">移出</button>
          </view>
        </view>
      </view>
    </view>

    <view v-if="activeTab === 'words'" class="panel">
      <view class="form-row">
        <input class="input" v-model="wordForm.word" placeholder="敏感词" />
        <input class="input" v-model="wordForm.reason" placeholder="拦截原因" />
        <picker :range="['BLOCK', 'WARN']" @change="e => wordForm.severity = ['BLOCK', 'WARN'][e.detail.value]">
          <view class="filter">{{ wordForm.severity }}</view>
        </picker>
        <button class="primary-btn compact" size="mini" @click="saveWord">保存</button>
      </view>
      <view class="list">
        <view v-for="word in sensitiveWords" :key="word.id" class="list-item">
          <view>
            <text class="strong">{{ word.word }}</text>
            <text class="muted">{{ word.reason || '无原因' }}</text>
          </view>
          <view class="actions">
            <text :class="['status', word.active ? 'ok' : 'blocked']">{{ word.active ? '启用' : '停用' }}</text>
            <button v-if="word.active" class="danger-btn mini" size="mini" @click="disableWord(word)">停用</button>
            <button v-else class="danger-btn mini" size="mini" @click="deleteWord(word)">删除</button>
          </view>
        </view>
      </view>
    </view>

    <view v-if="activeTab === 'moderation'" class="panel">
      <view class="list">
        <view v-for="item in moderationRecords" :key="item.id" class="audit-item">
          <view class="audit-head">
            <text class="strong">#{{ item.id }} {{ item.source }}</text>
            <text :class="['status', item.decision === 'PASS' ? 'ok' : 'blocked']">{{ item.decision }}</text>
          </view>
          <text class="muted">用户 {{ item.user_id }} · {{ item.review_status }} · {{ formatTime(item.created_at) }}</text>
          <view class="audit-text">{{ item.input_text }}</view>
          <view v-if="item.output_text" class="audit-text">{{ item.output_text }}</view>
          <view v-if="item.matched_words" class="matched">命中：{{ item.matched_words }}</view>
          <button v-if="item.review_status !== 'REVIEWED'" class="primary-btn mini" size="mini" @click="reviewRecord(item)">标记已审</button>
        </view>
      </view>
    </view>

    <view v-if="activeTab === 'logs'" class="panel">
      <view class="list">
        <view v-for="log in actionLogs" :key="log.id" class="list-item">
          <view>
            <text class="strong">{{ log.action }}</text>
            <text class="muted">管理员 {{ log.admin_user_id }} · 目标 {{ log.target_user_id || '-' }}</text>
            <text class="muted">{{ log.detail || '无详情' }}</text>
          </view>
          <text class="muted">{{ formatTime(log.created_at) }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import http from '@/http/http.js';

const tabs = [
  { key: 'users', label: '用户与权限' },
  { key: 'words', label: '敏感词' },
  { key: 'moderation', label: '内容巡查' },
  { key: 'logs', label: '审计日志' }
];

const activeTab = ref('users');
const currentUser = ref(uni.getStorageSync('user') || {});
const users = ref([]);
const usersTotal = ref(0);
const sensitiveWords = ref([]);
const moderationRecords = ref([]);
const actionLogs = ref([]);
const userQuery = ref({ page: 1, page_size: 20, keyword: '', user_segment: '', status: '' });
const wordForm = ref({ word: '', reason: '', severity: 'BLOCK' });
const segmentOptions = ['全部画像', 'B', 'C'];
const statusOptions = ['全部状态', 'ACTIVE', 'BANNED'];

const bannedCount = computed(() => users.value.filter(item => item.status === 'BANNED').length);
const blacklistedCount = computed(() => users.value.filter(item => item.blacklisted).length);
const pendingReviewCount = computed(() => moderationRecords.value.filter(item => item.review_status !== 'REVIEWED').length);

const ensureAdmin = () => {
  if (!currentUser.value || currentUser.value.role !== 'ADMIN') {
    uni.showToast({ title: '需要管理员权限', icon: 'none' });
    setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 800);
  }
};

const switchTab = async (key) => {
  activeTab.value = key;
  if (key === 'users') await loadUsers();
  if (key === 'words') await loadSensitiveWords();
  if (key === 'moderation') await loadModerationRecords();
  if (key === 'logs') await loadActionLogs();
};

const loadUsers = async () => {
  const res = await http.getAdminUsers(userQuery.value);
  users.value = res.items || [];
  usersTotal.value = res.total || 0;
};

const loadSensitiveWords = async () => {
  sensitiveWords.value = await http.getSensitiveWords();
};

const loadModerationRecords = async () => {
  const res = await http.getModerationRecords({ page: 1, page_size: 20 });
  moderationRecords.value = res.items || [];
};

const loadActionLogs = async () => {
  const res = await http.getAdminActionLogs({ page: 1, page_size: 20 });
  actionLogs.value = res.items || [];
};

const safeLoad = async (loader) => {
  try {
    await loader();
  } catch (error) {
    console.error(error);
  }
};

const refreshAll = async () => {
  await safeLoad(loadUsers);
  await safeLoad(loadSensitiveWords);
  await safeLoad(loadModerationRecords);
  await safeLoad(loadActionLogs);
};

const onSegmentFilter = (e) => {
  const value = segmentOptions[e.detail.value];
  userQuery.value.user_segment = value === '全部画像' ? '' : value;
  loadUsers();
};

const onStatusFilter = (e) => {
  const value = statusOptions[e.detail.value];
  userQuery.value.status = value === '全部状态' ? '' : value;
  loadUsers();
};

const changeRole = async (user, role) => {
  if (user.role === role) return;
  await http.updateAdminUserRole(user.id, role);
  await loadUsers();
};

const changeSegment = async (user, segment) => {
  if (user.user_segment === segment) return;
  await http.updateAdminUserSegment(user.id, segment);
  await loadUsers();
};

const banUser = (user) => {
  uni.showModal({
    title: '封禁用户',
    editable: true,
    placeholderText: '封禁原因',
    success: async (res) => {
      if (!res.confirm) return;
      await http.banAdminUser(user.id, { reason: res.content || '管理员封禁' });
      await loadUsers();
    }
  });
};

const unbanUser = async (user) => {
  await http.unbanAdminUser(user.id);
  await loadUsers();
};

const blacklistUser = (user) => {
  uni.showModal({
    title: '加入黑名单',
    editable: true,
    placeholderText: '黑名单原因',
    success: async (res) => {
      if (!res.confirm) return;
      await http.addAdminBlacklist(user.id, res.content || '管理员拉黑');
      await loadUsers();
    }
  });
};

const removeBlacklist = async (user) => {
  await http.removeAdminBlacklist(user.id);
  await loadUsers();
};

const saveWord = async () => {
  if (!wordForm.value.word.trim()) {
    return uni.showToast({ title: '请输入敏感词', icon: 'none' });
  }
  await http.saveSensitiveWord(wordForm.value);
  wordForm.value = { word: '', reason: '', severity: 'BLOCK' };
  await loadSensitiveWords();
};

const disableWord = async (word) => {
  await http.disableSensitiveWord(word.word);
  await loadSensitiveWords();
};

const deleteWord = (word) => {
  uni.showModal({
    title: '删除敏感词',
    content: `确认彻底删除“${word.word}”吗？删除后不会再占用列表位置。`,
    success: async (res) => {
      if (!res.confirm) return;
      await http.deleteSensitiveWord(word.word);
      uni.showToast({ title: '已删除', icon: 'success' });
      await loadSensitiveWords();
    }
  });
};

const reviewRecord = async (item) => {
  await http.reviewModerationRecord(item.id, '管理员已复核');
  await loadModerationRecords();
};

const formatTime = (value) => {
  if (!value) return '-';
  return String(value).replace('T', ' ').slice(0, 19);
};

const goApp = () => uni.reLaunch({ url: '/pages/index/index' });

const logout = () => {
  uni.removeStorageSync('token');
  uni.removeStorageSync('user');
  uni.reLaunch({ url: '/pages/login/login' });
};

onMounted(async () => {
  ensureAdmin();
  await refreshAll();
});
</script>

<style scoped>
.page { min-height: 100vh; background: #f4f6f8; padding: 24rpx; box-sizing: border-box; color: #172033; }
.topbar { display: flex; justify-content: space-between; align-items: center; gap: 20rpx; margin-bottom: 22rpx; }
.title { font-size: 40rpx; font-weight: 700; }
.subtitle, .muted { display: block; color: #667085; font-size: 24rpx; line-height: 1.5; }
.top-actions { display: flex; gap: 12rpx; align-items: center; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16rpx; margin-bottom: 20rpx; }
.stat { background: #fff; border: 1px solid #e5e7eb; border-radius: 8rpx; padding: 22rpx; }
.stat-label { display: block; color: #667085; font-size: 24rpx; }
.stat-value { display: block; margin-top: 8rpx; font-size: 42rpx; font-weight: 700; color: #111827; }
.tabs { white-space: nowrap; margin-bottom: 20rpx; }
.tab { display: inline-flex; padding: 18rpx 26rpx; margin-right: 12rpx; background: #fff; border: 1px solid #d8dee8; border-radius: 8rpx; color: #475467; font-size: 26rpx; }
.tab.active { background: #165dff; border-color: #165dff; color: #fff; font-weight: 600; }
.panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 8rpx; padding: 20rpx; }
.toolbar, .form-row { display: flex; align-items: center; gap: 14rpx; flex-wrap: wrap; margin-bottom: 18rpx; }
.search, .input { min-width: 260rpx; height: 72rpx; padding: 0 20rpx; background: #f9fafb; border: 1px solid #d8dee8; border-radius: 8rpx; box-sizing: border-box; }
.filter { height: 72rpx; line-height: 72rpx; padding: 0 20rpx; background: #f9fafb; border: 1px solid #d8dee8; border-radius: 8rpx; color: #344054; font-size: 26rpx; }
.table { width: 100%; }
.user-grid { display: grid; grid-template-columns: 2fr 1fr 1fr 1.8fr; gap: 16rpx; align-items: center; }
.table-head { padding: 14rpx 12rpx; color: #667085; font-size: 24rpx; border-bottom: 1px solid #edf0f3; }
.table-row { min-height: 128rpx; padding: 18rpx 12rpx; border-bottom: 1px solid #edf0f3; }
.user-cell, .stack { display: flex; flex-direction: column; gap: 8rpx; min-width: 0; }
.strong { display: block; font-weight: 700; color: #101828; font-size: 28rpx; line-height: 1.5; word-break: break-all; }
.chip, .status { display: inline-flex; width: fit-content; padding: 6rpx 14rpx; border-radius: 8rpx; font-size: 23rpx; background: #eef2ff; color: #3538cd; }
.status.ok { background: #e7f8ef; color: #067647; }
.status.blocked { background: #fff1f3; color: #c01048; }
.link-btn { color: #165dff; font-size: 24rpx; }
.actions { display: flex; gap: 8rpx; flex-wrap: wrap; align-items: center; }
button { margin: 0; }
.primary-btn { background: #165dff; color: #fff; border-radius: 8rpx; }
.ghost-btn { background: #fff; color: #344054; border: 1px solid #d8dee8; border-radius: 8rpx; }
.warn-btn { background: #f79009; color: #fff; border-radius: 8rpx; }
.danger-btn { background: #d92d20; color: #fff; border-radius: 8rpx; }
.mini { padding: 0 16rpx; font-size: 23rpx; }
.compact { height: 72rpx; line-height: 72rpx; padding: 0 24rpx; font-size: 26rpx; }
.list { display: flex; flex-direction: column; gap: 14rpx; }
.list-item, .audit-item { border: 1px solid #edf0f3; border-radius: 8rpx; padding: 18rpx; }
.list-item { display: flex; justify-content: space-between; gap: 18rpx; align-items: center; }
.audit-head { display: flex; justify-content: space-between; align-items: center; gap: 16rpx; margin-bottom: 8rpx; }
.audit-text { margin-top: 12rpx; padding: 14rpx; background: #f9fafb; border-radius: 8rpx; color: #344054; font-size: 24rpx; line-height: 1.6; word-break: break-all; }
.matched { margin-top: 10rpx; color: #c01048; font-size: 24rpx; }

@media screen and (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .user-grid { grid-template-columns: 1fr; }
  .table-head { display: none; }
  .topbar { align-items: flex-start; }
}
</style>
