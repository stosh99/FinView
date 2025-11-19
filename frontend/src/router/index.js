import { createRouter, createWebHistory } from 'vue-router'
import RRG from '../views/RRG.vue'
import SectorCharts from '../views/SectorCharts.vue'

const routes = [
  {
    path: '/',
    name: 'RRG',
    component: RRG
  },
  {
    path: '/sector-charts',
    name: 'SectorCharts',
    component: SectorCharts
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router