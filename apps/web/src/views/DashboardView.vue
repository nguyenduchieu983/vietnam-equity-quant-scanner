<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import Card from 'primevue/card';
import Tag from 'primevue/tag';
import Button from 'primevue/button';
import Message from 'primevue/message';
import Skeleton from 'primevue/skeleton';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import type { SystemStatus } from '@quant/contracts';
import { api } from '../services/api';
const status = ref<SystemStatus | null>(null);
const instruments = ref<{symbol:string; exchange:string; name:string}[]>([]);
const loading = ref(true);
const error = ref('');
async function load() {
  loading.value = true; error.value = '';
  try {
    const [s, i] = await Promise.all([api<SystemStatus>('system/status'), api<typeof instruments.value>('instruments')]);
    status.value = s.data; instruments.value = i.data;
  } catch (e) { error.value = (e as Error).message; }
  finally { loading.value = false; }
}
onMounted(load);
</script>
<template>
  <div class="page-heading"><div><div class="eyebrow">MARKET OVERVIEW</div><h1>Tổng quan thị trường</h1><p>Nguồn dữ liệu, chất lượng và trạng thái nghiên cứu cuối ngày.</p></div><Button label="Làm mới" icon="pi pi-refresh" severity="secondary" :loading="loading" @click="load" /></div>
  <Message v-if="error" severity="error">{{ error }}</Message>
  <template v-if="loading"><div class="metric-grid"><Skeleton v-for="n in 4" :key="n" height="9rem" /></div></template>
  <template v-else-if="status">
    <div class="session-strip"><Tag :value="status.isDemo ? 'DEMO / SYNTHETIC' : 'DATA UNAVAILABLE'" severity="warn" /><span>Phiên {{ status.latestSession ?? '—' }}</span><span>Nguồn: {{ status.isDemo ? 'fixture-v1' : 'chưa cấu hình' }}</span><span>HOSE / HNX</span></div>
    <Message severity="warn" :closable="false">Dữ liệu tổng hợp dùng kiểm thử hệ thống, không phải lịch sử giá thị trường. Chưa đủ lịch sử để tạo tín hiệu.</Message>
    <div class="metric-grid">
      <Card><template #content><div class="metric-label">MARKET REGIME <i class="pi pi-compass" /></div><div class="metric-value muted">UNKNOWN</div><div class="metric-foot">Chưa có feature engine</div></template></Card>
      <Card><template #content><div class="metric-label">UNIVERSE <i class="pi pi-list" /></div><div class="metric-value">{{ status.instruments }} <small>mã</small></div><div class="metric-foot">Đã nhập từ fixture</div></template></Card>
      <Card><template #content><div class="metric-label">DAILY BARS <i class="pi pi-database" /></div><div class="metric-value">{{ status.bars }}</div><div class="metric-foot">OHLC đã chuẩn hóa • VND</div></template></Card>
      <Card><template #content><div class="metric-label">WORKER <i class="pi pi-bolt" /></div><div class="metric-value" :class="{ positive: status.worker }">{{ status.worker ? 'ONLINE' : 'OFFLINE' }}</div><div class="metric-foot">Heartbeat trong 30 giây</div></template></Card>
    </div>
    <div class="section-heading"><h2>Chiến lược nghiên cứu</h2><Tag value="M2 · CHƯA TRIỂN KHAI" severity="secondary" /></div>
    <div class="strategy-grid"><Card v-for="(name, index) in ['Momentum Rank', 'Breakout + Volume', 'Pullback in Uptrend', 'Mean Reversion']" :key="name"><template #content><div class="strategy-code">S{{ index + 1 }} <Tag v-if="index === 3" value="EXPERIMENTAL" severity="warn" /></div><h3>{{ name }}</h3><p>— tín hiệu</p><small>Chưa tính điểm / chưa kiểm định</small></template></Card></div>
    <div class="section-heading"><h2>Universe đã nhập</h2><RouterLink to="/operations">Xem chất lượng dữ liệu <i class="pi pi-arrow-up-right" /></RouterLink></div>
    <DataTable :value="instruments" size="small" stripedRows paginator :rows="10" tableStyle="min-width: 32rem"><template #empty>Chưa có dữ liệu. Nhập fixture tại Dữ liệu & vận hành.</template><Column field="symbol" header="MÃ" sortable /><Column field="exchange" header="SÀN" sortable /><Column field="name" header="MÔ TẢ" /><Column header="NGUỒN"><template #body><Tag value="DEMO" severity="warn" /></template></Column><Column header="TÍN HIỆU"><template #body><span class="muted">Chưa tính</span></template></Column></DataTable>
  </template>
</template>
