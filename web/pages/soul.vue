<template>
  <div class="soul-studio">
    <!-- ═══ 顶栏 ═══ -->
    <header class="studio-header">
      <div class="header-left">
        <div class="header-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6">
            <circle cx="12" cy="12" r="8.2" />
            <path d="M12 3.8v16.4M3.8 12h16.4" opacity=".55" />
            <circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none" />
          </svg>
        </div>
        <div>
          <h1 class="page-title">{{ t('soul.page.title') }}</h1>
          <p class="page-subtitle">{{ t('soul.page.subtitle') }}</p>
        </div>
      </div>
      <div class="header-actions">
        <button v-if="runningTasks" class="task-live" @click="openTaskCenter()" :title="t('soul.page.viewRunningTasks')">
          <i class="live-dot"></i>{{ t('soul.page.tasksRunning', { n: runningTasks }) }}
          <span class="task-live-arrow">▾</span>
        </button>
        <button class="btn btn-ghost" @click="loadAll" :disabled="loadingList">
          <span class="btn-glyph">⟳</span> {{ t('soul.page.refresh') }}
        </button>
        <button class="btn btn-primary" @click="openCreate">
          <span class="btn-glyph">＋</span> {{ t('soul.page.create') }}
        </button>
      </div>
    </header>

    <div class="studio-body">
      <!-- ═══ 左 rail: 人格清单 ═══ -->
      <SoulPersonaRail
        :souls="souls"
        :selected-kb-id="selected?.kb_id || ''"
        :loading="loadingList"
        :kb-catalog="kbCatalog"
        @select="selectSoul"
      />

      <!-- ═══ 主区 ═══ -->
      <main class="studio-main">
        <template v-if="selected">
          <!-- 身份条 -->
          <section class="identity-bar">
            <div class="id-avatar">{{ soulAvatar(selected.name) }}</div>
            <div class="id-text">
              <div class="id-title">
                <h2>{{ selected.name }}</h2>
                <span v-if="selected.meditation?.enabled && selected.meditation?.meditation_mode === 'soul'" class="chip chip-red">{{ t('soul.identity.autoTraining', { interval: selected.meditation.interval_hours, rounds: selected.meditation.rounds_per_run }) }}</span>
                <span v-if="selected._training" class="chip chip-amber">{{ t('soul.identity.training') }}</span>
              </div>
              <p class="id-summary">{{ selected.summary || t('soul.identity.noSummary') }}</p>
              <div class="id-tags">
                <span class="tag-kb" v-for="s in selected.kb_scope || []" :key="s">{{ s }}</span>
                <span class="tag-dom" v-for="d in selected.domain_labels || []" :key="d">{{ d }}</span>
              </div>
            </div>
            <div class="id-actions">
              <button class="btn btn-primary btn-sm" @click="openAsk(selected)">{{ t('soul.identity.ask') }}</button>
              <button class="btn btn-copper btn-sm" @click="openTrain(selected)">{{ t('soul.identity.train') }}</button>
              <button class="btn btn-ghost btn-sm" @click="reviewDrafts(selected)">{{ t('soul.identity.review') }}<template v-if="selected._status?.drafts_pending_review"> {{ selected._status.drafts_pending_review }}</template></button>
              <button class="btn btn-ghost btn-sm" @click="openEdit(selected)">{{ t('soul.identity.config') }}</button>
              <button class="btn btn-ghost btn-sm" @click="doReflect(selected)">{{ t('soul.identity.reflect') }}</button>
              <button class="btn btn-ghost btn-sm" @click="doCheckpoint(selected)">{{ t('soul.identity.checkpoint') }}</button>
              <button v-if="selectedTaskStatus === 'paused'" class="btn btn-copper btn-sm" @click="resumeTask()">{{ t('soul.identity.resume') }}</button>
              <button v-if="selectedTaskStatus === 'running'" class="btn btn-ghost btn-sm" @click="pauseTask()">{{ t('soul.identity.pause') }}</button>
              <button class="btn btn-ghost btn-sm btn-danger" @click="confirmDelete(selected)">{{ t('soul.identity.delete') }}</button>
            </div>
          </section>

          <!-- 监控带 -->
          <section class="monitor-strip">
            <div class="metric-cell" v-for="m in metrics" :key="m.label">
              <span class="metric-val" :class="{ warn: m.warn }">{{ m.value }}</span>
              <span class="metric-label">{{ m.label }}</span>
            </div>
            <div class="metric-cell metric-reward" v-if="rewardRecords.length">
              <span class="metric-val">{{ lastReward }}</span>
              <span class="metric-label">{{ t('soul.monitor.rlReward') }}</span>
            </div>
          </section>

          <div class="workspace">
            <!-- 训练控制台 -->
            <section class="console train-console">
              <div class="console-head">
                <h3>{{ t('soul.train.consoleTitle') }}</h3>
                <span class="console-sub">{{ t('soul.train.consoleSub') }}</span>
                <button class="btn btn-ghost btn-xs" style="margin-left:auto" @click="loadTrainingHistory(selected); openHistory()">{{ t('soul.train.history') }}</button>
              </div>

              <!-- ═══ 统一 RL 训练面板 ═══ -->

              <!-- 暂停态 -->
              <div v-if="trainTaskStatus === 'paused'" class="train-paused">
                <div class="pause-banner">
                  <b>{{ t('soul.train.pausedBanner') }}</b>
                  <button class="btn btn-copper btn-sm" @click="resumeTask()">{{ t('soul.train.resumeTraining') }}</button>
                </div>
              </div>

              <!-- 未运行: RL 启动面板(唯一训练模式) -->
              <div v-if="trainTaskStatus !== 'running' && trainTaskStatus !== 'paused'" class="train-launch rl-launch">
                <div class="rl-banner">
                  <span class="rl-icon">🧠</span>
                  <div class="rl-banner-text">
                    <b>{{ t('soul.train.rlTitle') }}</b>
                    <p>{{ t('soul.train.rlDesc') }}</p>
                  </div>
                </div>
                <div class="rl-params">
                  <label class="field">
                    <span class="field-label">{{ t('soul.train.fieldRounds') }}</span>
                    <input class="inp" type="number" v-model.number="trainForm.rounds" min="1" max="10" />
                  </label>
                </div>
                <div class="launch-row">
                  <button class="btn btn-copper btn-lg" :disabled="training" @click="doTrain">
                    {{ training ? t('soul.train.submitting') : t('soul.train.launchBtn') }}
                  </button>
                  <span class="launch-hint">{{ t('soul.train.launchHint') }}</span>
                </div>
              </div>

              <!-- 运行中 / 已完成: 实时三角色监控 -->
              <div v-else class="train-monitor rl-monitor">
                <!-- 三角色进度时间线 -->
                <div class="phase-track rl-phases" v-if="trainProgress">
                  <div class="phase" :class="{ on: rlPhaseIdx('actor') >= 1, done: rlPhaseIdx('actor') === 2 }">
                    <span class="phase-dot actor"></span>
                    <span class="phase-name">{{ t('soul.train.phaseActor') }}</span>
                    <span class="phase-note">{{ t('soul.train.phaseQuestions', { n: trainProgress.questions ?? 0 }) }} · {{ t('soul.train.phaseMemories', { n: trainProgress.memories ?? 0 }) }}</span>
                  </div>
                  <div class="phase-conn" :class="{ on: rlPhaseIdx('critic') >= 1 }"></div>
                  <div class="phase" :class="{ on: rlPhaseIdx('critic') >= 1, done: rlPhaseIdx('critic') === 2 }">
                    <span class="phase-dot critic"></span>
                    <span class="phase-name">{{ t('soul.train.phaseCritic') }}</span>
                    <span class="phase-note" v-if="trainProgress.reward !== undefined">reward {{ fmtNum(trainProgress.reward) }}</span>
                  </div>
                  <div class="phase-conn" :class="{ on: rlPhaseIdx('updater') >= 1 }"></div>
                  <div class="phase" :class="{ on: rlPhaseIdx('updater') >= 1, done: rlPhaseIdx('updater') === 2 }">
                    <span class="phase-dot updater"></span>
                    <span class="phase-name">{{ t('soul.train.phaseUpdater') }}</span>
                    <span class="phase-note">{{ t('soul.train.phaseDrafts', { n: (trainProgress.drafts_count ?? trainProgress.auto_applied ?? 0) }) }}</span>
                  </div>
                </div>

                <!-- 收敛状态指示器 -->
                <div class="convergence-bar" v-if="trainProgress">
                  <span class="conv-badge" :class="{ converged: trainProgress.converged }">
                    {{ trainProgress.converged ? t('soul.train.converged') : t('soul.train.notConverged') }}
                  </span>
                  <span class="conv-round" v-if="trainProgress.round">R{{ trainProgress.round }}/{{ trainProgress.rounds }}</span>
                  <span class="conv-auto" v-if="trainProgress.auto_applied">{{ t('soul.train.autoAppliedBadge') }} {{ trainProgress.auto_applied }}</span>
                </div>

                <!-- 进度条 -->
                <div class="mon-line">
                  <span class="mon-label">{{ t('soul.train.progressLabel') }}</span>
                  <div class="bar"><i class="bar-fill" :style="{ width: trainPercent() + '%' }"></i></div>
                  <span class="mon-pct">{{ trainPercent() }}%</span>
                </div>

                <!-- 六维评分雷达(当 Critic 评分可用时) -->
                <div class="rl-scores" v-if="latestScores">
                  <div class="scores-head">{{ t('soul.train.criticPanel') }}</div>
                  <div class="scores-grid">
                    <div class="score-item" v-for="dim in scoreDims" :key="dim.key">
                      <span class="score-label">{{ t('soul.train.' + dim.i18n) }}</span>
                      <div class="score-bar-wrap">
                        <div class="score-bar" :style="{ width: (latestScores[dim.key] / 5 * 100) + '%' }" :class="scoreClass(latestScores[dim.key])"></div>
                      </div>
                      <span class="score-val">{{ fmtNum(latestScores[dim.key]) }}</span>
                    </div>
                  </div>
                </div>

                <!-- 实时事件流(每个模型的输出) -->
                <div class="event-log rl-events">
                  <div class="log-head">{{ t('soul.train.eventStream') }}</div>
                  <div class="log-body rl-log-body" ref="logBody">
                    <div v-if="!eventLog.length" class="log-empty">{{ t('soul.train.noEvents') }}</div>
                    <div v-for="(ev, i) in eventLog" :key="i" class="log-line rl-event" :class="'ev-' + ev.tone">
                      <span class="log-time">{{ ev.time }}</span>
                      <i class="log-dot" :class="ev.tone"></i>
                      <span class="ev-icon">{{ evPhaseIcon(ev.tone) }}</span>
                      <span class="log-text" v-html="ev.text"></span>
                    </div>
                  </div>
                </div>

                <!-- 训练结果 -->
                <div class="train-result-box" v-if="trainResult">
                  <div class="result-head2">
                    <span>{{ t('soul.train.trainResult') }}</span>
                    <button class="btn btn-ghost btn-xs" @click="trainResult = ''">{{ t('soul.train.close') }}</button>
                  </div>
                  <pre class="result-pre">{{ trainResult }}</pre>
                </div>
              </div>

              <!-- RL 进化曲线(常驻, 无论是否训练中) -->
              <div class="reward-curve" v-if="rewardRecords.length > 1">
                <div class="curve-head">
                  <span>{{ t('soul.train.rlCurve') }}</span>
                  <span class="curve-sub">{{ t('soul.train.rlCurveSub', { n: rewardRecords.length, reward: fmtNum(lastReward) }) }}</span>
                </div>
                <svg :viewBox="`0 0 320 96`" preserveAspectRatio="none" class="curve-svg">
                  <polyline
                    :points="curvePoints"
                    fill="none" stroke="var(--kb-primary, #b24422)" stroke-width="2"
                    vector-effect="non-scaling-stroke"
                  />
                  <circle v-for="(p, i) in curveDots" :key="i" :cx="p.x" :cy="p.y" r="2.6" fill="var(--kb-gold, #b8860b)" />
                </svg>
              </div>
              <div v-else-if="rewardRecords.length === 1" class="reward-curve">
                <div class="curve-head">
                  <span>{{ t('soul.train.rlCurve') }}</span>
                  <span class="curve-sub">{{ t('soul.train.rlCurveOneRecord', { reward: fmtNum(lastReward) }) }}</span>
                </div>
              </div>
            </section>

            <!-- 人格定义查看器 -->
            <section class="console def-console">
              <div class="console-head">
                <h3>{{ t('soul.persona.definition') }}</h3>
                <span class="console-sub">
                  {{ t('soul.persona.constitution') }}<template v-if="docEvolution > 0">{{ t('soul.persona.evolved', { n: docEvolution }) }}</template><template v-else>{{ t('soul.persona.toEvolve') }}</template>
                </span>
              </div>
              <div class="doc-tabs">
                <button
                  v-for="d in personaDocs"
                  :key="d.name"
                  class="doc-tab"
                  :class="{ on: activeDoc === d.name }"
                  @click="activeDoc = d.name"
                >{{ docShortName(d.name) }}</button>
                <button
                  class="doc-tab folder-tab"
                  :class="{ on: activeDoc === '__folder__' }"
                  @click="activeDoc = '__folder__'"
                >{{ t('soul.persona.folderArch') }}</button>
              </div>
              <!-- 宪法文档内容 -->
              <div class="doc-body" v-if="activeDoc !== '__folder__' && activeDocContent">
                <div class="doc-meta">
                  <span class="doc-updated">{{ t('soul.persona.updated', { time: fmtTime(activeDocMeta.updated_at) }) }}</span>
                  <span class="doc-char">{{ t('soul.persona.chars', { n: activeDocContent.length }) }}</span>
                </div>
                <div class="doc-scroll" ref="docScroll">
                  <template v-for="(line, i) in renderedDoc" :key="i">
                    <h4 v-if="isHeading(line)" class="doc-h">{{ line.replace(/^#+\s*/, '') }}</h4>
                    <div v-else-if="isBullet(line)" class="doc-bullet" :class="{ evolved: isEvolvedLine(line) }">
                      <span class="b-dot"></span><span>{{ line.replace(/^[-•*]\s*/, '') }}</span>
                      <span v-if="isEvolvedLine(line)" class="evolved-mark">RL</span>
                    </div>
                    <p v-else-if="line.trim()" class="doc-p" :class="{ evolved: isEvolvedLine(line) }">{{ line }}</p>
                  </template>
                </div>
              </div>
              <div class="doc-body" v-else-if="activeDoc !== '__folder__' && !activeDocContent">
                <div class="doc-empty">{{ t('soul.persona.loading') }}</div>
              </div>
              <!-- 📂 文件夹浏览器 -->
              <div class="folder-browser" v-if="activeDoc === '__folder__'">
                <template v-if="folderLoading">
                  <div class="doc-empty">{{ t('soul.persona.loadingFolder') }}</div>
                </template>
                <template v-else-if="folderStructure && folderStructure.sections.length">
                  <aside class="folder-sections">
                    <button
                      v-for="sec in folderStructure.sections"
                      :key="sec.key"
                      class="folder-section-btn"
                      :class="{ on: activeFolderSection === sec.key }"
                      @click="activeFolderSection = sec.key"
                    >
                      <span class="sec-icon">{{ sectionIcon(sec.key) }}</span>
                      <span class="sec-name">{{ sec.name }}</span>
                      <span class="sec-count">{{ (sec.entries || sec.items).length }}</span>
                    </button>
                  </aside>
                  <div class="folder-content">
                    <!-- 非空分区: 内容展示 -->
                    <template v-if="activeSection && (activeSection.entries || activeSection.items).length">
                      <div class="folder-content-head">
                        <h4>{{ activeSection.name }}</h4>
                        <span class="folder-content-desc">{{ activeSection.description }}</span>
                        <span class="folder-item-count">{{ t('soul.persona.items', { n: (activeSection.entries || activeSection.items).length }) }}</span>
                      </div>
                      <div class="folder-items">
                        <template v-for="item in (activeSection.entries || activeSection.items || [])" :key="item.name">
                          <!-- MD 文件渲染（含记忆卡片） -->
                          <div v-if="item.type === 'md' && item.content" class="folder-item-md">
                            <div class="item-head">
                              <span class="item-name">{{ item.name }}</span>
                              <span class="item-size">{{ fmtSize(item.size) }}</span>
                            </div>
                            <!-- 记忆文件 → 卡片视图 -->
                            <template v-if="activeSection.key === 'memories' && parseMemoryFrontmatter(item.content)">
                              <div class="mem-card">
                                <div class="mem-card-q">{{ parseMemoryFrontmatter(item.content)!.frontmatter.question || '—' }}</div>
                                <div class="mem-card-scores">
                                  <span class="mem-score" v-for="(v,k) in scoreEntries(parseMemoryFrontmatter(item.content)!.frontmatter.scores)" :key="k">
                                    <b>{{ scoreLabel(String(k)) }}</b> {{ v }}
                                  </span>
                                </div>
                                <div class="mem-card-meta">
                                  <span class="mem-chip" :class="parseMemoryFrontmatter(item.content)!.frontmatter.status">{{ parseMemoryFrontmatter(item.content)!.frontmatter.status }}</span>
                                  <span class="mem-chip" v-if="parseMemoryFrontmatter(item.content)!.frontmatter.evidence_paths">{{ t('soul.persona.evidence', { n: (parseMemoryFrontmatter(item.content)!.frontmatter.evidence_paths || []).length }) }}</span>
                                  <span class="mem-chip" v-if="parseMemoryFrontmatter(item.content)!.frontmatter.stale">stale</span>
                                </div>
                                <details class="mem-card-body">
                                  <summary>{{ t('soul.persona.answersAndEvidence') }}</summary>
                                  <div class="mem-answer">{{ parseMemoryFrontmatter(item.content)!.body }}</div>
                                </details>
                              </div>
                            </template>
                            <!-- 普通 MD → 行渲染（复用 doc-* 样式） -->
                            <template v-else>
                              <div class="folder-md-scroll">
                                <template v-for="(line, i) in renderMdLines(item.content!)" :key="i">
                                  <h4 v-if="isHeading(line)" class="doc-h">{{ line.replace(/^#+\s*/, '') }}</h4>
                                  <div v-else-if="isBullet(line)" class="doc-bullet">
                                    <span class="b-dot"></span><span>{{ line.replace(/^[-•*]\s*/, '') }}</span>
                                  </div>
                                  <p v-else-if="line.trim()" class="doc-p">{{ line }}</p>
                                </template>
                              </div>
                            </template>
                          </div>
                          <!-- YAML → 键值表 -->
                          <div v-else-if="item.type === 'yaml' && item.content" class="folder-item-kv">
                            <div class="item-head">
                              <span class="item-name">{{ item.name }}</span>
                              <span class="item-size">{{ fmtSize(item.size) }}</span>
                            </div>
                            <table class="kv-table">
                              <tbody>
                                <tr v-for="kv in parseYamlKv(item.content)" :key="kv.key">
                                  <td class="kv-key">{{ kv.key }}</td>
                                  <td class="kv-val"><code>{{ kv.value }}</code></td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                          <!-- JSON → 对象表格 -->
                          <div v-else-if="item.type === 'json' && item.content" class="folder-item-kv">
                            <div class="item-head">
                              <span class="item-name">{{ item.name }}</span>
                              <span class="item-size">{{ fmtSize(item.size) }}</span>
                            </div>
                            <table class="kv-table">
                              <tbody>
                                <tr v-for="(v,k) in safeJsonParse(item.content)" :key="k">
                                  <td class="kv-key">{{ k }}</td>
                                  <td class="kv-val"><code>{{ fmtJsonVal(v) }}</code></td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                          <!-- JSONL → 数组表格 -->
                          <div v-else-if="item.type === 'jsonl' && item.content" class="folder-item-table">
                            <div class="item-head">
                              <span class="item-name">{{ item.name }}</span>
                              <span class="item-size">{{ fmtSize(item.size) }} · {{ t('soul.persona.recordsPrefix', { n: parseJsonl(item.content).length }) }}</span>
                            </div>
                            <div class="jsonl-table-wrap">
                              <table class="jsonl-table">
                                <thead>
                                  <tr>
                                    <th v-for="col in jsonlColumns([item])" :key="col">{{ col }}</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  <tr v-for="(row, ri) in parseJsonl(item.content)" :key="ri">
                                    <td v-for="col in jsonlColumns([item])" :key="col">
                                      <code>{{ fmtJsonVal(row[col]) }}</code>
                                    </td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                          </div>
                          <!-- 无内容条目 / text -->
                          <div v-else class="folder-item-plain">
                            <span class="item-name">{{ item.name }}</span>
                            <span class="item-size">{{ fmtSize(item.size) }}</span>
                          </div>
                        </template>
                      </div>
                    </template>
                    <!-- 空分区: 用途说明 -->
                    <div v-else-if="activeSection" class="folder-empty-section">
                      <div class="empty-section-icon">{{ sectionIcon(activeSection.key) }}</div>
                      <p class="empty-section-title">{{ activeSection.name }}</p>
                      <p class="empty-section-desc">{{ activeSection.description }}</p>
                      <div class="empty-section-hint" v-if="sectionUsageHints[activeSection.key]">
                        {{ sectionUsageHints[activeSection.key] }}
                      </div>
                    </div>
                    <!-- 未选择 -->
                    <div v-else class="doc-empty">{{ t('soul.persona.pickSection') }}</div>
                  </div>
                </template>
                <div v-else class="doc-empty">{{ t('soul.persona.noFolderData') }}</div>
              </div>
            </section>
          </div>
        </template>
        <!-- 未选择 -->
        <div v-else class="studio-empty">
          <div class="empty-symbol" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.3">
              <circle cx="12" cy="12" r="8.2" />
              <path d="M12 3.8v16.4M3.8 12h16.4" opacity=".5" />
            </svg>
          </div>
          <p class="empty-title">{{ t('soul.page.selectPrompt') }}</p>
          <p class="empty-desc">{{ t('soul.page.selectDescription') }}</p>
        </div>
      </main>
    </div>

    <!-- ═══ Toast ═══ -->
    <transition name="toast-fade">
      <div v-if="toast" class="soul-toast" :class="toastType">
        <span>{{ toast }}</span>
        <button class="toast-close" @click="toast = ''">×</button>
      </div>
    </transition>

    <!-- ═══════════ 创建人格 Modal ═══════════ -->
    <a-modal v-model:open="createOpen"  :title="t('soul.create.title')" :footer="null" width="620">
      <a-form layout="vertical">
        <a-form-item  :label="t('soul.create.nameLabel')">
          <a-input v-model:value="form.soul_name"  :placeholder="t('soul.create.namePlaceholder')" />
        </a-form-item>
        <a-form-item  :label="t('soul.create.modeLabel')">
          <a-radio-group v-model:value="form.create_mode" button-style="solid" style="width:100%">
            <a-radio-button value="template">{{ t('soul.create.modeTemplate') }}</a-radio-button>
            <a-radio-button value="nuwa">{{ t('soul.create.modeNuwa') }}</a-radio-button>
            <a-radio-button value="dot">{{ t('soul.create.modeDot') }}</a-radio-button>
            <a-radio-button value="butian">{{ t('soul.create.modeButian') }}</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <div class="mode-desc" v-if="form.create_mode !== 'template'">
          {{ modeDesc }}
        </div>
        <a-form-item  :label="t('soul.create.scopeLabel')">
          <a-checkbox v-model:checked="form.allKb">{{ t('soul.create.allKbCheckbox') }}</a-checkbox>
          <a-select v-model:value="form.kb_scope" mode="multiple"  :placeholder="t('soul.create.scopePlaceholder')" style="width:100%; margin-top:6px" :disabled="form.allKb">
            <a-select-option v-for="kb in kbCatalog" :key="kb.kbId" :value="kb.kbId">{{ kb.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item  :label="t('soul.create.domainLabel')">
          <a-select v-model:value="form.domain_labels" mode="tags"  :placeholder="t('soul.create.domainPlaceholder')" style="width:100%" />
        </a-form-item>
        <a-form-item  :label="t('soul.create.taskTypeLabel')">
          <a-select v-model:value="form.supported_task_types" mode="tags"  :placeholder="t('soul.create.taskTypePlaceholder')" style="width:100%" />
        </a-form-item>
        <!-- ═══ 女娲模式: 输入名人/主题 → 蒸馏创建(可接入 nuwa-skill 深研) ═══ -->
        <template v-if="form.create_mode === 'nuwa'">
          <a-form-item  :label="t('soul.create.personLabel')">
            <a-input v-model:value="form.person_name"  :placeholder="t('soul.create.personPlaceholder')" />
          </a-form-item>
          <a-form-item  :label="t('soul.create.personDescLabel')">
            <a-textarea v-model:value="form.source_material" :rows="3"  :placeholder="t('soul.create.personDescPlaceholder')" />
          </a-form-item>
          <div class="distill-hint" v-html="t('soul.create.nuwaHint')"></div>
          <a-divider style="margin:8px 0">{{ t('soul.create.nuwaDeepDivider') }}</a-divider>
          <a-form-item  :label="t('soul.create.nuwaSkillLabel')">
            <a-textarea v-model:value="form.skill_md" :rows="6"  :placeholder="t('soul.create.nuwaSkillPlaceholder')" />
          </a-form-item>
        </template>

        <!-- ═══ dot-skill 模式: 传入文档/材料 → 蒸馏 ═══ -->
        <template v-if="form.create_mode === 'dot'">
          <div class="distill-hint" v-html="t('soul.create.dotHint')"></div>
          <a-form-item  :label="t('soul.create.sourceMaterialLabel')">
            <a-textarea v-model:value="form.source_material" :rows="3"  :placeholder="t('soul.create.sourceMaterialPlaceholder')" />
          </a-form-item>
          <a-form-item  :label="t('soul.create.uploadLabel')">
            <div class="file-drop" @click="distillFileInput?.click()" @dragover.prevent @drop.prevent="onDistillFilesDrop">
              <input ref="distillFileInput" type="file" multiple hidden
                     accept=".md,.txt,.markdown,.csv,.json,.eml,.mbox,.xlsx,.xls,.docx,.pdf,.png,.jpg,.jpeg,.webp,.bmp,.pptx,.ppt"
                     @change="onDistillFilesPick" />
              <template v-if="!form.files.length">
                <span class="fd-main">{{ t('soul.create.uploadMain') }}</span>
                <span class="fd-sub">{{ t('soul.create.uploadSub') }}</span>
              </template>
              <template v-else>
                <div v-for="(f, i) in form.files" :key="i" class="fd-item">
                  <span class="fd-name">{{ f.name }}</span>
                  <span class="fd-size">{{ (f.size / 1024).toFixed(0) }}KB</span>
                  <span class="fd-rm" @click.stop="form.files.splice(i, 1)">×</span>
                </div>
              </template>
            </div>
          </a-form-item>
          <a-divider style="margin:8px 0">{{ t('soul.create.dotSeedDivider') }}</a-divider>
          <a-form-item  :label="t('soul.create.seedUploadLabel')">
            <div class="file-drop" @click="seedFileInput?.click()" @dragover.prevent @drop.prevent="onSeedFilesDrop">
              <input ref="seedFileInput" type="file" multiple hidden accept=".json,.md" @change="onSeedFilesPick" />
              <template v-if="!form.seedFiles.length">
                <span class="fd-main">{{ t('soul.create.seedUploadMain') }}</span>
                <span class="fd-sub">{{ t('soul.create.seedUploadSub') }}</span>
              </template>
              <template v-else>
                <div v-for="(f, i) in form.seedFiles" :key="i" class="fd-item">
                  <span class="fd-name">{{ f.name }}</span>
                  <span class="fd-size">{{ (f.size / 1024).toFixed(0) }}KB</span>
                  <span class="fd-rm" @click.stop="form.seedFiles.splice(i, 1)">×</span>
                </div>
              </template>
            </div>
          </a-form-item>
        </template>

        <!-- ═══ 补天·智能集成模式: 人物 + 材料 双通道 ═══ -->
        <template v-if="form.create_mode === 'butian'">
          <div class="distill-hint" v-html="t('soul.create.butianHint')"></div>
          <a-form-item  :label="t('soul.create.personLabel')">
            <a-input v-model:value="form.person_name"  :placeholder="t('soul.create.personPlaceholder')" />
          </a-form-item>
          <a-form-item  :label="t('soul.create.personalityReqLabel')">
            <a-textarea v-model:value="form.personality_req" :rows="2"  :placeholder="t('soul.create.personalityReqPlaceholder')" />
          </a-form-item>
          <a-form-item  :label="t('soul.create.sourceMaterialLabel')">
            <a-textarea v-model:value="form.source_material" :rows="3"  :placeholder="t('soul.create.sourceMaterialPlaceholder')" />
          </a-form-item>
          <a-form-item  :label="t('soul.create.uploadLabel')">
            <div class="file-drop" @click="distillFileInput?.click()" @dragover.prevent @drop.prevent="onDistillFilesDrop">
              <input ref="distillFileInput" type="file" multiple hidden
                     accept=".md,.txt,.markdown,.csv,.json,.eml,.mbox,.xlsx,.xls,.docx,.pdf,.png,.jpg,.jpeg,.webp,.bmp,.pptx,.ppt"
                     @change="onDistillFilesPick" />
              <template v-if="!form.files.length">
                <span class="fd-main">{{ t('soul.create.uploadMain') }}</span>
                <span class="fd-sub">{{ t('soul.create.uploadSub') }}</span>
              </template>
              <template v-else>
                <div v-for="(f, i) in form.files" :key="i" class="fd-item">
                  <span class="fd-name">{{ f.name }}</span>
                  <span class="fd-size">{{ (f.size / 1024).toFixed(0) }}KB</span>
                  <span class="fd-rm" @click.stop="form.files.splice(i, 1)">×</span>
                </div>
              </template>
            </div>
          </a-form-item>
        </template>
        <a-form-item :label="t('soul.create.harnessLabel', { default: defaultHarness || 'omp' })">
          <a-select v-model:value="form.harness" style="width:100%">
            <a-select-option value="">{{ t('soul.create.harnessDefault', { default: defaultHarness || 'omp' }) }}</a-select-option>
            <a-select-option value="omp">{{ t('soul.create.harnessOmp', { status: harnessInstalled('omp') ? t('soul.create.harnessAvailable') : t('soul.create.harnessNotInstalled') }) }}</a-select-option>
            <a-select-option value="claude">{{ t('soul.create.harnessClaude', { status: harnessInstalled('claude') ? t('soul.create.harnessAvailable') : t('soul.create.harnessClaudeNeedKey') }) }}</a-select-option>
          </a-select>
        </a-form-item>
        <div class="modal-actions">
          <a-button @click="createOpen = false">{{ t('soul.create.cancel') }}</a-button>
          <a-button type="primary" :loading="creating" @click="doCreate">{{ t('soul.create.create') }}</a-button>
        </div>
      </a-form>
    </a-modal>

    <!-- ═══════════ 配置 Modal ═══════════ -->
    <a-modal v-model:open="editOpen"  :title="t('soul.config.title')" :footer="null" width="620">
      <a-form layout="vertical" v-if="editing">
        <a-form-item  :label="t('soul.config.personaLabel')"><a-input :value="editing.name" disabled /></a-form-item>
        <a-form-item  :label="t('soul.config.scopeLabel')">
          <a-select v-model:value="editForm.kb_scope" mode="multiple" style="width:100%">
            <a-select-option v-for="kb in kbCatalog" :key="kb.kbId" :value="kb.kbId">{{ kb.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item  :label="t('soul.config.domainLabel')"><a-select v-model:value="editForm.domain_labels" mode="tags" style="width:100%" /></a-form-item>
        <a-form-item  :label="t('soul.config.taskTypeLabel')"><a-select v-model:value="editForm.supported_task_types" mode="tags" style="width:100%" /></a-form-item>
        <a-form-item  :label="t('soul.config.routeWeightLabel')"><a-slider v-model:value="editForm.route_weight" :min="0" :max="2" :step="0.1" /></a-form-item>
        <a-divider style="margin:8px 0">{{ t('soul.config.engineDivider') }}</a-divider>
        <a-form-item label="harness">
          <a-select v-model:value="editForm.harness" style="width:100%">
            <a-select-option value="omp">omp</a-select-option>
            <a-select-option value="claude">claude</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item  :label="t('soul.config.modelLabel')"><a-input v-model:value="editForm.model"  :placeholder="t('soul.config.modelPlaceholder')" /></a-form-item>
        <a-divider style="margin:8px 0">{{ t('soul.config.autoDivider') }}</a-divider>
        <a-form-item  :label="t('soul.config.autoEnableLabel')"><a-switch v-model:value="editForm.autoTrainEnabled" /></a-form-item>
        <div class="ask-row">
          <a-form-item  :label="t('soul.config.intervalLabel')"><a-input-number v-model:value="editForm.intervalHours" :min="1" :max="720" /></a-form-item>
          <a-form-item  :label="t('soul.config.roundsLabel')"><a-input-number v-model:value="editForm.roundsPerRun" :min="1" :max="20" /></a-form-item>
          <a-form-item  :label="t('soul.config.budgetLabel')"><a-input-number v-model:value="editForm.maxBudgetUsd" :min="0.01" :max="2" :step="0.05" /></a-form-item>
        </div>
        <a-form-item  :label="t('soul.config.maxQuestionsLabel')"><a-input-number v-model:value="editForm.maxQuestions" :min="1" :max="20" /></a-form-item>
        <div class="modal-actions">
          <a-button @click="editOpen = false">{{ t('soul.config.cancel') }}</a-button>
          <a-button type="primary" :loading="savingConfig" @click="doSaveConfig">{{ t('soul.config.save') }}</a-button>
        </div>
      </a-form>
    </a-modal>

    <!-- ═══════════ 问答 Modal ═══════════ -->
    <a-modal v-model:open="askOpen"  :title="t('soul.ask.title')" :footer="null" width="720">
      <div v-if="askSoul || true">
        <div class="ask-target">
          <span class="ask-target-label">{{ t('soul.ask.target') }}</span>
          <a-tag v-if="askSoul?.name" color="purple">{{ askSoul.name }}</a-tag>
          <span v-else class="ask-route-hint">{{ t('soul.ask.autoRoute') }}</span>
          <span class="ask-hint">{{ t('soul.ask.autoRouteHint') }}</span>
        </div>
        <a-form layout="vertical">
          <a-form-item  :label="t('soul.ask.queryLabel')">
            <a-textarea v-model:value="askForm.query" :rows="3"  :placeholder="t('soul.ask.queryPlaceholder')" />
          </a-form-item>
          <div class="ask-row">
            <a-form-item  :label="t('soul.config.taskTypeLabel')"><a-input v-model:value="askForm.task_type"  :placeholder="t('soul.ask.taskTypePlaceholder')" /></a-form-item>
            <a-form-item  :label="t('soul.ask.taskGoalLabel')"><a-input v-model:value="askForm.task_goal"  :placeholder="t('soul.ask.taskGoalPlaceholder')" /></a-form-item>
          </div>
          <a-form-item  :label="t('soul.ask.contextLabel')">
            <a-textarea v-model:value="askForm.context_override" :rows="2"  :placeholder="t('soul.ask.contextPlaceholder')" />
          </a-form-item>
        </a-form>
        <div class="ask-row">
          <a-button :loading="searchingKb" @click="doPreSearch">{{ t('soul.ask.preSearch') }}</a-button>
          <a-button type="primary" ghost :loading="asking" @click="doQdcvrAsk">{{ t('soul.ask.qdcvrAsk') }}</a-button>
          <a-button type="primary" :loading="asking" @click="doAsk">{{ t('soul.identity.ask') }}</a-button>
        </div>
        <div v-if="preSearchChunks.length" class="pre-search-list">
          <div v-for="(c, i) in preSearchChunks.slice(0, 5)" :key="i" class="cite-item">
            <span class="cite-path">{{ c.doc_path }}</span>
            <span class="cite-score">{{ c.score?.toFixed?.(3) ?? c.score }}</span>
          </div>
        </div>
        <div v-if="askResult" class="ask-result">
          <div class="result-head">
            <span class="result-label">{{ t('soul.ask.answer') }}</span>
            <a-tag v-if="askResult.selected_soul" color="green">{{ t('soul.ask.route') }}: {{ soulName(askResult.selected_soul) }}</a-tag>
            <a-tag v-if="askResult.pas_score !== undefined && askResult.pas_score !== null" :color="askResult.pas_score >= 3 ? 'cyan' : 'red'">PAS {{ askResult.pas_score }}</a-tag>
            <a-tag v-if="askResult.evidence_count !== undefined">{{ t('soul.ask.evidence', { n: askResult.evidence_count }) }}</a-tag>
          </div>
          <div class="answer-text">{{ askResult.answer }}</div>
          <div v-if="askResult.citations?.length" class="cite-list">
            <div class="cite-title">{{ t('soul.ask.citations', { n: askResult.citations.length }) }}</div>
            <div v-for="(c, i) in askResult.citations.slice(0, 8)" :key="i" class="cite-item">
              <span class="cite-path">{{ c.path }}</span>
              <span class="cite-score">{{ c.score?.toFixed?.(3) ?? c.score }}</span>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <a-button @click="askOpen = false">{{ t('soul.ask.close') }}</a-button>
        </div>
      </div>
    </a-modal>

    <!-- ═══════════ 任务中心 Modal(全局运行中任务) ═══════════ -->
    <a-modal v-model:open="taskCenterOpen"  :title="t('soul.taskCenter.title')" :footer="null" width="820">
      <div class="task-center">
        <div v-if="!activeTasks.length" class="h-empty">{{ t('soul.taskCenter.empty') }}</div>
        <div v-for="t in activeTasks" :key="t.task_id" class="tc-item">
          <div class="tc-head">
            <i class="tc-pulse"></i>
            <span class="tc-soul">{{ soulName(t.meta?.soul_kb_id) || t.meta?.soul_kb_id || t('soul.taskCenter.global') }}</span>
            <span class="tc-kind">{{ t.kind }}</span>
            <span class="tc-elapsed">{{ Math.round(t.elapsed_seconds || 0) }}s</span>
            <button v-if="t.status === 'running'" class="btn btn-ghost btn-xs" @click="pauseTaskById(t.task_id)">{{ t('soul.identity.pause') }}</button>
            <button v-if="t.status === 'paused'" class="btn btn-copper btn-xs" @click="resumeTaskById(t.task_id)">{{ t('soul.identity.resume') }}</button>
            <button class="btn btn-ghost btn-xs" @click="focusTask(t)">{{ t('soul.taskCenter.locate') }}</button>
          </div>
          <div class="tc-phase" v-if="t.progress">
            <span class="tc-phase-name">{{ phaseLabel(t.progress) }}</span>
            <span class="tc-phase-detail">{{ phaseDetail(t.progress) }}</span>
          </div>
          <div class="tc-bar" v-if="t.progress"><i class="bar-fill" :style="{ width: taskPercent(t) + '%' }"></i></div>
        </div>
        <div class="tc-history-hint" @click="historyOpen = true; openHistory()">{{ t('soul.taskCenter.viewHistory') }}</div>
      </div>
    </a-modal>

    <!-- ═══════════ 训练历史 Modal(SQLite) ═══════════ -->
    <a-modal v-model:open="historyOpen"  :title="t('soul.history.title')" :footer="null" width="860">
      <div class="history-layout">
        <div class="history-list">
          <div v-for="r in trainingHistory" :key="r.id" class="history-item" :class="{ on: historyRun?.id === r.id }" @click="openHistory(r)">
            <div class="h-row1">
              <span class="h-kind">{{ r.kind }}</span>
              <span class="h-status" :class="r.status">{{ r.status }}</span>
            </div>
            <div class="h-row2">
              <span class="h-time">{{ fmtTime(r.started_at) }}</span>
              <span v-if="r.finished_at" class="h-dur">{{ Math.round((+new Date(r.finished_at) - +new Date(r.started_at)) / 1000) }}s</span>
            </div>
            <div class="h-row3">
              <span>Q{{ r.questions ?? 0 }}</span><span>M{{ r.memories ?? 0 }}</span><span>D{{ r.docs ?? 0 }}</span>
              <span v-if="r.reward != null">★{{ r.reward }}</span>
              <span v-if="r.cost_usd">${{ r.cost_usd.toFixed(2) }}</span>
            </div>
          </div>
          <div v-if="!trainingHistory.length" class="h-empty">{{ t('soul.history.empty') }}</div>
        </div>
        <div class="history-detail">
          <template v-if="historyRun">
            <div class="hd-head">
              <span class="hd-title">{{ historyRun.kind }} · {{ historyRun.soul_kb_id }}</span>
              <span class="hd-status" :class="historyRun.status">{{ historyRun.status }}</span>
            </div>
            <div class="hd-metrics">
              <span>{{ t('soul.history.rounds', { n: historyRun.rounds ?? 0 }) }}</span><span>{{ t('soul.history.questions', { n: historyRun.questions ?? 0 }) }}</span>
              <span>{{ t('soul.history.memories', { n: historyRun.memories ?? 0 }) }}</span><span>{{ t('soul.history.docs', { n: historyRun.docs ?? 0 }) }}</span>
              <span v-if="historyRun.reward != null">reward {{ historyRun.reward }}</span>
              <span v-if="historyRun.cost_usd">${{ historyRun.cost_usd.toFixed(2) }}</span>
            </div>
            <div class="hd-events">
              <div v-for="e in historyEvents" :key="e.id" class="hd-event">
                <span class="hd-ev-time">{{ e.ts.slice(11, 19) }}</span>
                <i class="log-dot" :class="e.phase === 'reward' ? 'reward' : (e.phase === 'learn' ? 'ok' : 'info')"></i>
                <span class="hd-ev-phase">{{ e.phase }}</span>
                <span class="hd-ev-payload">{{ JSON.stringify(e.payload).slice(0, 160) }}</span>
              </div>
              <div v-if="!historyEvents.length" class="h-empty">{{ t('soul.history.noEvents') }}</div>
            </div>
          </template>
          <div v-else class="h-empty">{{ t('soul.history.selectHint') }}</div>
        </div>
      </div>
      <div class="modal-actions">
        <a-button @click="historyOpen = false">{{ t('soul.history.close') }}</a-button>
      </div>
    </a-modal>

    <!-- ═══════════ 审批 Modal ═══════════ -->
    <a-modal v-model:open="reviewOpen"  :title="t('soul.review.title')" :footer="null" width="780">
      <div v-if="reviewSoul">
        <div class="ask-target">
          <span class="ask-target-label">{{ t('soul.review.persona') }}</span>
          <a-tag color="purple">{{ reviewSoul.name }}</a-tag>
          <a-radio-group v-model:value="reviewType" size="small" style="margin-left:12px">
            <a-radio-button value="memory" @click="reviewDrafts(reviewSoul, 'memory')">{{ t('soul.review.memoryDrafts') }}</a-radio-button>
            <a-radio-button value="cognition" @click="reviewDrafts(reviewSoul, 'cognition')">{{ t('soul.review.cognitionDrafts') }}</a-radio-button>
          </a-radio-group>
          <a-button v-if="drafts.length > 1 && !reviewTaskStatus" size="small" type="primary" ghost style="margin-left:auto" @click="approveAllDrafts()">
            {{ t('soul.review.approveAll', { n: drafts.length }) }}
          </a-button>
        </div>
        <a-alert v-if="reviewTaskStatus === 'running'" type="info" show-icon style="margin-bottom:8px">
          <template #message>
            <div>{{ t('soul.review.reviewing', { processed: reviewProgress?.processed || 0, total: reviewProgress?.total || drafts.length, approved: reviewProgress?.approved || 0 }) }}</div>
            <a-progress :percent="Math.round(((reviewProgress?.processed || 0) / (reviewProgress?.total || drafts.length || 1)) * 100)" size="small" />
          </template>
        </a-alert>
        <a-alert v-if="reviewTaskStatus === 'error'" type="error" show-icon :message="reviewError || t('soul.review.reviewError')" style="margin-bottom:8px" />
        <a-table
          :data-source="drafts"
          :columns="draftColumns"
          size="small"
          :pagination="false"
          :scroll="{ y: 360 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'scores'">
              <span class="score-cell" :class="{ low: (record.scores?.groundedness ?? 0) < 3 }">G{{ record.scores?.groundedness ?? '-' }}</span>
              <span class="score-cell">{{ record.scores?.completeness ?? '-' }}</span>
              <span class="score-cell">{{ record.scores?.coherence ?? '-' }}</span>
              <span class="score-cell">{{ record.scores?.info_gain ?? '-' }}</span>
              <span class="score-cell" v-if="record.scores?.reward !== undefined">R{{ record.scores.reward }}</span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-button size="small" type="primary" @click="approveDraft(record.draft_id)">{{ t('soul.review.approve') }}</a-button>
              <a-button size="small" danger class="ml-4" @click="rejectDraft(record.draft_id)">{{ t('soul.review.reject') }}</a-button>
            </template>
          </template>
        </a-table>
        <div class="modal-actions" style="margin-top:12px">
          <a-button @click="reviewOpen = false">{{ t('soul.review.close') }}</a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import SoulPersonaRail from '../components/SoulPersonaRail.vue'
import {
  RobotOutlined, PlusOutlined, ReloadOutlined, MoreOutlined, SettingOutlined,
  MessageOutlined, ExperimentOutlined, AuditOutlined, SyncOutlined,
  CameraOutlined, ExportOutlined, DeleteOutlined, SearchOutlined,
} from '@ant-design/icons-vue'
import { message, Modal } from 'ant-design-vue'

const { t } = useI18n()

// ── 类型 ──
interface Soul {
  kb_id: string
  name: string
  summary?: string
  kb_scope?: string[]
  domain_labels?: string[]
  supported_task_types?: string[]
  route_weight?: number
  is_template?: boolean
  meditation?: {
    harness?: string
    model?: string
    enabled?: boolean
    meditation_mode?: string
    interval_hours?: number
    rounds_per_run?: number
    max_questions_per_run?: number
    max_budget_usd?: number
  }
  _status?: any
  _training?: boolean
  _trainingMsg?: string
}
// ── 文件夹浏览器类型 ──
interface FolderItem {
  name: string
  type: 'md' | 'json' | 'yaml' | 'jsonl' | 'text'
  size: number
  mtime?: string
  content?: string
  meta?: Record<string, any>
}
interface FolderSection {
  key: string
  name: string
  description: string
  items: FolderItem[]
  /** 后端结构可能用 entries 字段(与 items 同义) */
  entries?: FolderItem[]
}
interface FolderStructure {
  sections: FolderSection[]
}

// ── 状态 ──
const souls = ref<Soul[]>([])
const kbCatalog = ref<any[]>([])
const loadingList = ref(false)
const creating = ref(false)
const savingConfig = ref(false)
const training = ref(false)
const asking = ref(false)
const searchingKb = ref(false)
const toast = ref('')
const toastType = ref<'ok' | 'err'>('ok')
const selected = ref<Soul | null>(null)
const runningTasks = ref(0)

// 系统级设置
const soulSettings = ref<any>(null)
const defaultHarness = computed(() => soulSettings.value?.default_harness || 'omp')
const docOptions = ref<{ path: string }[]>([])
const loadingDocs = ref(false)
const preSearchChunks = ref<any[]>([])

// Modals
const createOpen = ref(false)
const editOpen = ref(false)
const trainOpen = ref(false)
const askOpen = ref(false)
const reviewOpen = ref(false)

const form = ref({ soul_name: '', kb_scope: [] as string[], domain_labels: [] as string[], supported_task_types: [] as string[], harness: '', allKb: true, personality_req: '', source_material: '', files: [] as { name: string; size: number; file: File }[], create_mode: 'template' as 'template' | 'nuwa' | 'dot' | 'butian', skill_md: '', seedFiles: [] as { name: string; size: number; file: File }[], person_name: '' })
const editing = ref<Soul | null>(null)
const editForm = ref({
  kb_scope: [] as string[], domain_labels: [] as string[], supported_task_types: [] as string[], route_weight: 1,
  harness: 'omp', model: '', autoTrainEnabled: false, intervalHours: 24, roundsPerRun: 1,
  maxBudgetUsd: 0.15, maxQuestions: 10,
})
const trainingSoul = ref<Soul | null>(null)
const trainMode = ref<'docs' | 'all' | 'rl'>('docs')
const trainForm = ref({ doc_paths: [] as string[], limit: 6, dry_run: false, rounds: 1, maxDocs: 10 })
const trainResult = ref('')
const trainTaskId = ref('')
const trainTaskStatus = ref('')
/** 训练完成判定(独立 computed, 避免模板 v-if 收窄导致 'done' 比较被 TS 拒绝) */
const trainTaskDone = computed(() => trainTaskStatus.value === 'done')
const trainProgress = ref<any>(null)
const trainError = ref('')
const reviewTaskId = ref('')
const reviewTaskStatus = ref('')
const reviewProgress = ref<any>(null)
const reviewError = ref('')
let trainPollTimer: any = null
let reviewPollTimer: any = null
let taskListTimer: any = null

// 事件日志流（训练监控）
const eventLog = ref<{ time: string; tone: string; text: string }[]>([])
const logBody = ref<HTMLElement | null>(null)

// 人格定义查看器
const personaDocs = ref<{ name: string; content: string; updated_at?: string }[]>([])
const activeDoc = ref('soul-definition.md')
const docEvolution = ref(0)
const evolutionLines = ref<string[]>([])

// 文件夹浏览器
const folderStructure = ref<FolderStructure | null>(null)
const activeFolderSection = ref('')
const folderLoading = ref(false)

// RL 进化曲线
const rewardRecords = ref<any[]>([])

const askSoul = ref<Soul | null>(null)
const askForm = ref({ query: '', task_type: '', task_goal: '', context_override: '' })
const askResult = ref<any>(null)
const reviewSoul = ref<Soul | null>(null)
const drafts = ref<any[]>([])
const draftColumns = [
  { title: t('soul.review.drafts'), dataIndex: 'question', key: 'question', ellipsis: true },
  { title: 'G/C/C/I/R', key: 'scores', width: 150 },
  { title: t('soul.review.actions'), key: 'actions', width: 130 },
]

// ── 工具 ──
function soulAvatar(name: string) {
  const m = name.match(/soul-([\u4e00-\u9fa5A-Za-z]+)/)
  return m ? m[1].slice(0, 2) : 'S'
}
function soulName(kbId: string) {
  return souls.value.find(s => s.kb_id === kbId)?.name || kbId.slice(0, 8)
}
function harnessInstalled(name: string): boolean {
  const h = soulSettings.value?.harnesses?.[name]
  return !!h?.installed
}
function scopeDocs(soul: Soul): string[] {
  const out: string[] = []
  for (const kb of kbCatalog.value) {
    if ((soul.kb_scope || []).includes(kb.kbId) || (soul.kb_scope || []).includes(kb.name)) {
      out.push(kb.name)
    }
  }
  return out
}
function fmtNum(v: any): string {
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(2) : String(v ?? '—')
}
function fmtTime(iso?: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
function showToast(msg: string, type: 'ok' | 'err' = 'ok') {
  toast.value = msg
  toastType.value = type
  setTimeout(() => { if (toast.value === msg) toast.value = '' }, 5000)
}
function pushLog(tone: string, text: string) {
  const now = new Date()
  const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  eventLog.value.push({ time, tone, text })
  if (eventLog.value.length > 200) eventLog.value.splice(0, eventLog.value.length - 200)
  nextTick(() => { if (logBody.value) logBody.value.scrollTop = logBody.value.scrollHeight })
}
function phaseIdx(phase: string): number {
  // 0=未开始 1=进行中 2=完成
  const p = trainProgress.value || {}
  if (trainTaskStatus.value === 'done') return 2
  if (p.phase === phase) return 1
  const order = ['learn', 'reward']
  if (order.indexOf(phase) >= 0 && order.indexOf(p.phase) > order.indexOf(phase)) return 2
  if (phase === 'reward' && p.phase === 'reward') return 1
  return p.phase === phase ? 1 : 0
}
function docShortName(name: string) {
  return name.replace(/\.md$/, '').replace(/-/g, ' ')
}
function isHeading(line: string) { return /^#{1,4}\s/.test(line) }
function isBullet(line: string) { return /^[-•*]\s/.test(line) }
function isEvolvedLine(line: string): boolean {
  const t = line.replace(/^[-•*]\s*/, '').trim()
  return evolutionLines.value.includes(t)
}

// ── 派生 ──
const metrics = computed(() => {
  const s = selected.value?._status
  if (!s) return []
  return [
    { label: t('soul.monitor.memory'), value: s.total_memories ?? 0 },
    { label: t('soul.monitor.pending'), value: s.drafts_pending_review ?? 0, warn: s.drafts_pending_review > 0 },
    { label: t('soul.monitor.gaps'), value: s.total_gaps ?? 0 },
    { label: t('soul.monitor.mastery'), value: s.mastery?.avg_score != null ? s.mastery.avg_score.toFixed(1) : '—' },
    { label: t('soul.monitor.cost'), value: s.estimated_cost_usd != null ? `$${s.estimated_cost_usd.toFixed(2)}` : '—', warn: (s.estimated_cost_usd ?? 0) > 0.12 },
    { label: t('soul.monitor.divergence'), value: s.judge_divergence_count ?? 0, warn: s.judge_divergence_count > 0 },
  ]
})
const lastReward = computed(() => {
  const r = rewardRecords.value[rewardRecords.value.length - 1]
  return r ? fmtNum(r.reward) : '—'
})
const activeDocMeta = computed<{ name: string; content: string; updated_at?: string }>(() =>
  personaDocs.value.find(d => d.name === activeDoc.value) || { name: '', content: '', updated_at: undefined })
const activeDocContent = computed(() => activeDocMeta.value.content || '')
const renderedDoc = computed(() => activeDocContent.value.split('\n'))
const curvePoints = computed(() => {
  const n = rewardRecords.value.length
  if (n < 2) return ''
  const maxR = Math.max(...rewardRecords.value.map(r => Number(r.reward) || 0))
  const minR = Math.min(...rewardRecords.value.map(r => Number(r.reward) || 0))
  const span = Math.max(0.5, maxR - minR)
  return rewardRecords.value.map((r, i) => {
    const x = (i / (n - 1)) * 320
    const y = 88 - ((Number(r.reward) || 0) - minR) / span * 76
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})
const curveDots = computed(() => {
  const n = rewardRecords.value.length
  if (n < 2) return []
  const maxR = Math.max(...rewardRecords.value.map(r => Number(r.reward) || 0))
  const minR = Math.min(...rewardRecords.value.map(r => Number(r.reward) || 0))
  const span = Math.max(0.5, maxR - minR)
  return rewardRecords.value.map((r, i) => ({
    x: (i / (n - 1)) * 320,
    y: 88 - ((Number(r.reward) || 0) - minR) / span * 76,
  }))
})

// ── 数据加载 ──
async function loadAll() {
  loadingList.value = true
  try {
    const list = await $fetch<any>('/api/soul/list')
    souls.value = (list || []).map((s: Soul) => ({ ...s }))
    await Promise.all(souls.value.map(async (s) => {
      try { s._status = await $fetch<any>(`/api/soul/status?soul_kb_id=${encodeURIComponent(s.kb_id)}`) } catch { /* noop */ }
    }))
    try {
      const cat = await $fetch<any>('/api/kb/catalog')
      kbCatalog.value = cat?.knowledgeBases || []
    } catch { /* noop */ }
    try {
      soulSettings.value = await $fetch<any>('/api/soul/settings')
    } catch { /* noop */ }
    // 默认选中第一个非模板人格
    if (!selected.value && souls.value.length) {
      selectSoul(souls.value.find(s => !s.is_template) || souls.value[0])
    } else if (selected.value) {
      const fresh = souls.value.find(s => s.kb_id === selected.value?.kb_id)
      if (fresh) selected.value = { ...fresh, _status: fresh._status, _training: selected.value._training }
    }
  } catch (e: any) {
    showToast(t('soul.actions.loadFailed', { error: e.message }), 'err')
  } finally {
    loadingList.value = false
  }
}

function selectSoul(soul: Soul) {
  selected.value = soul
  // 重置训练监控为该人格上下文
  trainResult.value = ''
  trainTaskStatus.value = ''
  trainProgress.value = null
  eventLog.value = []
  loadRewardHistory(soul)
  loadPersonaDocs(soul)
  loadSoulFolder(soul)
  loadScopeDocs(soul)
  loadTrainingHistory(soul)
}

async function loadRewardHistory(soul: Soul) {
  try {
    const res = await $fetch<any>(`/api/soul/reward-history?soul_kb_id=${encodeURIComponent(soul.kb_id)}`)
    rewardRecords.value = res?.records || []
  } catch { rewardRecords.value = [] }
}
async function loadPersonaDocs(soul: Soul) {
  try {
    const res = await $fetch<any>(`/api/soul/persona-docs?soul_kb_id=${encodeURIComponent(soul.kb_id)}`)
    personaDocs.value = res?.docs || []
    docEvolution.value = res?.evolution_count ?? 0
    evolutionLines.value = res?.evolution_lines || []
    if (personaDocs.value.length && !personaDocs.value.some(d => d.name === activeDoc.value)) {
      activeDoc.value = personaDocs.value[0].name
    }
  } catch {
    personaDocs.value = []
    docEvolution.value = 0
    evolutionLines.value = []
  }
}

async function loadSoulFolder(soul: Soul) {
  folderLoading.value = true
  try {
    const res = await $fetch<any>(`/api/soul/folder?soul_kb_id=${encodeURIComponent(soul.kb_id)}`)
    if (res?.success && res?.structure) {
      folderStructure.value = res.structure
      // 默认选中第一个有内容的 section
      const firstNonEmpty = res.structure.sections?.find((s: FolderSection) => (s.entries || s.items)?.length > 0)
      activeFolderSection.value = firstNonEmpty?.key || (res.structure.sections?.[0]?.key || '')
    } else {
      folderStructure.value = null
      activeFolderSection.value = ''
    }
  } catch {
    folderStructure.value = null
    activeFolderSection.value = ''
  } finally {
    folderLoading.value = false
  }
}

// 当前选中分区
const activeSection = computed(() => {
  if (!folderStructure.value) return null
  return folderStructure.value.sections.find(s => s.key === activeFolderSection.value) || null
})

// ── 分区空态用途说明 ──
const sectionUsageHints: Record<string, string> = {
  constitution: t('soul.folder.hint.constitution'),
  config: t('soul.folder.hint.config'),
  memories: t('soul.folder.hint.memories'),
  'cognition-drafts': t('soul.folder.hint.cognitionDrafts'),
  cognition: t('soul.folder.hint.cognition'),
  training: t('soul.folder.hint.training'),
  questions: t('soul.folder.hint.questions'),
  reports: t('soul.folder.hint.reports'),
  audit: t('soul.folder.hint.audit'),
  calibration: t('soul.folder.hint.calibration'),
  checkpoints: t('soul.folder.hint.checkpoints'),
}

// ── JSONL 表格列提取 ──
function jsonlColumns(items: FolderItem[]): string[] {
  const keys = new Set<string>()
  for (const item of items) {
    if (!item.content) continue
    try {
      const lines = item.content.trim().split('\n')
      for (const line of lines) {
        const obj = JSON.parse(line)
        Object.keys(obj).forEach(k => keys.add(k))
      }
    } catch { /* skip */ }
  }
  // 优先关键列
  const priority = ['timestamp', 'operator', 'action', 'draft_id', 'status', 'question']
  const ordered: string[] = priority.filter(k => keys.has(k))
  for (const k of keys) { if (!ordered.includes(k)) ordered.push(k) }
  return ordered.slice(0, 8)
}

// ── JSONL 解析为行数组 ──

function parseJsonl(content: string): Record<string, any>[] {
  try {
    return content.trim().split('\n').filter(Boolean).map(line => JSON.parse(line))
  } catch { return [] }
}

function parseMemoryFrontmatter(content: string): { frontmatter: Record<string, any>; body: string } | null {
  const m = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/)
  if (!m) return null
  const fm: Record<string, any> = {}
  let currentKey = ''
  let currentObj: Record<string, any> | null = null
  for (const line of m[1].split('\n')) {
    // 一级键: key: value
    const kv = line.match(/^(\w[\w_]*(?:\s*\[[\w\s,]*\])?):\s*(.*)$/)
    if (kv) {
      currentKey = kv[1].trim().replace(/\s*\[.*\]/, '')
      currentObj = null
      const val = kv[2].trim()
      if (val === '' || val === 'null') {
        // 可能是空值或嵌套对象的父键
        fm[currentKey] = val === 'null' ? null : {}
        if (fm[currentKey] !== null && typeof fm[currentKey] === 'object' && !Array.isArray(fm[currentKey])) {
          currentObj = fm[currentKey] as Record<string, any>
        }
      } else if (val === 'true') fm[currentKey] = true
      else if (val === 'false') fm[currentKey] = false
      else if (/^-?\d+\.?\d*$/.test(val)) fm[currentKey] = Number(val)
      else fm[currentKey] = val.replace(/^['"]|['"]$/g, '')
    } else if (line.trim().startsWith('-') && currentKey) {
      // 数组项: - value (当前键的数组或嵌套对象的数组)
      const itemVal = line.trim().replace(/^-\s*/, '').replace(/^['"]|['"]$/g, '')
      const obj = currentObj
      if (obj) {
        if (!Array.isArray(obj[currentKey])) {
          // 找到当前嵌套对象中的实际数组键
          const listKey = Object.keys(obj).find(k => Array.isArray(obj[k])) || '_items'
          if (!Array.isArray(obj[listKey])) obj[listKey] = []
          obj[listKey].push(itemVal)
        }
      } else {
        if (!Array.isArray(fm[currentKey])) fm[currentKey] = []
        fm[currentKey].push(itemVal)
      }
    } else if (line.trim()) {
      // 嵌套键:   subkey: value
      const nkv = line.match(/^\s{2,}(\w[\w_]*):\s*(.*)$/)
      if (nkv && currentObj) {
        const nk = nkv[1]
        const nv = nkv[2].trim()
        if (nv === 'null') currentObj[nk] = null
        else if (nv === 'true') currentObj[nk] = true
        else if (nv === 'false') currentObj[nk] = false
        else if (/^-?\d+\.?\d*$/.test(nv)) currentObj[nk] = Number(nv)
        else currentObj[nk] = nv.replace(/^['"]|['"]$/g, '')
        currentKey = nk
      }
    }
  }
  return { frontmatter: fm, body: m[2].trim() }
}

// ── YAML 解析为键值对 ──
function parseYamlKv(content: string): { key: string; value: string }[] {
  const pairs: { key: string; value: string }[] = []
  for (const line of content.split('\n')) {
    const m = line.match(/^(\w[\w_]*):\s*(.*)$/)
    if (m) pairs.push({ key: m[1], value: m[2].trim() || '—' })
  }
  return pairs
}

// ── 格式化值展示 ──
function fmtJsonVal(v: any): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

// ── MD 渲染（复用 doc-short-name 等已有逻辑；新帮助函数用于文件夹内 md 显示） ──
function renderMdLines(content: string): string[] {
  return content.split('\n')
}

// ── 文件夹浏览器辅助函数 ──
function sectionIcon(key: string): string {
  const map: Record<string, string> = {
    constitution: '📜', config: '⚙️', memories: '🧠', 'cognition-drafts': '🌱',
    cognition: '🗄️', training: '🎯', questions: '📋', reports: '📊',
    audit: '📝', calibration: '🎚️', checkpoints: '💾',
  }
  return map[key] || '📁'
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function scoreEntries(scores: Record<string, number> | null | undefined): [string, number][] {
  if (!scores || typeof scores !== 'object') return []
  return Object.entries(scores)
}

function scoreLabel(key: string): string {
  const map: Record<string, string> = {
    groundedness: t('soul.monitor.groundedness'), completeness: t('soul.monitor.completeness'), coherence: t('soul.monitor.coherence'), info_gain: t('soul.monitor.infoGain'),
  }
  return map[key] || key
}

function safeJsonParse(content: string): Record<string, any> {
  try { return JSON.parse(content) } catch { return {} }
}
async function loadScopeDocs(soul: Soul) {
  loadingDocs.value = true
  docOptions.value = []
  try {
    const scope = (soul.kb_scope || []).filter((s: string) => s !== '*')
    const kbs = scope.length
      ? kbCatalog.value.filter((kb: any) => scope.includes(kb.kbId) || scope.includes(kb.name))
      : kbCatalog.value
    const paths = new Set<string>()
    await Promise.all(kbs.map(async (kb: any) => {
      try {
        const res = await $fetch<any>(`/api/kb/documents?kb_id=${encodeURIComponent(kb.kbId)}`)
        for (const d of (res?.documents || [])) {
          if (d.path && (d.file_type === 'md' || d.path.endsWith('.md'))) paths.add(d.path)
        }
      } catch { /* noop */ }
    }))
    docOptions.value = [...paths].sort().map(p => ({ path: p }))
  } finally {
    loadingDocs.value = false
  }
}

// 全局任务列表监控（顶栏运行中计数）
async function pollTaskList() {
  try {
    const res = await $fetch<any>('/api/soul/tasks')
    const arr = (res?.tasks || []).filter((t: any) => t.status === 'running' || t.status === 'paused')
    runningTasks.value = arr.length
    activeTasks.value = arr
    // 训练中的人格状态灯 + 训练控制台任务绑定
    for (const t of arr) {
      const kbId = t.meta?.soul_kb_id
      if (kbId) {
        const s = souls.value.find(x => x.kb_id === kbId)
        if (s) { s._training = true; s._trainingMsg = `${t.kind} · ${t.elapsed_seconds ?? 0}s` }
      }
    }
  } catch { /* noop */ }
}

// ── 任务中心(全局运行中任务可视化) ──
const activeTasks = ref<any[]>([])
const taskCenterOpen = ref(false)
function openTaskCenter() {
  taskCenterOpen.value = true
  pollTaskList()
}
function phaseLabel(p: any): string {
  if (!p) return t('soul.taskCenter.phaseExecuting')
  if (p.phase === 'learn') return t('soul.taskCenter.phaseLearn', { round: p.round ?? 1, rounds: p.rounds ?? 1 })
  if (p.phase === 'reward') return t('soul.taskCenter.phaseReward', { reward: p.reward != null ? fmtNum(p.reward) : '…' })
  if (p.phase === 'scan') return t('soul.taskCenter.phaseScan')
  if (p.phase === 'parse_files') return t('soul.taskCenter.phaseParseFiles')
  if (p.phase === 'distill') return t('soul.taskCenter.phaseDistill')
  if (p.phase === 'build') return t('soul.taskCenter.phaseBuild')
  if (p.phase === 'done') return t('soul.taskCenter.phaseDone')
  if (p.processed !== undefined) return t('soul.taskCenter.phaseReview', { processed: p.processed, total: p.total })
  return t('soul.taskCenter.phaseExecuting')
}
function phaseDetail(p: any): string {
  if (!p) return ''
  if (p.phase === 'learn') return t('soul.taskCenter.detailLearn', { q: p.questions ?? 0, m: p.memories ?? 0, d: p.docs_processed ?? 0 }) + (p.soul_kb_id ? ' · ' + p.soul_kb_id : '')
  if (p.phase === 'reward') return t('soul.taskCenter.detailReward', { n: p.drafts_created ?? 0 }) + (p.msg ? ' · ' + p.msg : '')
  if (p.phase === 'scan') return t('soul.taskCenter.detailScan', { scanned: p.scanned, total: p.total, unique: p.unique_docs })
  if (p.phase === 'parse_files' || p.phase === 'distill' || p.phase === 'build') return p.msg || ''
  if (p.processed !== undefined) return t('soul.taskCenter.detailReview', { approved: p.approved ?? 0, rejected: p.rejected ?? 0 })
  return ''
}
function taskPercent(t: any): number {
  const p = t.progress || {}
  if (p.phase === 'learn' && p.rounds > 1) return Math.min(99, Math.round((p.round / p.rounds) * 100))
  if (p.phase === 'scan') return Math.min(90, Math.round((p.scanned / (p.total || 1)) * 90))
  return 55 // unknown phase → mid progress
}
async function pauseTaskById(id: string) {
  try { await $fetch(`/api/soul/tasks/${id}/pause`, { method: 'POST' }); showToast(t('soul.actions.taskPaused')); pollTaskList() } catch (e: any) { showToast(t('soul.actions.pauseFailed', { error: e.message }), 'err') }
}
async function resumeTaskById(id: string) {
  try { await $fetch(`/api/soul/tasks/${id}/resume`, { method: 'POST' }); showToast(t('soul.actions.taskResumed')); pollTaskList() } catch (e: any) { showToast(t('soul.actions.resumeFailed', { error: e.message }), 'err') }
}
function focusTask(t: any) {
  // 定位到对应 SOUL 并打开其训练监控
  const kbId = t.meta?.soul_kb_id
  const soul = souls.value.find((x: any) => x.kb_id === kbId || x.name === kbId)
  if (soul) {
    selectSoul(soul)
    taskCenterOpen.value = false
    // 若正是自己的训练任务, 绑定监控
    if (trainTaskId.value !== t.task_id && (t.kind || '').startsWith('soul_')) {
      trainTaskId.value = t.task_id
      trainTaskStatus.value = t.status === 'paused' ? 'paused' : 'running'
      trainProgress.value = t.progress || null
      pollTrainTask(t.task_id)
    }
    showToast(t('soul.taskCenter.located', { name: soul.name }))
  }
}

// ── CRUD ──
function openCreate() {
  form.value = { soul_name: '', kb_scope: [], domain_labels: [], supported_task_types: [], harness: '', allKb: true, personality_req: '', source_material: '', files: [], create_mode: 'template', skill_md: '', seedFiles: [], person_name: '' }
  createOpen.value = true
}

/** 三模式说明(女娲=人物深研 / dot-skill=材料蒸馏 / 补天=双通道集成) */
const modeDesc = computed(() => {
  const key = `soul.create.modeDesc${form.value.create_mode.charAt(0).toUpperCase() + form.value.create_mode.slice(1)}` as any
  return (t as any)(key)
})
async function doCreate() {
  if (!form.value.soul_name.trim()) { message.warning(t('soul.create.nameRequired')); return }
  creating.value = true
  try {
    const kbName = form.value.soul_name.startsWith('soul-') ? form.value.soul_name : `soul-${form.value.soul_name}`
    const kbScope = form.value.allKb ? ['*'] : (form.value.kb_scope || [])

    // ═══ 女娲模式: 人物深研蒸馏 ═══
    // 路径 A: 粘贴 nuwa-skill 深研产物 SKILL.md → 服务端转种子包 → ragctl 落地
    // 路径 B: 输入人名/主题 → LLM 蒸馏(网络深研需在 harness 中 Skill("butian")→Skill("nuwa-skill"))
    if (form.value.create_mode === 'nuwa') {
      if (form.value.skill_md?.trim()) {
        const r = await $fetch<any>('/api/soul/distill-nuwa', {
          method: 'POST',
          body: { name: kbName, skill_md: form.value.skill_md, kb_scope: kbScope, domain_labels: form.value.domain_labels, harness: form.value.harness || '' },
        })
        if (r?.success) {
          showToast(t('soul.create.nuwaSuccess', { name: kbName }), 'ok')
          createOpen.value = false
          await loadAll()
        } else {
          showToast(t('soul.create.importFailed', { detail: r?.error || JSON.stringify(r).slice(0, 160) }), 'err')
        }
        return
      }
      const person = form.value.person_name?.trim()
      if (!person) { message.warning(t('soul.create.nuwaPersonRequired')); return }
      const req = t('soul.create.nuwaReqTemplate', { person })
      const r = await $fetch<any>('/api/soul/distill', {
        method: 'POST',
        body: {
          name: kbName, kb_scope: kbScope,
          domain_labels: form.value.domain_labels,
          supported_task_types: form.value.supported_task_types,
          harness: form.value.harness || '',
          personality_req: req,
          source_material: form.value.source_material || '',
          async_mode: true,
        },
      })
      if (r?.task_id) {
        trainTaskId.value = r.task_id
        trainTaskStatus.value = 'running'
        trainProgress.value = { phase: 'distill', msg: t('soul.actions.eventDistillRunning') }
        eventLog.value = []
        pushLog('info', t('soul.actions.eventSubmitDistillSimple', { name: kbName }))
        pollTrainTask(r.task_id)
        showToast(t('soul.create.distillSubmitted', { name: kbName }))
        createOpen.value = false
        await loadAll()
      } else {
        showToast(t('soul.create.distillSubmitFailed', { detail: JSON.stringify(r).slice(0, 160) }), 'err')
      }
      return
    }

    // ═══ dot-skill 模式: 材料蒸馏(文件/文本/种子包) ═══
    if (form.value.create_mode === 'dot') {
      if (form.value.seedFiles.length) {
        const fd = new FormData()
        fd.append('name', kbName)
        fd.append('kb_scope', kbScope.join(','))
        fd.append('domain_labels', (form.value.domain_labels || []).join(','))
        fd.append('harness', form.value.harness || '')
        for (const f of form.value.seedFiles) fd.append('files', f.file, f.name)
        const r = await $fetch<any>('/api/soul/distill-seed', { method: 'POST', body: fd })
        if (r?.success) {
          showToast(t('soul.create.seedSuccess', { name: kbName }), 'ok')
          createOpen.value = false
          await loadAll()
        } else {
          showToast(t('soul.create.importFailed', { detail: r?.error || JSON.stringify(r).slice(0, 160) }), 'err')
        }
        return
      }
      if (form.value.files.length) {
        const fd = new FormData()
        fd.append('name', kbName)
        fd.append('kb_scope', kbScope.join(','))
        fd.append('domain_labels', (form.value.domain_labels || []).join(','))
        fd.append('supported_task_types', (form.value.supported_task_types || []).join(','))
        fd.append('harness', form.value.harness || '')
        fd.append('personality_req', '')
        for (const f of form.value.files) fd.append('files', f.file, f.name)
        const r = await $fetch<any>('/api/soul/distill-files', { method: 'POST', body: fd })
        if (r?.task_id) {
          trainTaskId.value = r.task_id
          trainTaskStatus.value = 'running'
          trainProgress.value = { phase: 'parse_files', msg: t('soul.actions.eventDistillParse') }
          eventLog.value = []
          pushLog('info', t('soul.actions.eventSubmitDistill', { n: form.value.files.length, name: kbName }))
          pollTrainTask(r.task_id)
          showToast(t('soul.create.distillFileSubmitted', { name: kbName }))
          createOpen.value = false
          await loadAll()
        } else {
          showToast(t('soul.create.distillSubmitFailed', { detail: JSON.stringify(r).slice(0, 160) }), 'err')
        }
        return
      }
      if (form.value.source_material?.trim()) {
        const r = await $fetch<any>('/api/soul/distill', {
          method: 'POST',
          body: {
            name: kbName, kb_scope: kbScope,
            domain_labels: form.value.domain_labels,
            supported_task_types: form.value.supported_task_types,
            harness: form.value.harness || '',
            personality_req: form.value.personality_req || '',
            source_material: form.value.source_material,
            async_mode: true,
          },
        })
        if (r?.task_id) {
          trainTaskId.value = r.task_id
          trainTaskStatus.value = 'running'
          trainProgress.value = { phase: 'distill', msg: t('soul.actions.eventDistillRunning') }
          eventLog.value = []
          pushLog('info', t('soul.actions.eventSubmitDistillSimple', { name: kbName }))
          pollTrainTask(r.task_id)
          showToast(t('soul.create.distillSubmitted', { name: kbName }))
          createOpen.value = false
          await loadAll()
        } else {
          showToast(t('soul.create.distillSubmitFailed', { detail: JSON.stringify(r).slice(0, 160) }), 'err')
        }
        return
      }
      message.warning(t('soul.create.dotRequired'))
      return
    }

    // ═══ 补天·智能集成模式: 人物需求 + 材料(文本/文件) 双通道 ═══
    if (form.value.create_mode === 'butian') {
      const hasMaterial = !!(form.value.files.length || form.value.source_material?.trim())
      const person = form.value.person_name?.trim()
      if (!hasMaterial && !person) { message.warning(t('soul.create.butianRequired')); return }
      const req = [form.value.personality_req?.trim(), person ? t('soul.create.nuwaReqTemplate', { person }) : ''].filter(Boolean).join('; ')
      if (form.value.files.length) {
        const fd = new FormData()
        fd.append('name', kbName)
        fd.append('kb_scope', kbScope.join(','))
        fd.append('domain_labels', (form.value.domain_labels || []).join(','))
        fd.append('supported_task_types', (form.value.supported_task_types || []).join(','))
        fd.append('harness', form.value.harness || '')
        fd.append('personality_req', req)
        for (const f of form.value.files) fd.append('files', f.file, f.name)
        const r = await $fetch<any>('/api/soul/distill-files', { method: 'POST', body: fd })
        if (r?.task_id) {
          trainTaskId.value = r.task_id
          trainTaskStatus.value = 'running'
          trainProgress.value = { phase: 'parse_files', msg: t('soul.actions.eventDistillParse') }
          eventLog.value = []
          pushLog('info', t('soul.actions.eventSubmitDistill', { n: form.value.files.length, name: kbName }))
          pollTrainTask(r.task_id)
          showToast(t('soul.create.distillFileSubmitted', { name: kbName }))
          createOpen.value = false
          await loadAll()
        } else {
          showToast(t('soul.create.distillSubmitFailed', { detail: JSON.stringify(r).slice(0, 160) }), 'err')
        }
        return
      }
      const r = await $fetch<any>('/api/soul/distill', {
        method: 'POST',
        body: {
          name: kbName, kb_scope: kbScope,
          domain_labels: form.value.domain_labels,
          supported_task_types: form.value.supported_task_types,
          harness: form.value.harness || '',
          personality_req: req,
          source_material: form.value.source_material || '',
          async_mode: true,
        },
      })
      if (r?.task_id) {
        trainTaskId.value = r.task_id
        trainTaskStatus.value = 'running'
        trainProgress.value = { phase: 'distill', msg: t('soul.actions.eventDistillRunning') }
        eventLog.value = []
        pushLog('info', t('soul.actions.eventSubmitDistillSimple', { name: kbName }))
        pollTrainTask(r.task_id)
        showToast(t('soul.create.distillSubmitted', { name: kbName }))
        createOpen.value = false
        await loadAll()
      } else {
        showToast(t('soul.create.distillSubmitFailed', { detail: JSON.stringify(r).slice(0, 160) }), 'err')
      }
      return
    }
    // ═══ 模板初始化(唯一剩余模式) ═══
    const r = await $fetch<any>('/api/soul/init', {
      method: 'POST',
      body: {
        name: kbName,
        description: `SOUL Persona ${kbName}`,
        kb_scope: kbScope,
        domain_labels: form.value.domain_labels,
        supported_task_types: form.value.supported_task_types,
        harness: form.value.harness || '',
      },
    })
    const docsOk = (r?.docs_created || []).filter((d: any) => d.ok).length
    if (docsOk < 4) {
      showToast(t('soul.create.createPartial', { n: docsOk }), 'err')
    } else {
      showToast(t('soul.create.createSuccess', { name: kbName }))
    }
    createOpen.value = false
    await loadAll()
  } catch (e: any) {
    showToast(t('soul.create.createFailed', { error: e.message }), 'err')
  } finally {
    creating.value = false
  }
}


const distillFileInput = ref<any>(null)
const seedFileInput = ref<any>(null)
function onSeedFilesPick(e: any) {
  const picked = [...(e.target?.files || [])]
  const known = ['meta.json', 'persona.md', 'work.md', 'values.md']
  for (const f of picked) {
    if (known.includes(f.name)) {
      form.value.seedFiles.push({ name: f.name, size: f.size, file: f })
    } else {
      message.warning(t('soul.create.seedSkip', { name: f.name }))
    }
  }
  if (e.target) e.target.value = ''
}
function onSeedFilesDrop(e: any) {
  const picked = [...(e.dataTransfer?.files || [])]
  const known = ['meta.json', 'persona.md', 'work.md', 'values.md']
  for (const f of picked) {
    if (known.includes(f.name)) {
      form.value.seedFiles.push({ name: f.name, size: f.size, file: f })
    } else {
      message.warning(t('soul.create.seedSkip', { name: f.name }))
    }
  }
}
function onDistillFilesPick(e: any) {
  const picked = [...(e.target?.files || [])]
  for (const f of picked) {
    if (!form.value.files.some(x => x.name === f.name && x.size === f.size)) {
      form.value.files.push({ name: f.name, size: f.size, file: f })
    }
  }
  e.target.value = ''
}
function onDistillFilesDrop(e: any) {
  const dropped = [...(e.dataTransfer?.files || [])]
  for (const f of dropped) {
    if (!form.value.files.some(x => x.name === f.name && x.size === f.size)) {
      form.value.files.push({ name: f.name, size: f.size, file: f })
    }
  }
}

// ── 任务暂停/继续 ──
const selectedTaskStatus = computed(() => trainTaskStatus.value)
async function pauseTask() {
  if (!trainTaskId.value) return
  try {
    const r = await $fetch<any>(`/api/soul/tasks/${trainTaskId.value}/pause`, { method: 'POST' })
    trainTaskStatus.value = 'paused'
    pushLog('info', t('soul.actions.taskPausedDetail'))
    showToast(t('soul.actions.taskPaused'))
  } catch (e: any) { showToast(t('soul.actions.pauseFailed', { error: e.message }), 'err') }
}
async function resumeTask() {
  if (!trainTaskId.value) return
  try {
    const r = await $fetch<any>(`/api/soul/tasks/${trainTaskId.value}/resume`, { method: 'POST' })
    trainTaskStatus.value = 'running'
    pushLog('ok', t('soul.actions.eventTaskResumed'))
    showToast(t('soul.actions.taskResumed'))
  } catch (e: any) { showToast(t('soul.actions.resumeFailed', { error: e.message }), 'err') }
}

// ── 训练历史(SQLite) ──
const trainingHistory = ref<any[]>([])
const historyOpen = ref(false)
const historyEvents = ref<any[]>([])
const historyRun = ref<any>(null)
async function loadTrainingHistory(soul?: Soul) {
  try {
    const res = await $fetch<any>(`/api/soul/training/history?soul_kb_id=${encodeURIComponent(soul?.kb_id || selected.value?.kb_id || '')}&limit=20`)
    trainingHistory.value = res?.runs || []
  } catch { trainingHistory.value = [] }
}
async function openHistory(run?: any) {
  historyOpen.value = true
  if (run) {
    historyRun.value = run
    try {
      const res = await $fetch<any>(`/api/soul/training/runs/${run.id}`)
      historyEvents.value = res?.events || []
    } catch { historyEvents.value = [] }
  } else {
    historyRun.value = null
    historyEvents.value = []
  }
}
function openEdit(soul: Soul) {
  editing.value = soul
  const med = soul.meditation || {}
  editForm.value = {
    kb_scope: soul.kb_scope || [],
    domain_labels: soul.domain_labels || [],
    supported_task_types: soul.supported_task_types || [],
    route_weight: soul.route_weight ?? 1,
    harness: med.harness || 'omp',
    model: med.model || '',
    autoTrainEnabled: !!med.enabled && med.meditation_mode === 'soul',
    intervalHours: med.interval_hours || 24,
    roundsPerRun: med.rounds_per_run || 1,
    maxBudgetUsd: med.max_budget_usd || 0.15,
    maxQuestions: med.max_questions_per_run || 10,
  }
  editOpen.value = true
}
async function doSaveConfig() {
  if (!editing.value) return
  savingConfig.value = true
  try {
    await $fetch('/api/soul/config', { method: 'PUT', body: { soul_kb_id: editing.value.kb_id, ...editForm.value } })
    await $fetch('/api/kb/meditation', { method: 'PUT', body: {
      kb_id: editing.value.kb_id,
      config: {
        harness: editForm.value.harness,
        model: editForm.value.model,
        enabled: editForm.value.autoTrainEnabled,
        meditation_mode: 'soul',
        interval_hours: editForm.value.intervalHours,
        rounds_per_run: editForm.value.roundsPerRun,
        max_budget_usd: editForm.value.maxBudgetUsd,
        max_questions_per_run: editForm.value.maxQuestions,
      },
    } })
    editOpen.value = false
    showToast(t('soul.config.saved'))
    await loadAll()
  } catch (e: any) {
    showToast(t('soul.config.saveFailed', { error: e.message }), 'err')
  } finally {
    savingConfig.value = false
  }
}
function confirmDelete(soul: Soul) {
  Modal.confirm({
    title: t('soul.actions.deleteConfirmTitle', { name: soul.name }),
    content: t('soul.actions.deleteConfirmContent'),
    okType: 'danger',
    onOk: async () => {
      try {
        await $fetch('/api/soul/delete', { method: 'DELETE', body: { soul_kb_id: soul.kb_id } })
        showToast(t('soul.actions.deleted', { name: soul.name }))
        if (selected.value?.kb_id === soul.kb_id) selected.value = null
        await loadAll()
      } catch (e: any) { showToast(t('soul.actions.deleteFailed', { error: e.message }), 'err') }
    },
  })
}

// ── 训练(统一 RL) ──
function openTrain(soul: Soul) {
  trainingSoul.value = soul
  trainMode.value = 'rl'
  trainForm.value = { doc_paths: [], limit: 6, dry_run: false, rounds: 2, maxDocs: 10 }
  trainResult.value = ''
  preSearchChunks.value = []
  latestScores.value = null
}
async function doTrain() {
  if (!trainingSoul.value) return
  training.value = true
  trainResult.value = ''
  trainTaskId.value = ''
  trainTaskStatus.value = 'running'
  trainProgress.value = null
  trainError.value = ''
  eventLog.value = []
  latestScores.value = null
  pushLog('info', t('soul.actions.eventTrainSubmit', { mode: ' RL 统一', name: trainingSoul.value.name }))
  clearInterval(trainPollTimer)
  try {
    const res: any = await $fetch<any>('/api/soul/train-rl', {
      method: 'POST',
      body: { soul_kb_id: trainingSoul.value.kb_id, rounds: trainForm.value.rounds || 1 },
    })
    const taskId = res?.task_id
    if (taskId) {
      trainTaskId.value = taskId
      pushLog('ok', t('soul.actions.eventTaskSubmitted', { id: taskId.slice(0, 8) }))
      pollTrainTask(taskId)
    } else {
      trainResult.value = JSON.stringify(res?.report || res, null, 2)
      training.value = false
      trainTaskStatus.value = ''
      showToast(t('soul.actions.trainComplete'))
      await loadAll()
    }
  } catch (e: any) {
    trainResult.value = t('soul.actions.trainFailed') + `: ${e.message}`
    trainTaskStatus.value = 'error'
    pushLog('err', t('soul.actions.trainSubmitFailed', { error: e.message }))
    showToast(t('soul.actions.trainFailed'), 'err')
    training.value = false
  }
}

function pollTrainTask(taskId: string) {
  let lastEventCount = 0
  let lastProgressSig = ''
  clearInterval(trainPollTimer)
  trainPollTimer = setInterval(async () => {
    try {
      const st: any = await $fetch(`/api/soul/tasks/${taskId}`)
      trainTaskStatus.value = st.status
      const p = st.progress || null
      trainProgress.value = p
      trainError.value = st.error || ''

      // 详细事件流(从 task record 的 events buffer 渲染)
      const events: any[] = st.events || []
      if (events.length > lastEventCount) {
        const newEvents = events.slice(lastEventCount)
        lastEventCount = events.length
        for (const ev of newEvents) {
          renderRlEvent(ev)
        }
      }

      // 进度变化摘要(补充事件流)
      const sig = JSON.stringify(p)
      if (p && sig !== lastProgressSig) {
        lastProgressSig = sig
        updateLatestScores(p)
      }

      if (st.status === 'done') {
        clearInterval(trainPollTimer)
        const rep = st.result?.report || st.result
        trainResult.value = JSON.stringify(rep, null, 2)
        trainTaskStatus.value = 'done'
        training.value = false
        pushLog('ok', t('soul.actions.eventTrainComplete'))
        showToast(t('soul.actions.trainComplete'))
        await loadAll()
        if (selected.value) { loadRewardHistory(selected.value); loadPersonaDocs(selected.value) }
      } else if (st.status === 'error') {
        clearInterval(trainPollTimer)
        trainResult.value = t('soul.actions.trainFailed') + `: ${st.error || 'unknown'}`
        trainTaskStatus.value = 'error'
        training.value = false
        pushLog('err', t('soul.actions.eventTrainError', { error: st.error || 'unknown' }))
        showToast(t('soul.actions.trainFailed'), 'err')
      }
    } catch { /* poll failure is non-fatal */ }
  }, 3000)
}

// ── RL 事件渲染 + 辅助函数 ──
const latestScores = ref<any>(null)
const scoreDims = [
  { key: 'identity', i18n: 'dimIdentity' },
  { key: 'values', i18n: 'dimValues' },
  { key: 'thinking', i18n: 'dimThinking' },
  { key: 'language', i18n: 'dimLanguage' },
  { key: 'knowledge', i18n: 'dimKnowledge' },
  { key: 'coherence', i18n: 'dimCoherence' },
]

function renderRlEvent(ev: any) {
  const phase = ev.phase || 'info'
  const type = ev.type || 'info'
  const d = ev.data || {}
  const round = ev.round ? `R${ev.round} ` : ''

  if (type === 'actor_done') {
    pushLog('actor', `<b>${round}🎯 ${t('soul.train.actorPanel')}</b><br>` +
      `${t('soul.train.phaseQuestions', { n: d.questions ?? 0 })} · ` +
      `${t('soul.train.phaseMemories', { n: d.memories ?? 0 })} · ` +
      `文档 ${d.docs_processed ?? 0}` +
      (d.learn_error ? ` <span class="err">${d.learn_error}</span>` : ''))
  } else if (type === 'critic_score') {
    const scores: any = {}
    for (const dim of scoreDims) scores[dim.key] = d[dim.key] ?? 0
    latestScores.value = { ...scores, overall: d.overall ?? 0 }
    const dimsStr = scoreDims.map(dim => `${t('soul.train.' + dim.i18n)}: ${fmtNum(scores[dim.key])}`).join(' · ')
    pushLog('critic', `<b>${round}📊 ${t('soul.train.criticPanel')}</b><br>` +
      `reward <b>${fmtNum(d.overall ?? 0)}</b> · ${dimsStr}`)
  } else if (type === 'updater_done') {
    const auto = d.auto_applied ?? 0
    const pending = d.pending ?? 0
    const convBadge = d.converged ? ` · <span class="conv-tag">✅ ${t('soul.train.converged')}</span>` : ''
    pushLog('updater', `<b>${round}🔄 ${t('soul.train.updaterPanel')}</b><br>` +
      `${t('soul.train.phaseAutoApplied', { n: auto })} · ${t('soul.train.pendingBadge')} ${pending}${convBadge}`)
  } else if (type === 'questions') {
    const qList = (d.questions || []).map((q: any) => `  <i>· [${q.q_type}] ${escapeHtml(q.q_text)}</i>`).join('<br>')
    pushLog('actor', `📄 <b>${t('soul.train.eventQuestion')}</b> (${d.count}): ${escapeHtml(d.doc_path || '')}<br>${qList}`)
  } else if (type === 'answer') {
    pushLog('actor', `💬 <b>${t('soul.train.eventAnswer')}</b> [${d.q_type}]: <i>${escapeHtml(d.answer_preview)}</i>` +
      (d.evidence_count ? ` · ${t('soul.folder.hint.memories')} ${d.evidence_count}` : ''))
  } else if (type === 'eval') {
    const sc = d.scores || {}
    const grounded = sc.groundedness ?? 0
    const distilled = d.distilled ? ` · <b class="ok">✓ ${t('soul.train.eventDistilled')}</b>` : ''
    pushLog('actor', `⚖️ <b>${t('soul.train.eventEval')}</b>: 接地性 ${fmtNum(grounded)} · ` +
      `完整 ${fmtNum(sc.completeness ?? 0)} · 思维 ${fmtNum(sc.coherence ?? 0)} · 增益 ${fmtNum(sc.info_gain ?? 0)}${distilled}`)
  } else if (d.msg) {
    pushLog(phase, `<b>${round}${rlPhaseLabel(phase)}</b> ${escapeHtml(d.msg)}`)
  }

  // Phase 4.5 approve event
  if (phase === 'approve' && d.msg) {
    pushLog('ok', `<b>${round}✅ ${escapeHtml(d.msg)}</b>`)
  }
  // Phase 5 distill event
  if (phase === 'distill' && d.msg) {
    pushLog('ok', `<b>${round}📚 ${escapeHtml(d.msg)}</b>`)
  }
}

function escapeHtml(s: string): string {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
function rlPhaseLabel(phase: string): string {
  if (phase === 'actor') return t('soul.train.phaseActor')
  if (phase === 'critic') return t('soul.train.phaseCritic')
  if (phase === 'updater') return t('soul.train.phaseUpdater')
  return phase
}
function updateLatestScores(p: any) {
  if (p && p.type === 'critic_score') {
    latestScores.value = {
      identity: p.identity, values: p.values, thinking: p.thinking,
      language: p.language, knowledge: p.knowledge, coherence: p.coherence,
      overall: p.overall,
    }
  }
}
function rlPhaseIdx(phase: string): number {
  const p = trainProgress.value || {}
  if (trainTaskDone.value) return 2
  const cur = p.phase || ''
  if (cur === phase) return 1
  const order = ['actor', 'critic', 'updater', 'approve', 'distill', 'reward']
  const ci = order.indexOf(cur)
  const pi = order.indexOf(phase)
  if (pi >= 0 && ci >= 0 && ci > pi) return 2
  return 0
}
function evPhaseIcon(tone: string): string {
  if (tone === 'actor') return '🎯'
  if (tone === 'critic') return '📊'
  if (tone === 'updater') return '🔄'
  if (tone === 'reward') return '📈'
  if (tone === 'ok') return '✅'
  if (tone === 'err') return '❌'
  return '•'
}
function scoreClass(v: number): string {
  if (v >= 4) return 'good'
  if (v >= 3) return 'ok'
  return 'weak'
}

function trainPercent() {
  const p = trainProgress.value
  if (!p) return 0
  const rounds = p.rounds || 1
  let base = 0
  if (rounds > 1 && p.round) base = Math.round(((p.round - 1) / rounds) * 100)
  // phase within round: actor=0-40%, critic=40-60%, updater=60-75%, approve=75-85%, distill=85-95%, reward=95-100%
  const phaseMap: any = { actor: 0, critic: 0.4, updater: 0.6, approve: 0.75, distill: 0.85, reward: 0.95 }
  const phFrac = phaseMap[p.phase] ?? 0
  return Math.min(99, base + Math.round(phFrac * (100 / rounds)))
}

// ── 问答 ──
function openAsk(soul?: Soul) {
  askSoul.value = soul || null
  askForm.value = { query: '', task_type: '', task_goal: '', context_override: '' }
  askResult.value = null
  preSearchChunks.value = []
  askOpen.value = true
}
async function doPreSearch() {
  if (!askForm.value.query.trim()) { message.warning(t('soul.ask.enterQuestionSearch')); return }
  searchingKb.value = true
  try {
    let kbId = ''
    const scope = (askSoul.value?.kb_scope || []).filter((s: string) => s !== '*')
    if (askSoul.value && scope.length === 1) {
      const hit = kbCatalog.value.find((kb: any) => kb.kbId === scope[0] || kb.name === scope[0])
      kbId = hit?.kbId || scope[0]
    }
    const res = await $fetch<any>('/api/soul/pre-search', {
      method: 'POST',
      body: { query: askForm.value.query, kb_id: kbId, top_k: 5 },
    })
    if (res?.success && res.chunks?.length) {
      preSearchChunks.value = res.chunks
      askForm.value.context_override = res.context_override
      showToast(t('soul.ask.searchSuccess', { n: res.chunks.length }))
    } else {
      preSearchChunks.value = []
      askForm.value.context_override = ''
      showToast(t('soul.ask.searchNoResults'), 'err')
    }
  } catch (e: any) {
    showToast(t('soul.ask.searchFailed', { error: e.message }), 'err')
  } finally {
    searchingKb.value = false
  }
}
async function doQdcvrAsk() {
  if (!askForm.value.query.trim()) { message.warning(t('soul.ask.enterQuestion')); return }
  asking.value = true
  askResult.value = null
  try {
    let kbId = ''
    const scope = (askSoul.value?.kb_scope || []).filter((s: string) => s !== '*')
    if (askSoul.value && scope.length === 1) {
      const hit = kbCatalog.value.find((kb: any) => kb.kbId === scope[0] || kb.name === scope[0])
      kbId = hit?.kbId || scope[0]
    }
    const res = await $fetch<any>('/api/soul/qdcvr-ask', {
      method: 'POST',
      body: {
        query: askForm.value.query,
        soul_kb_id: askSoul.value?.kb_id || '',
        task_type: askForm.value.task_type,
        task_goal: askForm.value.task_goal,
        top_k: 5,
      },
    })
    if (res?.success === false) {
      askResult.value = { answer: `Error: ${res.error} ${res.detail || ''}` }
    } else {
      askResult.value = res
      const ev = (res as any)?.evidence_count ?? (res?.citations?.length ?? 0)
      showToast(t('soul.ask.personaAnswered', { n: ev }))
    }
  } catch (e: any) {
    askResult.value = { answer: t('soul.ask.qdcvrFailed', { error: e.message }) }
  } finally {
    asking.value = false
  }
}
async function doAsk() {
  if (!askForm.value.query.trim()) { message.warning(t('soul.ask.enterQuestion')); return }
  asking.value = true
  askResult.value = null
  try {
    const res = await $fetch<any>('/api/soul/ask', {
      method: 'POST',
      body: {
        query: askForm.value.query,
        soul_kb_id: askSoul.value?.kb_id || '',
        task_type: askForm.value.task_type,
        task_goal: askForm.value.task_goal,
        context_override: askForm.value.context_override,
      },
    })
    if (res?.success === false) {
      askResult.value = { answer: `Error: ${res.error} ${res.detail || ''}` }
    } else {
      askResult.value = res
    }
  } catch (e: any) {
    askResult.value = { answer: t('soul.ask.askFailed', { error: e.message }) }
  } finally {
    asking.value = false
  }
}

// ── 草稿审批 ──
const reviewType = ref<'memory' | 'cognition'>('memory')
async function reviewDrafts(soul: Soul, type: 'memory' | 'cognition' = 'memory') {
  reviewSoul.value = soul
  reviewType.value = type
  drafts.value = []
  reviewOpen.value = true
  try {
    const res = await $fetch<any>('/api/soul/review', {
      method: 'POST', body: { soul_kb_id: soul.kb_id, action: 'list', draft_type: type },
    })
    drafts.value = res?.drafts || []
  } catch (e: any) {
    showToast(t('soul.review.loadFailed', { error: e.message }), 'err')
  }
}
async function approveDraft(id: string) {
  try {
    await $fetch('/api/soul/review', { method: 'POST', body: { soul_kb_id: reviewSoul.value!.kb_id, action: 'approve', draft_id: id, draft_type: reviewType.value } })
    showToast(t('soul.review.approved', { id: id }))
    await reviewDrafts(reviewSoul.value!, reviewType.value)
    await loadAll()
    if (selected.value && reviewType.value === 'cognition') loadPersonaDocs(selected.value)
  } catch (e: any) { showToast(t('soul.review.approveFailed', { error: e.message }), 'err') }
}
async function approveAllDrafts() {
  if (!reviewSoul.value || !drafts.value.length) return
  const ids = drafts.value.map((d: any) => d.draft_id)
  reviewTaskId.value = ''
  reviewTaskStatus.value = 'running'
  reviewProgress.value = null
  reviewError.value = ''
  clearInterval(reviewPollTimer)
  try {
    const res: any = await $fetch('/api/soul/review', {
      method: 'POST',
      body: { soul_kb_id: reviewSoul.value.kb_id, action: 'approve', draft_ids: ids, draft_type: reviewType.value },
    })
    const taskId = res?.task_id
    if (!taskId) {
      showToast(t('soul.review.approveAllDone', { n: res?.approved?.length || 0 }))
      await reviewDrafts(reviewSoul.value!)
      await loadAll()
      reviewTaskStatus.value = ''
      if (selected.value && reviewType.value === 'cognition') loadPersonaDocs(selected.value)
      return
    }
    reviewTaskId.value = taskId
    pollReviewTask(taskId)
  } catch (e: any) {
    reviewTaskStatus.value = 'error'
    reviewError.value = e.message
    showToast(t('soul.review.approveAllFailed', { error: e.message }), 'err')
  }
}
function pollReviewTask(taskId: string) {
  clearInterval(reviewPollTimer)
  reviewPollTimer = setInterval(async () => {
    try {
      const st: any = await $fetch(`/api/soul/tasks/${taskId}`)
      reviewTaskStatus.value = st.status
      reviewProgress.value = st.progress || null
      reviewError.value = st.error || ''
      if (st.status === 'done') {
        clearInterval(reviewPollTimer)
        showToast(t('soul.review.reviewComplete', { n: st.result?.approved?.length || st.result?.results?.length || 0 }))
        await reviewDrafts(reviewSoul.value!)
        await loadAll()
        reviewTaskStatus.value = ''
        if (selected.value && reviewType.value === 'cognition') loadPersonaDocs(selected.value)
      } else if (st.status === 'error') {
        clearInterval(reviewPollTimer)
        reviewTaskStatus.value = 'error'
        reviewError.value = st.error || 'unknown'
        showToast(t('soul.review.reviewFailed', { error: st.error || 'unknown' }), 'err')
      }
    } catch { /* noop */ }
  }, 3000)
}
async function rejectDraft(id: string) {
  try {
    await $fetch('/api/soul/review', { method: 'POST', body: { soul_kb_id: reviewSoul.value!.kb_id, action: 'reject', draft_id: id, draft_type: reviewType.value } })
    showToast(t('soul.review.rejected', { id: id }))
    await reviewDrafts(reviewSoul.value!, reviewType.value)
  } catch (e: any) { showToast(t('soul.review.rejectFailed', { error: e.message }), 'err') }
}

// ── 其他动作 ──
async function doReflect(soul: Soul) {
  try {
    const res = await $fetch<any>('/api/soul/reflect', { method: 'POST', body: { soul_kb_id: soul.kb_id } })
    showToast(t('soul.actions.reflectDone', { drift: res?.drift_detected ? t('soul.actions.reflectDrift') : t('soul.actions.reflectNoDrift'), report: res?.report_path || '' }))
  } catch (e: any) { showToast(t('soul.actions.reflectFailed', { error: e.message }), 'err') }
}
async function doCheckpoint(soul: Soul) {
  try {
    const res = await $fetch<any>('/api/soul/checkpoint', { method: 'POST', body: { soul_kb_id: soul.kb_id } })
    showToast(t('soul.actions.checkpointSaved', { id: res?.checkpoint_id?.slice(0, 8) || '' }))
  } catch (e: any) { showToast(t('soul.actions.checkpointFailed', { error: e.message }), 'err') }
}
async function doExport(soul: Soul) {
  try {
    const res = await $fetch<any>('/api/soul/export', { method: 'POST', body: { soul_kb_id: soul.kb_id, min_score: 3.0 } })
    showToast(t('soul.actions.exportDone', { n: res?.record_count || 0, path: res?.export_path || '' }))
  } catch (e: any) { showToast(t('soul.actions.exportFailed', { error: e.message }), 'err') }
}

onMounted(() => {
  loadAll()
  taskListTimer = setInterval(pollTaskList, 8000)
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════════
   SOUL Persona Studio — 继承项目设计系统 (theme.css 变量)
   暖象牙学者风 · 铜金强调 · JetBrains Mono 数据 · 克制阴影
   ═══════════════════════════════════════════════════════════════ */
.soul-studio {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: 20px 24px 40px;
  max-width: 1560px;
  margin: 0 auto;
  gap: 18px;
}

/* ── 顶栏 ── */
.studio-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--kb-border);
}
.header-left { display: flex; align-items: center; gap: 14px; }
.header-mark {
  width: 42px; height: 42px; border-radius: 8px;
  background: var(--kb-bg-dark);
  color: var(--kb-gold-bright);
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--kb-border-strong);
}
.page-title { margin: 0; font-size: 21px; font-weight: 650; letter-spacing: .01em; color: var(--kb-fg); }
.page-subtitle { margin: 2px 0 0; font-size: 12.5px; color: var(--kb-fg-3); }
.header-actions { display: flex; align-items: center; gap: 10px; }
.task-live {
  font-family: 'JetBrains Mono', monospace; font-size: 12px;
  color: var(--kb-primary); display: inline-flex; align-items: center; gap: 6px;
  background: var(--kb-primary-tint); border: 1px solid var(--kb-border);
  padding: 4px 10px; border-radius: 6px;
}
.live-dot {
  width: 7px; height: 7px; border-radius: 50%; background: var(--kb-primary);
  animation: breathe 1.6s ease-in-out infinite;
}
@keyframes breathe { 0%, 100% { opacity: .35; } 50% { opacity: 1; } }

/* ── 按钮体系 ── */
.btn {
  font: inherit; font-size: 13px; cursor: pointer;
  padding: 7px 14px; border-radius: 6px;
  border: 1px solid var(--kb-border-strong);
  background: var(--kb-bg-elevated); color: var(--kb-fg);
  transition: border-color .15s, background .15s, transform .06s, box-shadow .15s;
  display: inline-flex; align-items: center; gap: 6px;
}
.btn:hover { border-color: var(--kb-primary); background: var(--kb-primary-tint); }
.btn:active { transform: translateY(1px); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-primary { background: var(--kb-bg-dark); color: var(--kb-gold-bright); border-color: var(--kb-bg-dark); }
.btn-primary:hover { background: #241f18; color: var(--kb-gold); }
.btn-copper { background: var(--kb-primary); color: #fff; border-color: var(--kb-primary); }
.btn-copper:hover { background: var(--kb-primary-hover); border-color: var(--kb-primary-hover); }
.btn-ghost { background: transparent; }
.btn-danger { color: var(--kb-primary); border-color: #d99a86; }
.btn-danger:hover { background: var(--kb-primary-soft); border-color: var(--kb-primary); }
.btn-sm { padding: 5px 11px; font-size: 12.5px; }
.btn-xs { padding: 3px 8px; font-size: 11.5px; }
.btn-glyph { font-size: 13px; line-height: 1; }

/* ── 主体布局 ── */
.studio-body {
  display: grid;
  grid-template-columns: 288px 1fr;
  gap: 18px;
  align-items: start;
}

/* ── 左 rail ── */
.persona-rail {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: 8px;
  overflow: hidden;
  position: sticky; top: 16px;
  max-height: calc(100vh - 120px);
  display: flex; flex-direction: column;
}
.rail-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 11px 14px; font-size: 12.5px; font-weight: 600;
  color: var(--kb-fg-3); letter-spacing: .04em;
  border-bottom: 1px solid var(--kb-border);
  text-transform: uppercase;
}
.rail-count {
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  background: var(--kb-gold-soft); color: var(--kb-gold-deep);
  padding: 1px 7px; border-radius: 10px;
}
.rail-loading, .rail-empty { padding: 22px 14px; font-size: 12.5px; color: var(--kb-fg-3); text-align: center; }
.rail-items { overflow-y: auto; }
.rail-item {
  padding: 11px 14px;
  border-bottom: 1px solid var(--kb-border);
  cursor: pointer;
  transition: background .15s;
  border-left: 2px solid transparent;
}
.rail-item:hover { background: var(--kb-bg-subtle); }
.rail-item.active {
  background: var(--kb-gold-soft);
  border-left-color: var(--kb-gold);
}
.rail-item-top { display: flex; align-items: center; gap: 8px; }
.state-light { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.state-light.idle { background: var(--kb-emerald); opacity: .75; }
.state-light.warn { background: var(--kb-gold); animation: breathe 2s infinite; }
.state-light.training { background: var(--kb-primary); animation: breathe 1.2s infinite; }
.rail-name { font-size: 13.5px; font-weight: 600; color: var(--kb-fg); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rail-mem { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--kb-fg-3); }
.rail-scope {
  font-size: 11.5px; color: var(--kb-fg-3); margin: 4px 0 6px 16px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.rail-meta { display: flex; gap: 5px; flex-wrap: wrap; margin-left: 16px; }
.pill {
  font-size: 10.5px; padding: 1px 7px; border-radius: 9px;
  border: 1px solid var(--kb-border);
  color: var(--kb-fg-3); background: var(--kb-bg-subtle);
}
.pill-harness { color: var(--kb-gold-deep); border-color: var(--kb-gold); }
.pill-sched { color: var(--kb-primary); border-color: var(--kb-primary); }
.pill-warn { color: var(--kb-gold-deep); background: var(--kb-gold-soft); border-color: var(--kb-gold); }
.pill-err { color: #b0442a; border-color: #d99a86; background: var(--kb-primary-soft); }

/* ── 主区 ── */
.studio-main { min-width: 0; display: flex; flex-direction: column; gap: 14px; }

/* 身份条 */
.identity-bar {
  display: flex; align-items: flex-start; gap: 16px;
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: 8px;
  padding: 16px 18px;
}
.id-avatar {
  width: 46px; height: 46px; border-radius: 8px; flex-shrink: 0;
  background: var(--kb-bg-dark);
  color: var(--kb-gold-bright);
  border: 1px solid var(--kb-border-strong);
  display: flex; align-items: center; justify-content: center;
  font-weight: 650; font-size: 16px;
}
.id-text { flex: 1; min-width: 0; }
.id-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.id-title h2 { margin: 0; font-size: 19px; font-weight: 650; }
.id-summary {
  margin: 5px 0 0; font-size: 12.5px; line-height: 1.55;
  color: var(--kb-fg-3);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.id-tags { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 8px; }
.tag-kb, .tag-dom { font-size: 11px; padding: 1px 8px; border-radius: 4px; }
.tag-kb { background: var(--kb-cyan-soft); color: var(--kb-cyan); }
.tag-dom { background: var(--kb-gold-soft); color: var(--kb-gold-deep); }
.id-actions { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.chip { font-size: 10.5px; padding: 2px 9px; border-radius: 9px; }
.chip-red { background: var(--kb-primary-soft); color: var(--kb-primary); border: 1px solid #e3b3a4; }
.chip-amber { background: var(--kb-gold-soft); color: var(--kb-gold-deep); border: 1px solid var(--kb-gold); animation: breathe 2s infinite; }

/* 监控带 */
.monitor-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 1px;
  background: var(--kb-border);
  border: 1px solid var(--kb-border);
  border-radius: 8px;
  overflow: hidden;
}
.metric-cell {
  background: var(--kb-bg-elevated);
  padding: 10px 14px;
  text-align: center;
}
.metric-val {
  display: block; font-family: 'JetBrains Mono', monospace;
  font-size: 19px; font-weight: 600; color: var(--kb-fg);
}
.metric-val.warn { color: var(--kb-primary); }
.metric-label { font-size: 10.5px; color: var(--kb-fg-3); letter-spacing: .05em; text-transform: uppercase; }
.metric-reward .metric-val { color: var(--kb-gold-deep); }

/* 工作区双栏 */
.workspace {
  display: grid;
  grid-template-columns: minmax(420px, 1.05fr) minmax(360px, .95fr);
  gap: 14px;
  align-items: start;
}
@media (max-width: 1180px) { .workspace { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .studio-body { grid-template-columns: 1fr; } .persona-rail { position: static; max-height: 280px; } }

.console {
  background: var(--kb-bg-elevated);
  border: 1px solid var(--kb-border);
  border-radius: 8px;
  overflow: hidden;
}
.console-head {
  display: flex; align-items: baseline; gap: 10px;
  padding: 11px 16px;
  border-bottom: 1px solid var(--kb-border);
}
.console-head h3 { margin: 0; font-size: 14px; font-weight: 650; }
.console-sub { font-size: 11px; color: var(--kb-fg-3); margin-left: auto; }

/* 训练触发面板 */
.train-launch { padding: 16px; display: flex; flex-direction: column; gap: 13px; }
.mode-tabs { display: flex; gap: 4px; background: var(--kb-bg-subtle); padding: 4px; border-radius: 7px; width: fit-content; }
.mode-tab {
  font: inherit; font-size: 12.5px; cursor: pointer;
  padding: 5px 14px; border-radius: 5px;
  border: none; background: transparent; color: var(--kb-fg-3);
  transition: background .15s, color .15s;
}
.mode-tab:hover { color: var(--kb-fg); }
.mode-tab.on { background: var(--kb-bg-elevated); color: var(--kb-fg); font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.mode-rl.on { color: var(--kb-primary); }
.field { display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 0; }
.field-row { display: flex; gap: 12px; }
.field-label { font-size: 11.5px; color: var(--kb-fg-3); }
.inp {
  font: inherit; font-size: 13px;
  padding: 6px 10px; border-radius: 6px;
  border: 1px solid var(--kb-border-strong);
  background: var(--kb-bg-subtle); color: var(--kb-fg);
  transition: border-color .15s;
}
.inp:focus { outline: none; border-color: var(--kb-primary); }
select.inp[multiple] { min-height: 110px; }
.check { font-size: 12.5px; color: var(--kb-fg-3); display: flex; gap: 6px; align-items: center; cursor: pointer; }
.rl-desc {
  font-size: 12.5px; line-height: 1.65; color: var(--kb-fg-3);
  margin: 0; padding: 10px 12px;
  background: var(--kb-gold-soft); border: 1px solid var(--kb-gold);
  border-radius: 6px;
}
.rl-desc b { color: var(--kb-gold-deep); }
.launch-row { display: flex; align-items: center; gap: 12px; margin-top: 2px; }
.launch-hint { font-size: 11.5px; color: var(--kb-fg-3); }

/* 训练监控 */
.train-monitor { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.phase-track { display: flex; align-items: flex-start; }
.phase { display: flex; flex-direction: column; gap: 3px; min-width: 76px; }
.phase-dot {
  width: 11px; height: 11px; border-radius: 50%;
  border: 2px solid var(--kb-border-strong);
  background: var(--kb-bg-elevated);
  transition: background .3s, border-color .3s;
}
.phase.on .phase-dot { border-color: var(--kb-primary); background: var(--kb-primary); box-shadow: 0 0 0 3px var(--kb-primary-glow); }
.phase.done .phase-dot { border-color: var(--kb-emerald); background: var(--kb-emerald); }
.phase-name { font-size: 12px; font-weight: 600; color: var(--kb-fg); }
.phase-note { font-size: 10.5px; color: var(--kb-fg-3); font-family: 'JetBrains Mono', monospace; }
.phase-conn { flex: 1; height: 2px; margin-top: 4.5px; background: var(--kb-border); transition: background .3s; }
.phase-conn.on { background: var(--kb-primary); }
.mon-line { display: flex; align-items: center; gap: 12px; }
.mon-label { font-size: 11.5px; color: var(--kb-fg-3); width: 42px; flex-shrink: 0; }
.bar { flex: 1; height: 7px; border-radius: 4px; background: var(--kb-bg-subtle); border: 1px solid var(--kb-border); overflow: hidden; }
.bar-fill {
  display: block; height: 100%; border-radius: 4px;
  background: linear-gradient(90deg, var(--kb-gold), var(--kb-primary));
  transition: width .6s ease;
  position: relative;
}
.bar-fill::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent);
  animation: shimmer 1.8s infinite;
}
@keyframes shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
.mon-pct { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--kb-fg-3); width: 40px; text-align: right; }
.mon-text { font-size: 12.5px; color: var(--kb-fg); line-height: 1.5; }
.mon-text .err { color: var(--kb-primary); }

/* RL 曲线 */
.reward-curve {
  border: 1px solid var(--kb-border);
  border-radius: 6px;
  padding: 10px 12px 6px;
  background: var(--kb-bg-subtle);
}
.curve-head { display: flex; justify-content: space-between; font-size: 11.5px; color: var(--kb-fg-3); margin-bottom: 4px; }
.curve-sub { font-family: 'JetBrains Mono', monospace; }
.curve-svg { width: 100%; height: 76px; display: block; }

/* 事件流 */
.event-log { border: 1px solid var(--kb-border); border-radius: 6px; overflow: hidden; }
.log-head {
  font-size: 11px; letter-spacing: .05em; text-transform: uppercase;
  color: var(--kb-fg-3); padding: 7px 12px;
  border-bottom: 1px solid var(--kb-border); background: var(--kb-bg-subtle);
}
.log-body { max-height: 170px; overflow-y: auto; padding: 6px 0; font-family: 'JetBrains Mono', monospace; }
.log-line { display: flex; align-items: center; gap: 8px; padding: 3px 12px; font-size: 11.5px; }
.log-time { color: var(--kb-fg-3); flex-shrink: 0; }
.log-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.log-dot.info { background: var(--kb-cyan); }
.log-dot.ok { background: var(--kb-emerald); }
.log-dot.reward { background: var(--kb-gold); }
.log-dot.err { background: var(--kb-primary); }
.log-dot.actor { background: var(--kb-cyan); }
.log-dot.critic { background: var(--kb-gold); }
.log-dot.updater { background: var(--kb-violet); }
.log-text { color: var(--kb-fg-2); }

/* ── 统一 RL 训练面板 ── */
.rl-launch { gap: 16px; }
.rl-banner { display: flex; gap: 12px; align-items: flex-start; background: var(--kb-bg-subtle); border-radius: 8px; padding: 14px; }
.rl-icon { font-size: 28px; line-height: 1; }
.rl-banner-text b { font-size: 13.5px; color: var(--kb-fg); }
.rl-banner-text p { margin: 4px 0 0; font-size: 11.5px; line-height: 1.6; color: var(--kb-fg-2); }
.rl-params { display: flex; gap: 12px; }
.btn-lg { padding: 9px 24px !important; font-size: 14px !important; }
.rl-phases .phase-dot.actor { background: var(--kb-cyan); }
.rl-phases .phase-dot.critic { background: var(--kb-gold); }
.rl-phases .phase-dot.updater { background: var(--kb-violet); }
.convergence-bar { display: flex; gap: 10px; align-items: center; font-size: 11.5px; }
.conv-badge { padding: 3px 9px; border-radius: 4px; font-weight: 600; font-size: 11px; }
.conv-badge.converged { background: var(--kb-emerald); color: white; }
.conv-badge:not(.converged) { background: var(--kb-bg-subtle); color: var(--kb-fg-3); }
.conv-round { color: var(--kb-fg-3); font-family: 'JetBrains Mono', monospace; }
.conv-auto { color: var(--kb-primary); font-weight: 600; }
.conv-tag { color: var(--kb-emerald); }

/* 六维评分 */
.rl-scores { border: 1px solid var(--kb-border); border-radius: 6px; overflow: hidden; }
.scores-head { font-size: 11px; letter-spacing: .05em; text-transform: uppercase; color: var(--kb-fg-3); padding: 7px 12px; border-bottom: 1px solid var(--kb-border); background: var(--kb-bg-subtle); }
.scores-grid { padding: 10px 12px; display: flex; flex-direction: column; gap: 7px; }
.score-item { display: flex; align-items: center; gap: 10px; }
.score-label { width: 64px; font-size: 11.5px; color: var(--kb-fg-2); flex-shrink: 0; }
.score-bar-wrap { flex: 1; height: 7px; background: var(--kb-bg-subtle); border-radius: 4px; overflow: hidden; }
.score-bar { height: 100%; border-radius: 4px; transition: width .4s; }
.score-bar.good { background: var(--kb-emerald); }
.score-bar.ok { background: var(--kb-gold); }
.score-bar.weak { background: var(--kb-primary); }
.score-val { width: 30px; text-align: right; font-size: 11.5px; font-family: 'JetBrains Mono', monospace; color: var(--kb-fg); }

/* 实时事件流 RL 样式 */
.rl-log-body { max-height: 280px !important; }
.rl-event .log-text { line-height: 1.5; }
.rl-event .log-text :deep(b) { color: var(--kb-fg); }
.rl-event .log-text :deep(i) { color: var(--kb-fg-3); }
.rl-event .log-text :deep(.err) { color: var(--kb-primary); }
.rl-event .log-text :deep(.ok) { color: var(--kb-emerald); }
.rl-event.ev-actor { border-left: 3px solid var(--kb-cyan); padding-left: 9px; }
.rl-event.ev-critic { border-left: 3px solid var(--kb-gold); padding-left: 9px; }
.rl-event.ev-updater { border-left: 3px solid var(--kb-violet); padding-left: 9px; }
.ev-icon { flex-shrink: 0; font-size: 12px; }
.log-empty { padding: 20px; text-align: center; color: var(--kb-fg-3); font-size: 11.5px; }

.train-result-box { border: 1px solid var(--kb-border); border-radius: 6px; overflow: hidden; }
.result-head2 {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 12px; font-size: 12px; font-weight: 600;
  border-bottom: 1px solid var(--kb-border); background: var(--kb-bg-subtle);
}
.result-pre {
  margin: 0; padding: 12px; font-size: 11.5px; line-height: 1.5;
  max-height: 220px; overflow: auto; white-space: pre-wrap;
  font-family: 'JetBrains Mono', monospace; color: var(--kb-fg-2);
}

/* 人格定义查看器 */
.def-console { display: flex; flex-direction: column; min-height: 460px; }
.doc-tabs { display: flex; gap: 2px; padding: 9px 12px 0; border-bottom: 1px solid var(--kb-border); overflow-x: auto; }
.doc-tab {
  font: inherit; font-size: 11.5px; cursor: pointer;
  padding: 6px 11px; border: none; background: transparent;
  color: var(--kb-fg-3); border-bottom: 2px solid transparent;
  white-space: nowrap;
}
.doc-tab:hover { color: var(--kb-fg); }
.doc-tab.on { color: var(--kb-primary); border-bottom-color: var(--kb-primary); font-weight: 600; }
.doc-body { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.doc-meta {
  display: flex; justify-content: space-between; gap: 10px;
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
  color: var(--kb-fg-3); padding: 7px 14px;
  border-bottom: 1px dashed var(--kb-border);
}
.doc-scroll { padding: 10px 14px 18px; overflow-y: auto; max-height: 520px; }
.doc-h {
  margin: 14px 0 7px; font-size: 13px; font-weight: 650; color: var(--kb-fg);
  padding-bottom: 4px; border-bottom: 1px solid var(--kb-border);
}
.doc-h:first-child { margin-top: 4px; }
.doc-bullet { display: flex; align-items: flex-start; gap: 7px; padding: 2.5px 0; font-size: 12.5px; line-height: 1.55; color: var(--kb-fg-2); }
.b-dot { width: 4px; height: 4px; border-radius: 50%; background: var(--kb-border-strong); margin-top: 7px; flex-shrink: 0; }
.doc-p { margin: 4px 0; font-size: 12.5px; line-height: 1.6; color: var(--kb-fg-2); }
.doc-bullet.evolved, .doc-p.evolved {
  background: var(--kb-gold-soft);
  border-radius: 3px;
  padding-left: 4px;
  outline: 1px solid var(--kb-gold);
}
.evolved-mark {
  font-size: 9px; font-weight: 700; letter-spacing: .05em;
  color: var(--kb-gold-deep); border: 1px solid var(--kb-gold);
  border-radius: 3px; padding: 0 3px; margin-left: 2px; flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
}
.doc-empty { padding: 30px; text-align: center; font-size: 12.5px; color: var(--kb-fg-3); }

/* ── 文件夹浏览器 ── */
.folder-tab { color: var(--kb-gold-deep); }
.folder-tab.on { color: var(--kb-primary); border-bottom-color: var(--kb-primary); }
.folder-browser {
  flex: 1; display: flex; min-height: 360px; max-height: 520px;
}
.folder-sections {
  width: 172px; flex-shrink: 0;
  border-right: 1px solid var(--kb-border);
  overflow-y: auto;
  background: var(--kb-bg-subtle);
}
.folder-section-btn {
  display: flex; align-items: center; gap: 6px; width: 100%;
  padding: 8px 10px; border: none; background: transparent;
  font: inherit; font-size: 12px; cursor: pointer;
  color: var(--kb-fg-2); text-align: left;
  border-left: 2px solid transparent;
  transition: background .15s, border-color .15s;
}
.folder-section-btn:hover { background: var(--kb-bg-elevated); }
.folder-section-btn.on {
  background: var(--kb-gold-soft);
  border-left-color: var(--kb-gold);
  color: var(--kb-fg); font-weight: 600;
}
.sec-icon { font-size: 13px; flex-shrink: 0; }
.sec-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sec-count {
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
  background: var(--kb-gold-soft); color: var(--kb-gold-deep);
  padding: 0 6px; border-radius: 8px; flex-shrink: 0;
}

.folder-content {
  flex: 1; min-width: 0; display: flex; flex-direction: column;
  overflow-y: auto; padding: 10px 14px;
}
.folder-content-head {
  display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
  padding-bottom: 8px; margin-bottom: 8px;
  border-bottom: 1px solid var(--kb-border);
}
.folder-content-head h4 { margin: 0; font-size: 13px; font-weight: 650; color: var(--kb-fg); }
.folder-content-desc { font-size: 11px; color: var(--kb-fg-3); }
.folder-item-count {
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  color: var(--kb-fg-3); margin-left: auto;
}

.folder-items { display: flex; flex-direction: column; gap: 12px; }

/* 条目头 */
.item-head {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 4px;
}
.item-name { font-size: 12px; font-weight: 600; color: var(--kb-fg); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-size {
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  color: var(--kb-fg-3); flex-shrink: 0;
}

/* 普通条目 */
.folder-item-plain {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px; background: var(--kb-bg-subtle);
  border-radius: 4px; border: 1px solid var(--kb-border);
}

/* MD 文件 */
.folder-item-md {
  border: 1px solid var(--kb-border); border-radius: 6px;
  padding: 8px 10px; background: var(--kb-bg-subtle);
}
.folder-md-scroll {
  max-height: 280px; overflow-y: auto;
  font-size: 12px; line-height: 1.55;
}
.folder-md-scroll .doc-h { font-size: 12px; margin: 8px 0 4px; }
.folder-md-scroll .doc-bullet, .folder-md-scroll .doc-p { font-size: 11.5px; }

/* 键值表 (YAML / JSON) */
.folder-item-kv {
  border: 1px solid var(--kb-border); border-radius: 6px;
  padding: 8px 10px; background: var(--kb-bg-subtle);
}
.kv-table {
  width: 100%; border-collapse: collapse; font-size: 11.5px;
  margin-top: 4px;
}
.kv-table td {
  padding: 3px 6px; border-bottom: 1px solid var(--kb-border);
  vertical-align: top;
}
.kv-key {
  font-weight: 600; color: var(--kb-gold-deep);
  white-space: nowrap; width: 1%; padding-right: 12px;
}
.kv-val {
  color: var(--kb-fg-2); word-break: break-all;
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
}
.kv-val code {
  font-family: 'JetBrains Mono', monospace;
  background: var(--kb-bg-elevated); padding: 1px 5px;
  border-radius: 3px; font-size: 10.5px;
}

/* JSONL 表格 */
.folder-item-table {
  border: 1px solid var(--kb-border); border-radius: 6px;
  padding: 8px 10px; background: var(--kb-bg-subtle);
}
.jsonl-table-wrap {
  max-height: 260px; overflow: auto; margin-top: 4px;
}
.jsonl-table {
  width: 100%; border-collapse: collapse; font-size: 10.5px;
  font-family: 'JetBrains Mono', monospace;
}
.jsonl-table th {
  text-align: left; padding: 4px 6px;
  background: var(--kb-bg-elevated); color: var(--kb-fg-3);
  font-weight: 600; white-space: nowrap;
  border-bottom: 2px solid var(--kb-border);
  position: sticky; top: 0; z-index: 1;
}
.jsonl-table td {
  padding: 2px 6px; border-bottom: 1px solid var(--kb-border);
  color: var(--kb-fg-2); max-width: 180px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.jsonl-table td code {
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
}

/* 记忆卡片 */
.mem-card {
  border: 1px solid var(--kb-gold); border-radius: 6px;
  padding: 10px 12px; background: var(--kb-gold-soft);
  margin-top: 6px;
}
.mem-card-q {
  font-size: 12.5px; font-weight: 600; color: var(--kb-fg);
  margin-bottom: 7px; line-height: 1.5;
}
.mem-card-scores { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 7px; }
.mem-score {
  font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
  background: var(--kb-bg-elevated); padding: 2px 7px;
  border-radius: 4px; border: 1px solid var(--kb-border);
  color: var(--kb-fg-2);
}
.mem-score b { color: var(--kb-gold-deep); font-weight: 600; }
.mem-card-meta { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 6px; }
.mem-chip {
  font-family: 'JetBrains Mono', monospace; font-size: 9.5px;
  padding: 1px 7px; border-radius: 8px;
  background: var(--kb-bg-elevated); border: 1px solid var(--kb-border);
  color: var(--kb-fg-3);
}
.mem-chip.approved { color: var(--kb-emerald); border-color: var(--kb-emerald); }
.mem-chip.pending { color: var(--kb-gold-deep); border-color: var(--kb-gold); }
.mem-chip.stale { color: var(--kb-primary); }
.mem-card-body { margin-top: 4px; }
.mem-card-body summary {
  font-size: 11px; color: var(--kb-fg-3); cursor: pointer;
}
.mem-answer {
  margin-top: 6px; font-size: 11.5px; line-height: 1.6;
  color: var(--kb-fg-2); white-space: pre-wrap;
}

/* 空分区 */
.folder-empty-section {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 6px;
  text-align: center; padding: 30px 20px;
}
.empty-section-icon { font-size: 36px; opacity: .6; }
.empty-section-title { margin: 0; font-size: 14px; font-weight: 600; color: var(--kb-fg); }
.empty-section-desc { margin: 0; font-size: 11.5px; color: var(--kb-fg-3); max-width: 300px; line-height: 1.5; }
.empty-section-hint {
  margin-top: 8px; font-size: 11px; color: var(--kb-fg-3);
  background: var(--kb-bg-subtle); border: 1px dashed var(--kb-border-strong);
  border-radius: 6px; padding: 8px 12px; max-width: 380px; line-height: 1.6;
}

/* 空态 */
.studio-empty {
  min-height: 420px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px;
  border: 1px dashed var(--kb-border-strong); border-radius: 8px;
  background: var(--kb-bg-elevated);
  text-align: center; padding: 40px;
}
.empty-symbol { color: var(--kb-gold); opacity: .75; }
.empty-title { margin: 6px 0 0; font-size: 16px; font-weight: 600; color: var(--kb-fg); }
.empty-desc { margin: 4px 0 0; font-size: 12.5px; color: var(--kb-fg-3); max-width: 420px; line-height: 1.6; }

/* Toast */
.soul-toast {
  position: fixed; bottom: 26px; right: 26px; z-index: 9999;
  padding: 11px 16px; border-radius: 7px; font-size: 13px;
  display: flex; align-items: center; gap: 12px; max-width: 440px;
  box-shadow: 0 6px 22px rgba(42, 31, 21, .22);
  border: 1px solid;
}
.soul-toast.ok { background: var(--kb-emerald-soft); border-color: var(--kb-emerald); color: #2c4a2c; }
.soul-toast.err { background: var(--kb-primary-soft); border-color: var(--kb-primary); color: var(--kb-primary); }
.toast-close { border: none; background: none; font-size: 15px; cursor: pointer; opacity: .6; color: inherit; }
.toast-fade-enter-active, .toast-fade-leave-active { transition: opacity .25s, transform .25s; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translateY(8px); }

/* 复用旧类(模态内) */
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.ask-target { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.ask-target-label { font-size: 13px; color: var(--kb-fg-3); }
.ask-route-hint { font-size: 12.5px; color: var(--kb-gold-deep); background: var(--kb-gold-soft); padding: 2px 9px; border-radius: 9px; }
.ask-hint { font-size: 12px; color: var(--kb-fg-3); margin-left: 8px; }
.ask-row { display: flex; gap: 12px; }
.ask-row .ant-form-item { flex: 1; }
.ask-result { margin-top: 16px; border-top: 1px solid var(--kb-border); padding-top: 12px; }
.result-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.result-label { font-weight: 600; }
.answer-text {
  white-space: pre-wrap; font-size: 13px; line-height: 1.7;
  background: var(--kb-bg-subtle); border: 1px solid var(--kb-border);
  border-radius: 6px; padding: 12px;
  max-height: 320px; overflow-y: auto;
}
.cite-list { margin-top: 10px; }
.cite-title { font-size: 12px; color: var(--kb-fg-3); margin-bottom: 6px; }
.cite-item { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; padding: 3px 0; }
.cite-path { color: var(--kb-fg-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cite-score { color: var(--kb-gold-deep); flex-shrink: 0; font-family: 'JetBrains Mono', monospace; }
.pre-search-list {
  margin-top: 8px; padding: 8px 10px;
  border: 1px dashed var(--kb-border-strong); border-radius: 6px;
  max-height: 140px; overflow-y: auto;
  background: var(--kb-bg-subtle);
}
.score-cell {
  display: inline-block; margin-right: 4px;
  background: var(--kb-emerald-soft); color: var(--kb-emerald);
  padding: 1px 5px; border-radius: 4px; font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
}
.score-cell.low { background: var(--kb-primary-soft); color: var(--kb-primary); }
.ml-4 { margin-left: 4px; }

:global([data-theme='dark']) .btn-primary { background: var(--kb-gold); color: #1a1612; }
:global([data-theme='dark']) .btn-primary:hover { background: var(--kb-gold-bright); }
:global([data-theme='dark']) .soul-toast.ok { background: #162312; border-color: #274916; color: #95de64; }
:global([data-theme='dark']) .soul-toast.err { background: #2a1215; border-color: #58181c; color: #ff7875; }

/* ── 暂停横幅 ── */
.train-paused { padding: 16px; }
.pause-banner {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  padding: 14px 16px; border-radius: 6px;
  background: var(--kb-gold-soft); border: 1px solid var(--kb-gold);
  font-size: 13px; color: var(--kb-gold-deep);
}
/* ── 训练历史 ── */
.history-layout { display: grid; grid-template-columns: 300px 1fr; gap: 14px; min-height: 380px; }
.history-list { border: 1px solid var(--kb-border); border-radius: 6px; overflow-y: auto; max-height: 480px; }
.history-item { padding: 9px 12px; border-bottom: 1px solid var(--kb-border); cursor: pointer; }
.history-item:hover { background: var(--kb-bg-subtle); }
.history-item.on { background: var(--kb-gold-soft); border-left: 2px solid var(--kb-gold); }
.h-row1 { display: flex; justify-content: space-between; align-items: center; }
.h-kind { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; }
.h-status { font-size: 10px; padding: 1px 7px; border-radius: 8px; }
.h-status.running { background: var(--kb-cyan-soft); color: var(--kb-cyan); }
.h-status.paused { background: var(--kb-gold-soft); color: var(--kb-gold-deep); }
.h-status.done { background: var(--kb-emerald-soft); color: var(--kb-emerald); }
.h-status.error { background: var(--kb-primary-soft); color: var(--kb-primary); }
.h-row2 { display: flex; gap: 10px; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: var(--kb-fg-3); margin-top: 3px; }
.h-row3 { display: flex; gap: 8px; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; margin-top: 4px; color: var(--kb-fg-2); }
.h-empty { padding: 24px; text-align: center; font-size: 12px; color: var(--kb-fg-3); }
.history-detail { border: 1px solid var(--kb-border); border-radius: 6px; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; overflow: hidden; }
.hd-head { display: flex; justify-content: space-between; align-items: center; }
.hd-title { font-size: 13px; font-weight: 650; }
.hd-status { font-size: 10.5px; padding: 1px 8px; border-radius: 8px; }
.hd-status.running { background: var(--kb-cyan-soft); color: var(--kb-cyan); }
.hd-status.paused { background: var(--kb-gold-soft); color: var(--kb-gold-deep); }
.hd-status.done { background: var(--kb-emerald-soft); color: var(--kb-emerald); }
.hd-status.error { background: var(--kb-primary-soft); color: var(--kb-primary); }
.hd-metrics { display: flex; gap: 14px; font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: var(--kb-fg-2); flex-wrap: wrap; padding: 8px 0; border-top: 1px dashed var(--kb-border); border-bottom: 1px dashed var(--kb-border); }
.hd-events { overflow-y: auto; max-height: 340px; }
.hd-event { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-family: 'JetBrains Mono', monospace; font-size: 11px; }
.hd-ev-time { color: var(--kb-fg-3); flex-shrink: 0; }
.hd-ev-phase { width: 64px; flex-shrink: 0; color: var(--kb-cyan); }
.hd-ev-payload { color: var(--kb-fg-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.distill-hint { font-size: 11.5px; color: var(--kb-fg-3); background: var(--kb-bg-subtle); border: 1px dashed var(--kb-border-strong); border-radius: 6px; padding: 8px 10px; line-height: 1.6; }
 .distill-hint b { color: var(--kb-gold-deep); }
.mode-desc {
  font-size: 12px; color: var(--kb-fg-2); background: var(--kb-bg-subtle);
  border-left: 3px solid var(--kb-gold); border-radius: 0 6px 6px 0;
  padding: 6px 10px; margin: -4px 0 10px; line-height: 1.6;
}
.file-drop {
  border: 1.5px dashed var(--kb-border-strong); border-radius: 6px;
  padding: 12px; cursor: pointer; text-align: center;
  background: var(--kb-bg-subtle); transition: border-color .15s;
}
.file-drop:hover { border-color: var(--kb-gold); }
.fd-main { display: block; font-size: 13px; color: var(--kb-ink); }
.fd-sub { display: block; font-size: 11px; color: var(--kb-fg-3); margin-top: 3px; }
.fd-item { display: flex; align-items: center; gap: 10px; padding: 5px 8px; border-radius: 4px; background: var(--kb-bg-elevated); border: 1px solid var(--kb-border); margin-bottom: 5px; text-align: left; }
.fd-name { font-size: 12px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fd-size { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: var(--kb-fg-3); }
.fd-rm { color: var(--kb-primary); cursor: pointer; font-size: 14px; }
@media (max-width: 720px) { .history-layout { grid-template-columns: 1fr; } }
.task-live { cursor: pointer; }
.task-live:hover { border-color: var(--kb-primary); }
.task-live-arrow { font-size: 10px; }
.task-center { display: flex; flex-direction: column; gap: 10px; max-height: 480px; overflow-y: auto; }
.tc-item { border: 1px solid var(--kb-border); border-radius: 6px; padding: 10px 12px; background: var(--kb-bg-elevated); }
.tc-head { display: flex; align-items: center; gap: 10px; }
.tc-pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--kb-primary); animation: breathe 1.2s infinite; flex-shrink: 0; }
.tc-soul { font-size: 13px; font-weight: 650; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tc-kind { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: var(--kb-fg-3); background: var(--kb-bg-subtle); border: 1px solid var(--kb-border); padding: 1px 7px; border-radius: 8px; }
.tc-elapsed { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--kb-fg-3); }
.tc-phase { display: flex; gap: 10px; align-items: baseline; margin-top: 7px; font-size: 12px; }
.tc-phase-name { font-weight: 600; color: var(--kb-gold-deep); flex-shrink: 0; }
.tc-phase-detail { color: var(--kb-fg-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tc-bar { height: 6px; border-radius: 3px; background: var(--kb-bg-subtle); border: 1px solid var(--kb-border); overflow: hidden; margin-top: 7px; }
.tc-bar .bar-fill { display: block; height: 100%; background: linear-gradient(90deg, var(--kb-gold), var(--kb-primary)); border-radius: 3px; }
.tc-history-hint { text-align: center; font-size: 12px; color: var(--kb-gold-deep); cursor: pointer; padding: 6px; border: 1px dashed var(--kb-border-strong); border-radius: 6px; }
.tc-history-hint:hover { background: var(--kb-gold-soft); }

</style>
