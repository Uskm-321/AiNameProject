<template>
  <view class="page">
    <view class="shell">
      <view class="topbar">
        <view>
          <view class="title">用户管理</view>
          <text class="subtitle">{{ currentUser.email || '管理员' }}</text>
        </view>
        <button class="secondary-btn" @click="goBack">返回工作台</button>
      </view>

      <view class="stats-grid">
        <view class="stat-card">
          <text class="stat-label">总用户数</text>
          <text class="stat-value">{{ overview.total_users }}</text>
        </view>
        <view class="stat-card">
          <text class="stat-label">今日活跃用户</text>
          <text class="stat-value green">{{ overview.active_users_today }}</text>
        </view>
        <view class="stat-card">
          <text class="stat-label">总调用量</text>
          <text class="stat-value blue">{{ overview.total_usage }}</text>
        </view>
      </view>

      <view class="panel">
        <view class="toolbar">
          <input
            v-model="keyword"
            class="search-input"
            placeholder="搜索用户名或邮箱"
            confirm-type="search"
            @confirm="searchUsers"
          />
          <button class="primary-btn" @click="searchUsers">搜索</button>
        </view>

        <scroll-view scroll-x class="table-scroll">
          <view class="user-table">
            <view class="table-row table-head">
              <text>ID</text><text>用户名</text><text>邮箱</text><text>角色</text>
              <text>注册时间</text><text>状态</text><text>今日调用量</text><text class="align-right">操作</text>
            </view>
            <view v-for="user in users" :key="user.id" class="table-row">
              <text>{{ user.id }}</text>
              <text class="name-link" @click="openDetail(user)">{{ user.username }}</text>
              <text class="truncate">{{ user.email }}</text>
              <view>
                <picker
                  v-if="canChangeRole(user)"
                  :range="roleOptions"
                  :value="roleIndex(user.role)"
                  @change="event => changeRole(user, event)"
                >
                  <view class="role-select">{{ roleLabel(user.role) }}</view>
                </picker>
                <text v-else>{{ roleLabel(user.role) }}</text>
              </view>
              <text>{{ formatTime(user.created_at) }}</text>
              <view>
                <text :class="['status-badge', user.status === 'ACTIVE' ? 'normal' : 'banned']">
                  {{ user.status === 'ACTIVE' ? '正常' : '封禁' }}
                </text>
              </view>
              <text>{{ user.today_usage || 0 }}</text>
              <view class="row-actions">
                <button
                  v-if="canBan(user) && user.status === 'ACTIVE'"
                  class="text-btn warning"
                  @click="banUser(user)"
                >封禁</button>
                <button
                  v-if="canBan(user) && user.status === 'BANNED'"
                  class="text-btn success"
                  @click="unbanUser(user)"
                >解封</button>
              </view>
            </view>
            <view v-if="!users.length && !loading" class="empty">暂无用户</view>
          </view>
        </scroll-view>

        <view class="pagination">
          <button class="page-btn" :disabled="page <= 1" @click="changePage(-1)">上一页</button>
          <text>第 {{ page }} / {{ totalPages }} 页，共 {{ total }} 人</text>
          <button class="page-btn" :disabled="page >= totalPages" @click="changePage(1)">下一页</button>
        </view>
      </view>
    </view>

    <view v-if="detailVisible" class="modal-mask" @click.self="closeDetail">
      <view class="detail-modal">
        <view class="modal-head">
          <view>
            <view class="modal-title">{{ detail.user.username }}</view>
            <text class="subtitle">{{ detail.user.email }} · ID {{ detail.user.id }}</text>
          </view>
          <button class="close-btn" @click="closeDetail">×</button>
        </view>

        <view class="detail-grid">
          <view><text class="detail-label">角色</text><text>{{ roleLabel(detail.user.role) }}</text></view>
          <view><text class="detail-label">状态</text><text>{{ detail.user.status === 'ACTIVE' ? '正常' : '封禁' }}</text></view>
          <view><text class="detail-label">注册时间</text><text>{{ formatTime(detail.user.created_at) }}</text></view>
          <view><text class="detail-label">今日调用</text><text>{{ detail.user.today_usage }}</text></view>
        </view>

        <view class="section-title">API Key（{{ detail.api_keys.length }}）</view>
        <scroll-view scroll-x class="table-scroll">
          <view class="key-table">
            <view class="key-row key-head">
              <text>名称</text><text>Key</text><text>状态</text><text>今日用量</text><text>历史用量</text>
            </view>
            <view v-for="key in detail.api_keys" :key="key.id" class="key-row">
              <text>{{ key.name }}</text>
              <text class="key-text">{{ key.key_masked }}</text>
              <text :class="['status-badge', key.status === 'active' ? 'normal' : 'disabled']">
                {{ key.status === 'active' ? '激活' : '禁用' }}
              </text>
              <text>{{ key.used_today }} / {{ key.total_quota }}</text>
              <text>{{ key.total_used }}</text>
            </view>
            <view v-if="!detail.api_keys.length" class="empty">该用户尚未创建 API Key</view>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import http from '@/http/http.js';

const currentUser = ref(uni.getStorageSync('user') || {});
const loading = ref(false);
const users = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const keyword = ref('');
const overview = ref({ total_users: 0, active_users_today: 0, total_usage: 0 });
const detailVisible = ref(false);
const detail = ref({ user: {}, api_keys: [] });
const roleOptions = ['USER', 'ADMIN'];
const freezeDurationOptions = [
  { label: '1天', days: 1 },
  { label: '7天', days: 7 },
  { label: '30天', days: 30 },
  { label: '永久', days: null }
];
const adminRoles = ['admin', 'super_admin', 'ADMIN', 'SUPER_ADMIN'];
const superAdminRoles = ['super_admin', 'SUPER_ADMIN'];

const isSuperAdmin = computed(() => superAdminRoles.includes(currentUser.value.role));
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
const normalizedRole = (role) => String(role || '').toLowerCase();
const roleLabel = (role) => normalizedRole(role) || 'user';
const roleIndex = (role) => normalizedRole(role) === 'admin' ? 1 : 0;

const canChangeRole = (user) => (
  isSuperAdmin.value
  && user.id !== currentUser.value.id
  && normalizedRole(user.role) !== 'super_admin'
);
const canBan = (user) => {
  if (user.id === currentUser.value.id || normalizedRole(user.role) === 'super_admin') return false;
  if (isSuperAdmin.value) return true;
  return normalizedRole(user.role) === 'user';
};

const ensureAccess = () => {
  if (!adminRoles.includes(currentUser.value.role)) {
    uni.showToast({ title: '仅限管理员访问', icon: 'none' });
    setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 600);
    return false;
  }
  return true;
};

const loadOverview = async () => {
  overview.value = await http.getAdminUsersOverview();
};
const loadUsers = async () => {
  loading.value = true;
  try {
    const result = await http.getAdminUsers({
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value.trim()
    });
    users.value = result.items || [];
    total.value = result.total || 0;
  } finally {
    loading.value = false;
  }
};
const refresh = () => Promise.all([loadOverview(), loadUsers()]);

const searchUsers = () => {
  page.value = 1;
  loadUsers();
};
const changePage = (delta) => {
  const next = page.value + delta;
  if (next < 1 || next > totalPages.value) return;
  page.value = next;
  loadUsers();
};
const openDetail = async (user) => {
  detail.value = await http.getAdminUserDetail(user.id);
  detailVisible.value = true;
};
const closeDetail = () => { detailVisible.value = false; };

const calcBannedUntil = (days) => {
  if (days === null) return null;
  const until = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
  const local = new Date(until.getTime() - until.getTimezoneOffset() * 60 * 1000);
  return local.toISOString().slice(0, 19);
};

const banUser = (user) => {
  uni.showActionSheet({
    itemList: freezeDurationOptions.map(item => item.label),
    success: ({ tapIndex }) => {
      const duration = freezeDurationOptions[tapIndex];
      uni.showModal({
        title: `封禁 ${user.username}`,
        editable: true,
        placeholderText: '请输入封禁理由',
        success: async (result) => {
          if (!result.confirm) return;
          const reason = (result.content || '').trim();
          if (!reason) {
            return uni.showToast({ title: '请输入封禁理由', icon: 'none' });
          }
          await http.banAdminUser(user.id, {
            reason,
            banned_until: calcBannedUntil(duration.days)
          });
          uni.showToast({ title: '已封禁', icon: 'success' });
          await refresh();
        }
      });
    }
  });
};
const unbanUser = async (user) => {
  await http.unbanAdminUser(user.id);
  uni.showToast({ title: '已解封', icon: 'success' });
  await refresh();
};
const changeRole = (user, event) => {
  const role = roleOptions[Number(event.detail.value)];
  if (role === String(user.role).toUpperCase()) return;
  uni.showModal({
    title: '修改角色',
    content: `确认将 ${user.username} 修改为 ${role.toLowerCase()}？`,
    success: async (result) => {
      if (!result.confirm) return;
      await http.updateAdminUserRole(user.id, role);
      uni.showToast({ title: '角色已更新', icon: 'success' });
      await loadUsers();
    }
  });
};

const formatTime = (value) => value
  ? new Date(value).toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-')
  : '-';
const goBack = () => uni.navigateBack({ delta: 1 });

onMounted(async () => {
  if (!ensureAccess()) return;
  await refresh();
});
</script>

<style scoped>
.page { min-height: 100vh; background: #f5f7fa; color: #101828; }
.shell { width: min(1440px, calc(100% - 48rpx)); margin: 0 auto; padding: 34rpx 0 60rpx; }
.topbar, .toolbar, .pagination, .row-actions, .modal-head { display: flex; align-items: center; }
.topbar { justify-content: space-between; gap: 20rpx; margin-bottom: 24rpx; }
.title { font-size: 38rpx; font-weight: 700; }.subtitle { display: block; margin-top: 6rpx; color: #667085; font-size: 24rpx; }
button { letter-spacing: 0; }
.primary-btn, .secondary-btn, .page-btn { height: 66rpx; margin: 0; padding: 0 24rpx; border-radius: 10rpx; font-size: 24rpx; line-height: 64rpx; }
.primary-btn { color: #fff; background: #2563eb; border: 1px solid #2563eb; }
.secondary-btn, .page-btn { color: #344054; background: #fff; border: 1px solid #d0d5dd; }
.stats-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18rpx; margin-bottom: 20rpx; }
.stat-card, .panel { background: #fff; border: 1px solid #e4e7ec; border-radius: 12rpx; }
.stat-card { min-height: 140rpx; display: flex; flex-direction: column; justify-content: center; padding: 26rpx; }
.stat-label { color: #667085; font-size: 24rpx; }.stat-value { margin-top: 9rpx; font-size: 38rpx; font-weight: 700; }
.stat-value.green { color: #067647; }.stat-value.blue { color: #175cd3; }
.panel { padding: 26rpx; }.toolbar { gap: 14rpx; margin-bottom: 22rpx; }
.search-input { flex: 1; height: 66rpx; padding: 0 20rpx; border: 1px solid #d0d5dd; border-radius: 10rpx; font-size: 25rpx; box-sizing: border-box; }
.table-scroll { width: 100%; }.user-table { min-width: 1380rpx; }
.table-row { min-height: 88rpx; display: grid; grid-template-columns: .5fr 1fr 1.5fr .8fr 1.25fr .8fr .8fr 1fr; align-items: center; gap: 18rpx; padding: 0 14rpx; border-top: 1px solid #eaecf0; font-size: 23rpx; box-sizing: border-box; }
.table-head { min-height: 66rpx; border-top: 0; background: #f9fafb; color: #667085; font-size: 21rpx; font-weight: 600; }
.name-link { color: #175cd3; font-weight: 600; cursor: pointer; }.truncate { overflow: hidden; text-overflow: ellipsis; }
.role-select { display: inline-block; min-width: 110rpx; padding: 8rpx 12rpx; border: 1px solid #d0d5dd; border-radius: 8rpx; }
.status-badge { display: inline-block; padding: 5rpx 13rpx; border-radius: 999px; font-size: 21rpx; font-weight: 600; }
.status-badge.normal { color: #067647; background: #ecfdf3; }.status-badge.banned { color: #b42318; background: #fef3f2; }
.status-badge.disabled { color: #475467; background: #f2f4f7; }
.align-right { text-align: right; }.row-actions { justify-content: flex-end; }
.text-btn { width: auto; min-width: 76rpx; height: 52rpx; margin: 0; padding: 0 12rpx; border: 0; background: transparent; font-size: 22rpx; line-height: 50rpx; }
.text-btn.warning { color: #b54708; }.text-btn.success { color: #067647; }
.empty { padding: 60rpx 20rpx; text-align: center; color: #98a2b3; font-size: 24rpx; }
.pagination { justify-content: flex-end; gap: 18rpx; margin-top: 22rpx; color: #667085; font-size: 23rpx; }
.page-btn { height: 58rpx; line-height: 56rpx; padding: 0 18rpx; }
.modal-mask { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; padding: 28rpx; background: rgba(16, 24, 40, .55); box-sizing: border-box; }
.detail-modal { width: min(1050rpx, 100%); max-height: 86vh; overflow-y: auto; padding: 30rpx; border-radius: 14rpx; background: #fff; }
.modal-head { justify-content: space-between; gap: 20rpx; }.modal-title { font-size: 32rpx; font-weight: 700; }
.close-btn { width: 58rpx; height: 58rpx; margin: 0; padding: 0; border: 0; background: #f2f4f7; color: #475467; font-size: 36rpx; line-height: 54rpx; }
.detail-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14rpx; margin: 26rpx 0; }
.detail-grid > view { display: flex; flex-direction: column; gap: 7rpx; padding: 18rpx; border: 1px solid #eaecf0; border-radius: 10rpx; font-size: 23rpx; }
.detail-label { color: #667085; }.section-title { margin: 8rpx 0 14rpx; font-size: 27rpx; font-weight: 650; }
.key-table { min-width: 820rpx; }.key-row { min-height: 72rpx; display: grid; grid-template-columns: 1.2fr 1.7fr .8fr 1fr .8fr; align-items: center; gap: 14rpx; padding: 0 12rpx; border-top: 1px solid #eaecf0; font-size: 22rpx; }
.key-head { border-top: 0; color: #667085; background: #f9fafb; font-weight: 600; }.key-text { font-family: Consolas, Monaco, monospace; color: #475467; }
@media (max-width: 700px) {
  .shell { width: calc(100% - 28rpx); padding-top: 20rpx; }.stats-grid { grid-template-columns: 1fr; gap: 12rpx; }
  .stat-card { min-height: 110rpx; }.panel { padding: 18rpx 14rpx; }.detail-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
