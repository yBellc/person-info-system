<template>
  <div class="page-container">
    <div class="section-title">智能表格</div>

    <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px"
      title="上传 Word/PDF/Excel 文档 → 系统智能识别为在线表格 → 自动填充已有信息 → 下发给成员填写 → 自动收集汇总" />

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- ===== 我的表格 ===== -->
      <el-tab-pane label="我创建的表格" name="my-forms">
        <el-card>
          <div class="toolbar">
            <span class="card-title">我的表格</span>
            <el-button type="primary" @click="openUpload"><el-icon :icon="Upload" />上传文档识别</el-button>
            <el-button type="success" @click="openAICreate"><el-icon :icon="MagicStick" />AI 智能创建</el-button>
            <el-button @click="loadForms"><el-icon :icon="Refresh" />刷新</el-button>
          </div>
          <el-table :data="forms" v-loading="loadingForms" border stripe style="margin-top: 16px">
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="title" label="表格标题" min-width="180" />
            <el-table-column label="来源" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ row.source_type || '手动' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="字段数" width="80" align="center">
              <template #default="{ row }">{{ row.fields?.length || 0 }}</template>
            </el-table-column>
            <el-table-column label="自动填充" width="80" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.fields?.some(f => f.auto_fill_key)" type="success" size="small">有</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="下发次数" width="80" align="center">
              <template #default="{ row }">{{ row.distributions || 0 }}</template>
            </el-table-column>
            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">{{ row.created_at }}</template>
            </el-table-column>
            <el-table-column label="操作" width="260" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="success" @click="openDistribute(row)">下发</el-button>
                <el-button size="small" @click="viewDistributions(row)">收集结果</el-button>
                <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ===== 待我填写 ===== -->
      <el-tab-pane label="待我填写" name="my-tasks">
        <el-card>
          <div class="toolbar">
            <span class="card-title">待填写的表格</span>
            <el-button @click="loadMyTasks"><el-icon :icon="Refresh" />刷新</el-button>
          </div>
          <el-table :data="myTasks" v-loading="loadingTasks" border stripe style="margin-top: 16px">
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="form_title" label="表格标题" min-width="180" />
            <el-table-column prop="distribution_title" label="任务标题" min-width="150" />
            <el-table-column prop="distributor" label="下发人" width="100" />
            <el-table-column label="截止时间" width="160">
              <template #default="{ row }">
                <span :style="{ color: isOverdue(row.deadline) ? '#f56c6c' : '' }">{{ row.deadline || '无限制' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'pending'" type="info" size="small">待填写</el-tag>
                <el-tag v-else-if="row.status === 'submitted'" type="success" size="small">已提交</el-tag>
                <el-tag v-else-if="row.status === 'returned'" type="warning" size="small">已退回</el-tag>
                <el-tag v-else type="info" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="300" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status === 'pending' || row.status === 'returned'"
                  size="small" type="primary" @click="openFillForm(row)">
                  {{ row.status === 'returned' ? '重新填写' : '填写' }}
                </el-button>
                <el-tooltip v-if="row.status === 'submitted' && !row.has_source_file"
                  content="该表单无原始模板，无法下载" placement="top">
                  <el-button size="small" type="success" disabled>下载原模板</el-button>
                </el-tooltip>
                <el-button v-if="row.status === 'submitted' && row.has_source_file"
                  size="small" type="success" @click="downloadTaskOriginal(row)">下载原模板</el-button>
                <el-button v-if="row.status === 'submitted'"
                  size="small" @click="viewSubmittedForm(row)">查看填写</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loadingTasks && myTasks.length === 0" description="暂无填写任务" />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- ===== 上传识别对话框 ===== -->
    <el-dialog v-model="uploadVisible" title="上传文档并智能识别" width="950px" top="5vh" :close-on-click-modal="false" @closed="resetUpload">
      <el-alert type="warning" :closable="false" show-icon style="margin-bottom: 12px"
        title="支持 Word(.docx)、PDF(.pdf)、Excel(.xlsx/.xls) 文档，系统会自动识别文档中的表单字段并匹配系统已有数据。" />

      <!-- 步骤1：上传 -->
      <div class="step-block">
        <div class="step-title">① 选择文档并上传识别</div>
        <el-upload ref="uploadRef" :auto-upload="false" :limit="1" accept=".docx,.pdf,.xlsx,.xls"
          :on-change="onFileChange" :on-exceed="() => ElMessage.warning('一次只能上传一个文件')"
          :on-remove="onFileRemove" :file-list="fileList" drag>
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">将文档拖到此处，或<em>点击上传</em></div>
        </el-upload>
        <div style="margin-top: 12px">
          <el-button type="primary" :loading="recognizing" :disabled="!selectedFile" @click="doRecognize">
            <el-icon :icon="MagicStick" />上传并智能识别
          </el-button>
        </div>
      </div>

      <!-- 步骤2：识别结果 + 手动标注 -->
      <div v-if="recognizedFields.length" class="step-block">
        <div class="step-title">② 确认/修改字段配置
          <span class="step-tip-inline">自动识别 + 手动标注</span>
        </div>

        <!-- 标注操作指南 -->
        <div class="annotate-guide">
          <div class="guide-title">📌 标注操作指南：</div>
          <div class="guide-items">
            <div class="guide-item"><span class="legend-dot annotatable"></span>蓝色虚线 = 空白单元格，点击可创建字段</div>
            <div class="guide-item"><span class="legend-dot placeholder"></span>橙色虚线 = 含占位符文本的单元格，点击可创建字段</div>
            <div class="guide-item"><span class="legend-dot editable"></span>绿色实线 = 已标注的字段，点击可删除</div>
            <div class="guide-item"><span class="legend-dot label"></span>红色 = 字段标签单元格（如"姓名"），点击可自动标注右侧/下方为填写区域</div>
          </div>
        </div>

        <div class="annotate-layout">
          <!-- 左侧：字段列表 -->
          <div class="annotate-left">
            <div class="annotate-toolbar">
              <el-button size="small" type="primary" plain @click="addField"><el-icon :icon="Plus" />添加字段</el-button>
              <el-button size="small" @click="clearAllFields" :disabled="!recognizedFields.length">清空全部</el-button>
              <span class="field-count">共 {{ recognizedFields.length }} 个字段</span>
              <span class="field-origin-count">
                自动识别: {{ recognizedFields.filter(f => !f.source_cell_path).length }} |
                手动标注: {{ recognizedFields.filter(f => f.source_cell_path).length }}
              </span>
            </div>
            <el-table :data="recognizedFields" border stripe size="small" max-height="500">
              <el-table-column label="来源" width="70" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.source_cell_path" type="success" size="small">手动</el-tag>
                  <el-tag v-else type="info" size="small">自动</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="字段名" min-width="120">
                <template #default="{ row }">
                  <el-input v-model="row.field_label" size="small" placeholder="字段名称" />
                </template>
              </el-table-column>
              <el-table-column label="类型" width="100">
                <template #default="{ row }">
                  <el-select v-model="row.field_type" size="small" style="width: 90px">
                    <el-option label="文本" value="text" />
                    <el-option label="数字" value="number" />
                    <el-option label="日期" value="date" />
                    <el-option label="多行" value="textarea" />
                    <el-option label="单选" value="radio" />
                    <el-option label="下拉" value="select" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="自动填充" width="140">
                <template #default="{ row }">
                  <el-select v-model="row.auto_fill_key" size="small" clearable filterable placeholder="不自动填充" style="width: 130px">
                    <el-option label="不自动填充" value="" />
                    <el-option-group v-for="group in systemFieldGroups" :key="group.label" :label="group.label">
                      <el-option v-for="f in group.fields" :key="f.key" :label="f.label" :value="f.key" />
                    </el-option-group>
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="绑定位置" width="80" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.source_cell_path" type="success" size="small" effect="dark">已绑定</el-tag>
                  <el-tag v-else type="warning" size="small" effect="plain">未绑定</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="必填" width="50" align="center">
                <template #default="{ row }">
                  <el-checkbox v-model="row.is_required" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="50" align="center" fixed="right">
                <template #default="{ $index }">
                  <el-button size="small" type="danger" link @click="removeField($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 右侧：文档预览（标注模式） -->
          <div class="annotate-right">
            <DocPreview
              ref="annotatePreviewRef"
              :form-id="tempFormId"
              :form-type="recognizedMeta?.source_type || ''"
              mode="annotate"
              :fields="recognizedFields"
              @update:fields="(fields) => { recognizedFields = fields }"
              @annotate="onFieldAnnotated"
            />
          </div>
        </div>
      </div>

      <!-- 步骤3：保存 -->
      <div v-if="recognizedFields.length" class="step-block">
        <div class="step-title">③ 设置标题并保存</div>
        <el-form label-width="100px" style="margin-top: 8px">
          <el-form-item label="表格标题" required>
            <el-input v-model="formTitle" placeholder="如：2026年度人员信息采集表" style="width: 400px" />
          </el-form-item>
          <el-form-item label="表格说明">
            <el-input v-model="formDescription" type="textarea" :rows="2" placeholder="可选" style="width: 400px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveForm"><el-icon :icon="Check" />保存表格</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-dialog>

    <!-- ===== 下发对话框 ===== -->
    <el-dialog v-model="distributeVisible" title="下发表格" width="600px">
      <el-form label-width="100px">
        <el-form-item label="表格">
          <span style="font-weight: 600">{{ distributingForm?.title }}</span>
        </el-form-item>
        <el-form-item label="任务标题" required>
          <el-input v-model="distTitle" placeholder="如：请填写2026年度信息采集表" style="width: 100%" />
        </el-form-item>
        <el-form-item label="任务说明">
          <el-input v-model="distDescription" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker v-model="distDeadline" type="datetime" placeholder="选择截止时间" style="width: 100%"
            value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="下发范围" required>
          <el-radio-group v-model="targetType">
            <el-radio-button label="all">全部成员</el-radio-button>
            <el-radio-button label="department">按部门</el-radio-button>
            <el-radio-button label="individual">按个人</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="targetType === 'department'" label="选择部门">
          <el-select v-model="targetIds" multiple filterable placeholder="选择部门" style="width: 100%">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="targetType === 'individual'" label="选择成员">
          <el-select v-model="targetIds" multiple filterable placeholder="输入用户名搜索" style="width: 100%"
            :filterable="true" remote :remote-method="searchUsers" :loading="false">
            <el-option v-for="u in userOptions" :key="u.id"
              :label="u.name ? `${u.name}（${u.username}）${u.department ? '-' + u.department : ''}` : u.username"
              :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="distributeVisible = false">取消</el-button>
        <el-button type="primary" :loading="distributing" @click="doDistribute">确认下发</el-button>
      </template>
    </el-dialog>

    <!-- ===== 收集结果对话框 ===== -->
    <el-dialog v-model="responsesVisible" title="收集结果" width="95%" top="3vh">
      <div v-if="currentForm" style="margin-bottom: 12px">
        <span style="font-size: 16px; font-weight: 600">{{ currentForm.title }}</span>
      </div>
      <el-table :data="distributions" border stripe size="small" style="margin-bottom: 16px">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="title" label="任务标题" min-width="150" />
        <el-table-column label="下发数" width="80" align="center">
          <template #default="{ row }">{{ row.total_count }}</template>
        </el-table-column>
        <el-table-column label="已提交" width="80" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.submitted_count === row.total_count ? '#67c23a' : '#e6a23c', fontWeight: 600 }">
              {{ row.submitted_count }}/{{ row.total_count }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="截止时间" width="160">
          <template #default="{ row }">{{ row.deadline || '无限制' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'closed' ? 'info' : 'success'" size="small">
              {{ row.status === 'closed' ? '已关闭' : '收集中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewResponses(row)">查看详情</el-button>
            <el-button size="small" type="success" @click="exportResponses(row)">汇总Excel</el-button>
            <el-button v-if="row.has_source_file" size="small" type="primary" @click="exportOriginal(row)">按模板导出</el-button>
            <el-button v-if="row.status === 'collecting'" size="small" type="warning" @click="closeDist(row)">关闭</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 填写详情 -->
      <div v-if="responsesData">
        <div style="margin-bottom: 8px; font-weight: 600">填写详情（{{ responsesData.submitted }}/{{ responsesData.total }} 已提交）</div>
        <el-table :data="responsesData.responses" border stripe size="small" max-height="400">
          <el-table-column type="index" label="序号" width="60" align="center" />
          <el-table-column prop="person_name" label="姓名" width="100" fixed />
          <el-table-column prop="status" label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'submitted' ? 'success' : 'info'" size="small">
                {{ row.status === 'submitted' ? '已提交' : '待填写' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column v-for="f in responsesData.form?.fields || []" :key="f.field_key" :label="f.field_label" min-width="120">
            <template #default="{ row }">
              {{ row.response_data?.[f.field_key] || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="submitted_at" label="提交时间" width="160" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'submitted'" size="small" type="warning" @click="returnTask(row)">退回</el-button>
              <el-button v-if="row.status === 'submitted' && responsesData?.form?.source_file_path"
                size="small" type="primary" @click="exportTaskOriginal(row)">下载原模板</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- ===== 填写表格对话框 ===== -->
    <el-dialog v-model="fillVisible"
      :title="currentTask?.status === 'submitted' ? '已提交: ' + (currentTask?.form_title || '') :
               currentTask?.status === 'returned' ? '退回重填: ' + (currentTask?.form_title || '') :
               '填写: ' + (currentTask?.form_title || '')"
      width="900px" top="5vh" :close-on-click-modal="false">
      <el-alert v-if="currentTask?.return_note" type="warning" :closable="false" show-icon style="margin-bottom: 12px"
        :title="'退回原因: ' + currentTask.return_note" />

      <!-- 可编辑文档预览（有源文件时） -->
      <div v-if="currentForm?.source_type" style="border: 1px solid #e4e7ed; border-radius: 6px; overflow: hidden; max-height: 65vh; overflow-y: auto">
        <div style="background: #f5f7fa; padding: 8px 12px; font-weight: 600; font-size: 13px; border-bottom: 1px solid #e4e7ed; display: flex; align-items: center; gap: 6px">
          <span>📄 在原版文档上直接填写</span>
          <el-tag type="warning" size="small">点击黄色单元格编辑</el-tag>
        </div>
        <DocPreview
          ref="docPreviewRef"
          v-if="currentTask?.form_id"
          :form-id="currentTask.form_id"
          :form-type="currentForm?.source_type || ''"
          :mode="isReadOnly ? 'view' : 'fill'"
          :fields="fillFields"
          :fill-data="fillData"
          @update:fillData="(data) => fillData = data"
        />
      </div>

      <!-- 无源文件时使用传统表单 -->
      <div v-else style="max-height: 65vh; overflow-y: auto">
        <el-form v-if="fillFields.length" :model="fillData" label-width="100px" style="padding: 12px">
          <el-form-item v-for="f in fillFields" :key="f.field_key" :label="f.field_label" :required="f.is_required">
            <div style="display: flex; align-items: center; width: 100%">
              <el-input v-if="f.field_type === 'text'" v-model="fillData[f.field_key]" :placeholder="f.placeholder"
                :disabled="f.is_readonly || isReadOnly" style="flex: 1" />
              <el-input-number v-else-if="f.field_type === 'number'" v-model="fillData[f.field_key]"
                :disabled="f.is_readonly || isReadOnly" style="flex: 1" />
              <el-date-picker v-else-if="f.field_type === 'date'" v-model="fillData[f.field_key]" type="date"
                value-format="YYYY-MM-DD" :disabled="f.is_readonly || isReadOnly" style="flex: 1" />
              <el-input v-else-if="f.field_type === 'textarea'" v-model="fillData[f.field_key]" type="textarea" :rows="3"
                :disabled="f.is_readonly || isReadOnly" style="flex: 1" />
              <el-radio-group v-else-if="f.field_type === 'radio'" v-model="fillData[f.field_key]" :disabled="f.is_readonly || isReadOnly" style="flex: 1">
                <el-radio v-for="opt in (f.field_options || ['是', '否'])" :key="opt" :label="opt">{{ opt }}</el-radio>
              </el-radio-group>
              <el-select v-else-if="f.field_type === 'select'" v-model="fillData[f.field_key]" :disabled="f.is_readonly || isReadOnly"
                clearable style="flex: 1">
                <el-option v-for="opt in (f.field_options || [])" :key="opt" :label="opt" :value="opt" />
              </el-select>
              <el-input v-else v-model="fillData[f.field_key]" :placeholder="f.placeholder" :disabled="f.is_readonly || isReadOnly"
                style="flex: 1" />
              <el-tag v-if="f.auto_fill_key" type="success" size="small" style="margin-left: 8px">自动填充</el-tag>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="fillVisible = false">关闭</el-button>
        <el-button v-if="currentTask?.status === 'pending' || currentTask?.status === 'returned'"
          type="primary" :loading="submitting" @click="submitForm">
          {{ currentTask?.status === 'returned' ? '重新提交' : '提交表格' }}
        </el-button>
        <el-tag v-if="currentTask?.status === 'submitted'" type="success" style="margin-right: 12px">
          已提交 · {{ currentTask?.submitted_at }}
        </el-tag>
        <el-tag v-if="currentTask?.status === 'returned'" type="warning" style="margin-right: 12px">
          已退回：{{ currentTask?.return_note || '请修改后重新提交' }}
        </el-tag>
      </template>
    </el-dialog>

    <!-- AI 智能创建对话框 -->
    <el-dialog v-model="aiVisible" title="AI 智能创建表单" width="780px" top="5vh" :close-on-click-modal="false" @closed="resetAICreate">
      <el-alert type="success" :closable="false" show-icon style="margin-bottom: 16px"
        title="描述表单需求，系统智能识别字段并自动匹配人员档案数据，无需上传文档" />

      <!-- 步骤1：输入描述 -->
      <div class="step-block">
        <div class="step-title">① 描述表单需求</div>
        <el-input v-model="aiDescription" type="textarea" :rows="3"
          placeholder="例如：创建一份人员信息更新表，包含姓名、性别、出生日期、手机号、家庭住址" />
        <div class="ai-quick-tags">
          <span class="ai-quick-label">快速选择：</span>
          <el-tag v-for="preset in aiPresets" :key="preset.text" class="ai-quick-tag"
            @click="aiDescription = preset.text" effect="plain" type="success">
            {{ preset.label }}
          </el-tag>
        </div>
        <div style="margin-top: 12px">
          <el-button type="primary" :loading="aiRecommending" :disabled="!aiDescription.trim()" @click="doAIRecommend">
            <el-icon :icon="MagicStick" />智能识别字段
          </el-button>
        </div>
      </div>

      <!-- 步骤2：确认字段 -->
      <div v-if="aiFields.length" class="step-block">
        <div class="step-title">② 确认表单字段（共 {{ aiFields.length }} 个）</div>
        <el-table :data="aiFields" border stripe size="small" max-height="280">
          <el-table-column type="index" label="序号" width="60" align="center" />
          <el-table-column label="字段名" min-width="120">
            <template #default="{ row }">
              <el-input v-model="row.field_label" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <el-select v-model="row.field_type" size="small" style="width: 90px">
                <el-option label="文本" value="text" />
                <el-option label="数字" value="number" />
                <el-option label="日期" value="date" />
                <el-option label="多行" value="textarea" />
                <el-option label="单选" value="radio" />
                <el-option label="下拉" value="select" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="自动填充" width="140">
            <template #default="{ row }">
              <el-select v-model="row.auto_fill_key" size="small" clearable filterable placeholder="不填充" style="width: 130px">
                <el-option label="不自动填充" value="" />
                <el-option v-for="f in systemFieldList" :key="f.key" :label="f.label" :value="f.key" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="来源" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.source === 'preset'" type="success" size="small">预设</el-tag>
              <el-tag v-else-if="row.source === 'extracted'" type="warning" size="small">提取</el-tag>
              <el-tag v-else type="info" size="small">默认</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="必填" width="50" align="center">
            <template #default="{ row }">
              <el-checkbox v-model="row.is_required" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="60" align="center">
            <template #default="{ $index }">
              <el-button size="small" type="danger" link @click="aiFields.splice($index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div style="margin-top: 8px">
          <el-button size="small" @click="addFieldToAI">+ 添加字段</el-button>
        </div>
      </div>

      <!-- 步骤3：创建 -->
      <div v-if="aiFields.length" class="step-block">
        <div class="step-title">③ 设置标题并创建</div>
        <el-form label-width="100px">
          <el-form-item label="表单标题">
            <el-input v-model="aiTitle" placeholder="如：2026年度人员信息更新表" style="width: 360px" />
          </el-form-item>
          <el-form-item>
            <el-button type="success" :loading="aiCreating" @click="doAICreate">
              <el-icon :icon="Check" />一键创建表单
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Refresh, UploadFilled, MagicStick, Check, Plus } from '@element-plus/icons-vue'
import api from '@/api'
import DocPreview from '@/components/DocPreview.vue'

const activeTab = ref('my-tasks')

// ===== 我的表格 =====
const forms = ref([])
const loadingForms = ref(false)
const currentForm = ref(null)
const loadForms = async () => {
  loadingForms.value = true
  try {
    forms.value = await api.get('/smart-forms')
  } finally { loadingForms.value = false }
}

// ===== 我的任务 =====
const myTasks = ref([])
const loadingTasks = ref(false)
const loadMyTasks = async () => {
  loadingTasks.value = true
  try {
    myTasks.value = await api.get('/smart-forms/my-tasks')
  } finally { loadingTasks.value = false }
}

const onTabChange = (tab) => {
  if (tab === 'my-tasks') loadMyTasks()
  else loadForms()
}

const isOverdue = (deadline) => {
  if (!deadline) return false
  return new Date(deadline) < new Date()
}

// ===== 上传识别 =====
const uploadVisible = ref(false)
const uploadRef = ref(null)
const fileList = ref([])
const selectedFile = ref(null)
const recognizing = ref(false)
const saving = ref(false)

const recognizedFields = ref([])
const formTitle = ref('')
const formDescription = ref('')
const recognizedMeta = ref({})
const annotatePreviewRef = ref(null)
const tempFormId = ref(null)

// 系统字段分组（供自动填充下拉选择）
const systemFieldGroups = [
  { label: '基本信息', fields: [
    { key: 'name', label: '姓名' }, { key: 'gender', label: '性别' },
    { key: 'birth_date', label: '出生日期' }, { key: 'ethnicity', label: '民族' },
    { key: 'native_place', label: '现籍贯' }, { key: 'birth_place', label: '出生地' },
    { key: 'id_card', label: '身份证号' }, { key: 'political_status', label: '政治面貌' },
    { key: 'party_join_date', label: '入党时间' },
  ]},
  { label: '联系方式', fields: [
    { key: 'phone', label: '手机号' }, { key: 'office_phone', label: '办公电话' },
    { key: 'emergency_contact', label: '紧急联系人' },
  ]},
  { label: '工作信息', fields: [
    { key: 'unit_name', label: '所在单位' }, { key: 'department', label: '部门' },
    { key: 'position', label: '职务' }, { key: 'rank', label: '职级' },
    { key: 'work_start_date', label: '参加工作时间' }, { key: 'join_unit_date', label: '入职本单位时间' },
  ]},
  { label: '学历信息', fields: [
    { key: 'education_level', label: '最高学历' }, { key: 'degree', label: '学位' },
    { key: 'school', label: '毕业院校' }, { key: 'major', label: '所学专业' },
    { key: 'graduation_date', label: '毕业时间' },
  ]},
  { label: '家庭信息', fields: [
    { key: 'marital_status', label: '婚姻状况' }, { key: 'spouse_name', label: '配偶姓名' },
    { key: 'children_count', label: '子女数' }, { key: 'home_address', label: '家庭住址' },
  ]},
  { label: '派生数据', fields: [
    { key: 'age', label: '年龄' }, { key: 'work_years', label: '工龄' },
    { key: 'party_years', label: '党龄' },
  ]},
]

let fieldCounter = 0
const addField = () => {
  fieldCounter += 1
  recognizedFields.value.push({
    field_key: `field_${Date.now()}`,
    field_label: `自定义字段${fieldCounter}`,
    field_type: 'text',
    field_options: [],
    field_options_text: '',
    auto_fill_key: '',
    is_required: false,
    is_readonly: false,
    default_value: '',
    sort_order: recognizedFields.value.length,
    placeholder: '',
  })
}

const removeField = (index) => {
  recognizedFields.value.splice(index, 1)
  recognizedFields.value.forEach((f, i) => f.sort_order = i)
}

const openUpload = () => {
  resetUpload()
  uploadVisible.value = true
}

const resetUpload = () => {
  fileList.value = []
  selectedFile.value = null
  recognizedFields.value = []
  formTitle.value = ''
  formDescription.value = ''
  recognizedMeta.value = {}
  tempFormId.value = null
  uploadRef.value?.clearFiles?.()
}

const onFileChange = (file) => {
  selectedFile.value = file.raw
  fileList.value = [file]
}
const onFileRemove = () => {
  selectedFile.value = null
  fileList.value = []
}

const doRecognize = async () => {
  if (!selectedFile.value) return
  recognizing.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    const res = await api.post('/smart-forms/recognize', formData)
    recognizedFields.value = (res.fields || []).map(f => ({
      ...f,
      is_required: f.is_required ?? false,
      is_readonly: f.is_readonly ?? false,
      field_options_text: Array.isArray(f.field_options) ? f.field_options.join(',') : '',
      field_options: f.field_options || [],
    }))
    recognizedMeta.value = res
    if (res.tmp_file) {
      recognizedMeta.value.tmp_file = res.tmp_file
    }
    if (!formTitle.value) {
      formTitle.value = selectedFile.value.name.replace(/\.(docx|pdf|xlsx|xls)$/i, '')
    }
    // 立即创建一个临时表单以获取 formId，用于文档预览
    try {
      const tempForm = await api.post('/smart-forms/create', {
        title: formTitle.value + '(草稿)',
        description: '临时草稿',
        source_filename: res.source_filename || '',
        source_type: res.source_type || '',
        source_file_path: res.source_file_path || '',
        tmp_file: res.tmp_file || '',
        preview_text: res.preview || '',
        fields: [],
      })
      tempFormId.value = tempForm.id
      recognizedMeta.value.form_id = tempForm.id
    } catch (e) {
      console.error('创建临时表单失败:', e)
    }
    const autoCount = recognizedFields.value.filter(f => f.auto_fill_key).length
    ElMessage.success(`识别到 ${recognizedFields.value.length} 个字段，其中 ${autoCount} 个可自动填充`)
  } finally {
    recognizing.value = false
  }
}

const saveForm = async () => {
  if (!formTitle.value.trim()) { ElMessage.warning('请输入表格标题'); return }
  if (recognizedFields.value.length === 0) { ElMessage.warning('请先上传并识别文档'); return }
  saving.value = true
  try {
    const fields = recognizedFields.value.map(f => {
      const fieldData = {
        ...f,
        field_options: f.field_options_text
          ? f.field_options_text.split(',').map(s => s.trim()).filter(Boolean)
          : (f.field_type === 'radio' ? ['是', '否'] : []),
        field_key: f.field_key || `field_${f.sort_order + 1}`,
        auto_fill_key: f.auto_fill_key || null,
        source_cell_path: f.source_cell_path || null,
      }
      // 清理临时属性
      delete fieldData.field_options_text
      return fieldData
    })

    if (tempFormId.value) {
      // 更新已存在的临时表单
      await api.put(`/smart-forms/${tempFormId.value}`, {
        title: formTitle.value.trim(),
        description: formDescription.value,
        fields: fields,
      })
      ElMessage.success('表格保存成功')
    } else {
      await api.post('/smart-forms/create', {
        title: formTitle.value.trim(),
        description: formDescription.value,
        source_filename: recognizedMeta.value.source_filename || '',
        source_type: recognizedMeta.value.source_type || '',
        source_file_path: recognizedMeta.value.source_file_path || '',
        tmp_file: recognizedMeta.value.tmp_file || '',
        preview_text: recognizedMeta.value.preview || '',
        fields: fields,
      })
      ElMessage.success('表格创建成功')
    }
    uploadVisible.value = false
    loadForms()
  } finally {
    saving.value = false
  }
}

const clearAllFields = () => {
  if (confirm('确定要清空所有字段吗？')) {
    recognizedFields.value = []
  }
}

const onFieldAnnotated = (field) => {
  // 新增字段时的提示
  // ElMessage.success(`已添加字段: ${field.field_label}`)
}

// ===== 下发 =====
const distributeVisible = ref(false)
const distributing = ref(false)
const distributingForm = ref(null)
const distTitle = ref('')
const distDescription = ref('')
const distDeadline = ref('')
const targetType = ref('all')
const targetIds = ref([])
const departments = ref([])
const userOptions = ref([])

const openDistribute = (row) => {
  distributingForm.value = row
  distTitle.value = `请填写: ${row.title}`
  distDescription.value = ''
  distDeadline.value = ''
  targetType.value = 'all'
  targetIds.value = []
  distributeVisible.value = true
  loadDepartments()
}

const loadDepartments = async () => {
  try {
    departments.value = await api.get('/smart-forms/options/departments')
  } catch {}
}

const searchUsers = async (query) => {
  if (!query) return
  try {
    userOptions.value = await api.get('/smart-forms/options/users', { params: { q: query } })
  } catch {}
}

const doDistribute = async () => {
  if (!distTitle.value.trim()) { ElMessage.warning('请输入任务标题'); return }
  if (targetType.value !== 'all' && targetIds.value.length === 0) {
    ElMessage.warning('请选择下发目标'); return
  }
  distributing.value = true
  try {
    const res = await api.post(`/smart-forms/${distributingForm.value.id}/distribute`, {
      title: distTitle.value,
      description: distDescription.value,
      deadline: distDeadline.value || null,
      target_type: targetType.value,
      target_ids: targetIds.value,
    })
    ElMessage.success(`已下发给 ${res.total_count} 人`)
    distributeVisible.value = false
    loadForms()
  } finally {
    distributing.value = false
  }
}

// ===== 收集结果 =====
const responsesVisible = ref(false)
const distributions = ref([])
const responsesData = ref(null)
const currentDistId = ref(null)

const viewDistributions = async (row) => {
  responsesData.value = null
  currentDistId.value = null
  responsesVisible.value = true
  try {
    distributions.value = await api.get(`/smart-forms/${row.id}/distributions`)
  } catch {}
}

const viewResponses = async (dist) => {
  currentDistId.value = dist.id
  try {
    responsesData.value = await api.get(`/distributions/${dist.id}/responses`)
  } catch {}
}

const exportResponses = async (dist) => {
  try {
    const res = await api.post(`/distributions/${dist.id}/export`)
    const filename = res.filename
    const blob = await api.get(`/smart-forms/download/${filename}`, { responseType: 'blob' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = filename
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success(`已导出 ${res.total} 条记录`)
  } catch {}
}

const exportOriginal = async (dist) => {
  try {
    const res = await api.post(`/distributions/${dist.id}/export-original`)
    const filename = res.filename
    const blob = await api.get(`/smart-forms/download/${filename}`, { responseType: 'blob' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = filename
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success(`已按模板导出 ${res.total} 份文档`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '导出失败')
  }
}

const closeDist = async (dist) => {
  await ElMessageBox.confirm('确定关闭收集？关闭后成员将无法再提交。', '确认', { type: 'warning' })
  await api.post(`/distributions/${dist.id}/close`)
  ElMessage.success('已关闭收集')
  if (currentForm.value) await viewDistributions(currentForm.value)
  if (currentDistId.value) viewResponses({ id: currentDistId.value })
}

const returnTask = async (row) => {
  const { value } = await ElMessageBox.prompt('请输入退回原因', '退回重填', {
    confirmButtonText: '退回', cancelButtonText: '取消', inputType: 'textarea',
  })
  await api.post(`/smart-forms/tasks/${row.task_id}/return`, { note: value || '请修改后重新提交' })
  ElMessage.success('已退回')
  if (currentDistId.value) viewResponses({ id: currentDistId.value })
}

const exportTaskOriginal = async (row) => {
  try {
    // Step 1: Generate the filled document on server
    const res = await api.post(`/smart-forms/tasks/${row.task_id}/export-original`)
    if (!res?.filename) {
      ElMessage.error('服务器未返回有效文件')
      return
    }
    // Step 2: Download the generated file
    const blobRes = await fetch(`/api/v1/smart-forms/download/${encodeURIComponent(res.filename)}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    if (!blobRes.ok) throw new Error('下载失败')
    const blob = await blobRes.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = res.name || res.filename
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('已下载原模板文档')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e.message || '下载失败')
  }
}

const downloadTaskOriginal = async (row) => {
  await exportTaskOriginal(row)
}

const viewSubmittedForm = async (row) => {
  currentTask.value = row
  currentForm.value = forms.value.find(f => f.id === row.form_id) || { source_type: row.source_type, source_file_path: row.source_file_path }
  fillVisible.value = true
  try {
    const detail = await api.get(`/smart-forms/tasks/${row.task_id}`)
    fillFields.value = detail.fields || []
    fillData.value = {}
    for (const f of fillFields.value) {
      fillData.value[f.field_key] = f.current_value || ''
    }
  } catch {}
}

// ===== 填写表格 =====
const fillVisible = ref(false)
const currentTask = ref(null)
const fillFields = ref([])
const fillData = ref({})
const submitting = ref(false)
const docPreviewRef = ref(null)
const isReadOnly = computed(() => currentTask.value?.status === 'submitted')

const openFillForm = async (task) => {
  currentTask.value = task
  // 先尝试从创建的表单列表中查找
  currentForm.value = forms.value.find(f => f.id === task.form_id) || null
  fillVisible.value = true
  try {
    const detail = await api.get(`/smart-forms/tasks/${task.task_id}`)
    fillFields.value = detail.fields || []
    fillData.value = {}
    for (const f of fillFields.value) {
      fillData.value[f.field_key] = f.current_value || ''
    }
    // 重要：如果当前用户不是表单创建者，forms列表里找不到这个表单，必须单独调用表单详情API获取source_type
    if (!currentForm.value) {
      try {
        currentForm.value = await api.get(`/smart-forms/${task.form_id}`)
      } catch (e) {
        currentForm.value = null
      }
    }
  } catch {}
}

const submitForm = async () => {
  // 如果有可编辑文档预览，从 DOM 中获取最新填写数据
  if (docPreviewRef.value && currentForm.value?.source_type) {
    const latestData = docPreviewRef.value.getFillData()
    fillData.value = latestData
  }

  for (const f of fillFields.value) {
    if (f.is_required) {
      const val = fillData.value[f.field_key]
      if (!val || (typeof val === 'string' && !val.trim())) {
        ElMessage.warning(`必填字段「${f.field_label}」未填写`)
        return
      }
    }
  }
  submitting.value = true
  try {
    await api.post(`/smart-forms/tasks/${currentTask.value.task_id}/submit`, { response_data: fillData.value })
    ElMessage.success('提交成功')
    fillVisible.value = false
    loadMyTasks()
  } finally {
    submitting.value = false
  }
}

// ===== 删除 =====
const onDelete = (row) => {
  ElMessageBox.confirm(`确定删除表格「${row.title}」？`, '删除确认', { type: 'warning' })
    .then(async () => {
      await api.delete(`/smart-forms/${row.id}`)
      ElMessage.success('已删除')
      loadForms()
    }).catch(() => {})
}

// ===== AI 智能创建 =====
const aiVisible = ref(false)
const aiDescription = ref('')
const aiFields = ref([])
const aiTitle = ref('')
const aiRecommending = ref(false)
const aiCreating = ref(false)

const systemFieldList = [
  { key: 'name', label: '姓名' }, { key: 'gender', label: '性别' },
  { key: 'birth_date', label: '出生日期' }, { key: 'age', label: '年龄' },
  { key: 'id_card', label: '身份证号' }, { key: 'ethnicity', label: '民族' },
  { key: 'native_place', label: '籍贯' }, { key: 'political_status', label: '政治面貌' },
  { key: 'phone', label: '手机号' }, { key: 'office_phone', label: '办公电话' },
  { key: 'department', label: '部门' }, { key: 'position', label: '职务' },
  { key: 'rank', label: '职级' }, { key: 'work_start_date', label: '参加工作时间' },
  { key: 'education_level', label: '最高学历' }, { key: 'degree', label: '学位' },
  { key: 'school', label: '毕业院校' }, { key: 'major', label: '专业' },
  { key: 'home_address', label: '家庭住址' }, { key: 'emergency_contact', label: '紧急联系人' },
]

const aiPresets = [
  { label: '信息更新', text: '创建一份人员信息更新表，包含姓名、性别、出生日期、身份证号、手机号、家庭住址、紧急联系人' },
  { label: '年度考核', text: '创建一份年度考核表，包含姓名、部门、职务、本年度工作总结、下年度工作计划、自我评价' },
  { label: '请假申请', text: '创建一份请假申请表，包含姓名、部门、请假类型、开始时间、结束时间、请假事由' },
  { label: '出差申请', text: '创建一份出差申请表，包含姓名、部门、出差目的地、出差事由、开始时间、结束时间、预计费用' },
  { label: '加班申请', text: '创建一份加班申请表，包含姓名、部门、加班日期、开始时间、结束时间、加班事由' },
  { label: '培训登记', text: '创建一份培训登记表，包含姓名、部门、培训名称、培训时间、培训地点、培训内容、培训心得' },
  { label: '物资领用', text: '创建一份物资领用表，包含姓名、部门、物品名称、规格型号、领用数量、用途说明' },
  { label: '会议登记', text: '创建一份会议登记表，包含姓名、部门、会议名称、会议时间、会议地点、会议议题' },
  { label: '入党材料', text: '创建一份入党材料表，包含姓名、性别、民族、出生日期、入党时间、党籍状态、所在党支部' },
  { label: '健康申报', text: '创建一份健康申报表，包含姓名、性别、年龄、体温、健康状况、症状描述、近期行程' },
]

const openAICreate = () => {
  resetAICreate()
  aiVisible.value = true
}

const resetAICreate = () => {
  aiDescription.value = ''
  aiFields.value = []
  aiTitle.value = ''
}

const doAIRecommend = async () => {
  if (!aiDescription.value.trim()) return
  aiRecommending.value = true
  try {
    const res = await api.post('/smart-forms/ai-recommend', { description: aiDescription.value })
    aiFields.value = res?.recommended_fields || []
    aiTitle.value = res?.suggested_title || '自定义信息采集表'
    if (aiFields.value.length === 0) {
      ElMessage.warning('未识别到相关字段，请尝试更详细的描述')
    } else {
      ElMessage.success(`智能识别到 ${aiFields.value.length} 个字段`)
    }
  } finally {
    aiRecommending.value = false
  }
}

const addFieldToAI = () => {
  aiFields.value.push({
    field_label: '',
    field_type: 'text',
    auto_fill_key: '',
    is_required: false,
    source: 'manual',
  })
}

const doAICreate = async () => {
  if (aiFields.value.length === 0) {
    ElMessage.warning('请先智能识别字段')
    return
  }
  const validFields = aiFields.value.filter(f => f.field_label)
  if (validFields.length === 0) {
    ElMessage.warning('请确保至少有一个有效字段')
    return
  }
  aiCreating.value = true
  try {
    const payload = {
      title: aiTitle.value || '自定义信息采集表',
      description: aiDescription.value,
      fields: validFields.map((f, i) => ({
        field_label: f.field_label,
        field_type: f.field_type || 'text',
        field_options: f.field_options || null,
        auto_fill_key: f.auto_fill_key || null,
        is_required: f.is_required || false,
        sort_order: i,
      })),
    }
    // 直接调用 create 接口创建表单
    await api.post('/smart-forms/create', payload)
    ElMessage.success('表单创建成功！可点击"下发"分发给成员填写')
    aiVisible.value = false
    loadForms()
  } finally {
    aiCreating.value = false
  }
}

onMounted(() => {
  loadMyTasks()
  loadForms()
})
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 12px; }
.card-title { font-size: 15px; font-weight: 600; color: #303133; margin-right: 8px; }
.step-block { margin-top: 16px; padding-top: 8px; border-top: 1px dashed #ebeef5; }
.step-block:first-of-type { border-top: none; margin-top: 0; padding-top: 0; }
.step-title { font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 8px; display: flex; align-items: center; gap: 12px; }
.step-tip-inline { font-size: 12px; font-weight: normal; color: #909399; }
.step-tip { font-size: 13px; color: #909399; margin-bottom: 8px; line-height: 1.6; }

/* 标注布局样式 */
.annotate-layout {
  display: flex;
  gap: 16px;
  min-height: 500px;
}
.annotate-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.annotate-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.annotate-toolbar .field-count {
  margin-left: auto;
  color: #909399;
  font-size: 12px;
}
.annotate-toolbar .field-origin-count {
  font-size: 11px;
  color: #606266;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 10px;
}
.annotate-right {
  flex: 1.3;
  min-width: 0;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 标注操作指南 */
.annotate-guide {
  background: #f0f9ff;
  border: 1px solid #d9ecff;
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 12px;
}
.annotate-guide .guide-title {
  font-weight: 600;
  font-size: 13px;
  color: #1a73e8;
  margin-bottom: 6px;
}
.annotate-guide .guide-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}
.annotate-guide .guide-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #606266;
}
.annotate-guide .legend-dot {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  flex-shrink: 0;
}
.annotate-guide .legend-dot.annotatable {
  background: #f0f9ff;
  border: 1px dashed #91d5ff;
}
.annotate-guide .legend-dot.placeholder {
  background: #fdf6ec;
  border: 1px dashed #e6a23c;
}
.annotate-guide .legend-dot.editable {
  background: #f0f9eb;
  border: 2px solid #67c23a;
}
.annotate-guide .legend-dot.label {
  background: #fef0f0;
  border: 1px solid #f56c6c;
}
.ai-quick-tags {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.ai-quick-label {
  font-size: 13px;
  color: #909399;
  margin-right: 4px;
}
.ai-quick-tag {
  cursor: pointer;
  transition: all 0.2s;
}
.ai-quick-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(45, 90, 39, 0.15);
}
</style>
