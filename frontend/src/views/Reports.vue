<template>
  <div class="page-container">
    <div class="section-title">统计报表</div>

    <el-card>
      <!-- 维度切换 -->
      <el-radio-group v-model="dimension" @change="onDimensionChange">
        <el-radio-button label="gender">性别</el-radio-button>
        <el-radio-button label="age">年龄</el-radio-button>
        <el-radio-button label="education">学历</el-radio-button>
        <el-radio-button label="rank">职级</el-radio-button>
        <el-radio-button label="political">政治面貌</el-radio-button>
        <el-radio-button label="unit">各单位人数</el-radio-button>
      </el-radio-group>

      <div class="chart-toolbar">
        <span class="hint">当前维度：{{ currentMeta.title }}</span>
        <el-radio-group v-model="chartType" size="small" style="margin-left: 12px">
          <el-radio-button label="bar">柱状图</el-radio-button>
          <el-radio-button label="pie">饼图</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 图表 -->
      <div v-loading="loading" class="chart-wrap">
        <v-chart v-if="data.length" class="chart" :option="chartOption" autoresize />
        <el-empty v-else-if="!loading" description="暂无数据" />
      </div>

      <!-- 数据明细 -->
      <el-table :data="data" border stripe style="margin-top: 16px">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column :label="currentMeta.colLabel" min-width="180">
          <template #default="{ row }">{{ rowLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="人数" width="120" align="center">
          <template #default="{ row }">{{ row.count }}</template>
        </el-table-column>
        <el-table-column label="占比" width="160" align="center">
          <template #default="{ row }">
            <el-progress
              :percentage="percentOf(row.count)"
              :stroke-width="14"
              :show-text="true"
            />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

use([CanvasRenderer, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const auth = useAuthStore()

const dimension = ref('gender')
const chartType = ref('bar')
const data = ref([])
const loading = ref(false)

const DIMENSIONS = {
  gender: { title: '性别分布', colLabel: '性别', url: '/statistics/by-gender', pie: true, color: '#409eff' },
  age: { title: '年龄结构', colLabel: '年龄段', url: '/statistics/by-age', pie: false, color: '#67c23a' },
  education: { title: '学历结构', colLabel: '学历', url: '/statistics/by-education', pie: false, color: '#e6a23c' },
  rank: { title: '职级分布', colLabel: '职级', url: '/statistics/by-rank', pie: false, color: '#f56c6c' },
  political: { title: '政治面貌', colLabel: '政治面貌', url: '/statistics/by-political-status', pie: true, color: '#909399' },
  unit: { title: '各单位人数', colLabel: '单位', url: '/statistics/by-unit', pie: false, color: '#9254de' },
}

const currentMeta = computed(() => DIMENSIONS[dimension.value])

const rowLabel = (row) => row.unit_name || row.label || '—'

const total = computed(() => data.value.reduce((s, d) => s + (Number(d.count) || 0), 0))

const percentOf = (count) => {
  if (!total.value) return 0
  return Math.round((count / total.value) * 1000) / 10
}

const chartOption = computed(() => {
  const labels = data.value.map((d) => rowLabel(d))
  const values = data.value.map((d) => d.count)
  const color = currentMeta.value.color

  if (chartType.value === 'pie') {
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { type: 'scroll', bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        label: { formatter: '{b}\n{d}%' },
        data: data.value.map((d) => ({ name: rowLabel(d), value: d.count })),
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      }],
    }
  }

  // 柱状图
  const useHorizontal = ['age', 'education', 'rank', 'unit'].includes(dimension.value)
  return {
    color,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: useHorizontal ? 120 : 40, right: 30, top: 30, bottom: 40, containLabel: !useHorizontal },
    ...(useHorizontal
      ? {
          xAxis: { type: 'value' },
          yAxis: { type: 'category', data: labels, inverse: true },
          series: [{ type: 'bar', data: values, barMaxWidth: 28, label: { show: true, position: 'right' } }],
        }
      : {
          xAxis: { type: 'category', data: labels },
          yAxis: { type: 'value' },
          series: [{ type: 'bar', data: values, barMaxWidth: 40, label: { show: true, position: 'top' } }],
        }),
  }
})

const loadData = async () => {
  loading.value = true
  try {
    const url = currentMeta.value.url
    const res = await api.get(url)
    data.value = Array.isArray(res) ? res : []
    // 单位维度默认切到合适图表
    if (dimension.value !== 'gender' && dimension.value !== 'political') {
      // 保留用户选择，但不强制
    }
    if ((dimension.value === 'gender' || dimension.value === 'political') && chartType.value === 'bar') {
      // 默认饼图更直观，仅首次切换维度时不强制覆盖
    }
  } catch (e) {
    data.value = []
  } finally {
    loading.value = false
  }
}

const onDimensionChange = (val) => {
  // 切换维度时若该维度更适合饼图则自动建议
  const meta = DIMENSIONS[val]
  if (meta.pie && chartType.value === 'bar') {
    chartType.value = 'pie'
  } else if (!meta.pie && chartType.value === 'pie') {
    chartType.value = 'bar'
  }
  loadData()
}

onMounted(() => {
  if (!auth.isAdmin) {
    ElMessage.warning('您暂无查看统计报表的权限')
    return
  }
  // 默认饼图适合性别维度
  chartType.value = 'pie'
  loadData()
})
</script>

<style scoped>
.chart-toolbar {
  display: flex;
  align-items: center;
  margin-top: 16px;
  margin-bottom: 8px;
}
.chart-toolbar .hint {
  color: #606266;
  font-size: 14px;
}
.chart-wrap {
  min-height: 360px;
}
.chart {
  height: 360px;
  width: 100%;
}
</style>
