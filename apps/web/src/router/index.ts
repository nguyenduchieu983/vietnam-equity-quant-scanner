import { createRouter, createWebHistory } from 'vue-router';
const DashboardView = () => import('../views/DashboardView.vue');
const ScannerView = () => import('../views/ScannerView.vue');
const OperationsView = () => import('../views/OperationsView.vue');
const PendingView = () => import('../views/PendingView.vue');
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: DashboardView, meta: { title: 'Tổng quan thị trường' } },
    { path: '/scanner', component: ScannerView, meta: { title: 'Bộ lọc tín hiệu' } },
    { path: '/symbols/:symbol', component: PendingView, meta: { title: 'Phân tích mã', milestone: 'M2', detail: 'Biểu đồ giá, chỉ báo và nguồn dữ liệu theo từng phiên.' } },
    { path: '/lab', component: PendingView, meta: { title: 'Strategy Lab', milestone: 'M3', detail: 'Backtest, walk-forward và đối chiếu ngoài mẫu chưa được triển khai.' } },
    { path: '/portfolio', component: PendingView, meta: { title: 'Danh mục mô phỏng', milestone: 'M4', detail: 'Sổ cái và giao dịch giả lập có xác nhận thủ công chưa được triển khai.' } },
    { path: '/operations', component: OperationsView, meta: { title: 'Dữ liệu & vận hành' } }
  ]
});
