<template>
  <div class="container">
    <h1>Stellsora Master</h1>

    <div class="tabs">
      <button
        type="button"
        :class="{ active: activeTab === 'tasks' }"
        @click="activeTab = 'tasks'"
      >任务执行</button>
      <button
        type="button"
        :class="{ active: activeTab === 'settings' }"
        @click="activeTab = 'settings'"
      >设置</button>
    </div>

    <section v-if="activeTab === 'tasks'" class="tab-content">
      <div class="content-wrap">
        <div class="main">
          <div class="task-selection">
            <div class="checkbox-group">
              <label>
                <input type="checkbox" v-model="tasks.startGame">
                启动游戏
              </label>
              <label>
                <input type="checkbox" v-model="tasks.dailytasks">
                日常任务流程
              </label>
            </div>
            <div class="actions-row">
              <button class="primary-btn" @click="startUnifiedTasks" :disabled="taskStatus.running || !hasSelectedTasks">
                {{ taskStatus.running ? '执行中...' : '开始执行' }}
              </button>
              <button class="danger-btn" v-if="taskStatus.canStop" @click="stopTask">
                停止
              </button>
            </div>
          </div>

          <div class="status-line">
            当前状态: <strong>{{ statusLine }}</strong>
          </div>

          <div class="screenshot-wrap" v-if="image">
            <img :src="image" class="screenshot" alt="screenshot" />
          </div>
        </div>

        <aside class="logs-panel">
          <h3>服务端日志</h3>
          <div class="logs" ref="logsBox">
            <div v-for="item in logs" :key="item.idx" class="log-line">
              [{{ new Date(item.ts * 1000).toLocaleTimeString() }}] {{ item.level }}: {{ item.msg }}
            </div>
          </div>
        </aside>
      </div>
    </section>

    <section v-else class="tab-content settings-panel">
      <form class="settings-form" @submit.prevent="saveConfig">
        <label for="adbPath">ADB 路径</label>
        <input
          id="adbPath"
          type="text"
          v-model="settings.adb_path"
          placeholder="例如 D:\\Program Files\\Netease\\MuMu Player 12\\shell\\adb.exe"
        />
        <p class="hint">可填写绝对路径或相对于 exe 所在目录的相对路径。</p>
        <div class="settings-actions">
          <button type="submit" class="primary-btn" :disabled="savingSettings">
            {{ savingSettings ? '保存中...' : '保存设置' }}
          </button>
          <span v-if="configStatus" :class="['status-message', configStatusType]">
            {{ configStatus }}
          </span>
        </div>
      </form>
    </section>
  </div>
</template>

<script>
export default {
  data() {
    return {
      apiBase: (import.meta.env.VITE_API_BASE || '').replace(/\/$/, ''),
      activeTab: 'tasks',
      image: null,
      statusText: '-', // 兼容旧字段
      tasks: {
        startGame: false,
        dailytasks: false
      },
      logs: [],
      lastLogIndex: 0,
      _poller: null,
      _statusPoller: null,
      settings: {
        adb_path: ''
      },
      savingSettings: false,
      configStatus: '',
      configStatusType: 'info'
      ,
  taskStatus: { state: 'idle', task: null, running: false, canStop: false }
    }
  },
  computed: {
    hasSelectedTasks() {
      return Object.values(this.tasks).some(v => v)
    },
    statusLine() {
      const s = this.taskStatus
      if (s.running) {
        if (s.task === 'combo') return '组合任务执行中'
        if (s.task === 'start_game') return '启动游戏中'
        if (s.task === 'dailytasks') return '日常任务执行中'
      }
      switch (s.state) {
        case 'finished': return '任务已完成'
        case 'stopped': return '已停止'
        case 'idle': default: return '空闲'
      }
    }
  },
  mounted() {
    this.fetchConfig()
    this.startPolling()
    this.startStatusPolling()
  },
  watch: {
    activeTab(newVal) {
      if (newVal === 'settings') {
        this.fetchConfig()
      }
    }
  },
  methods: {
    apiUrl(path) {
      if (this.apiBase) {
        return `${this.apiBase}${path}`
      }
      return path
    },

    async handleFetch(path, opts) {
      const res = await fetch(this.apiUrl(path), opts)
      return res.json()
    },

    taskTypeSelected() {
      if (this.tasks.startGame && this.tasks.dailytasks) return 'combo'
      if (this.tasks.startGame) return 'start_game'
      if (this.tasks.dailytasks) return 'dailytasks'
      return null
    },

    async startUnifiedTasks() {
      const type = this.taskTypeSelected()
      if (!type) return
      try {
        const res = await fetch(this.apiUrl('/task/start'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type })
        })
        const data = await res.json()
        if (!data.ok) {
          this.statusText = data.error || '启动失败'
        } else {
          this.statusText = '任务已启动'
        }
      } catch (e) {
        this.statusText = `启动失败: ${e.message}`
      }
    },

    async stopTask() {
      try {
        const res = await fetch(this.apiUrl('/task/stop'), { method: 'POST' })
        const data = await res.json()
        if (!data.ok) {
          this.statusText = data.error || '停止失败'
        } else {
          this.statusText = '停止指令已发送'
        }
      } catch (e) {
        this.statusText = `停止失败: ${e.message}`
      }
    },


    startPolling() {
      if (this._poller) return
      this._poller = setInterval(this.pollLogs, 800)
      this.pollLogs()
    },

    stopPolling() {
      if (this._poller) {
        clearInterval(this._poller)
        this._poller = null
      }
    },

    async pollLogs() {
      try {
        const res = await fetch(this.apiUrl(`/logs?since=${this.lastLogIndex}`))
        const data = await res.json()
        if (data.ok && Array.isArray(data.logs) && data.logs.length) {
          this.logs.push(...data.logs)
          this.lastLogIndex = data.last || this.lastLogIndex
          this.$nextTick(() => {
            const el = this.$refs.logsBox
            if (el) el.scrollTop = el.scrollHeight
          })
        }
      } catch (e) {
        // ignore polling errors silently
      }
    },

    startStatusPolling() {
      if (this._statusPoller) return
      this._statusPoller = setInterval(this.pollStatus, 1000)
      this.pollStatus()
    },
    stopStatusPolling() {
      if (this._statusPoller) {
        clearInterval(this._statusPoller)
        this._statusPoller = null
      }
    },
    async pollStatus() {
      try {
        const res = await fetch(this.apiUrl('/task/status'))
        const data = await res.json()
        if (data.ok && data.status) {
          this.taskStatus = data.status
        }
      } catch (e) {
        // swallow
      }
    },

    async fetchConfig() {
      try {
        const res = await fetch(this.apiUrl('/config'))
        const data = await res.json()
        if (!res.ok || !data.ok) {
          throw new Error(data.error || '无法获取配置')
        }
        this.settings.adb_path = data.config?.adb_path || ''
        this.configStatus = ''
      } catch (e) {
        this.configStatus = `读取配置失败: ${e.message}`
        this.configStatusType = 'error'
      }
    },

    async saveConfig() {
      this.savingSettings = true
      this.configStatus = '保存中...'
      this.configStatusType = 'info'
      try {
        const res = await fetch(this.apiUrl('/config'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ adb_path: this.settings.adb_path || '' })
        })
        const data = await res.json()
        if (!res.ok || !data.ok) {
          throw new Error(data.error || '保存失败')
        }
        this.settings.adb_path = data.config?.adb_path || ''
        this.configStatus = '保存成功'
        this.configStatusType = 'success'
      } catch (e) {
        this.configStatus = `保存失败: ${e.message}`
        this.configStatusType = 'error'
      } finally {
        this.savingSettings = false
      }
    }
  },
  beforeUnmount() {
    this.stopPolling()
  }
}
</script>

<style>
body {
  font-family: "Segoe UI", Arial, sans-serif;
  margin: 50px;
  min-height: 100vh;
  background: url('/bg1.jpg') center/cover fixed no-repeat;
}

.container {
  position: relative;
  color: #f4f5ff;
  backdrop-filter: blur(4px);
  background: rgba(32, 14, 34, 0.5);
  border-radius: 18px;
  padding: 2rem;
  overflow: hidden;
}

.container::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(135deg, rgba(0, 0, 0, 0.45), rgba(60, 0, 90, 0.2));
  pointer-events: none;
  z-index: 0;
}

.container > * {
  position: relative;
  z-index: 1;
}

.tabs {
  display: inline-flex;
  gap: 0.5rem;
  margin-bottom: 1.2rem;
}

.tabs button {
  padding: 0.5rem 1.2rem;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  color: #f4f5ff;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tabs button.active {
  background: rgba(173, 78, 230, 0.8);
  border-color: rgba(173, 78, 230, 0.9);
}

.tabs button:hover {
  background: rgba(255, 255, 255, 0.2);
}

.tab-content {
  background: rgba(28, 12, 30, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 1.5rem;
}

.content-wrap {
  display: flex;
  gap: 1.25rem;
  align-items: flex-start;
}

.main {
  flex: 1 1 auto;
}

.task-selection {
  margin-bottom: 1.25rem;
  padding: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
}

.checkbox-group label {
  display: block;
  margin: 0.5rem 0;
  user-select: none;
}

.checkbox-group input[type="checkbox"] {
  margin-right: 0.5rem;
}

.primary-btn {
  padding: 0.55rem 1.4rem;
  background: #a86bff;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.primary-btn:hover:not(:disabled) {
  background: #9358ef;
}

.primary-btn:disabled {
  background: rgba(168, 107, 255, 0.4);
  cursor: not-allowed;
}

.danger-btn {
  padding: 0.55rem 1.4rem;
  background: #a83c8d;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.danger-btn:hover:not(:disabled) {
  background: #9358ef;
}

.danger-btn:disabled {
  background: rgba(168, 107, 255, 0.4);
  cursor: not-allowed;
}

.status-line {
  margin-bottom: 0.75rem;
  font-weight: 500;
}

.screenshot-wrap {
  margin-top: 0.75rem;
}

.screenshot {
  max-width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
}

.logs-panel {
  width: 360px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 0.75rem;
}

.logs-panel h3 {
  margin: 0 0 0.5rem 0;
}

.logs {
  flex: 1 1 auto;
  overflow: auto;
  background: rgba(15, 6, 20, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 0.5rem;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
}

.log-line {
  margin-bottom: 4px;
  color: rgba(255, 255, 255, 0.85);
}

.settings-panel {
  max-width: 640px;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.settings-form input {
  padding: 0.6rem 0.75rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(0, 0, 0, 0.35);
  color: #f4f5ff;
}

.settings-form input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.hint {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.65);
  margin: 0;
}

.settings-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.status-message {
  font-size: 0.85rem;
}

.status-message.success {
  color: #8ae5b4;
}

.status-message.error {
  color: #ff9aa2;
}

.status-message.info {
  color: #f9e79f;
}

@media (max-width: 960px) {
  .content-wrap {
    flex-direction: column;
  }

  .logs-panel {
    width: 100%;
    max-height: 40vh;
  }
}
</style>

