import { createRouter, createWebHistory } from 'vue-router';
const DashboardView = () => import('../views/DashboardView.vue');
const ScannerView = () => import('../views/ScannerView.vue');
const OperationsView = () => import('../views/OperationsView.vue');
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: DashboardView, meta: { title: 'Tổng quan thị trường' } },
    { path: '/scanner', component: ScannerView, meta: { title: 'Bộ lọc tín hiệu' } },
    { path: '/symbols/:symbol', component: () => import('../views/SymbolView.vue'), meta: { title: 'Phân tích mã' } },
    { path: '/lab', component: () => import('../views/StrategyLabView.vue'), meta: { title: 'Strategy Lab', milestone: 'M3', detail: 'Backtest nghiên cứu DEMO với walk-forward và ngoài mẫu.' } },
    { path: '/portfolio', component: () => import('../views/PaperView.vue'), meta: { title: 'Paper Portfolio · So sánh S1' } },
    { path: '/operations', component: OperationsView, meta: { title: 'Dữ liệu & vận hành' } }
  ]
});
