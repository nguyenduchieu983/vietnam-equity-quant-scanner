<script setup lang="ts">
import { useRoute } from 'vue-router';
import Card from 'primevue/card';
import Message from 'primevue/message';
import Tag from 'primevue/tag';
const route = useRoute();
</script>
<template>
  <div class="page-heading"><div><div class="eyebrow">RESEARCH WORKSPACE</div><h1>{{ route.meta.title }}</h1><p>{{ route.meta.detail }}</p></div><Tag :value="`${route.meta.milestone} · PENDING`" severity="secondary" /></div>
  <Card><template #content><div class="empty-state"><i class="pi pi-lock" /><h3>Chưa triển khai milestone này</h3><p>Chỉ mở tính năng sau khi milestone trước vượt kiểm thử end-to-end theo spec v1.1.</p></div><Message severity="info">Không có kết quả backtest, lệnh mô phỏng hoặc biểu đồ giả được hiển thị.</Message></template></Card>
</template>
