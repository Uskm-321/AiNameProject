<script setup>
import { onLaunch } from '@dcloudio/uni-app';

onLaunch(() => {
  const token = uni.getStorageSync('token');

  if (!token) {
    uni.reLaunch({ url: '/pages/login/login' });
  }
});
</script>

<style>
</style>
