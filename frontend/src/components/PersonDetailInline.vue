<template>
  <div v-if="person">
    <!-- 派生信息 -->
    <el-descriptions :column="6" border style="margin-bottom: 16px">
      <el-descriptions-item label="姓名">{{ person.name }}</el-descriptions-item>
      <el-descriptions-item label="性别">{{ person.gender }}</el-descriptions-item>
      <el-descriptions-item label="年龄"><el-tag type="success">{{ person.age }} 岁</el-tag></el-descriptions-item>
      <el-descriptions-item label="工龄">{{ person.work_years || '-' }} 年</el-descriptions-item>
      <el-descriptions-item label="党龄">{{ person.party_years || '-' }} 年</el-descriptions-item>
      <el-descriptions-item label="所在单位">{{ person.unit_name }}</el-descriptions-item>
    </el-descriptions>

    <el-descriptions :column="3" border title="基本信息">
      <el-descriptions-item label="出生日期">{{ person.birth_date || '-' }}</el-descriptions-item>
      <el-descriptions-item label="民族">{{ person.ethnicity || '-' }}</el-descriptions-item>
      <el-descriptions-item label="政治面貌">{{ person.political_status || '-' }}</el-descriptions-item>
      <el-descriptions-item label="现籍贯">{{ person.native_place || '-' }}</el-descriptions-item>
      <el-descriptions-item label="出生地">{{ person.birth_place || '-' }}</el-descriptions-item>
      <el-descriptions-item label="入党时间">{{ person.party_join_date || '-' }}</el-descriptions-item>
      <el-descriptions-item label="身份证号">{{ person.id_card || '-' }}</el-descriptions-item>
      <el-descriptions-item label="部门">{{ person.department || '-' }}</el-descriptions-item>
      <el-descriptions-item label="职务">{{ person.position || '-' }}</el-descriptions-item>
      <el-descriptions-item label="职级">{{ person.rank || '-' }}</el-descriptions-item>
      <el-descriptions-item label="最高学历">{{ person.education_level || '-' }}</el-descriptions-item>
      <el-descriptions-item label="学位">{{ person.degree || '-' }}</el-descriptions-item>
      <el-descriptions-item label="手机号">{{ person.phone || '-' }}</el-descriptions-item>
      <el-descriptions-item label="婚姻状况">{{ person.marital_status || '-' }}</el-descriptions-item>
      <el-descriptions-item label="家庭住址" :span="3">{{ person.home_address || '-' }}</el-descriptions-item>
    </el-descriptions>
  </div>
</template>

<script setup>
defineProps({ person: Object })
</script>
