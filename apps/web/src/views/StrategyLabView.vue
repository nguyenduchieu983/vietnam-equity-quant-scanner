<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import Button from 'primevue/button';
import Select from 'primevue/select';
import InputText from 'primevue/inputtext';
import InputNumber from 'primevue/inputnumber';
import Message from 'primevue/message';
import Tag from 'primevue/tag';
import ProgressBar from 'primevue/progressbar';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Panel from 'primevue/panel';
import ResearchChart from '../components/ResearchChart.vue';
import { api } from '../services/api';
const datasets=ref<any[]>([]),runs=ref<any[]>([]),result=ref<any>(null),error=ref(''),busy=ref(false),progress=ref(0),active=ref('');
const form=ref({datasetId:'',strategy:'S1',capital:50000000,trainStart:'2022-01-03',trainEnd:'2023-12-29',validationStart:'2024-02-15',validationEnd:'2024-06-28',testStart:'2024-09-02',testEnd:'2026-10-16',maxHold:30,embargoSessions:30,minLiquidity:5000000000,buyFee:.0015,sellFee:.0015,sellTax:.001,slippage:.001});
const dates=['trainStart','trainEnd','validationStart','validationEnd','testStart','testEnd'] as const;
const costs=['buyFee','sellFee','sellTax','slippage'] as const;
let disposed=false;
onUnmounted(()=>{disposed=true;});
async function refresh(){runs.value=(await api<any[]>('backtests')).data;}
async function show(id:string){result.value=(await api<any>(`backtests/${id}`)).data;}
async function run(){
  busy.value=true;error.value='';result.value=null;progress.value=0;
  try{
    const run=(await api<any>('backtests',form.value)).data;active.value=run.id;
    for(let i=0;i<300&&!disposed;i++){
      const job=(await api<any>(`jobs/${run.job_id}`)).data;progress.value=job.progress;
      if(['FAILED','CANCELLED'].includes(job.status))throw new Error(job.error_code||job.status);
      if(job.status==='COMPLETE'){await show(run.id);await refresh();return;}
      await new Promise(r=>setTimeout(r,3000));
    }
    if(!disposed)error.value='Job tiếp tục chạy trên worker. Mở lại kết quả từ lịch sử.';
  }catch(e){error.value=(e as Error).message;}finally{busy.value=false;}
}
async function cancel(){try{await api(`backtests/${active.value}/cancel`,{});}catch(e){error.value=(e as Error).message;}}
function download(){const url=URL.createObjectURL(new Blob([JSON.stringify(result.value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`backtest-${result.value.id}.json`;a.click();URL.revokeObjectURL(url);}
async function csv(kind:string){
  try{const data=(await api<any>(`backtests/${result.value.id}/export`)).data;const url=URL.createObjectURL(new Blob(['\uFEFF'+data[kind+'Csv']],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`${kind}-${result.value.id}.csv`;a.click();URL.revokeObjectURL(url);}catch(e){error.value=(e as Error).message;}
}
function percent(v:number|null){return v==null?'N/A':`${(v*100).toFixed(2)}%`;}
onMounted(async()=>{try{datasets.value=(await api<any[]>('datasets')).data.filter(d=>d.status==='COMPLETE');form.value.datasetId=datasets.value[0]?.id??'';await refresh();}catch(e){error.value=(e as Error).message;}});
</script>
<template>
  <div class="page-heading"><div><div class="eyebrow">QUANT RESEARCH / OUT-OF-SAMPLE</div><h1>Strategy Lab</h1><p>Snapshot bất biến · Khớp phiên kế tiếp · Chi phí và giới hạn vốn</p></div><Tag value="DEMO · RESEARCH ONLY" severity="warn"/></div>
  <Message severity="warn">Dữ liệu tổng hợp, lịch phiên và quy tắc thị trường minh họa. Kết quả không chứng minh hiệu quả đầu tư thực tế. S4 là thử nghiệm.</Message>
  <Message v-if="error" severity="error">{{error}}</Message>
  <div class="lab-grid">
    <label>Dataset<Select v-model="form.datasetId" :options="datasets" optionLabel="name" optionValue="id" aria-label="Dataset"/></label>
    <label>Chiến lược<Select v-model="form.strategy" :options="['S1','S2','S3','S4']" aria-label="Chiến lược backtest" @change="form.maxHold=form.strategy==='S4'?5:form.strategy==='S1'?30:20"/></label>
    <label>Vốn VND<InputNumber v-model="form.capital" :min="1" :max="100000000"/></label>
    <label v-for="field in dates" :key="field">{{field}}<InputText v-model="form[field]" type="date" :aria-label="field"/></label>
    <label>Giữ tối đa (phiên)<InputNumber v-model="form.maxHold" :min="1" :max="60"/></label>
    <label>Embargo (phiên)<InputNumber v-model="form.embargoSessions" :min="form.maxHold" :max="120"/></label>
    <label v-for="field in costs" :key="field">{{field}} (tỷ lệ)<InputNumber v-model="form[field]" :min="0" :max=".03" :minFractionDigits="4" :maxFractionDigits="4" :step=".0005"/></label>
  </div>
  <div class="filter-toolbar"><Button label="Chạy backtest" icon="pi pi-play" :loading="busy" :disabled="!form.datasetId" @click="run"/><Button v-if="busy" label="Hủy job" severity="danger" outlined @click="cancel"/><Select :options="runs" optionLabel="created_at" optionValue="id" placeholder="Lịch sử backtest" aria-label="Lịch sử backtest" @change="show($event.value)"/><Button label="Làm mới lịch sử" text @click="refresh"/></div>
  <ProgressBar v-if="busy" :value="progress"/>
  <section v-if="result">
    <Tag :value="result.status"/><Message v-if="result.error_code" severity="error">{{result.error_code}}</Message>
    <template v-if="result.metrics_json">
      <h2>Kết quả ngoài mẫu (sau phí / thuế)</h2>
      <div class="lab-grid"><div v-for="key in ['totalReturn','cagr','maxDrawdown','benchmarkReturn','hitRate']" :key="key" class="metric-cell"><small>{{key}}</small><h2>{{percent(result.metrics_json[key])}}</h2></div><div class="metric-cell"><small>Số giao dịch đóng</small><h2>{{result.metrics_json.tradeCount}}</h2></div></div>
      <Message severity="warn">{{result.warnings_json.join(' · ')}}</Message>
      <ResearchChart :equity="result.equity"/>
      <h2>Drawdown</h2><ResearchChart :equity="result.equity" drawdown/>
      <h2>So sánh các tập dữ liệu</h2>
      <DataTable :value="['train','validation','test'].map(s=>({split:s,...result.artifact[s+'Metrics']}))" size="small"><Column field="split" header="Tập"/><Column header="Net return"><template #body="{data}">{{percent(data.totalReturn)}}</template></Column><Column header="Max DD"><template #body="{data}">{{percent(data.maxDrawdown)}}</template></Column><Column field="tradeCount" header="Trades"/><Column header="Sharpe"><template #body="{data}">{{data.sharpe?.toFixed(2)??'N/A'}}</template></Column></DataTable>
      <h2>Lợi nhuận theo năm</h2><DataTable :value="Object.entries(result.metrics_json.yearlyReturns).map(([year,value])=>({year,value}))" size="small"><Column field="year" header="Năm"/><Column header="Net return"><template #body="{data}">{{percent(data.value)}}</template></Column></DataTable>
      <h2>Độ nhạy chi phí</h2><DataTable :value="result.artifact.costSensitivity" size="small"><Column field="name" header="Kịch bản"/><Column header="Slippage mỗi chiều"><template #body="{data}">{{percent(data.slippage)}}</template></Column><Column header="Net return"><template #body="{data}">{{percent(data.metrics.totalReturn)}}</template></Column><Column field="metrics.tradeCount" header="Trades"/></DataTable>
      <h2>Sổ giao dịch</h2><DataTable :value="result.trades" paginator :rows="10" size="small"><template #empty>Không có giao dịch đóng trong kỳ.</template><Column v-for="field in ['symbol','entry_date','exit_date','quantity','entry_price','exit_price','pnl','exit_reason']" :key="field" :field="field" :header="field"/></DataTable>
      <h2>Walk-forward (tham số cố định)</h2><DataTable :value="result.artifact.walkForward" size="small"><Column field="trainStart" header="Train start"/><Column field="trainEnd" header="Train end"/><Column field="testStart" header="Test start"/><Column field="testEnd" header="Test end"/><Column field="metrics.totalReturn" header="Net return"/></DataTable>
      <div class="filter-toolbar"><Button label="Xuất kết quả JSON" icon="pi pi-download" @click="download"/><Button label="Sổ lệnh CSV" outlined @click="csv('orders')"/><Button label="Equity CSV" outlined @click="csv('equity')"/></div>
      <Panel header="Nguồn gốc & giả định tái lập" toggleable collapsed><pre style="white-space:pre-wrap;overflow-wrap:anywhere">{{JSON.stringify(result.artifact,null,2)}}</pre></Panel>
    </template>
  </section>
</template>
<style scoped>.lab-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin:1.5rem 0}.lab-grid label{display:flex;flex-direction:column;gap:.5rem;font-size:.8rem;color:var(--p-text-muted-color)}.metric-cell{padding:1rem;border:1px solid var(--p-content-border-color);border-radius:8px}h2{margin:1.5rem 0 .8rem}</style>
