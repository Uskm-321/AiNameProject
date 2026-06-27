<template>
  <view class="page">
    <view class="shell">
      <view class="topbar">
        <view>
          <text class="eyebrow">开发者控制台</text>
          <view class="title">API 仪表盘</view>
          <text class="subtitle">{{ currentUser.email || currentUser.username || '当前用户' }}</text>
        </view>
        <view class="top-actions">
          <button class="secondary-button compact" @click="goNaming">返回起名页</button>
          <button class="primary-button compact" @click="openCreateModal">创建新 Key</button>
        </view>
      </view>

      <view class="stats-grid">
        <view v-for="item in statCards" :key="item.label" class="stat-card">
          <view :class="['stat-icon', item.tone]">{{ item.icon }}</view>
          <view>
            <text class="stat-label">{{ item.label }}</text>
            <view class="stat-value">{{ item.value }}</view>
          </view>
        </view>
      </view>

      <view class="chart-grid">
        <view class="panel">
          <view class="panel-heading">
            <view>
              <view class="panel-title">近 7 天调用趋势</view>
              <text class="panel-subtitle">所有 API Key 的每日调用次数</text>
            </view>
          </view>
          <canvas id="trendChart" canvas-id="trendChart" class="chart-canvas"></canvas>
        </view>
        <view class="panel">
          <view class="panel-heading">
            <view>
              <view class="panel-title">各接口调用分布</view>
              <text class="panel-subtitle">按接口类型汇总历史调用</text>
            </view>
          </view>
          <canvas id="distributionChart" canvas-id="distributionChart" class="chart-canvas"></canvas>
        </view>
      </view>

      <view class="panel">
        <view class="panel-heading">
          <view>
            <view class="panel-title">API Key</view>
            <text class="panel-subtitle">管理用于外部调用的访问密钥</text>
          </view>
          <button class="primary-button small-screen-create" @click="openCreateModal">创建新 Key</button>
        </view>
        <scroll-view scroll-x class="table-scroll">
          <view class="data-table key-table">
            <view class="table-row table-head">
              <text>名称</text><text>Key</text><text>状态</text><text>今日用量</text><text>创建时间</text><text class="align-right">操作</text>
            </view>
            <view v-for="item in keys" :key="item.id" class="table-row">
              <text class="cell-strong">{{ item.name }}</text>
              <text class="key-text">{{ item.key_masked }}</text>
              <view><text :class="['status-badge', item.status]">{{ item.status === 'active' ? '激活' : '禁用' }}</text></view>
              <view class="usage-cell">
                <text>{{ item.used_today }} / {{ item.total_quota }}</text>
                <view class="progress-track"><view class="progress-fill" :style="{ width: usagePercent(item) + '%' }"></view></view>
              </view>
              <text>{{ formatTime(item.created_at) }}</text>
              <view class="row-actions">
                <button v-if="item.status === 'active'" class="text-button warning" @click="changeKeyStatus(item, 'disable')">禁用</button>
                <button v-else class="text-button success" @click="changeKeyStatus(item, 'enable')">启用</button>
                <button class="text-button danger" @click="confirmDelete(item)">删除</button>
              </view>
            </view>
            <view v-if="!keys.length && !loading" class="empty-state">暂无 API Key</view>
          </view>
        </scroll-view>
      </view>

      <view class="panel">
        <view class="panel-heading">
          <view>
            <view class="panel-title">最近调用记录</view>
            <text class="panel-subtitle">共 {{ usageTotal }} 条记录</text>
          </view>
        </view>
        <scroll-view scroll-x class="table-scroll">
          <view class="data-table usage-table">
            <view class="table-row table-head"><text>时间</text><text>接口路径</text><text>消耗次数</text><text>状态</text></view>
            <view v-for="item in usageItems" :key="item.id" class="table-row">
              <text>{{ formatTime(item.created_at) }}</text>
              <text class="path-text">{{ item.path }}</text>
              <text>{{ item.cost }}</text>
              <view><text :class="['status-badge', item.status === 'success' ? 'active' : 'failed']">{{ usageStatusLabel(item.status) }}</text></view>
            </view>
            <view v-if="!usageItems.length && !loading" class="empty-state">暂无调用记录</view>
          </view>
        </scroll-view>
        <view class="pagination">
          <button class="page-button" :disabled="usagePage <= 1" @click="changePage(-1)">上一页</button>
          <text>第 {{ usagePage }} / {{ totalPages }} 页</text>
          <button class="page-button" :disabled="usagePage >= totalPages" @click="changePage(1)">下一页</button>
        </view>
      </view>

      <view class="panel">
        <view class="panel-heading">
          <view><view class="panel-title">接口示例代码</view><text class="panel-subtitle">POST {{ selectedEndpoint.path }}</text></view>
          <view class="language-tabs">
            <view :class="['language-tab', codeLanguage === 'curl' ? 'selected' : '']" @click="codeLanguage = 'curl'">curl</view>
            <view :class="['language-tab', codeLanguage === 'python' ? 'selected' : '']" @click="codeLanguage = 'python'">Python</view>
          </view>
        </view>
        <view class="endpoint-tabs">
          <view
            v-for="item in endpointOptions"
            :key="item.path"
            :class="['endpoint-tab', selectedEndpoint.path === item.path ? 'selected' : '']"
            @click="selectedEndpoint = item"
          >{{ item.label }}</view>
        </view>
        <view class="code-wrap">
          <button class="copy-button" @click="copyCode">复制</button>
          <scroll-view scroll-x><text class="code-text">{{ currentCode }}</text></scroll-view>
        </view>
        <view class="schema-grid">
          <view>
            <view class="schema-title">请求体</view>
            <view class="schema-box">
              <text>category</text><text>起名类型</text><text>surname</text><text>姓氏</text>
              <text>gender</text><text>性别倾向</text><text>length</text><text>名字长度</text>
              <text>style</text><text>名字风格</text><text>other</text><text>补充要求</text>
            </view>
          </view>
          <view>
            <view class="schema-title">返回体</view>
            <view class="schema-box">
              <text>thread_id</text><text>本次生成会话 ID</text><text>names[].name</text><text>候选名字</text>
              <text>names[].reference</text><text>出处与参考</text><text>names[].moral</text><text>名字寓意</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <view v-if="createModalVisible" class="modal-mask" @click.self="closeCreateModal">
      <view class="modal">
        <view class="modal-title">创建 API Key</view>
        <text class="modal-subtitle">为新密钥设置一个便于识别的名称</text>
        <input v-model="newKeyName" class="modal-input" maxlength="100" placeholder="例如：我的测试 Key" />
        <view class="modal-actions">
          <button class="secondary-button" @click="closeCreateModal">取消</button>
          <button class="primary-button" :loading="creating" @click="createKey">创建</button>
        </view>
      </view>
    </view>
    <view v-if="createdKeyVisible" class="modal-mask">
      <view class="modal">
        <view class="modal-title">API Key 已创建</view>
        <text class="modal-subtitle">完整密钥仅在此处显示，请妥善保存。</text>
        <view class="created-key">{{ createdKey }}</view>
        <view class="modal-actions">
          <button class="secondary-button" @click="copyCreatedKey">复制 Key</button>
          <button class="primary-button" @click="createdKeyVisible = false">完成</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import http from '@/http/http.js';

const currentUser = ref(uni.getStorageSync('user') || {});
const loading = ref(false);
const creating = ref(false);
const keys = ref([]);
const usageItems = ref([]);
const usageTotal = ref(0);
const usagePage = ref(1);
const pageSize = 10;
const stats = ref({ total_keys: 0, used_today: 0, remaining_today: 0, total_used: 0, recent_7_days: [], endpoint_distribution: [] });
const createModalVisible = ref(false);
const createdKeyVisible = ref(false);
const newKeyName = ref('');
const createdKey = ref('');
const codeLanguage = ref('curl');
const exampleKey = ref(uni.getStorageSync('dashboard_api_key') || 'YOUR_API_KEY');
const endpointOptions = [
  { label: 'NPC', path: '/name/npc', category: 'NPC', other: '奇幻城镇中的任务发布者' },
  { label: '小说角色', path: '/name/novel-character', category: '小说角色', other: '现代悬疑小说主角' },
  { label: '地名', path: '/name/place', category: '地名', other: '临海的东方幻想城市' }
];
const selectedEndpoint = ref(endpointOptions[0]);

const statCards = computed(() => [
  { label: '总 Key 数', value: stats.value.total_keys, icon: 'K', tone: 'blue' },
  { label: '今日调用次数', value: stats.value.used_today, icon: '今', tone: 'green' },
  { label: '剩余总次数', value: stats.value.remaining_today, icon: '余', tone: 'amber' },
  { label: '总调用次数', value: stats.value.total_used, icon: '总', tone: 'violet' }
]);
const totalPages = computed(() => Math.max(1, Math.ceil(usageTotal.value / pageSize)));
const requestBody = computed(() => JSON.stringify({
  category: selectedEndpoint.value.category,
  surname: '',
  gender: '不限',
  length: '不限',
  style: '东方幻想',
  brand_tone: '',
  other: selectedEndpoint.value.other,
  exclude: []
}, null, 2));
const baseUrl = 'http://127.0.0.1:9000';
const curlCode = computed(() => `curl -X POST "${baseUrl}${selectedEndpoint.value.path}" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: ${exampleKey.value}" \\
  -d '${requestBody.value.replace(/\n/g, ' ')}'`);
const pythonCode = computed(() => `import requests

response = requests.post(
    "${baseUrl}${selectedEndpoint.value.path}",
    headers={"X-API-Key": "${exampleKey.value}"},
    json=${requestBody.value}
)
print(response.json())`);
const currentCode = computed(() => codeLanguage.value === 'curl' ? curlCode.value : pythonCode.value);

const loadUsage = async () => {
  const result = await http.getApiKeyUsage({ page: usagePage.value, page_size: pageSize });
  usageItems.value = result.items || [];
  usageTotal.value = result.total || 0;
};
const loadDashboard = async () => {
  loading.value = true;
  try {
    const [statsResult, keyResult] = await Promise.all([http.getApiKeyStats(), http.getApiKeys()]);
    stats.value = statsResult;
    keys.value = keyResult || [];
    await loadUsage();
    await nextTick();
    drawCharts();
  } finally {
    loading.value = false;
  }
};

const getCanvasRect = (selector) => new Promise((resolve) => {
  uni.createSelectorQuery().select(selector).boundingClientRect((rect) => resolve(rect)).exec();
});
const drawCharts = () => {
  drawLineChart(stats.value.recent_7_days || []);
  drawBarChart(stats.value.endpoint_distribution || []);
};
const drawGrid = (context, width, height, pad, maxValue) => {
  const chartHeight = height - pad.top - pad.bottom;
  context.setStrokeStyle('#e5e7eb');
  context.setFillStyle('#667085');
  context.setFontSize(11);
  for (let index = 0; index <= 4; index += 1) {
    const y = pad.top + chartHeight * index / 4;
    context.beginPath();
    context.moveTo(pad.left, y);
    context.lineTo(width - pad.right, y);
    context.stroke();
    context.fillText(String(Math.round(maxValue * (4 - index) / 4)), 8, y + 4);
  }
};
const drawLineChart = async (items) => {
  const rect = await getCanvasRect('#trendChart');
  if (!rect) return;
  const { width, height } = rect;
  const context = uni.createCanvasContext('trendChart');
  const pad = { left: 44, right: 18, top: 22, bottom: 38 };
  const chartWidth = width - pad.left - pad.right;
  const chartHeight = height - pad.top - pad.bottom;
  const maxValue = Math.max(5, ...items.map((item) => Number(item.used || 0)));
  drawGrid(context, width, height, pad, maxValue);
  const points = items.map((item, index) => ({
    x: pad.left + (items.length <= 1 ? 0 : chartWidth * index / (items.length - 1)),
    y: pad.top + chartHeight * (1 - Number(item.used || 0) / maxValue),
    label: item.date ? item.date.slice(5) : ''
  }));
  if (points.length) {
    context.setStrokeStyle('#2563eb');
    context.setLineWidth(2);
    context.beginPath();
    points.forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y));
    context.stroke();
    points.forEach((point) => {
      context.setFillStyle('#fff'); context.setStrokeStyle('#2563eb'); context.beginPath();
      context.arc(point.x, point.y, 4, 0, Math.PI * 2); context.fill(); context.stroke();
      context.setFillStyle('#667085'); context.setFontSize(10); context.fillText(point.label, point.x - 14, height - 12);
    });
  }
  context.draw();
};
const drawBarChart = async (items) => {
  const rect = await getCanvasRect('#distributionChart');
  if (!rect) return;
  const { width, height } = rect;
  const context = uni.createCanvasContext('distributionChart');
  const pad = { left: 44, right: 18, top: 22, bottom: 42 };
  const chartHeight = height - pad.top - pad.bottom;
  const chartWidth = width - pad.left - pad.right;
  const source = items.length ? items : [{ name: 'NPC', used: 0 }, { name: '小说角色', used: 0 }, { name: '地名', used: 0 }];
  const maxValue = Math.max(5, ...source.map((item) => Number(item.used || 0)));
  drawGrid(context, width, height, pad, maxValue);
  const slot = chartWidth / source.length;
  const colors = ['#2563eb', '#12b76a', '#f59e0b'];
  source.forEach((item, index) => {
    const barWidth = Math.min(52, slot * .48);
    const barHeight = chartHeight * Number(item.used || 0) / maxValue;
    const x = pad.left + slot * index + (slot - barWidth) / 2;
    context.setFillStyle(colors[index % colors.length]);
    context.fillRect(x, pad.top + chartHeight - barHeight, barWidth, Math.max(2, barHeight));
    context.setFillStyle('#344054'); context.setFontSize(11);
    context.fillText(item.name, pad.left + slot * index + slot / 2 - item.name.length * 6, height - 14);
  });
  context.draw();
};

const openCreateModal = () => { newKeyName.value = ''; createModalVisible.value = true; };
const closeCreateModal = () => { if (!creating.value) createModalVisible.value = false; };
const createKey = async () => {
  const name = newKeyName.value.trim();
  if (!name) return uni.showToast({ title: '请输入 Key 名称', icon: 'none' });
  creating.value = true;
  try {
    const result = await http.createApiKey(name);
    createdKey.value = result.key;
    exampleKey.value = result.key;
    uni.setStorageSync('dashboard_api_key', result.key);
    createModalVisible.value = false;
    createdKeyVisible.value = true;
    await loadDashboard();
  } finally { creating.value = false; }
};
const changeKeyStatus = async (item, action) => {
  if (action === 'enable') await http.enableApiKey(item.id);
  else await http.disableApiKey(item.id);
  uni.showToast({ title: action === 'enable' ? '已启用' : '已禁用', icon: 'success' });
  await loadDashboard();
};
const confirmDelete = (item) => {
  uni.showModal({
    title: '删除 API Key',
    content: `确认删除“${item.name}”吗？删除后无法恢复使用。`,
    success: async (result) => {
      if (!result.confirm) return;
      await http.deleteApiKey(item.id);
      uni.showToast({ title: '已删除', icon: 'success' });
      await loadDashboard();
    }
  });
};
const changePage = async (delta) => {
  const nextPage = usagePage.value + delta;
  if (nextPage < 1 || nextPage > totalPages.value) return;
  usagePage.value = nextPage;
  await loadUsage();
};
const copyText = (text) => uni.setClipboardData({ data: text });
const copyCode = () => copyText(currentCode.value);
const copyCreatedKey = () => copyText(createdKey.value);
const goNaming = () => uni.reLaunch({ url: '/pages/index/index' });
const usagePercent = (item) => Math.min(100, Math.round(item.used_today / Math.max(1, item.total_quota) * 100));
const usageStatusLabel = (status) => ({ success: '成功', failed: '失败', pending: '处理中' }[status] || status);
const formatTime = (value) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-') : '-';

onShow(loadDashboard);
</script>

<style scoped>
.page { min-height: 100vh; background: #f5f7fa; color: #101828; }
.shell { width: min(1440px, calc(100% - 48rpx)); margin: 0 auto; padding: 34rpx 0 64rpx; box-sizing: border-box; }
.topbar, .panel-heading, .top-actions, .row-actions, .modal-actions, .pagination { display: flex; align-items: center; }
.topbar { justify-content: space-between; gap: 24rpx; margin-bottom: 28rpx; }
.eyebrow { color: #2563eb; font-size: 22rpx; font-weight: 600; }
.title { margin-top: 4rpx; font-size: 40rpx; font-weight: 700; line-height: 1.25; }
.subtitle, .panel-subtitle, .modal-subtitle { color: #667085; font-size: 24rpx; }
.top-actions { gap: 14rpx; }
button { letter-spacing: 0; }
.primary-button, .secondary-button, .page-button { height: 72rpx; padding: 0 26rpx; border-radius: 10rpx; font-size: 25rpx; line-height: 70rpx; margin: 0; }
.primary-button { background: #2563eb; color: #fff; border: 1px solid #2563eb; }
.secondary-button, .page-button { background: #fff; color: #344054; border: 1px solid #d0d5dd; }
.compact { height: 64rpx; line-height: 62rpx; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 20rpx; margin-bottom: 20rpx; }
.stat-card, .panel { background: #fff; border: 1px solid #e4e7ec; border-radius: 12rpx; }
.stat-card { min-height: 150rpx; display: flex; align-items: center; gap: 22rpx; padding: 26rpx; box-sizing: border-box; }
.stat-icon { width: 64rpx; height: 64rpx; display: flex; align-items: center; justify-content: center; border-radius: 10rpx; font-size: 24rpx; font-weight: 700; flex: none; }
.stat-icon.blue { color: #175cd3; background: #eff4ff; }.stat-icon.green { color: #067647; background: #ecfdf3; }
.stat-icon.amber { color: #b54708; background: #fffaeb; }.stat-icon.violet { color: #6941c6; background: #f4f3ff; }
.stat-label { color: #667085; font-size: 24rpx; }.stat-value { margin-top: 7rpx; font-size: 38rpx; font-weight: 700; }
.chart-grid { display: grid; grid-template-columns: 1.35fr 1fr; gap: 20rpx; margin-bottom: 20rpx; }
.panel { padding: 26rpx; margin-bottom: 20rpx; overflow: hidden; }
.panel-heading { justify-content: space-between; gap: 20rpx; margin-bottom: 24rpx; }
.panel-title { font-size: 29rpx; font-weight: 650; }.panel-subtitle { display: block; margin-top: 6rpx; }
.chart-canvas { width: 100%; height: 330rpx; }.small-screen-create { display: none; }.table-scroll { width: 100%; }
.data-table { min-width: 1040rpx; }.key-table .table-row { grid-template-columns: 1.2fr 1.6fr .8fr 1.1fr 1.3fr 1.2fr; }
.usage-table { min-width: 760rpx; }.usage-table .table-row { grid-template-columns: 1.4fr 2fr .8fr .8fr; }
.table-row { min-height: 88rpx; display: grid; align-items: center; gap: 20rpx; padding: 0 14rpx; border-top: 1px solid #eaecf0; font-size: 24rpx; box-sizing: border-box; }
.table-head { min-height: 66rpx; border-top: 0; background: #f9fafb; color: #667085; font-size: 22rpx; font-weight: 600; }
.cell-strong { font-weight: 600; }.key-text, .path-text, .code-text { font-family: Consolas, Monaco, monospace; }.key-text { color: #475467; }
.status-badge { display: inline-block; padding: 5rpx 13rpx; border-radius: 999px; font-size: 21rpx; font-weight: 600; }
.status-badge.active { color: #067647; background: #ecfdf3; }.status-badge.disabled { color: #475467; background: #f2f4f7; }
.status-badge.failed { color: #b42318; background: #fef3f2; }.usage-cell { padding-right: 18rpx; }
.progress-track { width: 100%; height: 7rpx; margin-top: 9rpx; overflow: hidden; background: #eaecf0; border-radius: 6rpx; }
.progress-fill { height: 100%; background: #2563eb; border-radius: 6rpx; }.align-right { text-align: right; }
.row-actions { justify-content: flex-end; gap: 4rpx; }
.text-button { width: auto; min-width: 76rpx; height: 54rpx; padding: 0 11rpx; margin: 0; border: 0; background: transparent; font-size: 22rpx; line-height: 52rpx; }
.text-button.warning { color: #b54708; }.text-button.success { color: #067647; }.text-button.danger { color: #b42318; }
.empty-state { padding: 68rpx 20rpx; text-align: center; color: #98a2b3; font-size: 25rpx; }
.pagination { justify-content: flex-end; gap: 20rpx; margin-top: 22rpx; color: #667085; font-size: 23rpx; }
.page-button { height: 58rpx; line-height: 56rpx; padding: 0 20rpx; }
.language-tabs { display: flex; padding: 5rpx; border: 1px solid #d0d5dd; border-radius: 10rpx; background: #f9fafb; }
.language-tab { min-width: 90rpx; padding: 10rpx 18rpx; text-align: center; color: #667085; font-size: 23rpx; border-radius: 7rpx; }
.language-tab.selected { background: #fff; color: #101828; box-shadow: 0 1px 2px rgba(16, 24, 40, .08); }
.endpoint-tabs { display: flex; gap: 10rpx; margin-bottom: 18rpx; flex-wrap: wrap; }
.endpoint-tab { padding: 10rpx 18rpx; border: 1px solid #d0d5dd; border-radius: 8rpx; color: #475467; font-size: 23rpx; }
.endpoint-tab.selected { color: #175cd3; border-color: #84adff; background: #eff4ff; }
.code-wrap { position: relative; padding: 26rpx; border-radius: 10rpx; background: #171a21; overflow: hidden; }
.code-text { display: block; white-space: pre; color: #d0d5dd; font-size: 23rpx; line-height: 1.7; }
.copy-button { position: absolute; z-index: 2; right: 16rpx; top: 14rpx; width: auto; height: 52rpx; line-height: 50rpx; padding: 0 17rpx; margin: 0; color: #e4e7ec; background: #292e38; border: 1px solid #475467; border-radius: 8rpx; font-size: 21rpx; }
.schema-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24rpx; margin-top: 26rpx; }.schema-title { margin-bottom: 12rpx; font-size: 25rpx; font-weight: 650; }
.schema-box { display: grid; grid-template-columns: minmax(180rpx, .8fr) 1.2fr; border: 1px solid #eaecf0; border-radius: 10rpx; overflow: hidden; }
.schema-box text { min-height: 60rpx; display: flex; align-items: center; padding: 0 16rpx; border-bottom: 1px solid #eaecf0; font-size: 22rpx; color: #475467; }
.schema-box text:nth-last-child(-n+2) { border-bottom: 0; }.schema-box text:nth-child(odd) { font-family: Consolas, Monaco, monospace; color: #344054; background: #f9fafb; }
.modal-mask { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; padding: 30rpx; background: rgba(16, 24, 40, .55); box-sizing: border-box; }
.modal { width: min(620rpx, 100%); padding: 34rpx; border-radius: 14rpx; background: #fff; box-shadow: 0 24rpx 60rpx rgba(16, 24, 40, .2); }
.modal-title { font-size: 32rpx; font-weight: 700; }.modal-subtitle { display: block; margin-top: 8rpx; }
.modal-input { height: 78rpx; margin-top: 28rpx; padding: 0 20rpx; border: 1px solid #d0d5dd; border-radius: 10rpx; font-size: 26rpx; box-sizing: border-box; }
.modal-actions { justify-content: flex-end; gap: 14rpx; margin-top: 28rpx; }
.created-key { margin-top: 24rpx; padding: 20rpx; word-break: break-all; font-family: Consolas, Monaco, monospace; font-size: 24rpx; color: #175cd3; background: #eff4ff; border: 1px solid #b2ccff; border-radius: 10rpx; }
@media (max-width: 900px) { .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.chart-grid { grid-template-columns: 1fr; } }
@media (max-width: 600px) {
  .shell { width: calc(100% - 28rpx); padding-top: 20rpx; }.topbar { align-items: flex-start; }.title { font-size: 34rpx; }
  .top-actions .primary-button { display: none; }.stats-grid { gap: 12rpx; }.stat-card { min-height: 128rpx; padding: 18rpx; gap: 14rpx; }
  .stat-icon { width: 52rpx; height: 52rpx; }.stat-value { font-size: 31rpx; }.panel { padding: 20rpx 16rpx; }
  .small-screen-create { display: block; height: 60rpx; line-height: 58rpx; padding: 0 18rpx; }.chart-canvas { height: 290rpx; }.schema-grid { grid-template-columns: 1fr; }
}
</style>
