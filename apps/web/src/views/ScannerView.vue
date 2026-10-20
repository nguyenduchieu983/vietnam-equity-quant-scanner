<script setup lang="ts">
import { onMounted, ref } from 'vue';
import Button from 'primevue/button';
import Select from 'primevue/select';
import InputText from 'primevue/inputtext';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Message from 'primevue/message';
import Tag from 'primevue/tag';
import type { ScanRun, ScanResult } from '@quant/contracts';
import { api } from '../services/api';
const runs = ref<ScanRun[]>([]);
const run = ref<string | null>(null);
const exchange = ref<string | null>(null);
const strategy = ref('S1');
const query = ref('');
const rows = ref<ScanResult[]>([]);
const total = ref(0), page = ref(0), loading = ref(false);
const sort = ref('symbol'), direction = ref('asc'), error = ref('');
async function load() {
  rows.value = []; total.value = 0;
  if (!run.value) return;
  loading.value = true; error.value = '';
  try {
    const params = new URLSearchParams({ strategy: strategy.value, page: String(page.value + 1), limit: '25', sort: sort.value, direction: direction.value, query: query.value });
    if (exchange.value) params.set('exchange', exchange.value);
    const result = await api<{items:ScanResult[];total:number}>(`scans/${run.value}/results?${params}`);
    rows.value = result.data.items; total.value = result.data.total;
  } catch (e) { error.value = (e as Error).message; }
  finally { loading.value = false; }
}
function filter() { page.value = 0; void load(); }
onMounted(async () => {
  try { runs.value = (await api<ScanRun[]>('scans')).data; run.value = runs.value[0]?.id ?? null; await load(); }
  catch (e) { error.value = (e as Error).message; }
});
</script>
<template>
  <div class="page-heading"><div><div class="eyebrow">SIGNAL EXPLORER</div><h1>Bộ lọc tín hiệu</h1><p>Điểm số có nguồn gốc, điều kiện rõ ràng và lý do loại trừ.</p></div><Tag value="M2 · PENDING" severity="secondary" /></div>
  <Message v-if="error" severity="error">{{ error }}</Message>
  <Message severity="info">M0 chỉ cung cấp hợp đồng API và bảng đọc kết quả. Chưa có scan được tính; không có điểm số giả lập.</Message>
  <div class="filter-toolbar"><Select v-model="strategy" :options="['S1','S2','S3','S4']" aria-label="Chiến lược" @change="filter" /><Select v-model="exchange" :options="['HOSE','HNX']" placeholder="Tất cả sàn" showClear aria-label="Sàn giao dịch" @change="filter" /><InputText v-model="query" placeholder="Tìm mã chứng khoán" aria-label="Tìm mã" @keyup.enter="filter" /><Button icon="pi pi-search" label="Lọc" @click="filter" /><Select v-model="run" :options="runs" optionLabel="session_date" optionValue="id" placeholder="Chưa có phiên scan" aria-label="Phiên scan" @change="filter" /></div>
  <DataTable :value="rows" lazy paginator :rows="25" :first="page * 25" :totalRecords="total" :loading="loading" size="small" @page="page = $event.page; load()" @sort="sort = String($event.sortField); direction = $event.sortOrder === -1 ? 'desc' : 'asc'; filter()">
    <template #empty><div class="empty-state"><i class="pi pi-filter" /><h3>Chưa có kết quả scan</h3><p>Kết quả chỉ xuất hiện sau khi feature engine và chiến lược vượt kiểm thử M2.</p></div></template>
    <Column field="symbol" header="MÃ" sortable /><Column field="exchange" header="SÀN" sortable /><Column field="composite_score" sortField="score" header="ĐIỂM" sortable /><Column field="excluded" header="LOẠI TRỪ" /><Column field="exclusion_codes_json" header="LÝ DO" />
  </DataTable>
</template>
