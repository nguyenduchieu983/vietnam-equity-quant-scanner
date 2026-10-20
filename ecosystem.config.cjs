// Secrets are injected from the protected environment file by deploy.sh.
module.exports = {
  apps: [{
    name: 'quant-api',
    cwd: '/opt/quant-vn',
    script: 'apps/api/dist/main.js',
    interpreter: '/usr/bin/node',
    instances: 1,
    exec_mode: 'fork',
    max_memory_restart: '512M',
    restart_delay: 3000,
    env_production: { NODE_ENV: 'production' },
    time: true,
    kill_timeout: 10000,
    listen_timeout: 10000
  }]
};
