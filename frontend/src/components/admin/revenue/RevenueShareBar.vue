<template>
  <div class="share-bar" :style="{ height: `${height}px` }">
    <div class="share-fill" :style="{ width: `${fillPercent}%` }">
      <div
        v-for="segment in visible"
        :key="segment.key"
        class="share-segment"
        :style="{ flexGrow: segment.value, backgroundColor: segment.color }"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  // [{ key, color, value }]
  segments: { type: Array, required: true },
  // The total that fills the whole bar. Defaults to this bar's own total.
  scale: { type: Number, default: null },
  height: { type: Number, default: 16 },
});

const visible = computed(() => props.segments.filter(s => s.value > 0));
const total = computed(() => visible.value.reduce((sum, s) => sum + s.value, 0));
const fillPercent = computed(() => {
  const scale = props.scale ?? total.value;
  return scale > 0 ? Math.min((total.value / scale) * 100, 100) : 0;
});
</script>

<style scoped>
.share-bar {
  width: 100%;
  min-width: 48px;
}

.share-fill {
  display: flex;
  gap: 2px;
  height: 100%;
  min-width: 2px;
  border-radius: 0 4px 4px 0;
  overflow: hidden;
}

.share-segment {
  flex-basis: 2px;
  min-width: 2px;
}
</style>
