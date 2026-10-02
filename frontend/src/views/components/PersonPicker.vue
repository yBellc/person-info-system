<template>
  <el-form-item :label="label" :required="required">
    <el-select
      v-model="inner"
      filterable
      remote
      reserve-keyword
      remote-show-suffix
      placeholder="搜索姓名或部门..."
      :remote-method="searchPerson"
      :loading="loading"
      style="width: 100%"
    >
      <el-option
        v-for="p in list"
        :key="p.id"
        :value="p.id"
        :label="`${p.name}（${p.department || '无部门'}）`"
      />
    </el-select>
  </el-form-item>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import api from '@/api'

const props = defineProps({
  modelValue: { type: [Number, String], default: null },
  label: { type: String, default: '人员' },
  required: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const inner = ref(props.modelValue)
const list = ref([])
const loading = ref(false)
let timer = null

watch(inner, (v) => emit('update:modelValue', v))
watch(() => props.modelValue, (v) => (inner.value = v))

const searchPerson = async (q) => {
  loading.value = true
  try {
    clearTimeout(timer)
    timer = setTimeout(async () => {
      const data = await api.get('/persons', { params: { keyword: q || '', size: 50, page: 1 } })
      list.value = (data.items || []).slice(0, 50)
      loading.value = false
    }, 200)
  } catch {
    loading.value = false
  }
}

onMounted(() => searchPerson(''))
</script>
