<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import Message from 'primevue/message';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import ResearchChart from '../components/ResearchChart.vue';
import {api} from '../services/api';
const route=useRoute();
const bars=ref<Record<string,any>[]>([]), values=ref<{key:string;value:unknown}[]>([]);
const datasets=ref<Record<string,any>[]>([]), datasetId=ref(''), basis=ref('raw'), error=ref('');
async function load(){try{error.value='';bars.value=(await api<Record<string,any>[]>(`instruments/${route.params.symbol}/bars?datasetId=${datasetId.value}&limit=1500`)).data;const result=(await api<any>(`instruments/${route.params.symbol}/features`)).data;values.value=Object.entries(result?.features_json??{}).map(([key,value])=>({key,value}));}catch(e){error.value=(e as Error).message;}}
onMounted(async()=>{try{datasets.value=(await api<any[]>('datasets')).data;datasetId.value=datasets.value[0]?.id??'';if(datasetId.value)await load();}catch(e){error.value=(e as Error).message;}});
watch(()=>route.params.symbol,()=>{if(datasetId.value)void load();});
</script>
<template>
<div class="page-heading"><div><div class="eyebrow">SYMBOL EXPLORER</div><h1>{{route.params.symbol}}</h1><p>OHLC, volume và EMA từ snapshot được chọn.</p></div><Tag :value="datasets.find(d=>d.id===datasetId)?.is_demo ? 'DEMO' : 'REAL EOD · PROVISIONAL'" severity="warn" /></div>
<Message v-if="error" severity="error">{{error}}</Message>
<div class="filter-toolbar"><Select v-model="datasetId" :options="datasets" optionLabel="name" optionValue="id" aria-label="Dataset" @change="load"/><Select v-model="basis" :options="['raw','adjusted']" aria-label="Giá raw/adjusted"/></div>
<ResearchChart v-if="bars.length" :bars="bars" :adjusted="basis==='adjusted'"/>
<Message v-else severity="info">Không có lịch sử mã trong snapshot này.</Message>
<div class="section-heading"><h2>Feature snapshot gần nhất</h2></div>
<DataTable :value="values" paginator :rows="10" size="small"><template #empty>Chạy scan để lưu feature snapshot.</template><Column field="key" header="Feature"/><Column field="value" header="Giá trị"/></DataTable>
</template>
