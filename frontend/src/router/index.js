import { createRouter, createWebHistory } from 'vue-router'
import RRG from '../views/RRG.vue'
import RRGOpenBB from '../views/RRGOpenBB.vue'
import SectorCharts from '../views/SectorCharts.vue'

const routes = [
  {
    path: '/',
    name: 'RRG',
    component: RRG
  },
  {
    path: '/rrg-openbb',
    name: 'RRGOpenBB',
    component: RRGOpenBB
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