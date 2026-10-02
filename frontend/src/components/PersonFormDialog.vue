<template>
  <el-dialog
    :model-value="visible"
    :title="isEdit ? '编辑人员信息' : '新增人员'"
    width="720px"
    :close-on-click-modal="false"
    @update:model-value="(v) => emit('update:visible', v)"
    @closed="resetForm"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-tabs v-model="activeTab">
        <!-- 基本信息 -->
        <el-tab-pane label="基本信息" name="basic">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="姓名" prop="name">
                <el-input v-model="form.name" placeholder="请输入姓名" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="性别">
                <el-select v-model="form.gender" placeholder="请选择" clearable style="width:100%">
                  <el-option label="男" value="男" />
                  <el-option label="女" value="女" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="出生日期">
                <el-date-picker v-model="form.birth_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="民族">
                <el-input v-model="form.ethnicity" placeholder="如: 汉族" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="籍贯">
                <el-input v-model="form.native_place" placeholder="如: 山东省济南市" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="出生地">
                <el-input v-model="form.birth_place" placeholder="如: 山东省济南市" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="身份证号">
            <el-input v-model="form.id_card" placeholder="请输入18位身份证号" maxlength="18" show-word-limit />
          </el-form-item>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="政治面貌">
                <el-select v-model="form.political_status" placeholder="请选择" clearable style="width:100%">
                  <el-option label="中共党员" value="中共党员" />
                  <el-option label="中共预备党员" value="中共预备党员" />
                  <el-option label="共青团员" value="共青团员" />
                  <el-option label="民主党派" value="民主党派" />
                  <el-option label="群众" value="群众" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="参加党派日期">
                <el-date-picker v-model="form.party_join_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 联系方式 -->
        <el-tab-pane label="联系方式" name="contact">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="手机号码">
                <el-input v-model="form.phone" placeholder="请输入手机号" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="办公电话">
                <el-input v-model="form.office_phone" placeholder="请输入办公电话" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="紧急联系人">
            <el-input v-model="form.emergency_contact" placeholder="紧急联系人姓名及电话" />
          </el-form-item>
          <el-form-item label="家庭住址">
            <el-input v-model="form.home_address" type="textarea" :rows="2" placeholder="请输入详细地址" />
          </el-form-item>
        </el-tab-pane>

        <!-- 职务信息 -->
        <el-tab-pane label="职务信息" name="work">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="所属单位">
                <el-select v-model="form.unit_id" placeholder="请选择单位" clearable filterable style="width:100%">
                  <el-option v-for="u in units" :key="u.id" :label="u.name" :value="u.id" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="部门">
                <el-input v-model="form.department" placeholder="如: 办公室" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="岗位">
                <el-input v-model="form.position" placeholder="如: 科员" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="职级">
                <el-input v-model="form.rank" placeholder="如: 一级科员" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="参加工作日期">
                <el-date-picker v-model="form.work_start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="进入本单位日期">
                <el-date-picker v-model="form.join_unit_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 教育与家庭 -->
        <el-tab-pane label="教育/家庭" name="edu">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="学历">
                <el-select v-model="form.education_level" placeholder="请选择" clearable style="width:100%">
                  <el-option label="中专/中技" value="中专/中技" />
                  <el-option label="高中" value="高中" />
                  <el-option label="大专" value="大专" />
                  <el-option label="本科" value="本科" />
                  <el-option label="硕士研究生" value="硕士研究生" />
                  <el-option label="博士研究生" value="博士研究生" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="学位">
                <el-input v-model="form.degree" placeholder="如: 学士、硕士" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="毕业院校">
                <el-input v-model="form.school" placeholder="如: 清华大学" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="所学专业">
                <el-input v-model="form.major" placeholder="如: 计算机科学" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="毕业日期">
            <el-date-picker v-model="form.graduation_date" type="date" value-format="YYYY-MM-DD" style="width:240px" />
          </el-form-item>
          <el-divider content-position="left">家庭情况</el-divider>
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="婚姻状况">
                <el-select v-model="form.marital_status" placeholder="请选择" clearable style="width:100%">
                  <el-option label="已婚" value="已婚" />
                  <el-option label="未婚" value="未婚" />
                  <el-option label="离异" value="离异" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="配偶姓名">
                <el-input v-model="form.spouse_name" placeholder="配偶姓名" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="子女数量">
                <el-input-number v-model="form.children_count" :min="0" :max="20" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  visible: { type: Boolean, default: false },
  person: { type: Object, default: null },
  units: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:visible', 'saved'])

const formRef = ref(null)
const saving = ref(false)
const activeTab = ref('basic')

const defaultForm = () => ({
  name: '',
  gender: '',
  birth_date: null,
  ethnicity: '',
  native_place: '',
  birth_place: '',
  id_card: '',
  political_status: '',
  party_join_date: null,
  phone: '',
  office_phone: '',
  emergency_contact: '',
  unit_id: null,
  department: '',
  position: '',
  rank: '',
  work_start_date: null,
  join_unit_date: null,
  education_level: '',
  degree: '',
  school: '',
  major: '',
  graduation_date: null,
  marital_status: '',
  spouse_name: '',
  children_count: 0,
  home_address: '',
})

const form = ref(defaultForm())

const isEdit = computed(() => !!props.person?.id)

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

watch(() => props.visible, (v) => {
  if (v && props.person) {
    Object.assign(form.value, defaultForm(), props.person)
  } else if (v) {
    form.value = defaultForm()
  }
})

const resetForm = () => {
  formRef.value?.resetFields()
  form.value = defaultForm()
  activeTab.value = 'basic'
}

const onSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    activeTab.value = 'basic'
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await api.put(`/persons/${props.person.id}`, form.value)
      ElMessage.success('保存成功')
    } else {
      await api.post('/persons', form.value)
      ElMessage.success('新增成功')
    }
    emit('saved')
    visible = false
  } catch (e) {
    // 错误由拦截器处理
  } finally {
    saving.value = false
  }
}
</script>
