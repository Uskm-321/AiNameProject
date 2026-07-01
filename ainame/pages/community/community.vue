<template>
  <view class="page">
    <view class="topbar">
      <view>
        <view class="title">社区投票</view>
        <view class="subtitle">看看大家正在纠结哪些好名字</view>
      </view>
      <button class="ghost-btn" size="mini" @click="goBack">返回起名</button>
    </view>

    <view v-if="polls.length === 0" class="empty">暂无社区投票</view>

    <view v-for="poll in polls" :key="poll.id" class="poll-card">
      <view class="poll-head">
        <view>
          <view class="poll-title">用户 {{ poll.username }} 发布的起名投票</view>
          <view class="muted">{{ poll.naming_type }} · {{ formatTime(poll.created_at) }}</view>
        </view>
        <view class="poll-actions">
          <view v-if="poll.hidden" class="hidden-tag">已隐藏</view>
          <button v-if="canDeletePoll(poll)" class="delete-btn" size="mini" @click="deletePoll(poll)">删除</button>
        </view>
      </view>

      <view v-if="poll.hidden && poll.hidden_reason" class="hidden-reason">隐藏理由：{{ poll.hidden_reason }}</view>
      <view v-if="poll.ai_analysis" class="analysis">AI 分析：{{ poll.ai_analysis }}</view>

      <view class="option-list">
        <view v-for="option in poll.options" :key="option.id" class="option">
          <view class="option-main">
            <view class="name-line">
              <text class="name">{{ option.name }}</text>
              <text class="score">{{ option.score }}分</text>
            </view>
            <view class="detail">出处：{{ option.reference || '-' }}</view>
            <view class="detail">寓意：{{ option.moral || '-' }}</view>
            <view class="detail">风格：{{ option.style_reason || '-' }}</view>
          </view>
          <view class="vote-box">
            <text class="votes">{{ option.votes_count }} 票</text>
            <button
              :class="['vote-btn', poll.my_vote_option_id === option.id ? 'selected' : '']"
              size="mini"
              @click="vote(poll, option)"
            >
              {{ poll.my_vote_option_id === option.id ? '已投' : '投票' }}
            </button>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import http from '@/http/http.js';

const polls = ref([]);
const currentUser = ref(uni.getStorageSync('user') || {});

const loadPolls = async () => {
  const res = await http.getCommunityPolls({ page: 1, page_size: 50 });
  polls.value = res.items || [];
};

const vote = async (poll, option) => {
  await http.voteCommunityPoll(poll.id, option.id);
  await loadPolls();
};

const canDeletePoll = (poll) => {
  return currentUser.value.role === 'ADMIN' || Number(currentUser.value.id) === Number(poll.user_id);
};

const deletePoll = (poll) => {
  uni.showModal({
    title: '删除投票',
    content: `确认删除用户 ${poll.username} 发布的这条投票吗？删除后无法恢复。`,
    success: async (res) => {
      if (!res.confirm) return;
      await http.deleteCommunityPoll(poll.id);
      uni.showToast({ title: '已删除', icon: 'success' });
      await loadPolls();
    }
  });
};

const formatTime = (value) => {
  if (!value) return '-';
  return String(value).replace('T', ' ').slice(0, 16);
};

const goBack = () => {
  uni.navigateBack({
    fail: () => uni.reLaunch({ url: '/pages/index/index' })
  });
};

onMounted(loadPolls);
</script>

<style scoped>
.page { min-height: 100vh; background: #f5f7fa; padding: 30rpx; box-sizing: border-box; color: #172033; }
.topbar { display: flex; justify-content: space-between; align-items: center; gap: 20rpx; margin-bottom: 24rpx; }
.title { font-size: 40rpx; font-weight: 700; }
.subtitle, .muted { color: #667085; font-size: 24rpx; line-height: 1.5; }
.ghost-btn { background: #fff; color: #344054; border: 1px solid #d0d5dd; border-radius: 10rpx; }
.empty { background: #fff; border-radius: 16rpx; padding: 40rpx; color: #667085; text-align: center; }
.poll-card { background: #fff; border-radius: 16rpx; padding: 26rpx; margin-bottom: 24rpx; box-shadow: 0 4rpx 12rpx rgba(0,0,0,0.05); }
.poll-head { display: flex; justify-content: space-between; gap: 16rpx; align-items: flex-start; margin-bottom: 18rpx; }
.poll-title { font-size: 30rpx; font-weight: 700; color: #101828; }
.poll-actions { display: flex; align-items: center; gap: 10rpx; flex-wrap: wrap; justify-content: flex-end; }
.hidden-tag { background: #fff1f3; color: #c01048; border-radius: 8rpx; padding: 6rpx 12rpx; font-size: 22rpx; }
.delete-btn { background: #d92d20; color: #fff; border-radius: 8rpx; }
.hidden-reason { background: #fff8e6; color: #b54708; border-radius: 8rpx; padding: 14rpx; margin-bottom: 16rpx; font-size: 24rpx; }
.analysis { background: #f9fafb; border-radius: 8rpx; padding: 16rpx; color: #344054; font-size: 25rpx; line-height: 1.6; margin-bottom: 16rpx; }
.option-list { display: flex; flex-direction: column; gap: 16rpx; }
.option { display: flex; justify-content: space-between; gap: 18rpx; padding: 18rpx; border: 1px solid #edf0f3; border-radius: 12rpx; }
.option-main { flex: 1; min-width: 0; }
.name-line { display: flex; align-items: center; gap: 12rpx; margin-bottom: 8rpx; }
.name { font-size: 34rpx; font-weight: 700; color: #111827; }
.score { color: #165dff; background: #eef2ff; border-radius: 8rpx; padding: 4rpx 10rpx; font-size: 22rpx; }
.detail { color: #667085; font-size: 24rpx; line-height: 1.6; word-break: break-all; }
.vote-box { width: 132rpx; display: flex; flex-direction: column; gap: 10rpx; align-items: stretch; justify-content: center; }
.votes { text-align: center; color: #667085; font-size: 24rpx; }
.vote-btn { background: #165dff; color: #fff; border-radius: 10rpx; }
.vote-btn.selected { background: #12b76a; color: #fff; }
</style>
