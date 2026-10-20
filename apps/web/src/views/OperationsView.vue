<script setup lang="ts">
import { onMounted, ref } from 'vue';
import Button from 'primevue/button';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Message from 'primevue/message';
import Tag from 'primevue/tag';
import { api } from '../services/api';
const runs = ref<Record<string, unknown>[]>([]);
const error = ref(''), job = ref('');
const busy = ref(false);
async function load() {
  try { runs.value = (await api<Record<string, unknown>[]>('ingestion/runs')).data; }
  catch (e) { error.value = (e as Error).message; }
}
async function ingest(provider = 'fixture_history') {
  busy.value = true; error.value = '';
  try {
    const result = await api<{id:string;status:string}>('ingestion/runs', { provider, idempotencyKey: crypto.randomUUID() });
    job.value = result.data.id;
    await check();
  } catch (e) { error.value = (e as Error).message; }
  finally { busy.value = false; }
}
const jobStatus = ref('');
async function check() {
  if (!job.value) return;
  try { jobStatus.value = (await api<{status:string}>(`jobs/${job.value}`)).data.status; await load(); }
  catch (e) { error.value = (e as Error).message; }
}
onMounted(load);
</script>
<template>
  <div class="page-heading"><div><div class="eyebrow">DATA CONTROL CENTER</div><h1>Dữ liệu & vận hành</h1><p>Theo dõi provenance, ingestion và job bền vững.</p></div><Button label="Nhập lịch sử DEMO 2022–2026" icon="pi pi-download" :loading="busy" @click="ingest()" /></div>
  <Message severity="warn">Provider thật chưa được bật. Cần xác minh quyền truy cập, hạn mức và corporate actions trước khi dùng dữ liệu thật.</Message>
  <Message v-if="error" severity="error">{{ error }}</Message>
  <div v-if="job" class="filter-toolbar"><span class="mono">Job {{ job }}</span><Tag :value="jobStatus" /><Button label="Kiểm tra job" icon="pi pi-refresh" severity="secondary" @click="check" /></div>
  <div class="section-heading"><h2>Lịch sử ingestion</h2><Button text label="Làm mới" icon="pi pi-refresh" @click="load" /></div>
  <DataTable :value="runs" size="small" paginator :rows="10" stripedRows><template #empty>Chưa có ingestion run.</template><Column field="started_at" header="THỜI GIAN" /><Column field="status" header="TRẠNG THÁI"><template #body="{ data }"><Tag :value="data.status" :severity="data.status === 'COMPLETE' ? 'success' : 'warn'" /></template></Column><Column field="counts_json" header="ĐỐI SOÁT"><template #body="{ data }"><code>{{ JSON.stringify(data.counts_json) }}</code></template></Column><Column field="error_summary" header="LỖI" /></DataTable>
</template>
