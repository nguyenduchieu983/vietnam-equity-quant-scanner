<script setup lang="ts">
import { ref } from 'vue';
import { useRoute } from 'vue-router';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Card from 'primevue/card';
import Toast from 'primevue/toast';
import { useSettings } from './stores/settings';
import { api, token } from './services/api';
const route = useRoute();
const settings = useSettings();
const password = ref('');
const busy = ref(false);
const error = ref('');
const nav = [
  { path: '/dashboard', icon: 'pi pi-th-large', label: 'Tổng quan', index: '01' },
  { path: '/scanner', icon: 'pi pi-filter', label: 'Scanner', index: '02' },
  { path: '/symbols/SIM00', icon: 'pi pi-chart-line', label: 'Phân tích mã', index: '03' },
  { path: '/lab', icon: 'pi pi-sliders-h', label: 'Strategy Lab', index: '04' },
  { path: '/portfolio', icon: 'pi pi-wallet', label: 'Paper Portfolio', index: '05' },
  { path: '/operations', icon: 'pi pi-server', label: 'Dữ liệu & vận hành', index: '06' }
];
async function login() {
  busy.value = true; error.value = '';
  try { token.value = (await api<{accessToken: string}>('auth/login', { password: password.value })).data.accessToken; password.value = ''; }
  catch (e) { error.value = (e as Error).message; }
  finally { busy.value = false; }
}
</script>
<template>
  <Toast />
  <div class="terminal">
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark">Q<span>V</span></span><div>QUANT VN<small>EQUITY RESEARCH TERMINAL</small></div></div>
      <div class="workspace-label">RESEARCH WORKSPACE</div>
      <nav aria-label="Điều hướng chính">
        <RouterLink v-for="item in nav" :key="item.path" :to="item.path"><i :class="item.icon" /><span>{{ item.label }}</span><small>{{ item.index }}</small></RouterLink>
      </nav>
      <div class="sidebar-note"><i class="pi pi-shield" /><strong>Research only</strong><p>Phân tích cuối ngày.<br>Giao dịch mô phỏng có kiểm soát.</p><Tag value="NO LIVE EXECUTION" severity="secondary" /></div>
      <div class="sidebar-footer"><span class="status-dot" /> Local research <span>v0.3</span></div>
    </aside>
    <div class="workspace">
      <header class="topbar"><div class="breadcrumb">WORKSPACE <span>/</span> {{ route.meta.title }}</div><div class="header-actions"><Tag value="EOD RESEARCH" severity="secondary" /><Button :icon="settings.dark ? 'pi pi-sun' : 'pi pi-moon'" text rounded :aria-label="settings.dark ? 'Chuyển giao diện sáng' : 'Chuyển giao diện tối'" @click="settings.dark = !settings.dark" /><Button v-if="token" icon="pi pi-sign-out" text aria-label="Đăng xuất" @click="token = ''" /></div></header>
      <main>
        <template v-if="!token">
          <div class="page-heading"><div><div class="eyebrow">VIETNAM EQUITIES / HOSE + HNX</div><h1>Research starts with evidence.</h1><p>Không có dữ liệu được xác thực, không có tín hiệu được công bố.</p></div></div>
          <Card class="login-panel"><template #title>Đăng nhập terminal</template><template #subtitle>Phiên quản trị • dữ liệu và thao tác được kiểm soát</template><template #content>
            <form @submit.prevent="login" class="login-form"><label for="password">Mật khẩu quản trị</label><InputText id="password" v-model="password" type="password" autocomplete="current-password" required minlength="12" maxlength="128" /><Message v-if="error" severity="error">{{ error }}</Message><Button type="submit" label="Mở workspace" icon="pi pi-arrow-right" :loading="busy" /></form>
          </template></Card>
        </template>
        <RouterView v-else />
      </main>
      <footer class="disclaimer"><span>QUANT VN / AUDITABLE RESEARCH</span><span>Not investment advice · Không phải khuyến nghị đầu tư</span></footer>
    </div>
  </div>
</template>
