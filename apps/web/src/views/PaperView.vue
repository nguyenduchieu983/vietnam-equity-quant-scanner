<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import Button from 'primevue/button';
import Select from 'primevue/select';
import Message from 'primevue/message';
import Tag from 'primevue/tag';
import Card from 'primevue/card';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Panel from 'primevue/panel';
import ResearchChart from '../components/ResearchChart.vue';
import { api } from '../services/api';
const listing=ref<any>({pairs:[],snapshot:null}), detail=ref<any>(null), selected=ref(''), error=ref(''), busy=ref(false);
const preview=ref<any>(null), confirmation=ref(false), jobId=ref(''), replayStart=ref('');
const account=ref('S1_PARTIAL');
const current=computed(()=>detail.value?.accounts.find((a:any)=>a.code===account.value));
let disposed=false;onUnmounted(()=>{disposed=true;});
const money=(v:unknown)=>Number(v??0).toLocaleString('vi-VN',{maximumFractionDigits:0});
const pct=(v:number|null|undefined)=>v==null?'—':`${(v*100).toFixed(2)}%`;
const date=(v:string)=>v?.slice(0,10)??'—';
const positions=computed(()=>Object.entries(current.value?.state_json.positions??{}).map(([symbol,p]:any)=>({symbol,...p,value:Number(p.qty)*Number(p.last)})));
async function refresh(){listing.value=(await api<any>('paper')).data;if(!replayStart.value)replayStart.value=listing.value.snapshot?.suggested_replay_start??'';if(!selected.value)selected.value=listing.value.pairs.find((p:any)=>p.mode==='FORWARD')?.id??listing.value.pairs[0]?.id??'';if(selected.value)await show();}
async function show(){detail.value=(await api<any>(`paper/pairs/${selected.value}`)).data;preview.value=null;}
async function waitJob(id:string){jobId.value=id;for(let i=0;i<600&&!disposed;i++){
  const j=(await api<any>(`paper/jobs/${id}`)).data;
  if(j.status==='FAILED')throw new Error(j.error_code);
  if(j.status==='COMPLETE'){if(j.result_json?.pairId)selected.value=j.result_json.pairId;await refresh();return;}
  await new Promise(r=>setTimeout(r,2000));
}if(!disposed)throw new Error('Job vẫn chạy; dùng Làm mới để kiểm tra.');}
async function create(mode:string){busy.value=true;error.value='';try{
  const j=(await api<any>('paper/pairs',{snapshotId:listing.value.snapshot.id,mode,...(mode==='REPLAY'?{startDay:replayStart.value}:{}),idempotencyKey:crypto.randomUUID()})).data;
  await waitJob(j.id);
}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
async function prepare(){error.value='';try{preview.value=(await api<any>(`paper/pairs/${selected.value}/preview`)).data;confirmation.value=true;}catch(e){error.value=(e as Error).message;}}
async function advance(){confirmation.value=false;busy.value=true;error.value='';try{
  const p=preview.value;const j=(await api<any>(`paper/pairs/${selected.value}/advance`,{snapshotId:p.snapshotId,through:p.through,expectedCursor:p.expectedCursor})).data;
  await waitJob(j.id);
}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
function download(){const url=URL.createObjectURL(new Blob([JSON.stringify(detail.value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`paper-${selected.value}.json`;a.click();URL.revokeObjectURL(url);}
onMounted(async()=>{try{await refresh();}catch(e){error.value=(e as Error).message;}});
</script>
<template>
  <div class="page-heading"><div><div class="eyebrow">PAIRED STRATEGY MONITOR / PAPER ONLY</div><h1>Paper Portfolio</h1><p>S1 gốc vs Chốt một phần 1R · Trailing 2 ATR · 15 phiên</p></div><Tag value="REAL DATA · PAPER ONLY" severity="info"/></div>
  <Message severity="warn">Dữ liệu thật public, quy tắc khớp và chi phí còn là giả định nghiên cứu. Replay là mô phỏng lịch sử; forward chỉ tính từ lúc khởi tạo. Không có lệnh gửi tới broker.</Message>
  <Message v-if="error" severity="error">{{error}}</Message>
  <div class="filter-toolbar"><Tag :value="`Dữ liệu EOD: ${listing.snapshot?.as_of??'Chưa nạp'}`" severity="secondary"/><Button label="Làm mới" icon="pi pi-refresh" text :disabled="busy" @click="refresh().catch(e=>error=e.message)"/><Button label="Tạo cặp forward · 50 triệu/bên" icon="pi pi-plus" :disabled="busy||!listing.snapshot" @click="create('FORWARD')"/></div>
  <Panel header="Replay lịch sử để đối chiếu" toggleable collapsed><p>Tạo hai tài khoản mới, độc lập với forward. Không ghi kết quả lịch sử thành lợi nhuận paper đã theo dõi.</p><div class="filter-toolbar"><InputText v-model="replayStart" type="date" aria-label="Phiên bắt đầu replay"/><Button label="Tạo cặp replay" outlined :disabled="busy||!listing.snapshot" @click="create('REPLAY')"/></div></Panel>
  <div class="filter-toolbar"><Select v-model="selected" :options="listing.pairs.map((p:any)=>({...p,label:`${p.mode} · ${p.cursor_day} · ${p.id.slice(0,8)}`}))" optionLabel="label" optionValue="id" placeholder="Chọn cặp danh mục" aria-label="Cặp paper" :disabled="busy" @change="show().catch(e=>error=e.message)"/><Button label="Xem trước & mô phỏng phiên mới" icon="pi pi-play" :disabled="busy||!selected" :loading="busy" @click="prepare"/><Button label="Xuất ledger JSON" icon="pi pi-download" outlined :disabled="!detail" @click="download"/></div>
  <Message v-if="busy" severity="info">Worker đang xử lý hai danh mục. Job {{jobId}} được lưu trong PostgreSQL; có thể mở lại trang để kiểm tra.</Message>
  <template v-if="detail">
    <div class="filter-toolbar"><Tag :value="detail.pair.mode" :severity="detail.pair.mode==='FORWARD'?'success':'warn'"/><span>Từ sau {{date(detail.pair.initial_day)}} · Đã xử lý {{date(detail.pair.cursor_day)}}</span></div>
    <div class="paper-cards"><Card v-for="a in detail.accounts" :key="a.id"><template #title>{{a.code==='S1'?'S1 gốc':'Partial 1R + Trail 2 ATR'}}</template><template #subtitle>{{a.config_json.maxHold}} phiên · 50 triệu VND ban đầu</template><template #content>
      <div class="nav-value">{{money(a.equity.at(-1)?.nav??50000000)}} <small>VND</small></div>
      <div class="stats"><div>Lợi nhuận<strong>{{pct(a.summary_json.return??0)}}</strong></div><div>Drawdown<strong>{{pct(a.summary_json.drawdown??0)}}</strong></div><div>Win rate đóng hết<strong>{{pct(a.summary_json.winRate)}}</strong></div><div>Vị thế đóng<strong>{{a.summary_json.closed??0}}</strong></div><div>Tiền khả dụng<strong>{{money(a.state_json.cash)}}</strong></div><div>Tiền chờ về<strong>{{money(a.state_json.pending.reduce((s:number,p:any)=>s+Number(p[1]),0))}}</strong></div></div>
      <Message v-if="!a.equity.length" severity="info">Chưa có phiên paper đã xử lý. Chờ dữ liệu EOD mới rồi phê duyệt mô phỏng.</Message>
    </template></Card></div>
    <h2>So sánh NAV</h2><div class="paper-cards"><div v-for="a in detail.accounts" :key="a.id"><h3>{{a.code}}</h3><ResearchChart v-if="a.equity.length" :equity="a.equity"/><p v-else>Chưa có lịch sử NAV.</p></div></div>
    <Select v-model="account" :options="['S1','S1_PARTIAL']" aria-label="Danh mục chi tiết"/>
    <h2>Vị thế đang giữ</h2><DataTable :value="positions" size="small" scrollable><template #empty>Không có vị thế mở.</template><Column field="symbol" header="Mã"/><Column field="qty" header="Số lượng"/><Column field="entry" header="Giá vào"/><Column field="stop" header="Stop"/><Column field="target" header="Target"/><Column field="runner_active" header="Trailing đã bật"/><Column header="Giá trị"><template #body="{data}">{{money(data.value)}}</template></Column></DataTable>
    <h2>Giao dịch đã khớp bán</h2><p>Chốt một phần không được tính riêng thành một lệnh thắng. Win rate chỉ tính khi vị thế đóng hết.</p><DataTable :value="current?.trades??[]" paginator :rows="10" size="small" scrollable><template #empty>Chưa có lần bán.</template><Column v-for="f in ['symbol','entry_date','exit_date','quantity','exit_price','pnl','exit_reason']" :key="f" :field="f" :header="f"/></DataTable>
    <h2>Sổ lệnh & lý do không khớp</h2><DataTable :value="current?.orders??[]" paginator :rows="10" size="small" scrollable><Column v-for="f in ['session_date','symbol','side','status','quantity','price','fee','tax','reason']" :key="f" :field="f" :header="f"/></DataTable>
    <Panel header="Tín hiệu chờ phiên sau & giả định" toggleable collapsed><p>Tín hiệu đã đóng băng tại {{current?.decision_json.day}}. Phí mua/bán 0,15%, thuế bán 0,10%, slippage 0,10% mỗi chiều. Vị thế 100 cổ phiếu không chia đôi; chuyển sang trailing toàn bộ sau 1R. Cổ phiếu thưởng/lô lẻ có thể còn giữ lâu hơn maxHold.</p><DataTable :value="current?.decision_json.signals??[]" size="small"><Column field="symbol" header="Mã"/><Column field="score" header="Điểm"/><Column field="invalidation_price" header="Stop dự kiến"/></DataTable></Panel>
    <h2>Nhật ký phê duyệt</h2><DataTable :value="detail.approvals" size="small"><Column field="through_date" header="Đến phiên"/><Column field="created_at" header="Phê duyệt lúc"/><Column field="status" header="Trạng thái"/><Column field="error_code" header="Lỗi"/></DataTable>
  </template>
  <Dialog v-model:visible="confirmation" modal header="Phê duyệt mô phỏng cả hai danh mục" :style="{width:'min(560px,95vw)'}"><template v-if="preview"><p>Từ sau {{preview.expectedCursor}} đến {{preview.through}} · {{preview.mode}}</p><p>Mỗi danh mục dùng vốn riêng 50 triệu VND và cùng snapshot. Đây chỉ là giao dịch giả lập; mỗi phiên được ghi một lần vào ledger bất biến.</p><Message v-if="!preview.canAdvance" severity="info">Chưa có phiên EOD mới. Làm mới dữ liệu bằng script paper-refresh rồi kiểm tra lại.</Message><Button label="Phê duyệt & chạy cả hai" :disabled="!preview.canAdvance" @click="advance"/></template></Dialog>
</template>
<style scoped>.paper-cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin:1.5rem 0}.nav-value{font-size:2rem;font-weight:700;font-variant-numeric:tabular-nums}.nav-value small{font-size:.8rem;color:var(--p-text-muted-color)}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-top:1.5rem}.stats div{font-size:.75rem;color:var(--p-text-muted-color)}.stats strong{display:block;font-size:1rem;color:var(--p-text-color);margin-top:.4rem}h2{margin:1.7rem 0 .8rem}@media(max-width:900px){.paper-cards{grid-template-columns:minmax(0,1fr)}.paper-cards>div{min-width:0}.stats{grid-template-columns:repeat(2,1fr)}}</style>
