<template>
  <div class="container">
    <h1>Stellsora Master</h1>

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
      <button class="start-btn" @click="startTasks" :disabled="busy || !hasSelectedTasks">
        {{ busy ? '执行中...' : '开始执行' }}
      </button>
    </div>

    <div>
      <label>当前状态: <strong>{{ statusText }}</strong></label>
    </div>

    <div>
      <img v-if="image" :src="image" class="screenshot" alt="screenshot" />
    </div>
    
      </div>
      <aside class="logs-panel">
        <h3>服务端日志</h3>
        <div class="logs" ref="logsBox">
          <div v-for="item in logs" :key="item.idx" class="log-line">[{{ new Date(item.ts*1000).toLocaleTimeString() }}] {{ item.level }}: {{ item.msg }}</div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      image: null,
      statusText: '-',
      busy: false,
      tasks: {
        startGame: false,
        dailytasks: false
      }
      ,
      logs: [],
      lastLogIndex: 0,
      _poller: null
    }
  },
  computed: {
    hasSelectedTasks() {
      return Object.values(this.tasks).some(v => v)
    }
  },
  methods: {
    async handleFetch(path, opts) {
      const res = await fetch(path, opts)
      return res.json()
    },

    async executeStartGame() {
      this.busy = true
      this.statusText = '正在启动游戏...'
      try {
        const r = await this.handleFetch('/start_game', { method: 'POST' })
        this.statusText = r.ok ? '启动完成' : `Error: ${r.error}`
      } catch (e) {
        this.statusText = `请求失败: ${e.message}`
      }
    },

    async executedailytasks() {
      this.busy = true
      this.statusText = '正在完成日常任务...'
      try {
        const r = await this.handleFetch('/start_dailytasks', { method: 'POST' })
        this.statusText = r.ok ? '已完成日常任务' : `Error: ${r.error}`
      } catch (e) {
        this.statusText = `请求失败: ${e.message}`
      }
    },

    async startTasks() {
      // 按顺序执行选中的任务
      try {
        this.busy = true
        // start polling logs while tasks run
        this.startPolling()
        if (this.tasks.startGame) {
          await this.executeStartGame()
        }
        if (this.tasks.dailytasks) {
          await this.executedailytasks()
        }
        this.statusText = '所有任务执行完成'
      } catch (e) {
        this.statusText = `任务执行失败: ${e.message}`
      } finally {
        this.busy = false
        // poll a little longer then stop
        setTimeout(() => this.stopPolling(), 1500)
      }
    },

    startPolling() {
      if (this._poller) return
      this._poller = setInterval(this.pollLogs, 800)
      // initial fetch
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
        const res = await fetch(`/logs?since=${this.lastLogIndex}`)
        const data = await res.json()
        if (data.ok && Array.isArray(data.logs) && data.logs.length) {
          this.logs.push(...data.logs)
          this.lastLogIndex = data.last || this.lastLogIndex
          // scroll to bottom
          this.$nextTick(() => {
            const el = this.$refs.logsBox
            if (el) el.scrollTop = el.scrollHeight
          })
        }
      } catch (e) {
        // ignore polling errors silently
      }
    }
  }
}
</script>

<style>
body { font-family: Arial, sans-serif }
.container { padding: 1rem }
.task-selection { 
  margin: 1rem 0;
  padding: 1rem;
  border: 1px solid #eee;
  border-radius: 4px;
}
.checkbox-group {
  margin-bottom: 1rem;
}
.checkbox-group label {
  display: block;
  margin: 0.5rem 0;
  user-select: none;
}
.checkbox-group input[type="checkbox"] {
  margin-right: 0.5rem;
}
.start-btn {
  padding: 0.5rem 1rem;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.start-btn:disabled {
  background: #cccccc;
  cursor: not-allowed;
}
.screenshot { max-width: 90%; border: 1px solid #ccc; margin-top: .5rem }
</style>

<style scoped>
/* Two-column layout: main content + right-side logs */
.content-wrap {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}
.main {
  flex: 1 1 auto;
}
.logs-panel {
  width: 360px;
  max-height: 70vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #eee;
  padding-left: 0.75rem;
}
.logs-panel h3 {
  margin: 0 0 0.5rem 0;
}
.logs {
  flex: 1 1 auto;
  overflow: auto;
  background: #fafafa;
  border: 1px solid #eee;
  padding: 0.5rem;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
}
.log-line { margin-bottom: 4px; }
</style>

