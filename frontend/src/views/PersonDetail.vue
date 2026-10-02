<template>
  <div class="page-container" v-loading="loading">
    <el-page-header @back="$router.back()" style="margin-bottom: 16px">
      <template #content>{{ person?.name }} 的详细信息</template>
    </el-page-header>

    <template v-if="person">
      <!-- 派生信息卡片 -->
      <el-card style="margin-bottom: 16px">
        <el-descriptions :column="6" border>
          <el-descriptions-item label="姓名">{{ person.name }}</el-descriptions-item>
          <el-descriptions-item label="性别">{{ person.gender }}</el-descriptions-item>
          <el-descriptions-item label="年龄">
            <el-tag type="success">{{ person.age }} 岁</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="工龄">{{ person.work_years || '-' }} 年</el-descriptions-item>
          <el-descriptions-item label="党龄">{{ person.party_years || '-' }} 年</el-descriptions-item>
          <el-descriptions-item label="所在单位">{{ person.unit_name }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-tabs v-model="activeTab">
        <!-- 详情 -->
        <el-tab-pane label="基本信息" name="info">
          <el-descriptions :column="3" border>
            <el-descriptions-item label="出生日期">{{ person.birth_date }}</el-descriptions-item>
            <el-descriptions-item label="民族">{{ person.ethnicity }}</el-descriptions-item>
            <el-descriptions-item label="政治面貌">{{ person.political_status }}</el-descriptions-item>
            <el-descriptions-item label="现籍贯">{{ person.native_place }}</el-descriptions-item>
            <el-descriptions-item label="出生地">{{ person.birth_place }}</el-descriptions-item>
            <el-descriptions-item label="入党时间">{{ person.party_join_date }}</el-descriptions-item>
            <el-descriptions-item label="身份证号">{{ person.id_card }}</el-descriptions-item>
            <el-descriptions-item label="部门">{{ person.department }}</el-descriptions-item>
            <el-descriptions-item label="职务">{{ person.position }}</el-descriptions-item>
            <el-descriptions-item label="职级">{{ person.rank }}</el-descriptions-item>
            <el-descriptions-item label="参加工作">{{ person.work_start_date }}</el-descriptions-item>
            <el-descriptions-item label="入职本单位">{{ person.join_unit_date }}</el-descriptions-item>
            <el-descriptions-item label="最高学历">{{ person.education_level }}</el-descriptions-item>
            <el-descriptions-item label="学位">{{ person.degree }}</el-descriptions-item>
            <el-descriptions-item label="毕业院校">{{ person.school }}</el-descriptions-item>
            <el-descriptions-item label="专业">{{ person.major }}</el-descriptions-item>
            <el-descriptions-item label="毕业时间">{{ person.graduation_date }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ person.phone }}</el-descriptions-item>
            <el-descriptions-item label="办公电话">{{ person.office_phone }}</el-descriptions-item>
            <el-descriptions-item label="婚姻状况">{{ person.marital_status }}</el-descriptions-item>
            <el-descriptions-item label="配偶">{{ person.spouse_name }}</el-descriptions-item>
            <el-descriptions-item label="家庭住址" :span="3">{{ person.home_address }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <!-- 家庭成员 -->
        <el-tab-pane :label="`家庭成员 (${person.family_members?.length || 0})`" name="family">
          <el-table :data="person.family_members" border>
            <el-table-column prop="relation" label="称谓" width="80" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="birth_date" label="出生年月" width="120" />
            <el-table-column prop="political_status" label="政治面貌" width="100" />
            <el-table-column prop="work_info" label="工作单位及职务" />
            <el-table-column prop="phone" label="联系电话" width="130" />
          </el-table>
        </el-tab-pane>

        <!-- 工作经历 -->
        <el-tab-pane :label="`工作经历 (${person.work_records?.length || 0})`" name="work">
          <el-timeline>
            <el-timeline-item
              v-for="w in person.work_records"
              :key="w.id"
              :timestamp="`${w.start_date} ~ ${w.end_date || '至今'}`"
              placement="top"
            >
              <el-card>
                <h4>{{ w.unit }} · {{ w.position }}</h4>
                <p v-if="w.witness" style="color:#909399;font-size:13px">证明人：{{ w.witness }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-tab-pane>

        <!-- 变更历史 -->
        <el-tab-pane label="变更历史" name="changes">
          <el-timeline>
            <el-timeline-item
              v-for="c in changes"
              :key="c.id"
              :timestamp="formatTime(c.created_at)"
              :type="c.change_type === 'create' ? 'success' : 'primary'"
              placement="top"
            >
              <p>
                <strong>{{ c.operator_name }}</strong>
                <el-tag size="small" style="margin: 0 8px">{{ fieldLabel(c.field_key) }}</el-tag>
                <span v-if="c.change_type === 'create'">创建了该人员档案</span>
                <span v-else>
                  {{ c.old_value || '空' }} → <strong style="color:#67c23a">{{ c.new_value || '空' }}</strong>
                </span>
              </p>
              <p v-if="c.reason" style="color:#909399;font-size:13px">原因：{{ c.reason }}</p>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-if="!changes.length" description="暂无变更记录" />
        </el-tab-pane>
      </el-tabs>

      <div style="margin-top: 16px">
        <el-button type="primary" @click="editVisible = true">
          <el-icon><Edit /></el-icon>编辑信息
        </el-button>
      </div>
    </template>

    <person-form-dialog
      v-model:visible="editVisible"
      :person="person"
      :units="[]"
      @saved="onSaved"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import PersonFormDialog from '@/components/PersonFormDialog.vue'

const route = useRoute()
const person = ref(null)
const changes = ref([])
const loading = ref(false)
const activeTab = ref('info')
const editVisible = ref(false)

const FIELD_LABELS = {
  name: '姓名', gender: '性别', birth_date: '出生日期', id_card: '身份证号',
  position: '职务', rank: '职级', unit_id: '所属单位', phone: '手机号',
  education_level: '学历', native_place: '籍贯',
  __all__: '档案',
}

const fieldLabel = (key) => FIELD_LABELS[key] || key

const formatTime = (t) => {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

const loadData = async () => {
  loading.value = true
  try {
    const id = route.params.id
    person.value = await api.get(`/persons/${id}`)
    changes.value = await api.get(`/persons/${id}/changes`)
  } finally {
    loading.value = false
  }
}

const onSaved = () => {
  editVisible.value = false
  loadData()
}

onMounted(loadData)
</script>
