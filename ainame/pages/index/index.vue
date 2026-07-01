<template>
  <view class="container">
    <view class="account-bar">
      <view>
        <view class="account-title">AI 智能起名</view>
        <view class="account-subtitle">{{ currentUser.email || '未登录' }}</view>
      </view>
      <view class="account-actions">
        <button class="invite-btn" size="mini" @click="goInvitation">邀请奖励</button>
        <button class="dashboard-btn" size="mini" @click="goDashboard">API 控制台</button>
        <button class="community-btn" size="mini" @click="goCommunity">社区投票</button>
        <button v-if="currentUser.role === 'ADMIN'" class="admin-btn" size="mini" @click="goAdmin">管理后台</button>
        <button class="logout-btn" size="mini" @click="switchAccount">切换账号</button>
      </view>
    </view>

    <view class="tabs">
      <view
        v-for="item in categories"
        :key="item"
        :class="['tab', formData.category === item ? 'active' : '']"
        @click="switchCategory(item)"
      >
        {{ item }}
      </view>
    </view>

    <view class="upload-section" v-if="formData.category === '企业名'">
      <view class="upload-tip">有企业命名规范？让 AI 学习你的专属标准</view>
      <button size="mini" @click="handleUploadDocs">上传专属知识库(TXT/PDF)</button>
    </view>

    <view class="form-group">
      <input
        v-if="formData.category === '人名'"
        class="input-box"
        v-model="formData.surname"
        placeholder="请输入姓氏（如：张）"
      />

      <picker
        v-if="formData.category !== '企业名'"
        mode="selector"
        :range="lengthOptions"
        @change="e => formData.length = lengthOptions[e.detail.value]"
      >
        <view class="input-box">字数要求：{{ formData.length }}</view>
      </picker>

      <picker
        v-if="formData.category === '人名'"
        mode="selector"
        :range="humanStyleOptions"
        @change="e => formData.style = humanStyleOptions[e.detail.value]"
      >
        <view class="input-box">名字风格：{{ formData.style }}</view>
      </picker>

      <picker
        v-if="formData.category === '企业名'"
        mode="selector"
        :range="brandToneOptions"
        @change="e => formData.brand_tone = brandToneOptions[e.detail.value]"
      >
        <view class="input-box">品牌调性：{{ formData.brand_tone }}</view>
      </picker>

      <picker
        v-if="formData.category === '宠物名'"
        mode="selector"
        :range="petStyleOptions"
        @change="e => formData.style = petStyleOptions[e.detail.value]"
      >
        <view class="input-box">名字风格：{{ formData.style }}</view>
      </picker>

      <textarea class="textarea-box" v-model="formData.other" :placeholder="getOtherPlaceholder()"></textarea>
    </view>

    <button class="btn-primary" :loading="loading" @click="handleGenerate">开始智能起名</button>

    <view class="result-box" v-if="names.length > 0">
      <view class="result-head">
        <view class="result-title">为您生成的专属方案：</view>
        <button class="publish-btn" size="mini" :loading="publishing" @click="publishToCommunity">发布到社区</button>
      </view>

      <view class="name-card" v-for="(item, index) in names" :key="index">
        <view class="name-header">
          <text class="name-text">{{ item.name }}</text>
          <text v-if="item.score" class="score-tag">推荐 {{ item.score }}</text>
        </view>
        <view class="name-detail"><text class="label">出处：</text>{{ item.reference }}</view>
        <view class="name-detail"><text class="label">寓意：</text>{{ item.moral }}</view>
        <view v-if="item.style_reason" class="name-detail"><text class="label">匹配：</text>{{ item.style_reason }}</view>

        <view v-if="getDomains(item).length" class="domain-list">
          <text class="label domain-label">{{ getDomainTitle() }}</text>
          <text
            v-for="domain in getDomains(item)"
            :key="domain.domain"
            :class="['domain-tag', getDomainClass(domain)]"
          >
            {{ domain.domain }} {{ domain.message }}
          </text>
        </view>

        <button
          v-if="formData.category === '企业名'"
          class="visual-btn"
          size="mini"
          :loading="visualLoadingIndex === index"
          @click="handleGenerateVisual(item, index)"
        >
          生成品牌视觉
        </button>

        <view v-if="visualResults[index]" class="visual-box">
          <view class="visual-main">
            <image class="logo-preview" :src="getLogoUrl(visualResults[index])" mode="aspectFit"></image>
            <view class="visual-copy">
              <view class="visual-title">{{ visualResults[index].slogans[0] }}</view>
              <view class="visual-note">{{ visualResults[index].design_note }}</view>
            </view>
          </view>
          <view class="visual-row">
            <text class="label">关键词：</text>
            <text class="visual-chip" v-for="keyword in visualResults[index].visual_keywords" :key="keyword">{{ keyword }}</text>
          </view>
          <view class="visual-row">
            <text class="label">色彩：</text>
            <text
              class="color-swatch"
              v-for="color in visualResults[index].color_palette"
              :key="color"
              :style="{ backgroundColor: color }"
            ></text>
          </view>
        </view>
      </view>

      <view class="feedback-box">
        <textarea class="textarea-box" v-model="feedbackText" placeholder="对结果不满意？请输入修改意见"></textarea>
        <button class="btn-secondary" :loading="loading" @click="handleFeedback">基于意见重新生成</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import http from '@/http/http.js';

const categories = ['人名', '企业名', '宠物名'];
const lengthOptions = ['不限', '单字', '双字'];
const humanStyleOptions = ['古典雅致', '诗意温柔', '清新自然', '大气稳重', '现代简洁', '独特少见'];
const brandToneOptions = ['科技感', '亲和力', '高端专业', '年轻潮流', '国风文化', '简洁国际化'];
const petStyleOptions = ['可爱软萌', '搞怪有趣', '高冷酷感', '国风雅致', '英文感', '虚拟 IP 感'];

const formData = ref({
  category: '人名',
  surname: '',
  gender: '不限',
  length: '不限',
  style: humanStyleOptions[0],
  brand_tone: '',
  other: '',
  exclude: []
});

const loading = ref(false);
const publishing = ref(false);
const names = ref([]);
const threadId = ref('');
const feedbackText = ref('');
const currentUser = ref(uni.getStorageSync('user') || {});
const visualResults = ref({});
const visualLoadingIndex = ref(-1);

const switchCategory = (cat) => {
  formData.value.category = cat;
  formData.value.length = '不限';
  formData.value.style = cat === '人名' ? humanStyleOptions[0] : (cat === '宠物名' ? petStyleOptions[0] : '');
  formData.value.brand_tone = cat === '企业名' ? brandToneOptions[0] : '';
  names.value = [];
  visualResults.value = {};
  threadId.value = '';
};

const getOtherPlaceholder = () => {
  if (formData.value.category === '企业名') return '补充行业、产品、目标用户或命名偏好';
  if (formData.value.category === '宠物名') return '补充宠物类型、性格、外貌或特别偏好';
  return '补充名字偏好、避讳或希望呈现的气质';
};

const getDomains = (item) => {
  if (Array.isArray(item.domains) && item.domains.length) {
    return item.domains.filter((domain) =>
      domain.status === 'available' ||
      domain.status === 'taken' ||
      domain.available === true ||
      domain.available === false
    );
  }
  if (item.domain && !String(item.domain_status || '').includes('超时') && !String(item.domain_status || '').includes('失败')) {
    return [{ domain: item.domain, message: item.domain_status || '', status: '' }];
  }
  return [];
};

const getDomainTitle = () => {
  if (formData.value.category === '企业名') return '品牌域名：';
  if (formData.value.category === '宠物名') return 'IP 域名：';
  return '个人域名：';
};

const getDomainClass = (domain) => {
  if (domain.available === true || domain.status === 'available' || String(domain.message).includes('可注册')) {
    return 'domain-success';
  }
  if (domain.available === false || domain.status === 'taken' || String(domain.message).includes('已被注册')) {
    return 'domain-fail';
  }
  return 'domain-warn';
};

const getLogoUrl = (visual) => {
  const image = visual.logo_images && visual.logo_images[0];
  if (!image || !image.url) return '';
  if (image.url.startsWith('http')) return image.url;
  const baseUrl = http.getBaseUrl ? http.getBaseUrl() : '';
  return baseUrl + image.url;
};

const goAdmin = () => uni.navigateTo({ url: '/pages/admin/admin' });
const goDashboard = () => uni.navigateTo({ url: '/pages/dashboard/index' });
const goInvitation = () => uni.navigateTo({ url: '/pages/invitation/index' });
const goCommunity = () => uni.navigateTo({ url: '/pages/community/community' });

const switchAccount = () => {
  uni.showModal({
    title: '切换账号',
    content: '将退出当前账号并返回登录页',
    success: (res) => {
      if (!res.confirm) return;
      uni.removeStorageSync('token');
      uni.removeStorageSync('user');
      uni.reLaunch({ url: '/pages/login/login' });
    }
  });
};

const handleUploadDocs = () => {
  uni.chooseFile({
    count: 1,
    type: 'all',
    extension: ['.txt', '.pdf'],
    success: async (res) => {
      const tempFilePath = res.tempFiles[0].path;
      uni.showLoading({ title: '知识库解析中...' });
      try {
        await http.uploadKnowledge(tempFilePath);
        uni.showToast({ title: '知识库学习完成', icon: 'success' });
      } catch (error) {
        console.error(error);
      } finally {
        uni.hideLoading();
      }
    }
  });
};

const handleGenerate = async () => {
  if (formData.value.category === '人名' && !formData.value.surname.trim()) {
    return uni.showToast({ title: '人名必须填写姓氏', icon: 'none' });
  }
  if (formData.value.category === '企业名' && !formData.value.brand_tone) {
    return uni.showToast({ title: '请选择品牌调性', icon: 'none' });
  }
  if (formData.value.category !== '企业名' && !formData.value.style) {
    return uni.showToast({ title: '请选择名字风格', icon: 'none' });
  }

  loading.value = true;
  uni.showLoading({ title: 'AI思考中...' });
  try {
    const res = await http.generateName(formData.value);
    names.value = res.names || [];
    visualResults.value = {};
    threadId.value = res.thread_id;
    feedbackText.value = '';
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
    uni.hideLoading();
  }
};

const handleFeedback = async () => {
  if (!feedbackText.value.trim()) {
    return uni.showToast({ title: '请输入修改意见', icon: 'none' });
  }

  loading.value = true;
  uni.showLoading({ title: '微调修改中...' });
  try {
    const res = await http.feedbackName({
      thread_id: threadId.value,
      category: formData.value.category,
      feedback: feedbackText.value
    });
    names.value = res.names || [];
    visualResults.value = {};
    feedbackText.value = '';
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
    uni.hideLoading();
  }
};

const handleGenerateVisual = async (item, index) => {
  visualLoadingIndex.value = index;
  try {
    const res = await http.generateVisual({
      name: item.name,
      moral: item.moral,
      brand_tone: formData.value.brand_tone,
      other: formData.value.other
    });
    visualResults.value = { ...visualResults.value, [index]: res };
  } catch (error) {
    console.error(error);
  } finally {
    visualLoadingIndex.value = -1;
  }
};

const publishToCommunity = async () => {
  if (!names.value.length) {
    return uni.showToast({ title: '暂无可发布的起名结果', icon: 'none' });
  }
  publishing.value = true;
  try {
    await http.createCommunityPoll({
      naming_type: formData.value.category,
      candidate_names: names.value,
      ai_analysis: formData.value.other || 'AI 已根据当前起名条件生成候选方案，请大家投票选择。'
    });
    uni.showToast({ title: '已发布到社区', icon: 'success' });
    setTimeout(() => uni.navigateTo({ url: '/pages/community/community' }), 500);
  } catch (error) {
    console.error(error);
  } finally {
    publishing.value = false;
  }
};
</script>

<style scoped>
.container { padding: 30rpx; background-color: #f5f7fa; min-height: 100vh; }
.account-bar { display: flex; justify-content: space-between; align-items: center; gap: 20rpx; background: #fff; padding: 20rpx 24rpx; border-radius: 16rpx; margin-bottom: 24rpx; }
.account-title { font-size: 34rpx; font-weight: bold; color: #111827; }
.account-subtitle { margin-top: 6rpx; font-size: 24rpx; color: #667085; }
.account-actions { display: flex; gap: 12rpx; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
.invite-btn { background: #f79009; color: #fff; border-radius: 10rpx; }
.dashboard-btn { background: #344054; color: #fff; border-radius: 10rpx; }
.community-btn { background: #12b76a; color: #fff; border-radius: 10rpx; }
.admin-btn { background: #165dff; color: #fff; border-radius: 10rpx; }
.logout-btn { background: #fff; color: #344054; border: 1px solid #d0d5dd; border-radius: 10rpx; }
.tabs { display: flex; justify-content: space-around; background: #fff; padding: 20rpx; border-radius: 16rpx; margin-bottom: 30rpx; }
.tab { font-size: 30rpx; color: #666; padding: 10rpx 30rpx; }
.tab.active { color: #007AFF; font-weight: bold; border-bottom: 4rpx solid #007AFF; }
.upload-section { background: #e6f7ff; padding: 20rpx; border-radius: 12rpx; margin-bottom: 30rpx; text-align: center; }
.upload-tip { font-size: 24rpx; color: #007AFF; margin-bottom: 10rpx; }
.form-group { background: #fff; padding: 20rpx; border-radius: 16rpx; margin-bottom: 30rpx; }
.input-box { border-bottom: 1px solid #eee; padding: 24rpx 10rpx; font-size: 28rpx; }
.textarea-box { width: 100%; height: 160rpx; background: #f9f9f9; padding: 20rpx; box-sizing: border-box; border-radius: 8rpx; font-size: 28rpx; margin-top: 20rpx; }
.btn-primary { background: #007AFF; color: #fff; border-radius: 50rpx; margin-bottom: 40rpx; }
.btn-secondary { background: #ff9800; color: #fff; border-radius: 50rpx; margin-top: 20rpx; }
.visual-btn { margin-top: 18rpx; background: #111827; color: #fff; border-radius: 8rpx; }
.result-box { margin-top: 40rpx; }
.result-head { display: flex; justify-content: space-between; align-items: center; gap: 16rpx; margin-bottom: 20rpx; }
.result-title { font-size: 32rpx; font-weight: bold; }
.publish-btn { background: #12b76a; color: #fff; border-radius: 10rpx; }
.name-card { background: #fff; padding: 30rpx; border-radius: 16rpx; margin-bottom: 24rpx; box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.05); }
.name-header { display: flex; justify-content: space-between; align-items: center; gap: 16rpx; margin-bottom: 16rpx; }
.name-text { font-size: 40rpx; font-weight: bold; color: #333; }
.score-tag { font-size: 22rpx; padding: 6rpx 16rpx; border-radius: 30rpx; background: #eef4ff; color: #165dff; }
.domain-list { display: flex; flex-wrap: wrap; gap: 12rpx; align-items: center; margin-top: 16rpx; }
.domain-label { font-size: 24rpx; }
.domain-tag { font-size: 22rpx; padding: 6rpx 16rpx; border-radius: 30rpx; }
.domain-success { background: #e8f5e9; color: #4caf50; }
.domain-fail { background: #ffebee; color: #f44336; }
.domain-warn { background: #fff7e6; color: #b26a00; }
.visual-box { margin-top: 20rpx; padding: 18rpx; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8rpx; }
.visual-main { display: flex; gap: 18rpx; align-items: center; margin-bottom: 16rpx; }
.logo-preview { width: 132rpx; height: 132rpx; background: #fff; border-radius: 8rpx; border: 1px solid #e5e7eb; flex-shrink: 0; }
.visual-copy { min-width: 0; flex: 1; }
.visual-title { font-size: 28rpx; font-weight: 700; color: #111827; line-height: 1.4; }
.visual-note { margin-top: 8rpx; font-size: 24rpx; color: #667085; line-height: 1.5; }
.visual-row { display: flex; flex-wrap: wrap; gap: 10rpx; align-items: center; margin-top: 10rpx; }
.visual-chip { font-size: 22rpx; padding: 4rpx 12rpx; border-radius: 8rpx; background: #eef4ff; color: #165dff; }
.color-swatch { width: 36rpx; height: 36rpx; border-radius: 50%; border: 1px solid #d0d5dd; }
.name-detail { font-size: 26rpx; color: #666; line-height: 1.6; margin-bottom: 8rpx; }
.label { font-weight: bold; color: #333; }
.feedback-box { margin-top: 40rpx; background: #fff; padding: 30rpx; border-radius: 16rpx; }
</style>
