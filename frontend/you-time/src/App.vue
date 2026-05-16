<script setup>
import { useRouter, useRoute } from 'vue-router'
import { computed } from 'vue'
import { Tabbar, TabbarItem } from 'vant'

const router = useRouter()
const route = useRoute()

const active = computed({
  get() {
    if (route.path === '/diary') return 'diary'
    if (route.path === '/stories') return 'stories'
    return 'home'
  },
  set(value) {
    const pathMap = {
      home: '/home',
      diary: '/diary',
      stories: '/stories',
    }
    router.push(pathMap[value] || '/home')
  },
})
</script>

<template>
  <div class="app">
    <router-view />

    <Tabbar v-model="active" class="tab-bar" active-color="#5C3E32" inactive-color="#999999">
      <TabbarItem icon="home-o" name="home">首页</TabbarItem>
      <TabbarItem icon="notes-o" name="diary">日记</TabbarItem>
      <TabbarItem icon="video-o" name="stories">故事集</TabbarItem>
    </Tabbar>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  background-color: var(--background-color);
}
</style>
