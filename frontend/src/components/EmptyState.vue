<template>
  <div class="empty-state" :style="{ padding: padding }">
    <el-empty :description="description" :image-size="imageSize">
      <template v-if="$slots.default" #default>
        <slot />
      </template>
    </el-empty>
  </div>
</template>

<script setup>
defineProps({
  description: { type: String, default: '暂无数据' },
  padding: { type: String, default: '40px 0' },
  imageSize: { type: Number, default: 80 },
})
</script>

<style scoped>
.empty-state {
  width: 100%;
}
</style>
