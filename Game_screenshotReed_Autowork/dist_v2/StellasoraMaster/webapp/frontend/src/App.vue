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
        :class="{ active: activeTab === 'monitor' }"
        @click="activeTab = 'monitor'"
      >实时监控</button>
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
              <!-- <label>
                <input type="checkbox" v-model="tasks.startGame">
                启动游戏
              </label> -->
              <label>
                <input type="checkbox" v-model="tasks.dailytasks">
                日常任务流程
              </label>
              <div v-if="tasks.dailytasks" class="sub-options">
                 <div style="margin-left: 20px; margin-bottom: 5px;">
                   <button type="button" class="text-btn" @click="selectAllDailyTasks">全选</button>
                   <button type="button" class="text-btn" @click="deselectAllDailyTasks" style="margin-left: 10px;">全不选</button>
                   <button type="button" class="text-btn" @click="selectOnlyInvitation" style="margin-left: 10px;">只选邀约</button>
                 </div>
                 <div class="daily-sub-tasks" style="display: flex; flex-direction: column; margin-left: 20px;">
                   <label><input type="checkbox" v-model="dailySubTasks.interaction"> 主页面角色互动</label>
                   <label><input type="checkbox" v-model="dailySubTasks.market_reward"> 领取商店随机奖励</label>
                   <label><input type="checkbox" v-model="dailySubTasks.commission"> 委托派遣</label>
                   <label><input type="checkbox" v-model="dailySubTasks.gift"> 赠送礼物</label>
                   <label><input type="checkbox" v-model="dailySubTasks.invitation"> 邀约</label>
                   <div v-if="dailySubTasks.invitation" class="invitation-settings" style="margin-left: 20px; margin-top: 5px; margin-bottom: 5px;">
                     <div v-for="(char, index) in invitationCharacters" :key="index" style="margin-bottom: 5px;">
                       <label>角色 {{ index + 1 }}:
                         <select v-model="invitationCharacters[index]" class="small-select">
                           <option value="">-- 选择角色 --</option>
                           <option v-for="opt in availableCharacters" :key="opt.value" :value="opt.value" :disabled="isCharacterSelected(opt.value, index)">
                             {{ opt.label }}
                           </option>
                         </select>
                       </label>
                     </div>
                   </div>
                   <label><input type="checkbox" v-model="dailySubTasks.card_upgrade"> 秘纹升级</label>
                   <label><input type="checkbox" v-model="dailySubTasks.character_upgrade"> 旅人升级</label>
                   <label><input type="checkbox" v-model="dailySubTasks.task_reward"> 领取日常任务奖励</label>
                 </div>
              </div>
              <label class="label-with-tooltip">
                <input type="checkbox" v-model="tasks.towerClimbing">
                自动爬塔
                
              </label>
              <div v-if="tasks.towerClimbing" class="sub-options">
                 <div class="tower-attrs">
                   <label><input type="radio" v-model="towerAttribute" value="light_earth"> 光/地</label>
                   <label><input type="radio" v-model="towerAttribute" value="water_wind"> 水/风</label>
                   <label><input type="radio" v-model="towerAttribute" value="fire_dark"> 火/暗</label>
                 </div>
                 <div class="climb-type">
                   <label><input type="radio" v-model="towerClimbType" value="quick"> 快速</label>
                   <label><input type="radio" v-model="towerClimbType" value="standard"> 标准</label>
                   <span class="info-icon" data-tooltip="快速：跳过购买和强化。消耗更少时间&#10;标准：完整流程->购买、强化。消耗更少的票">ⓘ</span>
                   
                 </div>
                 <div class="tower-settings">
                   <label class="input-label">
                     指定次数（若为0则运行至周任务完成为止）:
                     <input type="number" v-model.number="towerMaxRuns" min="0" placeholder="0为不限" class="small-input">
                   </label>
                 </div>
              </div>
            </div>
            <div class="actions-row">
              <button class="primary-btn" @click="startUnifiedTasks" :disabled="taskStatus.running || !hasSelectedTasks">
                {{ taskStatus.running ? '执行中...' : '开始执行' }}
              </button>
              <button class="secondary-btn" v-if="taskStatus.canPause" @click="pauseTask">
                暂停
              </button>
              <button class="secondary-btn" v-if="taskStatus.canResume" @click="resumeTask">
                继续
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
          <div class="logs-header">
            <h3>服务端日志</h3>
            <button class="text-btn small-btn" @click="exportLogs" title="导出日志">
              导出
            </button>
          </div>
          <div class="logs" ref="logsBox">
            <div v-for="item in logs" :key="item.idx" class="log-line">
              [{{ new Date(item.ts * 1000).toLocaleTimeString() }}] {{ item.level }}: {{ item.msg }}
            </div>
          </div>
        </aside>
      </div>
    </section>

    <section v-else-if="activeTab === 'monitor'" class="tab-content monitor-tab">
      <div class="monitor-panel-large">
        <div class="panel-header">
          <h3>实时监控</h3>
          <div class="monitor-controls">
             <button @click="startStream" class="primary-btn btn-small" :disabled="streamRunning">开启监控</button>
             <button @click="stopStream" class="danger-btn btn-small" :disabled="!streamRunning">暂停监控</button>
             <button @click="refreshStream" class="secondary-btn btn-small">刷新画面</button>
          </div>
        </div>
        <div class="screen-container-large">
          <img v-if="streamRunning" :src="streamUrl" alt="游戏画面监控" class="game-screen-large" @error="handleStreamError" />
          <div v-else class="stream-placeholder">
            <p>监控已暂停</p>
            <p class="sub-hint">点击“开启监控”以查看实时画面</p>
          </div>
          <div v-if="streamError" class="stream-error-msg">画面连接断开</div>
        </div>
        <div class="monitor-info">
          <p>FPS 已显示在画面左上角。若使用 RAW/Scrcpy 模式，帧率可达 10-30+ FPS。</p>
        </div>
      </div>
    </section>

    <section v-else class="tab-content settings-panel">
      <form class="settings-form" @submit.prevent="saveConfig">
        <label for="emulatorType">模拟器类型</label>
        <select id="emulatorType" v-model="settings.emulator_type">
          <option v-for="type in emulatorTypes" :key="type.value" :value="type.value">
            {{ type.label }}
          </option>
        </select>

        <label for="adbPath">ADB 路径</label>
        <input
          id="adbPath"
          type="text"
          v-model="settings.adb_path"
          placeholder="例如 D:\Program Files\Netease\MuMu Player 12\shell\adb.exe"
        />
        <p class="hint">填写对应模拟器目录下的adb.exe地址：MuMu一般位于shell文件夹下，雷电位于根目录。</p>

        <label for="adbPort">ADB 端口号</label>
        <input
          id="adbPort"
          type="number"
          v-model.number="settings.adb_port"
          placeholder="例如 16384"
        />
        <p class="hint">常见端口: 雷电(5555), MuMu12(16384)</p>

        <label>截图方式</label>
        <div class="screenshot-settings-row">
          <select v-model="settings.screenshot_method">
            <option value="PNG">兼容模式 (PNG) - 慢，稳定</option>
            <option value="RAW">高速模式 (RAW) - 快，推荐</option>
            <option value="SCRCPY">极速模式 (Scrcpy) - 最快</option>
          </select>
          <button type="button" class="secondary-btn btn-small" @click="testLatency" :disabled="testingLatency">
            {{ testingLatency ? '检测中...' : '截图检测' }}
          </button>
        </div>
        <p v-if="latencyResult" class="latency-result" :class="{ 'success': latencyResult.success, 'error': !latencyResult.success }">
          {{ latencyResult.message }}
        </p>
        <p class="hint">高速模式</p>

        <label>服务器语言</label>
        <div class="radio-group">
          <label>
            <input type="radio" v-model="settings.server_lang" value="zh-CN">
            简中
          </label>
          <label>
            <input type="radio" v-model="settings.server_lang" value="zh-Hant">
            繁中
          </label>
        </div>
        <p class="hint">切换语言后，将在下次重启脚本时生效。</p>

        <div class="settings-actions">
          <button type="button" class="secondary-btn" @click="testConnection" :disabled="testingConnection || savingSettings">
            {{ testingConnection ? '测试中...' : '测试连接' }}
          </button>
          <button type="submit" class="primary-btn" :disabled="savingSettings || testingConnection">
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
      streamUrl: '/video_feed',
      streamError: false,
      streamRunning: false,
      statusText: '-', // 兼容旧字段
      tasks: {
        startGame: false,
        dailytasks: false,
        towerClimbing: false
      },
      dailySubTasks: {
        interaction: true,
        market_reward: true,
        commission: true,
        gift: true,
        invitation: true,
        card_upgrade: true,
        character_upgrade: true,
        task_reward: true
      },
      invitationCharacters: ['', '', '', '', ''],
      availableCharacters: [
        { label: '小禾', value: 'xiaohe' },
        { label: '希娅', value: 'xiya' },
        { label: '雾语', value: 'wuyu' },
        { label: '格芮', value: 'gerui' },
        { label: '苍蓝', value: 'canglan' },
        { label: '岭川', value: 'lingchuan' },
        { label: '千都世', value: 'qiandushi' },
        { label: '尘沙', value: 'chensha' },
        { label: '鸢尾', value: 'yuanwei' },
        { label: '诗渺', value: 'shimiao' }
      ],
      towerAttribute: 'light_earth',
      towerClimbType: 'standard',
      towerMaxRuns: 0,
      logs: [],
      lastLogIndex: 0,
      _poller: null,
      _statusPoller: null,
      emulatorTypes: [
        { label: '雷电模拟器 (LDPlayer)', value: 'LDPlayer', defaultPort: 5555 },
        { label: 'MuMu模拟器 12', value: 'MuMu12', defaultPort: 16384 },
        { label: '自定义', value: 'Custom', defaultPort: 5555 },
      ],
      settings: {
        adb_path: '',
        adb_port: 16384,
        server_lang: 'zh-CN',
        emulator_type: 'Custom',
        emulator_configs: {}
      },
      savingSettings: false,
      testingConnection: false,
      testingLatency: false,
      latencyResult: null,
      configStatus: '',
      configStatusType: 'info',
      taskStatus: { state: 'idle', task: null, running: false, canStop: false, canPause: false, canResume: false }
    }
  },
  computed: {
    hasSelectedTasks() {
      return Object.values(this.tasks).some(v => v)
    },
    statusLine() {
      const s = this.taskStatus
      if (s.running && s.state !== 'paused') {
        if (s.task === 'combo') return '组合任务执行中'
        if (s.task === 'start_game') return '启动游戏中'
        if (s.task === 'dailytasks') return '日常任务执行中'
        if (s.task === 'tower_climbing') return '自动爬塔中'
      }
      switch (s.state) {
        case 'finished': return '任务已完成'
        case 'stopped': return '已停止'
        case 'paused': return '已暂停'
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
    },
    'settings.emulator_type': function(newVal, oldVal) {
      if (!newVal) return
      // Save old config
      if (oldVal && this.settings.emulator_configs) {
        this.settings.emulator_configs[oldVal] = {
          path: this.settings.adb_path,
          port: this.settings.adb_port
        }
      }
      // Load new config
      if (!this.settings.emulator_configs) this.settings.emulator_configs = {}
      const config = this.settings.emulator_configs[newVal]
      if (config) {
        this.settings.adb_path = config.path || ''
        this.settings.adb_port = config.port || this.getEmulatorDefaultPort(newVal)
      } else {
        this.settings.adb_path = ''
        this.settings.adb_port = this.getEmulatorDefaultPort(newVal)
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

    getEmulatorDefaultPort(type) {
      const found = this.emulatorTypes.find(t => t.value === type)
      return found ? found.defaultPort : 5555
    },

    taskTypeSelected() {
      if (this.tasks.dailytasks && this.tasks.towerClimbing) return 'daily_and_tower'
      if (this.tasks.towerClimbing) return 'tower_climbing'
      if (this.tasks.startGame && this.tasks.dailytasks) return 'combo'
      if (this.tasks.startGame) return 'start_game'
      if (this.tasks.dailytasks) return 'dailytasks'
      return null
    },

    async startUnifiedTasks() {
      const type = this.taskTypeSelected()
      if (!type) return
      try {
        const payload = { type }
        if (type === 'tower_climbing' || type === 'daily_and_tower') {
          payload.attribute_type = this.towerAttribute
          payload.climb_type = this.towerClimbType
          payload.max_runs = this.towerMaxRuns
        }
        if (type === 'dailytasks' || type === 'daily_and_tower' || type === 'combo') {
             const selected = Object.keys(this.dailySubTasks).filter(k => this.dailySubTasks[k]);
             payload.daily_sub_tasks = selected;
             if (this.dailySubTasks.invitation) {
               payload.invitation_characters = this.invitationCharacters;
             }
        }
        const res = await fetch(this.apiUrl('/task/start'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
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

    async pauseTask() {
      try {
        const res = await fetch(this.apiUrl('/task/pause'), { method: 'POST' })
        const data = await res.json()
        if (!data.ok) this.statusText = data.error || '暂停失败'
      } catch (e) {
        this.statusText = `暂停失败: ${e.message}`
      }
    },

    async resumeTask() {
      try {
        const res = await fetch(this.apiUrl('/task/resume'), { method: 'POST' })
        const data = await res.json()
        if (!data.ok) this.statusText = data.error || '恢复失败'
      } catch (e) {
        this.statusText = `恢复失败: ${e.message}`
      }
    },


    startPolling() {
      if (this._poller) return
      this._poller = setInterval(this.pollLogs, 800)
      this.pollLogs()
      
      // Poll stream status occasionally
      this._streamPoller = setInterval(this.pollStreamStatus, 2000)
      this.pollStreamStatus()
    },

    stopPolling() {
      if (this._poller) {
        clearInterval(this._poller)
        this._poller = null
      }
      if (this._streamPoller) {
        clearInterval(this._streamPoller)
        this._streamPoller = null
      }
    },

    async pollLogs() {
      try {
        const res = await fetch(this.apiUrl(`/logs?since=${this.lastLogIndex}`))
        const data = await res.json()
        if (data.ok && Array.isArray(data.logs) && data.logs.length) {
          this.logs.push(...data.logs)
          
          // Limit logs to last 2000 lines to prevent browser freeze
          if (this.logs.length > 2000) {
            this.logs = this.logs.slice(-2000)
          }

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

    exportLogs() {
      window.open(this.apiUrl('/logs/export'), '_blank')
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
    refreshStream() {
      this.streamUrl = `/video_feed?t=${new Date().getTime()}`;
      this.streamError = false;
    },
    handleStreamError() {
      this.streamError = true;
    },
    async startStream() {
      try {
        await fetch(this.apiUrl('/stream/start'));
        this.streamRunning = true;
        this.refreshStream();
      } catch (e) {
        console.error(e);
      }
    },
    async stopStream() {
      try {
        await fetch(this.apiUrl('/stream/stop'));
        this.streamRunning = false;
      } catch (e) {
        console.error(e);
      }
    },
    async pollStreamStatus() {
      try {
        const res = await fetch(this.apiUrl('/stream/status'));
        const data = await res.json();
        if (data.ok) {
          this.streamRunning = data.running;
        }
      } catch (e) {
        // ignore
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
        this.settings.adb_port = data.config?.adb_port || 16384
        this.settings.server_lang = data.config?.server_lang || 'zh-CN'
        this.settings.emulator_configs = data.config?.emulator_configs || {}
        this.settings.emulator_type = data.config?.emulator_type || 'Custom'
        this.settings.screenshot_method = data.config?.screenshot_method || 'PNG'
        if (data.config?.invitation_characters) {
          this.invitationCharacters = data.config.invitation_characters
        }
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
        // Update current emulator config before saving
        if (this.settings.emulator_type) {
          if (!this.settings.emulator_configs) this.settings.emulator_configs = {}
          this.settings.emulator_configs[this.settings.emulator_type] = {
            path: this.settings.adb_path,
            port: this.settings.adb_port
          }
        }

        const res = await fetch(this.apiUrl('/config'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ 
            adb_path: this.settings.adb_path || '',
            adb_port: this.settings.adb_port || 16384,
            server_lang: this.settings.server_lang || 'zh-CN',
            emulator_type: this.settings.emulator_type,
            emulator_configs: this.settings.emulator_configs,
            screenshot_method: this.settings.screenshot_method,
            invitation_characters: this.invitationCharacters
          })
        })
        const data = await res.json()
        if (!res.ok || !data.ok) {
          throw new Error(data.error || '保存失败')
        }
        this.settings.adb_path = data.config?.adb_path || ''
        this.settings.server_lang = data.config?.server_lang || 'zh-CN'
        this.settings.adb_port = data.config?.adb_port || 16384
        this.settings.emulator_type = data.config?.emulator_type || 'Custom'
        this.settings.emulator_configs = data.config?.emulator_configs || {}
        this.settings.screenshot_method = data.config?.screenshot_method || 'PNG'
        this.configStatus = '保存成功'
        this.configStatusType = 'success'
      } catch (e) {
        this.configStatus = `保存失败: ${e.message}`
        this.configStatusType = 'error'
      } finally {
        this.savingSettings = false
      }
    },

    async testLatency() {
      this.testingLatency = true;
      this.latencyResult = null;
      
      // 先保存配置，确保后端使用的是当前选择的截图方式
      await this.saveConfig();
      if (this.configStatusType === 'error') {
        this.testingLatency = false;
        return;
      }

      try {
        const res = await fetch(this.apiUrl('/api/test_latency'), {
          method: 'POST'
        });
        const data = await res.json();
        
        if (data.success) {
          let msg = `延迟: ${data.latency_ms.toFixed(2)} ms (模式: ${data.method})`;
          if (data.is_stream_running) {
            msg += " [流运行中，结果为缓存读取耗时]";
          }
          this.latencyResult = {
            success: true,
            message: msg
          };
        } else {
          this.latencyResult = {
            success: false,
            message: `检测失败: ${data.error}`
          };
        }
      } catch (e) {
        this.latencyResult = {
          success: false,
          message: `请求异常: ${e.message}`
        };
      } finally {
        this.testingLatency = false;
      }
    },

    async testConnection() {
      this.testingConnection = true
      this.configStatus = '正在测试连接...'
      this.configStatusType = 'info'
      try {
        const res = await fetch(this.apiUrl('/config/test_adb'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            adb_path: this.settings.adb_path || '',
            adb_port: this.settings.adb_port || 16384
          })
        })
        const data = await res.json()
        if (!res.ok || !data.ok) {
          throw new Error(data.error || '连接失败')
        }
        this.configStatus = '连接成功！'
        this.configStatusType = 'success'
      } catch (e) {
        this.configStatus = `测试失败: ${e.message}`
        this.configStatusType = 'error'
      } finally {
        this.testingConnection = false
      }
    },

    isCharacterSelected(value, currentIndex) {
      // 如果当前选项的值为空，不禁用
      if (!value) return false;
      // 检查该值是否已被其他下拉框选中
      return this.invitationCharacters.some((char, index) => {
        return char === value && index !== currentIndex;
      });
    },

    selectAllDailyTasks() {
      for (const key in this.dailySubTasks) {
        this.dailySubTasks[key] = true;
      }
    },

    deselectAllDailyTasks() {
      for (const key in this.dailySubTasks) {
        this.dailySubTasks[key] = false;
      }
    },

    selectOnlyInvitation() {
      for (const key in this.dailySubTasks) {
        this.dailySubTasks[key] = (key === 'invitation');
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

.sub-options {
  margin-left: 1.5rem;
  margin-bottom: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.9em;
  color: rgba(255, 255, 255, 0.8);
}

.tower-attrs, .tower-settings {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.small-input {
  width: 60px;
  padding: 2px 5px;
  margin-left: 5px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  border-radius: 4px;
}

.small-select {
  padding: 2px 5px;
  margin-left: 5px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  border-radius: 4px;
}

.sub-options label {
  display: inline-flex;
  align-items: center;
  margin: 0;
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

.secondary-btn {
  padding: 0.55rem 1.4rem;
  background: #6b8aff;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.secondary-btn:hover:not(:disabled) {
  background: #5879ef;
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

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.logs-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #f4f5ff;
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

.settings-form input,
.settings-form select {
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

.text-btn {
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: rgba(255, 255, 255, 0.8);
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  transition: all 0.2s;
}

.text-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.small-btn {
  font-size: 0.75rem;
  padding: 2px 6px;
}

.status-message.info {
  color: #f9e79f;
}

/* --- 监控面板样式 --- */
.monitor-tab {
  display: flex;
  justify-content: center;
}

.monitor-panel-large {
  width: 100%;
  max-width: 1000px;
  background: #1e1e1e;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  min-height: 500px;
}

.monitor-controls {
  display: flex;
  gap: 10px;
}

.screen-container-large {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #000;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
  min-height: 400px;
  margin-top: 10px;
}

.game-screen-large {
  max-width: 100%;
  max-height: 600px;
  object-fit: contain;
}

.stream-placeholder {
  color: #888;
  text-align: center;
}

.sub-hint {
  font-size: 12px;
  color: #555;
  margin-top: 5px;
}

.monitor-info {
  margin-top: 10px;
  font-size: 12px;
  color: #888;
  text-align: center;
}

.stream-error-msg {
  color: #ff6b6b;
  font-size: 14px;
  position: absolute;
  bottom: 10px;
}

.btn-small {
  padding: 4px 12px;
  font-size: 13px;
}

/* --- 新增 Tooltip 样式 --- */
.label-with-tooltip {
  display: flex !important; /* 覆盖默认的 block */
  align-items: center;
}

.info-icon {
  margin-left: 8px;
  cursor: help;
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  position: relative; /* 关键：作为定位基准 */
}

.info-icon:hover {
  color: #fff;
}

/* 提示框主体 */
.info-icon::after {
  content: attr(data-tooltip); /* 读取 HTML 中的文字 */
  position: absolute;
  bottom: 100%; /* 显示在上方 */
  left: 50%;
  transform: translateX(-50%) translateY(-5px);
  
  background: rgba(0, 0, 0, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre; /* 允许换行 */
  z-index: 1000;
  pointer-events: none;
  
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s, transform 0.2s;
  width: max-content;
  max-width: 250px;
  text-align: left;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}

/* 悬停时显示 */
.info-icon:hover::after {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) translateY(-10px);
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

