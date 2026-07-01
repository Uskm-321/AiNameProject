<template>
  <view class="page">
    <view class="shell">
      <view class="topbar">
        <view><view class="title">邀请奖励</view><text class="subtitle">邀请好友注册，双方都可获得 credits</text></view>
        <button class="secondary-btn" @click="goBack">返回</button>
      </view>

      <view class="stats">
        <view class="stat"><text class="label">我的 credits</text><text class="value credits">{{ summary.credits }}</text></view>
        <view class="stat"><text class="label">已邀请人数</text><text class="value">{{ summary.invite_count }}</text></view>
      </view>

      <view class="panel">
        <view class="panel-title">我的邀请码</view>
        <view class="copy-row">
          <text class="code">{{ summary.invite_code || '-' }}</text>
          <button class="copy-btn" @click="copy(summary.invite_code)">复制</button>
        </view>
        <view class="panel-title link-title">邀请链接</view>
        <view class="copy-row">
          <text class="invite-link">{{ summary.invite_link || '-' }}</text>
          <button class="copy-btn" @click="copy(summary.invite_link)">复制链接</button>
        </view>
        <view class="reward-rule">邀请人 +10 credits，被邀请人 +5 credits</view>
      </view>

      <view class="panel">
        <view class="panel-title">奖励记录</view>
        <scroll-view scroll-x class="table-scroll">
          <view class="reward-table">
            <view class="reward-row reward-head"><text>时间</text><text>奖励类型</text><text>关联用户</text><text>credits</text></view>
            <view v-for="item in summary.rewards" :key="item.id" class="reward-row">
              <text>{{ formatTime(item.created_at) }}</text>
              <text>{{ reasonLabel(item.reason) }}</text>
              <text>{{ item.related_user_id || '-' }}</text>
              <text class="amount">+{{ item.amount }}</text>
            </view>
            <view v-if="!summary.rewards.length" class="empty">暂无奖励记录</view>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import http from '@/http/http.js';

const summary = ref({ invite_code: '', invite_link: '', invite_count: 0, credits: 0, rewards: [] });
const load = async () => { summary.value = await http.getInvitationSummary(); };
const copy = (value) => {
  if (!value) return;
  uni.setClipboardData({ data: value });
};
const reasonLabel = (reason) => reason === 'INVITER_REWARD' ? '成功邀请好友' : '受邀注册奖励';
const formatTime = (value) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-') : '-';
const goBack = () => uni.navigateBack({ delta: 1 });
onMounted(load);
</script>

<style scoped>
.page { min-height: 100vh; background: #f5f7fa; color: #101828; }
.shell { width: min(1100px, calc(100% - 40rpx)); margin: 0 auto; padding: 34rpx 0 60rpx; }
.topbar, .copy-row { display: flex; align-items: center; justify-content: space-between; gap: 20rpx; }
.topbar { margin-bottom: 22rpx; }.title { font-size: 38rpx; font-weight: 700; }.subtitle { display: block; margin-top: 6rpx; color: #667085; font-size: 24rpx; }
.secondary-btn, .copy-btn { margin: 0; border: 1px solid #d0d5dd; border-radius: 10rpx; background: #fff; color: #344054; font-size: 23rpx; }
.stats { display: grid; grid-template-columns: 1fr 1fr; gap: 18rpx; margin-bottom: 18rpx; }
.stat, .panel { background: #fff; border: 1px solid #e4e7ec; border-radius: 12rpx; }
.stat { display: flex; flex-direction: column; padding: 28rpx; }.label { color: #667085; font-size: 24rpx; }.value { margin-top: 8rpx; font-size: 40rpx; font-weight: 700; }.credits { color: #b54708; }
.panel { padding: 28rpx; margin-bottom: 18rpx; }.panel-title { font-size: 28rpx; font-weight: 650; }.link-title { margin-top: 28rpx; }
.copy-row { margin-top: 13rpx; padding: 18rpx; border: 1px solid #eaecf0; border-radius: 10rpx; background: #f9fafb; }
.code { font-family: Consolas, Monaco, monospace; color: #175cd3; font-size: 30rpx; font-weight: 700; }.invite-link { min-width: 0; color: #475467; font-size: 23rpx; word-break: break-all; }
.copy-btn { flex: none; height: 58rpx; line-height: 56rpx; padding: 0 18rpx; }.reward-rule { margin-top: 20rpx; padding: 16rpx; color: #b54708; background: #fffaeb; border-radius: 10rpx; font-size: 23rpx; }
.table-scroll { width: 100%; margin-top: 16rpx; }.reward-table { min-width: 760rpx; }.reward-row { min-height: 72rpx; display: grid; grid-template-columns: 1.4fr 1.2fr .8fr .6fr; align-items: center; gap: 14rpx; padding: 0 12rpx; border-top: 1px solid #eaecf0; font-size: 23rpx; }
.reward-head { border-top: 0; color: #667085; background: #f9fafb; font-size: 21rpx; font-weight: 600; }.amount { color: #067647; font-weight: 700; }.empty { padding: 50rpx; text-align: center; color: #98a2b3; }
@media(max-width:600px){.stats{grid-template-columns:1fr}.shell{width:calc(100% - 28rpx)}.panel{padding:20rpx 16rpx}.copy-row{align-items:flex-start;flex-direction:column}.copy-btn{align-self:flex-end}}
</style>
