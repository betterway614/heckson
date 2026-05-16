import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('../views/HomeView.vue'),
  },
  {
    path: '/diary',
    name: 'Diary',
    component: () => import('../views/DiaryView.vue'),
  },
  {
    path: '/story/:id',
    name: 'Story',
    component: () => import('../views/StoryView.vue'),
  },
  {
    path: '/stories',
    name: 'Stories',
    component: () => import('../views/StoriesView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
