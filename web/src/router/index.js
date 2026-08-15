import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Knowledge from '../views/Knowledge.vue'
import QA from '../views/QA.vue'
import Creation from '../views/Creation.vue'
import Memory from '../views/Memory.vue'
import Optimize from '../views/Optimize.vue'
import Settings from '../views/Settings.vue'

const routes = [
  { path: '/', component: Home, name: '首页' },
  { path: '/knowledge', component: Knowledge, name: '知识库管理' },
  { path: '/qa', component: QA, name: '智能问答' },
  { path: '/creation', component: Creation, name: '文档创作' },
  { path: '/memory', component: Memory, name: '记忆管理' },
  { path: '/optimize', component: Optimize, name: '文档优化' },
  { path: '/settings', component: Settings, name: '系统设置' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
